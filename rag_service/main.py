from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import logging
import shutil
import json
from pathlib import Path
import glob
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Resilience & Networking ---
import socket
import time
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log

def wait_for_service(host: str, port: int, timeout: int = 60):
    """Waits for a TCP service to be available."""
    start_time = time.time()
    logger.info(f"Waiting for service at {host}:{port}...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                logger.info(f"Service at {host}:{port} is available.")
                return True
        except (OSError, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                logger.error(f"Timeout waiting for service at {host}:{port}")
                return False
            time.sleep(2)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables

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
status_stream = contextvars.ContextVar("status_stream", default=None)

class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid" # 'hybrid', 'vector', 'graph'
    tags: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None

# --- RAG Engine ---
# ... imports ...
# --- RAG Engine ---
# ... imports ...
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
# Storage classes will be loaded by LightRAG via string names
import numpy as np
import os
import pdfplumber
# ... (previous imports)
import asyncio
from openai import OpenAI, AsyncOpenAI # Import AsyncOpenAI
import ollama
import time

# Default API Key for public LLM
default_api_key = os.getenv("OPENAI_API_KEY")
default_openai_client = AsyncOpenAI(api_key=default_api_key) if default_api_key else None

def extract_tag_from_request(tags: Dict) -> Optional[str]:
    if not tags:
        return None
    # Use the first value or a specific key like 'project'
    return tags.get("project") or next(iter(tags.values()), None)

# ...

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

    # Push status update if stream is active - Retrieve from config
    stream_queue = config.get("stream_queue")
    if stream_queue:
        try:
            stream_queue.put_nowait({"type": "status", "content": f"Thinking... (Model: {model_name})"})
        except Exception:
            pass

    # Helper to clean kwargs for OpenAI
    openai_kwargs = {k: v for k, v in kwargs.items() if k not in ['hashing_kv', 'mode', 'enable_cot']}

    try:
        content = ""
        if llm_type == "local":
            # Use native Ollama library
            host = base_url
            if host and "/v1" in host:
                host = host.replace("/v1", "")
            
            # Default to docker host if empty
            if not host:
                host = "http://host.docker.internal:11434"

            # Ollama client is sync, wrap in thread
            client = ollama.Client(host=host)
            # Use run_in_executor to avoid blocking the event loop
            import functools
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                functools.partial(client.chat, model=model_name, messages=messages)
            )
            content = response['message']['content']
            
        elif llm_type == "public":
            key_to_use = api_key or default_api_key
            if not key_to_use:
                 logger.error("Public LLM requested but no API Key provided.")
                 status = "error_missing_key"
                 return "Error: Public LLM requires API Key."
            
            client = AsyncOpenAI(api_key=key_to_use)
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                **openai_kwargs
            )
            content = response.choices[0].message.content
            
        else:
             # Fallback
             if default_openai_client:
                response = await default_openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    **openai_kwargs
                )
                content = response.choices[0].message.content
             else:
                 return "Error: LLM Client not initialized."

        if config is not None:
             config["last_response"] = content
        
        logger.info(f"LLM Call [Success]: ResponseLen={len(content)}")
        logger.info(f"DEBUG: llm_model_func returning: {content}")
        return content

    except Exception as e:
        logger.error(f"LLM Call failed ({llm_type}/{model_name}): {e}", exc_info=True)
        status = "error_execution"
        return f"Error generating response: {e}"
        
    finally:
        duration = time.time() - start_time
        LLM_CALLS_TOTAL.labels(type=llm_type, model=model_name, status=status).inc()
        LLM_LATENCY.labels(type=llm_type, model=model_name).observe(duration)

async def embedding_func(texts: list[str]) -> np.ndarray:
    config = request_llm_config.get()
    # Default to public (OpenAI) embedding unless explicitly set to local
    # This ensures compatibility with ingested data (which defaults to public)
    # even if LLM is local.
    embedding_type = config.get("embedding_type", "public")
    
    api_key = config.get("apiKey")
    base_url = config.get("baseUrl")
    
    # Embedding model is distinct from LLM model. 
    # For now we use hardcoded defaults compatible with the types.
    if embedding_type == "public":
        model_name = "text-embedding-3-small"
    else:
        model_name = "all-minilm" 
    
    try:
        embeddings = []
        if embedding_type == "local":
            host = base_url
            if host and "/v1" in host:
                host = host.replace("/v1", "")
            if not host:
                host = "http://host.docker.internal:11434"
                
            client = ollama.Client(host=host)
            
            for text in texts:
                response = client.embeddings(model=model_name, prompt=text)
                embeddings.append(response['embedding'])
            return np.array(embeddings)
            
        elif embedding_type == "public":
            key_to_use = api_key or default_api_key
            if not key_to_use:
                return np.zeros((len(texts), 1536))
            
            client = AsyncOpenAI(api_key=key_to_use)
            response = await client.embeddings.create(input=texts, model=model_name)
            return np.array([data.embedding for data in response.data])
            
        else:
             # Fallback/Other types if needed
             if default_openai_client:
                 response = await default_openai_client.embeddings.create(input=texts, model=model_name)
                 return np.array([data.embedding for data in response.data])
             return np.zeros((len(texts), 1536))

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        # Return zero vector matching expected dimension
        dim = 1536 if embedding_type == "public" else 384
        return np.zeros((len(texts), dim))

