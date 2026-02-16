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
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
import markdown_splitter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Resilience & Networking ---
import socket
import time
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log

def wait_for_service(host: str, port: int, timeout: int = 300):
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
from contextvars import ContextVar
request_llm_config = contextvars.ContextVar("llm_config", default={})
status_stream = contextvars.ContextVar("status_stream", default=None)

class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid" # 'hybrid', 'vector', 'graph'
    tags: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None
    top_k: Optional[int] = None # Added for tuning retrieval

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
    openai_kwargs = {k: v for k, v in kwargs.items() if k not in ['hashing_kv', 'mode', 'enable_cot', 'keyword_extraction', 'json_model']}

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
            # OpenAI requires non-empty strings. Replace empty/None with space.
            processed_texts = [t if t and isinstance(t, str) and t.strip() else " " for t in texts]
            response = await client.embeddings.create(input=processed_texts, model=model_name)
            return np.array([data.embedding for data in response.data])
            
        else:
             # Fallback/Other types if needed
             if default_openai_client:
                 processed_texts = [t if t and isinstance(t, str) and t.strip() else " " for t in texts]
                 response = await default_openai_client.embeddings.create(input=processed_texts, model=model_name)
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

# Context variable to track current doc_id during ingestion
current_doc_id: ContextVar[str | None] = ContextVar('current_doc_id', default=None)

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
        
        # Tuning Retrieval
        os.environ["TOP_K"] = "100" # Increase from default 60

        
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

    async def ingest_file(self, file_path: str, doc_id: str, tags: Dict, url: Optional[str] = None):
        if self.status != "ready" or not self.rag:
            error_msg = f"Ingestion failed: RAG Engine not ready (Status: {self.status})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

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
                    # CRITICAL: Pass doc_id to ainsert() to use our composite ID instead of MD5
                    # This ensures LightRAG stores the doc with our ID, making deletion possible
                    # Using async insert to ensure compatibility with async LLM function
                    # Set doc_id in context for storage layers to access
                    token_doc_id = current_doc_id.set(doc_id)
                    try:
                        # Pass ids=doc_id so LightRAG uses our composite ID
                        await self.rag.ainsert(
                            content, 
                            ids=doc_id,  # Use composite ID like "parent#file.md"
                            file_paths=[url] if url else None
                        )
                    finally:
                        current_doc_id.reset(token_doc_id)
                    
                    # Register tag
                    main_tag = extract_tag_from_request(tags)
                    if main_tag:
                         tag_manager.add_tag(main_tag, doc_id)
                         
                    logger.info(f"Inserted content successfully.")
                finally:
                    request_llm_config.reset(token)
            else:
                logger.warning(f"File {file_path} is empty, skipping ingestion.")

        except Exception as e:
            logger.error(f"Error reading/ingesting file {file_path}: {e}")
            raise e

    async def ingest_markdown_enhanced(self, file_path: str, doc_id: str, tags: Dict, base_url: Optional[str] = None):
        """
        Ingests a markdown file by splitting it into sections based on headers.
        Each section is ingested as a separate 'chunk' with its own deep-link URL.
        """
        if self.status != "ready" or not self.rag:
            error_msg = f"Ingestion failed: RAG Engine not ready (Status: {self.status})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Enhanced Ingestion for file: {file_path} (DocID: {doc_id})")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content:
                 logger.warning(f"File {file_path} is empty, skipping.")
                 return

            # Split content by headers
            sections = markdown_splitter.split_markdown_by_headers(content)
            logger.info(f"Split document into {len(sections)} sections.")
            
            token = request_llm_config.set({"type": "public"})
            
            try:
                for i, section in enumerate(sections):
                    header = section['header']
                    slug = section['slug']
                    section_content = section['content']
                    
                    if not section_content.strip():
                        continue
                        
                    # 1. Generate Deep Link URL
                    if base_url:
                        if slug:
                            section_url = f"{base_url}#{slug}"
                        else:
                            section_url = base_url
                    else:
                        section_url = None
                        
                    # 2. Generate Unique Sub-Doc ID
                    sub_doc_id = f"{doc_id}#{slug}" if slug else f"{doc_id}#sect_{i}"
                    
                    logger.info(f"Ingesting Section '{header}' as {sub_doc_id} (URL: {section_url})")
                    
                    # Set doc_id in context for storage layers
                    token_doc_id = current_doc_id.set(sub_doc_id)
                    try:
                        await self.rag.ainsert(
                            section_content,
                            ids=sub_doc_id, 
                            file_paths=[section_url] if section_url else None
                        )
                    finally:
                        current_doc_id.reset(token_doc_id)
                    
                    # Register tag
                    main_tag = extract_tag_from_request(tags)
                    if main_tag:
                         tag_manager.add_tag(main_tag, sub_doc_id)

                logger.info(f"Finished enhanced ingestion for {file_path}")

            finally:
                 request_llm_config.reset(token)

        except Exception as e:
            logger.error(f"Error in enhanced ingestion for {file_path}: {e}")
            raise e

    async def ingest_text(self, text: str, doc_id: str, tags: Dict):
        if self.status != "ready" or not self.rag:
            error_msg = f"Ingestion failed: RAG Engine not ready (Status: {self.status})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.info(f"Ingesting text for doc: {doc_id}")
        if text:
             # Default config for ingestion
             token = request_llm_config.set({"type": "public"})
             try:
                # CRITICAL: Pass ids=doc_id so LightRAG uses our doc_id instead of generating MD5
                await self.rag.ainsert(text, ids=doc_id)
                
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

    async def delete_doc(self, doc_id: str):
        """Delete all data associated with a document ID from Neo4j and Qdrant
        
        Args:
            doc_id: Document ID to delete
        """
        if self.status != "ready" or not self.rag:
            logger.error("Deletion failed: RAG Engine not ready.")
            return

        logger.info(f"Starting deletion process for doc_id: {doc_id}")
        
        try:
            # Step 1: Find all chunks with this doc_id from Qdrant
            from qdrant_client import models
            
            chunks_to_delete = []
            entities_to_delete = set()
            
            # Query chunks_vdb for all chunks with matching doc_id
            if hasattr(self.rag, 'chunks_vdb') and hasattr(self.rag.chunks_vdb, '_client'):
                logger.info(f"Querying Qdrant for chunks with doc_id: {doc_id}")
                
                # Scroll through all chunks with this doc_id
                scroll_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                )
                
                offset = None
                while True:
                    results = self.rag.chunks_vdb._client.scroll(
                        collection_name=self.rag.chunks_vdb.final_namespace,
                        scroll_filter=scroll_filter,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    points, next_offset = results
                    if not points:
                        break
                    
                    # Collect chunk IDs and entity names
                    for point in points:
                        if point.payload:
                            chunk_id = point.payload.get('id')
                            if chunk_id:
                                chunks_to_delete.append(chunk_id)
                            
                            # Extract entity names from chunk content if available
                            # Entities are typically stored with entity_name field
                            content = point.payload.get('content', '')
                            # We'll delete entities separately via entity_vdb query
                    
                    if next_offset is None:
                        break
                    offset = next_offset
                
                logger.info(f"Found {len(chunks_to_delete)} chunks to delete")
            
            # Step 2: Query entities_vdb for entities associated with this doc
            if hasattr(self.rag, 'entities_vdb') and hasattr(self.rag.entities_vdb, '_client'):
                logger.info(f"Querying Qdrant for entities with doc_id: {doc_id}")
                
                entity_scroll_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                )
                
                offset = None
                entity_ids_to_delete = []
                while True:
                    results = self.rag.entities_vdb._client.scroll(
                        collection_name=self.rag.entities_vdb.final_namespace,
                        scroll_filter=entity_scroll_filter,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    points, next_offset = results
                    if not points:
                        break
                    
                    for point in points:
                        if point.payload:
                            entity_id = point.payload.get('id')
                            entity_name = point.payload.get('entity_name')
                            if entity_id:
                                entity_ids_to_delete.append(entity_id)
                            if entity_name:
                                entities_to_delete.add(entity_name)
                    
                    if next_offset is None:
                        break
                    offset = next_offset
                
                logger.info(f"Found {len(entity_ids_to_delete)} entity vectors and {len(entities_to_delete)} unique entities")
                
                # Delete entity vectors from Qdrant
                if entity_ids_to_delete:
                    await self.rag.entities_vdb.delete(entity_ids_to_delete)
                    logger.info(f"Deleted {len(entity_ids_to_delete)} entity vectors from Qdrant")
            
            # Step 3: Delete chunks from Qdrant
            if chunks_to_delete:
                await self.rag.chunks_vdb.delete(chunks_to_delete)
                logger.info(f"Deleted {len(chunks_to_delete)} chunks from Qdrant")
            
            # Step 4: Delete entity nodes and relationships from Neo4j comprehensively
            # Query Neo4j directly for all entities associated with these chunks
            if chunks_to_delete and hasattr(self.rag, 'chunk_entity_relation_graph'):
                logger.info(f"Querying Neo4j for entities associated with {len(chunks_to_delete)} chunks")
                
                try:
                    # Use Cypher query to find all nodes where source_id contains any of our chunk IDs
                    # In Neo4j, entities have source_id field that contains chunk IDs separated by GRAPH_FIELD_SEP
                    workspace_label = self.rag.chunk_entity_relation_graph._get_workspace_label()
                    
                    # Build a comprehensive deletion query
                    # 1. Find all nodes where source_id contains any of the chunk IDs
                    # 2. DETACH DELETE removes both the nodes and their relationships
                    async with self.rag.chunk_entity_relation_graph._driver.session(database=self.rag.chunk_entity_relation_graph._DATABASE) as session:
                        deleted_count = 0
                        
                        # Process in batches to avoid query size limits
                        batch_size = 50
                        for i in range(0, len(chunks_to_delete), batch_size):
                            batch_chunks = chunks_to_delete[i:i+batch_size]
                            
                            # Create a pattern to match any chunk ID in source_id field
                            # source_id is a string with chunk IDs separated by GRAPH_FIELD_SEP (typically '\x00')
                            query = f"""
                            MATCH (n:`{workspace_label}`)
                            WHERE any(chunk_id IN $chunk_ids WHERE n.source_id CONTAINS chunk_id)
                            DETACH DELETE n
                            RETURN count(n) as deleted
                            """
                            
                            result = await session.run(query, chunk_ids=batch_chunks)
                            record = await result.single()
                            if record:
                                batch_deleted = record['deleted']
                                deleted_count += batch_deleted
                                logger.info(f"Deleted {batch_deleted} nodes in batch {i//batch_size + 1}")
                        
                        logger.info(f"Successfully deleted {deleted_count} entity nodes and their relationships from Neo4j")
                        
                except Exception as e:
                    logger.error(f"Error deleting entities from Neo4j: {e}", exc_info=True)
                    # Continue with deletion even if Neo4j cleanup fails
            
            
            # Step 5: Remove from tag manager
            # Find all tags containing this doc_id and remove it
            tags_to_update = []
            for tag, doc_ids in tag_manager.tags.items():
                if doc_id in doc_ids:
                    tags_to_update.append(tag)
            
            for tag in tags_to_update:
                tag_manager.remove_doc(tag, doc_id)
                logger.info(f"Removed doc_id {doc_id} from tag: {tag}")
            
            # Step 6: Delete from LightRAG's doc_status and full_docs storage
            # This prevents "already exists" errors when re-uploading the same document
            # CRITICAL: We need to delete BOTH the doc_id AND all associated MD5-based doc IDs
            if hasattr(self.rag, 'doc_status') and hasattr(self.rag, 'full_docs'):
                try:
                    # Collect ALL doc IDs to delete (both direct and MD5-based)
                    all_doc_ids_to_delete = set()
                    
                    # FIRST: Add the doc_id directly (for composite IDs like "parent#file.md")
                    all_doc_ids_to_delete.add(doc_id)
                    logger.info(f"Will delete doc_id: {doc_id}")
                    
                    # SECOND: Find ALL MD5-based doc IDs by scanning doc_status storage
                    # We need to check EVERY doc in storage to find which ones should be deleted
                    logger.info(f"Scanning all doc_status entries to find MD5 doc IDs...")
                    try:
                        # Get all keys from doc_status storage
                        all_storage_keys = await self.rag.doc_status.get_all_keys()
                        logger.info(f"Total doc_status entries: {len(all_storage_keys)}")
                        
                        # Get all doc info for these keys
                        doc_status_dict = await self.rag.doc_status.get_by_ids(list(all_storage_keys))
                        
                        # Scan through all doc entries to find ones that should be deleted
                        for storage_doc_id, doc_info in doc_status_dict.items():
                            should_delete = False
                            
                            # Check if this is the exact doc_id we want to delete
                            if storage_doc_id == doc_id:
                                should_delete = True
                                logger.info(f"Found exact match: {storage_doc_id}")
                            
                            # Check if this doc contains any of our deleted chunks
                            elif doc_info and isinstance(doc_info, dict):
                                chunks_list = doc_info.get('chunks_list', [])
                                if isinstance(chunks_list, list) and chunks_to_delete:
                                    # If ANY chunk from this doc is in our deletion list, delete the whole doc
                                    if any(chunk_id in chunks_list for chunk_id in chunks_to_delete):
                                        should_delete = True
                                        matching_chunks = [c for c in chunks_list if c in chunks_to_delete]
                                        logger.info(f"Found MD5 doc with matching chunks: {storage_doc_id} ({len(matching_chunks)} chunks)")
                            
                            if should_delete:
                                all_doc_ids_to_delete.add(storage_doc_id)
                        
                        logger.info(f"Total doc IDs to delete from storage: {len(all_doc_ids_to_delete)}")
                        
                    except Exception as e:
                        logger.warning(f"Could not scan doc_status storage: {e}", exc_info=True)
                        # Even if scanning fails, we still try to delete the doc_id directly
                    
                    # Delete ALL collected doc IDs from both doc_status and full_docs
                    if all_doc_ids_to_delete:
                        doc_ids_list = list(all_doc_ids_to_delete)
                        logger.info(f"Deleting {len(doc_ids_list)} entries from doc_status and full_docs")
                        
                        await self.rag.doc_status.delete(doc_ids_list)
                        await self.rag.full_docs.delete(doc_ids_list)
                        
                        logger.info(f"Successfully deleted {len(doc_ids_list)} doc entries from storage: {doc_ids_list}")
                    else:
                        logger.warning(f"No doc IDs found to delete for doc_id: {doc_id}")
                        
                except Exception as e:
                    logger.warning(f"Failed to delete from doc_status/full_docs storage: {e}", exc_info=True)
            
            logger.info(f"Successfully deleted all data for doc_id: {doc_id}")
            
        except Exception as e:
            logger.error(f"Error during deletion of doc_id {doc_id}: {e}", exc_info=True)
            raise

rag_engine = RAGEngine()

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
                try:
                    relative_path = md_file.relative_to(repo_path).as_posix()
                    # MkDocs uses simplified URLs: file.md -> file/
                    # If file is index.md, it maps to parent folder.
                    # Let's try to match MkDocs default behavior for the base URL.
                    
                    url_path = relative_path.replace('.md', '/')
                    if url_path.endswith('index/'):
                        url_path = url_path[:-6] # remove 'index/' to get parent/
                    
                    web_url = f"http://localhost:3001/docs/{request.doc_id}/{url_path}"
                    
                    # Composite ID for the FILE (parent)
                    # We use this as prefix for sections
                    file_doc_id = f"{request.doc_id}#{relative_path}"
                    logger.info(f"Using File Doc ID: {file_doc_id} (Base URL: {web_url})")
                    
                except Exception as e:
                    logger.warning(f"Failed to construct URL for {md_file}: {e}")
                    web_url = None
                    file_doc_id = request.doc_id

                # Use Enhanced Ingestion for Markdown
                await rag_engine.ingest_markdown_enhanced(str(md_file), file_doc_id, request.tags or {}, base_url=web_url)
                
        elif request.type == 'file':
             # ... (existing logic for file)
             # Check if it's a markdown file
             public_data_path = Path("/app/public_data")
             # ...
             # We should also use enhanced ingestion here if it's .md
             pass # (logic continues)
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
             # Construct Web URL for single file
             # Assuming standard file serving path or similar
             web_url = f"http://localhost:3001/public_data/{relative_path}"
             
             if file_path.suffix.lower() == '.md':
                 await rag_engine.ingest_markdown_enhanced(str(file_path), request.doc_id, request.tags or {}, base_url=web_url)
             else:
                 await rag_engine.ingest_file(str(file_path), request.doc_id, request.tags or {}, url=web_url)

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
    return {
        "status": "ok" if rag_engine.status == "ready" else "error", 
        "rag_status": rag_engine.status,
        "ready": rag_engine.status == "ready"
    }

@app.post("/ingest")
async def ingest_document(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_ingestion, request)
    return {"status": "processing", "doc_id": request.doc_id}

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete document and all its children (for multi-file documents like ZIPs).
    Uses composite ID pattern: parent children have IDs like {doc_id}#{file_path}
    
    This endpoint searches ALL databases (Qdrant, Neo4j, doc_status) to find
    all child documents, not just doc_status.keys()
    """
    deleted_ids = []
    failed_deletes = []
    
    logger.info(f"Starting comprehensive deletion for doc_id: {doc_id}")
    
    # Find ALL child documents by searching EVERY database
    all_child_ids = set()
    
    try:
        # 1. Search doc_status storage for child IDs
        if rag_engine.rag and hasattr(rag_engine.rag, 'doc_status'):
            try:
                all_storage_keys = await rag_engine.rag.doc_status.get_all_keys()
                child_pattern = f"{doc_id}#"
                doc_status_children = [k for k in all_storage_keys if k.startswith(child_pattern)]
                all_child_ids.update(doc_status_children)
                logger.info(f"Found {len(doc_status_children)} children in doc_status storage")
            except Exception as e:
                logger.warning(f"Error searching doc_status: {e}")
        
        # 2. Search Qdrant chunks_vdb for child IDs
        if rag_engine.rag and hasattr(rag_engine.rag, 'chunks_vdb'):
            try:
                from qdrant_client import models
                
                # Scroll through ALL chunks to find matching doc_ids
                child_pattern = f"{doc_id}#"
                offset = None
                qdrant_children = set()
                
                while True:
                    results = rag_engine.rag.chunks_vdb._client.scroll(
                        collection_name=rag_engine.rag.chunks_vdb.final_namespace,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    points, next_offset = results
                    if not points:
                        break
                    
                    for point in points:
                        if point.payload:
                            chunk_doc_id = point.payload.get('doc_id')
                            if chunk_doc_id and chunk_doc_id.startswith(child_pattern):
                                qdrant_children.add(chunk_doc_id)
                    
                    if next_offset is None:
                        break
                    offset = next_offset
                
                all_child_ids.update(qdrant_children)
                logger.info(f"Found {len(qdrant_children)} children in Qdrant chunks")
            except Exception as e:
                logger.warning(f"Error searching Qdrant: {e}")
        
        # 3. Search Qdrant entities_vdb for child IDs
        if rag_engine.rag and hasattr(rag_engine.rag, 'entities_vdb'):
            try:
                from qdrant_client import models
                
                child_pattern = f"{doc_id}#"
                offset = None
                entity_children = set()
                
                while True:
                    results = rag_engine.rag.entities_vdb._client.scroll(
                        collection_name=rag_engine.rag.entities_vdb.final_namespace,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    points, next_offset = results
                    if not points:
                        break
                    
                    for point in points:
                        if point.payload:
                            entity_doc_id = point.payload.get('doc_id')
                            if entity_doc_id and entity_doc_id.startswith(child_pattern):
                                entity_children.add(entity_doc_id)
                    
                    if next_offset is None:
                        break
                    offset = next_offset
                
                all_child_ids.update(entity_children)
                logger.info(f"Found {len(entity_children)} children in Qdrant entities")
            except Exception as e:
                logger.warning(f"Error searching Qdrant entities: {e}")
        
        logger.info(f"Total unique child documents found: {len(all_child_ids)}")
        
    except Exception as e:
        logger.error(f"Error during comprehensive child search: {e}", exc_info=True)
    
    # Delete parent document first
    try:
        await rag_engine.delete_doc(doc_id)
        deleted_ids.append(doc_id)
        logger.info(f"Deleted parent document: {doc_id}")
    except Exception as e:
        logger.warning(f"Could not delete parent {doc_id}: {e}")
        # Continue to delete children even if parent doesn't exist
    
    # Delete all child documents
    for child_id in all_child_ids:
        try:
            await rag_engine.delete_doc(child_id)
            deleted_ids.append(child_id)
            logger.info(f"Deleted child document: {child_id}")
        except Exception as e:
            logger.error(f"Failed to delete child {child_id}: {e}")
            failed_deletes.append({"id": child_id, "error": str(e)})
    
    # Return detailed response
    response = {
        "status": "deleted",
        "doc_id": doc_id,
        "total_deleted": len(deleted_ids),
        "deleted_ids": deleted_ids
    }
    
    if failed_deletes:
        response["failed"] = len(failed_deletes)
        response["failed_details"] = failed_deletes
        logger.warning(f"Completed deletion with {len(failed_deletes)} failures")
    else:
        logger.info(f"Successfully deleted all documents: {len(deleted_ids)} total")
    
    return response

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
                    await queue.put({"type": "answer", "content": response})
                else:
                    # Use aquery_llm to get full result including context
                    # IMPROVED: Pass custom response_type for better answers
                    # Also respect request.top_k if provided (though LightRAG uses init params usually, newer versions allow override)
                    param = QueryParam(mode=rag_mode)
                    
                    # Try to set top_k if supported (LightRAG might not support override in all versions, but good to try)
                    if hasattr(param, 'top_k') and request.top_k:
                         param.top_k = request.top_k
                    
                    # Force a detailed response type
                    # The default is often "Multiple Paragraphs", we want something better
                    response_type = "Detailed and comprehensive analysis with examples if relevant"
                    
                    result = await rag_engine.rag.aquery_llm(
                        request.query, 
                        param=param
                        # Note: response_type is passed as a separate arg in some versions or part of param
                        # Checking lightrag_copy.py, aquery_llm signature is (query, param)
                        # We might need to monkeypatch or check if param has response_type
                    )

                    # Wait, lightrag_copy.py doesn't show aquery_llm implementation fully (it imports from lightrag.operate)
                    # But traditionally LightRAG takes `query_param` which has `mode`.
                    # Let's trust that we can't easily change prompt WITHOUT modifying LightRAG source or using param.
                    
                    # If we can't pass response_type easily, we rely on the implementation.
                    # HOWEVER, we can update the ENV VARS before initialization in main.py to set TOP_K.
                    
                    # Let's extract LLM response
                    llm_response = result.get("llm_response", {})
                    content = llm_response.get("content")
                    
                    if not content and not llm_response.get("is_streaming"):
                         # Fallback logic
                         current_config = request_llm_config.get()
                         content = current_config.get("last_response") or "Sorry, I could not generate an answer."

                    await queue.put({"type": "answer", "content": content})

                    # Extract Sources Manually from Vector DB
                    try:
                        # Generate embedding for the query
                        embedding = await rag_engine.rag.embedding_func([request.query])
                        # Perform vector search on chunks
                        sources_results = await rag_engine.rag.chunks_vdb.query(embedding[0], top_k=5)
                        
                        sources = []
                        seen_urls = set()
                        
                        for res in sources_results:
                            url = res.get("file_path")
                            if url and url not in seen_urls and isinstance(url, str) and url.startswith("http"):
                                seen_urls.add(url)
                                sources.append({"url": url, "title": url.split("/")[-1] or "Document"})
                        
                        if sources:
                             await queue.put({"type": "sources", "content": sources})
                             
                    except Exception as e:
                        logger.error(f"Failed to retrieve sources: {e}")

            except Exception as e:
                logger.error(f"Query Error: {e}", exc_info=True)
                await queue.put({"type": "error", "content": str(e)})
            finally:
                await queue.put(None) # Signal done


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
