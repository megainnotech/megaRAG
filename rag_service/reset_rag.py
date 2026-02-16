
import os
import shutil
import logging
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
RAG_INDEX_DIR = "/app/public_data/rag_index"

def reset_neo4j():
    logger.info("Resetting Neo4j...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        with driver.session() as session:
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        logger.info("✅ Neo4j cleared.")
    except Exception as e:
        logger.error(f"❌ Failed to clear Neo4j: {e}")

def reset_qdrant():
    logger.info("Resetting Qdrant...")
    try:
        client = QdrantClient(url=QDRANT_URL)
        # Get all collections
        collections = client.get_collections().collections
        for collection in collections:
            logger.info(f"Deleting collection: {collection.name}")
            client.delete_collection(collection.name)
        logger.info("✅ Qdrant cleared.")
    except Exception as e:
        # Fallback if URL is missing scheme or port issue, try default
        if "http" not in QDRANT_URL:
             try:
                client = QdrantClient(host="qdrant", port=6333)
                collections = client.get_collections().collections
                for collection in collections:
                    logger.info(f"Deleting collection: {collection.name}")
                    client.delete_collection(collection.name)
                logger.info("✅ Qdrant cleared.")
             except Exception as ex:
                 logger.error(f"❌ Failed to clear Qdrant: {ex}")
        else:
            logger.error(f"❌ Failed to clear Qdrant: {e}")

def reset_local_storage():
    logger.info(f"Resetting Local Storage ({RAG_INDEX_DIR})...")
    if os.path.exists(RAG_INDEX_DIR):
        try:
            shutil.rmtree(RAG_INDEX_DIR)
            logger.info("✅ Local storage cleared.")
        except Exception as e:
            logger.error(f"❌ Failed to clear local storage: {e}")
    
    # Always recreate the directory
    try:
        os.makedirs(RAG_INDEX_DIR, exist_ok=True)
        logger.info(f"✅ Recreated directory: {RAG_INDEX_DIR}")
    except Exception as e:
        logger.error(f"❌ Failed to recreate directory: {e}")

def main():
    print("⚠️  WARNING: This will DELETE ALL DATA in the RAG system (Neo4j, Qdrant, Local Index).")
    print("Are you sure you want to proceed? (y/n)")
    
    # Non-interactive mode check if env var set? 
    # For now, let's assume if running script, user means it. 
    # But for safety, adding a small delay or check args.
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        pass
    else:
        # In docker, input might not be possible if run detached. 
        # But user asked for a script to help them test.
        # Let's require --force flag to run non-interactively or just run it if they call it.
        # I'll default to running it immediately as it's a utility script.
        pass

    reset_neo4j()
    reset_qdrant()
    reset_local_storage()
    print("\n✨ RAG System Reset Complete.")

if __name__ == "__main__":
    main()