# --- Tag Manager ---
class TagManager:
    def __init__(self, filepath="/app/public_data/tags.json"):
        self.filepath = filepath
        self.tags = {} 
        self._load_tags()

    def _load_tags(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r") as f:
                self.tags = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tags: {e}")

    def _save_tags(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.tags, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tags: {e}")

    def add_tag(self, tag: str, doc_id: str):
        if tag not in self.tags:
            self.tags[tag] = []
        if doc_id not in self.tags[tag]:
            self.tags[tag].append(doc_id)
            self._save_tags()

    def get_docs(self, tag: str) -> List[str]:
        return self.tags.get(tag, [])
    
    def remove_doc(self, tag: str, doc_id: str):
        if tag in self.tags and doc_id in self.tags[tag]:
             self.tags[tag].remove(doc_id)
             if not self.tags[tag]:
                 del self.tags[tag]
             self._save_tags()

# Initialize global TagManager
tag_manager = TagManager()

class RAGEngine:
    def __init__(self):
        self.status = "initializing"
        self.rag = None
        self.working_dir = "/app/public_data/rag_index"
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(5), before_sleep=before_sleep_log(logger, logging.INFO))
    async def initialize_lightrag(self):
        logger.info(f"Initializing LightRAG in {self.working_dir}...")
        
        # Storage Configurations
        os.environ["NEO4J_URI"] = NEO4J_URI
        os.environ["NEO4J_USERNAME"] = NEO4J_USERNAME
        os.environ["NEO4J_PASSWORD"] = NEO4J_PASSWORD
        os.environ["QDRANT_URL"] = QDRANT_URL
        
        # Initialize LightRAG with specific storage classes
        self.rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=llm_model_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536, # forced for public/OpenAI default
                max_token_size=8192,
                func=embedding_func
            ),
            # Using string names for automated loading
            graph_storage="Neo4JStorage",
            vector_storage="QdrantVectorDBStorage"
        )
        
        # Explicitly initialize storages (Async)
        logger.info(f"Initializing LightRAG storages...")
        if hasattr(self.rag, "initialize_storages"):
            await self.rag.initialize_storages()
        
        self.status = "ready"
        logger.info("LightRAG initialized successfully with Neo4j and Qdrant.")
        
        # Debug Logs
        try:
            logger.info(f"Graph Storage Instance: {type(self.rag.chunk_entity_relation_graph)}")
            logger.info(f"Vector Storage Instance: {type(self.rag.entities_vdb)}")
            logger.info(f"KV Storage Instance: {type(self.rag.full_docs)}")
            logger.info(f"Doc Status Storage Instance: {type(self.rag.doc_status)}")
        except Exception as e:
            logger.warning(f"Could not log storage types: {e}")
        
        return # Success

    async def ingest_file(self, file_path: str, doc_id: str, tags: Dict):
        if self.status != "ready" or not self.rag:
            logger.error(f"Ingestion failed: RAG Engine not ready (Status: {self.status})")
            return

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
                token = request_llm_config.set({"type": "public"}) # Default to public/env for ingestion for now
                try:
                    logger.info(f"Inserting content into RAG (Length: {len(content)}). This may involve LLM calls for graph extraction.")
                    # Using async insert to ensure compatibility with async LLM function
                    await self.rag.ainsert(content) 
                    
                    # Register tag
                    main_tag = extract_tag_from_request(tags)
                    if main_tag:
                         tag_manager.add_tag(main_tag, doc_id)
                         
                    logger.info(f"Inserted content successfully.")
                finally:
                    request_llm_config.reset(token)

        except Exception as e:
            logger.error(f"Error reading/ingesting file {file_path}: {e}")

    async def ingest_text(self, text: str, doc_id: str, tags: Dict):
        if self.status != "ready" or not self.rag:
            logger.error(f"Ingestion failed: RAG Engine not ready (Status: {self.status})")
            return
            
        logger.info(f"Ingesting text for doc: {doc_id}")
        if text:
             # Default config for ingestion
             token = request_llm_config.set({"type": "public"})
             try:
                # Using async insert
                await self.rag.ainsert(text)
                
                main_tag = extract_tag_from_request(tags)
                if main_tag:
                     tag_manager.add_tag(main_tag, doc_id)
                     
             finally:
                request_llm_config.reset(token)

    async def ingest_file(self, file_path: str, doc_id: str, tags: Dict):
        if self.status != "ready" or not self.rag:
            logger.error(f"Ingestion failed: RAG Engine not ready (Status: {self.status})")
            return

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
                token = request_llm_config.set({"type": "public"}) # Default to public/env for ingestion for now
                try:
                    logger.info(f"Inserting content into RAG (Length: {len(content)}). This may involve LLM calls for graph extraction.")
                    # Using async insert to ensure compatibility with async LLM function
                    await self.rag.ainsert(content) 
                    
                    # Register tag
                    main_tag = extract_tag_from_request(tags)
                    if main_tag:
                         tag_manager.add_tag(main_tag, doc_id)
                         
                    logger.info(f"Inserted content successfully.")
                finally:
                    request_llm_config.reset(token)

        except Exception as e:
            logger.error(f"Error reading/ingesting file {file_path}: {e}")

    async def ingest_text(self, text: str, doc_id: str, tags: Dict):
        if self.status != "ready" or not self.rag:
            logger.error(f"Ingestion failed: RAG Engine not ready (Status: {self.status})")
            return
            
        logger.info(f"Ingesting text for doc: {doc_id}")
        if text:
             # Default config for ingestion
             token = request_llm_config.set({"type": "public"})
             try:
                # Using async insert
                await self.rag.ainsert(text)
                
                main_tag = extract_tag_from_request(tags)
                if main_tag:
                     tag_manager.add_tag(main_tag, doc_id)
                     
             finally:
                request_llm_config.reset(token)

    def query(self, query: str, mode: str):
        if self.status != "ready" or not self.rag:
             return "RAG Engine is not ready."
        
        logger.info(f"Querying: {query} with mode: {mode}")
        return self.rag.query(query, param=QueryParam(mode=mode))

    def delete_doc(self, doc_id: str):
        if self.status != "ready" or not self.rag:
            logger.error("Deletion failed: RAG Engine not ready.")
            return

        logger.info(f"Deleting doc: {doc_id}")
        try:
             # Attempt to delete by doc_id if library supports it
             if hasattr(self.rag, "delete_by_doc_id"):
                 self.rag.delete_by_doc_id(doc_id)
             else:
                 logger.warning("LightRAG instance has no delete_by_doc_id method. Deletion might not persist in RAG.")
        except Exception as e:
             logger.error(f"Error deleting doc {doc_id}: {e}")

