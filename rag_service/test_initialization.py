
import asyncio
import os
import sys
import logging
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock LLM func
async def mock_llm_model_func(prompt, **kwargs):
    return "Mock LLM Response"

# Mock Embedding func
async def mock_embedding_func(texts):
    return np.zeros((len(texts), 1536))

async def test_init():
    working_dir = "/app/public_data/rag_index_test"
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)

    # Set env vars
    os.environ["NEO4J_URI"] = "bolt://neo4j:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["QDRANT_URL"] = "http://qdrant:6333"

    logger.info("Starting isolated LightRAG initialization test...")
    try:
        rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=mock_llm_model_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8192,
                func=mock_embedding_func
            ),
            graph_storage="Neo4JStorage",
            vector_storage="QdrantVectorDBStorage"
        )
        
        logger.info("LightRAG instance created.")
        
        if hasattr(rag, "initialize_storages"):
            logger.info("Calling initialize_storages()...")
            await rag.initialize_storages()
            logger.info("initialize_storages() completed.")
        else:
            logger.info("No initialize_storages method found.")

        logger.info("Test Success!")

    except Exception as e:
        logger.error("Test Failed!", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_init())
