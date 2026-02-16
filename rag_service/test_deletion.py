"""
Test script to verify document deletion behavior and debug MD5 doc ID cleanup
"""
import asyncio
import sys
import os

# Add the rag_service directory to path
sys.path.insert(0, '/app')

from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_deletion():
    """Test deletion of documents and verify MD5 doc IDs are cleared"""
    
    # Initialize LightRAG
    working_dir = "/app/public_data/rag_index"
    
    logger.info("="*80)
    logger.info("STEP 1: Inspecting current doc_status storage")
    logger.info("="*80)
    
    # We need to initialize LightRAG to access storage
    from main import rag_engine
    
    if not rag_engine.rag:
        logger.error("RAG engine not initialized!")
        return
    
    # Check current doc_status keys
    try:
        all_keys = await rag_engine.rag.doc_status.get_all_keys()
        logger.info(f"\nTotal doc_status entries: {len(all_keys)}")
        
        # Show all keys
        logger.info("\nAll doc_status keys:")
        for i, key in enumerate(all_keys):
            logger.info(f"  {i+1}. {key}")
        
        # Look for MD5 doc IDs
        md5_docs = [k for k in all_keys if k.startswith("doc-")]
        logger.info(f"\nMD5 doc IDs found: {len(md5_docs)}")
        for md5_id in md5_docs:
            logger.info(f"  - {md5_id}")
            
        # Look for composite IDs
        composite_ids = [k for k in all_keys if "#" in k]
        logger.info(f"\nComposite IDs found: {len(composite_ids)}")
        for comp_id in composite_ids[:10]:  # Show first 10
            logger.info(f"  - {comp_id}")
        
        # Get detailed info for one MD5 doc
        if md5_docs:
            sample_md5 = md5_docs[0]
            logger.info(f"\n" + "="*80)
            logger.info(f"STEP 2: Inspecting MD5 doc: {sample_md5}")
            logger.info("="*80)
            
            doc_info = await rag_engine.rag.doc_status.get_by_ids([sample_md5])
            if sample_md5 in doc_info:
                info = doc_info[sample_md5]
                logger.info(f"\nDoc info keys: {info.keys() if isinstance(info, dict) else 'Not a dict'}")
                if isinstance(info, dict):
                    logger.info(f"  - chunks_list: {info.get('chunks_list', 'N/A')}")
                    logger.info(f"  - doc_id: {info.get('doc_id', 'N/A')}")
                    logger.info(f"  - file_paths: {info.get('file_paths', 'N/A')}")
        
        # Check full_docs as well
        logger.info(f"\n" + "="*80)
        logger.info(f"STEP 3: Checking full_docs storage")
        logger.info("="*80)
        
        full_docs_keys = await rag_engine.rag.full_docs.get_all_keys()
        logger.info(f"\nTotal full_docs entries: {len(full_docs_keys)}")
        
        full_docs_md5 = [k for k in full_docs_keys if k.startswith("doc-")]
        logger.info(f"MD5 doc IDs in full_docs: {len(full_docs_md5)}")
        for md5_id in full_docs_md5[:5]:  # Show first 5
            logger.info(f"  - {md5_id}")
            
    except Exception as e:
        logger.error(f"Error inspecting storage: {e}", exc_info=True)
    
    logger.info("\n" + "="*80)
    logger.info("STEP 4: Testing delete logic")
    logger.info("="*80)
    
    # Test the delete logic on a composite ID
    if composite_ids:
        test_composite_id = composite_ids[0]
        logger.info(f"\nTesting deletion of: {test_composite_id}")
        
        try:
            # Call delete_doc
            await rag_engine.delete_doc(test_composite_id)
            logger.info(f"✓ Delete completed for: {test_composite_id}")
            
            # Verify deletion
            all_keys_after = await rag_engine.rag.doc_status.get_all_keys()
            logger.info(f"\nDoc_status entries after deletion: {len(all_keys_after)}")
            logger.info(f"Reduction: {len(all_keys) - len(all_keys_after)} entries")
            
            # Check if MD5 docs were deleted
            md5_docs_after = [k for k in all_keys_after if k.startswith("doc-")]
            logger.info(f"\nMD5 doc IDs after deletion: {len(md5_docs_after)}")
            logger.info(f"MD5 docs deleted: {len(md5_docs) - len(md5_docs_after)}")
            
        except Exception as e:
            logger.error(f"Error during deletion test: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_deletion())