rag_engine = RAGEngine()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup: Waiting for dependent services...")
    
    # Extract host/port from env vars
    neo4j_host = "neo4j"
    neo4j_port = 7687 
    # Can parse from NEO4J_URI if needed, but simple default is fine for now
    
    qdrant_host = "qdrant"
    qdrant_port = 6333 # Default
    
    # Wait for services
    services_ready = True
    if not wait_for_service(neo4j_host, neo4j_port):
        logger.error(f"Neo4j at {neo4j_host}:{neo4j_port} is not reachable.")
        services_ready = False
    
    if not wait_for_service(qdrant_host, qdrant_port):
        logger.error(f"Qdrant at {qdrant_host}:{qdrant_port} is not reachable.")
        services_ready = False
        
    if services_ready:
        logger.info("All dependent services are reachable. Initializing RAG Engine...")
        try:
             await rag_engine.initialize_lightrag()
        except Exception as e:
             logger.error(f"Failed to initialize RAG Engine despite services being ready: {e}")
             rag_engine.status = "error"
    else:
        logger.error("Dependent services are not ready. RAG Engine initialization skipped.")
        rag_engine.status = "error"
        
    yield
    # Shutdown
    logger.info("Application shutdown...")
    if rag_engine.rag:
        # Check for finalize method on LightRAG or storages if available
        # LightRAG v2 might have finalize_storages
        if hasattr(rag_engine.rag, "finalize_storages"):
             await rag_engine.rag.finalize_storages()

app = FastAPI(title="RAG Service", description="API for RAG ingestion and querying", lifespan=lifespan)

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# --- Background Tasks ---
# --- Background Tasks ---
async def process_ingestion(request: IngestRequest):
    logger.info(f"Starting ingestion task for DocID: {request.doc_id}, Type: {request.type}")
    try: 
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
                # Await the async ingest call
                await rag_engine.ingest_file(str(md_file), request.doc_id, request.tags or {})
                
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
             await rag_engine.ingest_file(str(file_path), request.doc_id, request.tags or {})

        elif request.type == 'text':
             if request.text_content:
                 logger.info(f"Processing raw text ingestion (Length: {len(request.text_content)})")
                 await rag_engine.ingest_text(request.text_content, request.doc_id, request.tags or {})
        
        logger.info(f"Ingestion completed successfully for {request.doc_id}")
        RAG_INGESTION_TOTAL.labels(type=request.type, status="success").inc()
        
    except Exception as e:
        logger.error(f"Ingestion failed with exception: {e}", exc_info=True)
        rag_engine.status = "error"
        RAG_INGESTION_TOTAL.labels(type=request.type, status="error_exception").inc()

