from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import logging
import shutil
from pathlib import Path
import glob
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Service")

# Initialize Prometheus Instrumentator
Instrumentator().instrument(app).expose(app)

# Environment Variables
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
TEMP_REPOS_DIR = "/app/temp_repos"


# --- Metrics ---
LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["type", "model", "status"]
)
LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "Duration of LLM calls in seconds",
    ["type", "model"]
)
RAG_INGESTION_TOTAL = Counter(
    "rag_ingestion_total",
    "Total number of documents ingested",
    ["type", "status"]
)
RAG_QUERY_TOTAL = Counter(
    "rag_query_total",
    "Total number of RAG queries",
    ["mode", "status"]
)

# --- Models ---
class IngestRequest(BaseModel):
    doc_id: str
    type: str # 'git', 'file', 'text'
    local_path: Optional[str] = None # For 'git' or 'file' (path relative to mount)
    text_content: Optional[str] = None # For 'text'
    tags: Optional[Dict[str, Any]] = None

# --- Context Vars for Request-Scoped Config ---
import contextvars
request_llm_config = contextvars.ContextVar("llm_config", default={})

class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid" # 'hybrid', 'vector', 'graph'
    tags: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None

# --- RAG Engine ---
# ... imports ...
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
import numpy as np
import os
import pdfplumber
from openai import OpenAI
import ollama # Native Ollama library

# ... (OpenAI client init) ...

import time

async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    # Get config from context (set per request)
    config = request_llm_config.get()
    
    llm_type = config.get("type", "public")
    api_key = config.get("apiKey")
    base_url = config.get("baseUrl")
    # Clean model name to remove unexpected whitespace
    model_name = (config.get("model") or "gpt-4o-mini").strip()

    start_time = time.time()
    status = "success"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    
    logger.info(f"LLM Call [Start]: Type={llm_type}, Model={model_name}, PromptLen={len(prompt)}")
    logger.info(f"LLM Config: {config}")

    try:
        content = ""
        if llm_type == "local":
            # Use native Ollama library
            # base_url usually needs to be just the host for ollama lib, e.g. http://host.docker.internal:11434
            # The OpenAI compatible user input might have /v1, we should strip it if present? 
            # Or just rely on user input. Standard Ollama client takes 'host'.
            
            host = base_url
            if host and "/v1" in host:
                host = host.replace("/v1", "")
            
            # Default to docker host if empty
            if not host:
                host = "http://host.docker.internal:11434"

            client = ollama.Client(host=host)
            response = client.chat(model=model_name, messages=messages)
            content = response['message']['content']
            
        elif llm_type == "public":
            key_to_use = api_key or default_api_key
            if not key_to_use:
                 logger.error("Public LLM requested but no API Key provided.")
                 status = "error_missing_key"
                 return "Error: Public LLM requires API Key."
            
            client = OpenAI(api_key=key_to_use)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                **kwargs
            )
            content = response.choices[0].message.content
            
        else:
             # Fallback
             if default_openai_client:
                response = default_openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    **kwargs
                )
                content = response.choices[0].message.content
             else:
                 return "Error: LLM Client not initialized."

        logger.info(f"LLM Call [Success]: ResponseLen={len(content)}")
        return content

    except Exception as e:
        logger.error(f"LLM Call failed ({llm_type}/{model_name}): {e}")
        status = "error_execution"
        return f"Error generating response: {e}"
        
    finally:
        duration = time.time() - start_time
        LLM_CALLS_TOTAL.labels(type=llm_type, model=model_name, status=status).inc()
        LLM_LATENCY.labels(type=llm_type, model=model_name).observe(duration)

