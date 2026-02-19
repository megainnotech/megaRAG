from main import rag_engine, initialize_lightrag
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_rag():
    try:
        logger.info("Initializing RAG storage...")
        # Simulate startup
        rag_engine.rag = await initialize_lightrag(rag_engine)
        
        if rag_engine.rag:
            logger.info("RAG Engine Initialized.")
            print(f"RAG Object: {rag_engine.rag}")
            print(f"RAG Dir: {dir(rag_engine.rag)}")
            
            # Check specific attributes
            print(f"Has chunks_vdb: {hasattr(rag_engine.rag, 'chunks_vdb')}")
            if hasattr(rag_engine.rag, 'chunks_vdb'):
                print(f"Chunks VDB Dir: {dir(rag_engine.rag.chunks_vdb)}")
        else:
            logger.error("RAG Engine is None after initialization.")
            
    except Exception as e:
        logger.error(f"Initialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_rag())