# --- Endpoints ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

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

@app.delete("/delete-by-tag")
async def delete_by_tag(tag: str):
    docs = tag_manager.get_docs(tag)
    if not docs:
        raise HTTPException(status_code=404, detail=f"No documents found for tag: {tag}")
    
    deleted_count = 0
    for doc_id in docs:
        rag_engine.delete_doc(doc_id)
        deleted_count += 1
    
    tag_manager.remove_tag(tag)
    return {"status": "success", "message": f"Deleted {deleted_count} documents for tag {tag}"}

@app.post("/query")
async def query_rag(request: QueryRequest):
    async def event_generator():
        # Create queue for status updates
        queue = asyncio.Queue()
        
        # Inject queue into LLM config
        llm_config = request.llm_config or {}
        llm_config["stream_queue"] = queue
        config_token = request_llm_config.set(llm_config)

        # Run RAG in background
        async def run_rag():
            try:
                # Check RAGEngine status
                if rag_engine.status != "ready" or not rag_engine.rag:
                     await queue.put({"type": "error", "content": f"RAG Engine is not ready. Status: {rag_engine.status}"})
                     return

                rag_mode = request.mode
                if request.mode == "vector":
                    rag_mode = "naive"
                elif request.mode == "graph":
                    rag_mode = "global"
                elif request.mode == "hybrid":
                    rag_mode = "hybrid"
                
                await queue.put({"type": "status", "content": f"Starting {rag_mode} search..."})
                
                if request.mode == "direct":
                    response = await llm_model_func(request.query)
                else:
                    response = await rag_engine.rag.aquery(request.query, param=QueryParam(mode=rag_mode))

                    # Fallback if aquery returns None but we captured LLM response
                    if response is None:
                         # Retrieve captured response from config
                         # Note: request.llm_config is just a dict copy, we need the one from context if available
                         # But wait, we set it in context: config = request_llm_config.get()
                         # llm_model_func modifies this dict object in place?
                         # request_llm_config.set(dict) -> get() returns dict reference.
                         # Since dict is mutable, modifications in llm_model_func should persist
                         # in the same context scope.
                         
                         current_config = request_llm_config.get()
                         captured_response = current_config.get("last_response")
                         if captured_response:
                             response = captured_response
                             logger.info("DEBUG: Used captured LLM response as fallback.")
                         else:
                             response = "Sorry, I could not generate an answer."
                             logger.warning("DEBUG: aquery returned None or empty, and no captured response found.")
                
                await queue.put({"type": "answer", "content": response})
                
            except Exception as e:
                logger.error(f"Query Error: {e}", exc_info=True)
                await queue.put({"type": "error", "content": str(e)})
            finally:
                await queue.put(None) # Signal done
                # Reset context vars (though specific to this task/generator)
                # Context vars in async generators can be tricky, but here we are in same context as set?
                # Actually run_rag is a task, it inherits context. 
                pass

        # Start the background task
        task = asyncio.create_task(run_rag())

        # Consume queue
        while True:
            try:
                data = await queue.get()
                if data is None:
                    break
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                logger.error(f"Stream Error: {e}")
                break
        
        # Ensure task is done
        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.delete("/documents/tag/{tag_name}")
async def delete_tag(tag_name: str):
    if not tag_name:
        raise HTTPException(status_code=400, detail="Tag name required")
    
    docs = tag_manager.get_docs(tag_name)
    if not docs:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_name}' not found")

    # Remove from TagManager
    # In a full implementation, we would also delete from LightRAG storages here.
    # checking if LightRAG supports deletion by content hash or similar is needed.
    # For now, we mainly remove the tag association.
    try:
        # We can iterate and remove each doc_id from the tag specific list 
        # But tag_manager.remove_doc takes (tag, doc_id).
        # Simpler: just clear the tag entry?
        # tag_manager does not have remove_tag method, only remove_doc.
        # Let's add remove_tag logic or iterate.
        current_docs = list(docs) # Copy list
        for doc_id in current_docs:
            tag_manager.remove_doc(tag_name, doc_id)
            
        logger.info(f"Deleted tag '{tag_name}' and associated {len(current_docs)} document associations.")
        return {"status": "success", "message": f"Tag '{tag_name}' deleted.", "deleted_docs": current_docs}

    except Exception as e:
        logger.error(f"Delete Tag Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