def embedding_func(texts: list[str]) -> np.ndarray:
    config = request_llm_config.get()
    llm_type = config.get("type", "public")
    api_key = config.get("apiKey")
    base_url = config.get("baseUrl")
    
    # Embedding model is distinct from LLM model. 
    # For now we use hardcoded defaults compatible with the types.
    model_name = "text-embedding-3-small" if llm_type == "public" else "all-minilm" 
    
    try:
        embeddings = []
        if llm_type == "local":
            host = base_url
            if host and "/v1" in host:
                host = host.replace("/v1", "")
            if not host:
                host = "http://host.docker.internal:11434"
                
            client = ollama.Client(host=host)
            # Ollama embed takes list of prompts? newer versions do.
            # Fallback to loop if needed, but 'embed' or 'embeddings' usually handle batches.
            # ollama-python 'embed' method: response = client.embed(model='...', input=...)
            # Note: verify method availability. 'embeddings' is for single?
            # client.embeddings(model=..., prompt=...) returns 'embedding'.
            
            for text in texts:
                response = client.embeddings(model=model_name, prompt=text)
                embeddings.append(response['embedding'])
            return np.array(embeddings)
            
        elif llm_type == "public":
            key_to_use = api_key or default_api_key
            if not key_to_use:
                return np.zeros((len(texts), 384))
            
            client = OpenAI(api_key=key_to_use)
            response = client.embeddings.create(input=texts, model=model_name)
            return np.array([data.embedding for data in response.data])
            
        else:
             if default_openai_client:
                 response = default_openai_client.embeddings.create(input=texts, model=model_name)
                 return np.array([data.embedding for data in response.data])
             return np.zeros((len(texts), 384))

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return np.zeros((len(texts), 384))

