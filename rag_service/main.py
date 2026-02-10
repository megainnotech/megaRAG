from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import logging
import shutil
from pathlib import Path
import glob

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Service")

# Environment Variables
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
TEMP_REPOS_DIR = "/app/temp_repos"

# --- Models ---
class IngestRequest(BaseModel):
    doc_id: str
    type: str # 'git', 'file', 'text'
    local_path: Optional[str] = None # For 'git' or 'file' (path relative to mount)
    text_content: Optional[str] = None # For 'text'
    tags: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid" # 'hybrid', 'vector', 'graph'
    tags: Optional[Dict[str, Any]] = None

# --- RAG Engine ---
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete, gpt_4o_complete 
import pdfplumber

class RAGEngine:
    def __init__(self):
        self.status = "initializing"
        self.working_dir = "/app/public_data/rag_index"
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
            
        logger.info(f"Initializing LightRAG in {self.working_dir}...")
        
        # Initialize LightRAG
        # Note: We need to configure LLM function based on user input (local vs public).
        # For now, initializing with defaults or placeholders. 
        # Real implementation needs dynamic LLM switch which LightRAG might support via config or re-init.
        try:
            self.rag = LightRAG(
                working_dir=self.working_dir,
                llm_model_func=gpt_4o_mini_complete # Default to a model, will need to be made dynamic
                # graph_storage="Neo4jStorage",
                # vector_storage="QdrantStorage",
                # ... other params based on LightRAG docs
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
                self.rag.insert(content)
                logger.info(f"Inserted content length: {len(content)}")
        except Exception as e:
            logger.error(f"Error reading/ingesting file {file_path}: {e}")

    def ingest_text(self, text: str, doc_id: str, tags: Dict):
        logger.info(f"Ingesting text for doc: {doc_id}")
        if text:
            self.rag.insert(text)

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
def process_ingestion(request: IngestRequest):
    logger.info(f"Starting ingestion for {request.doc_id}")
    try:
        rag_engine.status = "indexing" 
        if request.type == 'git':
            # request.local_path should be the repo folder name in temp_repos, e.g. "repo-uuid"
            repo_path = Path(TEMP_REPOS_DIR) / request.local_path
            
            if not repo_path.exists():
                logger.error(f"Repo path not found: {repo_path}")
                return

            md_files = list(repo_path.rglob("*.md"))
            logger.info(f"Found {len(md_files)} markdown files in {repo_path}")
            
            for md_file in md_files:
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
                 return

             rag_engine.ingest_file(str(file_path), request.doc_id, request.tags or {})

        elif request.type == 'text':
             if request.text_content:
                 rag_engine.ingest_text(request.text_content, request.doc_id, request.tags or {})
        
        rag_engine.status = "ready"
        logger.info(f"Ingestion completed for {request.doc_id}")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        rag_engine.status = "error"

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
    response = rag_engine.query(request.query, request.mode)
    return {"response": response}