class RAGEngine:
    def __init__(self):
        self.status = "initializing"
        self.working_dir = "/app/public_data/rag_index"
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
            
        logger.info(f"Initializing LightRAG in {self.working_dir}...")
        
        try:
            self.rag = LightRAG(
                working_dir=self.working_dir,
                llm_model_func=llm_model_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=384 if request_llm_config.get().get("type") != "public" else 1536, # Dynamic dim is hard. LightRAG might expect fixed dim.
                    max_token_size=8192,
                    func=embedding_func
                )
            )
            self.status = "ready"
            logger.info("LightRAG initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            self.status = "error"

    def ingest_file(self, file_path: str, doc_id: str, tags: Dict):
        logger.info(f"Ingesting file: {file_path} for doc: {doc_id}")
        content = ""
        try:
            if file_path.endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    content = "\n".join([page.extract_text() or "" for page in pdf.pages])
            else:
                 with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            if content:
                # We might need default config for ingestion if embedding also uses llm_model_func?
                # LightRAG separates embedding_func. We haven't overriden embedding_func, so it uses default (OpenAI).
                # If local embedding is needed, we need to override embedding_func too.
                # For now, assuming ingestion uses default Env var or default config.
                token = request_llm_config.set({"type": "public"}) # Default to public/env for ingestion for now
                try:
                    logger.info(f"Inserting content into RAG (Length: {len(content)}). This may involve LLM calls for graph extraction.")
                    self.rag.insert(content)
                    logger.info(f"Inserted content successfully.")
                finally:
                    request_llm_config.reset(token)

        except Exception as e:
            logger.error(f"Error reading/ingesting file {file_path}: {e}")

    def ingest_text(self, text: str, doc_id: str, tags: Dict):
        logger.info(f"Ingesting text for doc: {doc_id}")
        if text:
             # Default config for ingestion
             token = request_llm_config.set({"type": "public"})
             try:
                self.rag.insert(text)
             finally:
                request_llm_config.reset(token)

    def query(self, query: str, mode: str):
        if self.status != "ready":
             return "RAG Engine is not ready."
        
        logger.info(f"Querying: {query} with mode: {mode}")
        return self.rag.query(query, param=QueryParam(mode=mode))

    def delete_doc(self, doc_id: str):
        logger.info(f"Deleting doc: {doc_id} - Logic depending on LightRAG capabilities")
        # LightRAG might not support deletion by doc_id easily if not indexed with it.
        # We might need to implement custom deletion logic or rebuild index.
        pass

rag_engine = RAGEngine()

# --- Background Tasks ---
# --- Background Tasks ---
def process_ingestion(request: IngestRequest):
    logger.info(f"Starting ingestion task for DocID: {request.doc_id}, Type: {request.type}")
    try:
        rag_engine.status = "indexing" 
        if request.type == 'git':
            # request.local_path should be the repo folder name in temp_repos, e.g. "repo-uuid"
            repo_path = Path(TEMP_REPOS_DIR) / request.local_path
            
            if not repo_path.exists():
                logger.error(f"Repo path not found: {repo_path}")
                RAG_INGESTION_TOTAL.labels(type=request.type, status="error_path_not_found").inc()
                return

            md_files = list(repo_path.rglob("*.md"))
            logger.info(f"Found {len(md_files)} markdown files in {repo_path}")
            
            for md_file in md_files:
                logger.info(f"Processing file: {md_file}")
                rag_engine.ingest_file(str(md_file), request.doc_id, request.tags or {})
                
        elif request.type == 'file':
             # local_path from backend is relative to public folder, e.g. /files/abc.pdf
             # mapped to /app/public_data/files/abc.pdf
             public_data_path = Path("/app/public_data")
             # Remove leading slash if present to join correctly
             relative_path = request.local_path.lstrip('/')
             file_path = public_data_path / relative_path
             
             if not file_path.exists():
                 logger.error(f"File path not found: {file_path}")
                 RAG_INGESTION_TOTAL.labels(type=request.type, status="error_file_missing").inc()
                 return

             logger.info(f"Processing single file: {file_path}")
             rag_engine.ingest_file(str(file_path), request.doc_id, request.tags or {})

        elif request.type == 'text':
             if request.text_content:
                 logger.info(f"Processing raw text ingestion (Length: {len(request.text_content)})")
                 rag_engine.ingest_text(request.text_content, request.doc_id, request.tags or {})
        
        rag_engine.status = "ready"
        logger.info(f"Ingestion completed successfully for {request.doc_id}")
        RAG_INGESTION_TOTAL.labels(type=request.type, status="success").inc()
        
    except Exception as e:
        logger.error(f"Ingestion failed with exception: {e}", exc_info=True)
        rag_engine.status = "error"
        RAG_INGESTION_TOTAL.labels(type=request.type, status="error_exception").inc()

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/ingest")
async def ingest_document(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_ingestion, request)
    return {"status": "processing", "doc_id": request.doc_id}

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    rag_engine.delete_doc(doc_id)
    return {"status": "deleted", "doc_id": doc_id}

@app.post("/query")
async def query_rag(request: QueryRequest):
    # Set the context var for this request so llm_model_func can access it
    token = request_llm_config.set(request.llm_config or {})
    try:
        if request.mode == "direct":
            # Direct LLM call, bypassing RAG
            response = await llm_model_func(request.query)
            
            # Metric tracking
            llm_config = request.llm_config or {}
            LLM_CALLS_TOTAL.labels(
                type=llm_config.get("type", "unknown"), 
                model=llm_config.get("model", "unknown"), 
                status="success"
            ).inc()
            
            return {"response": response}

        # Map frontend modes to LightRAG modes
        rag_mode = request.mode
        if request.mode == "vector":
            rag_mode = "naive"
        elif request.mode == "graph":
            rag_mode = "global"
        elif request.mode == "hybrid":
            rag_mode = "hybrid"
            
        # Use aquery (async) instead of query (sync) to avoid event loop conflicts in FastAPI
        response = await rag_engine.rag.aquery(request.query, param=QueryParam(mode=rag_mode))
        RAG_QUERY_TOTAL.labels(mode=request.mode, status="success").inc()
        return {"response": response}
    except Exception as e:
         logger.error(f"Query Error: {e}", exc_info=True)
         RAG_QUERY_TOTAL.labels(mode=request.mode, status="error").inc()
         raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Reset context var
        request_llm_config.reset(token)
