#!/usr/bin/env python3
"""
Detailed test script to verify RAG ingestion with full logging
This script tests the actual end-to-end flow inside the container
"""
import asyncio
import sys
sys.path.append('/app')

from main import rag_engine, llm_model_func, embedding_func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm():
    """Test if LLM is working"""
    print("\n" + "="*60)
    print("Testing LLM Function")
    print("="*60)
    
    try:
        response = await llm_model_func("Say 'Hello, World!' and nothing else.")
        print(f"✅ LLM Response: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return False

async def test_embedding():
    """Test if embedding is working"""
    print("\n" + "="*60)
    print("Testing Embedding Function")
    print("="*60)
    
    try:
        result = await embedding_func(["Hello, this is a test."])
        print(f"✅ Embedding Shape: {result.shape}")
        print(f"✅ Embedding Sample (first 5 dims): {result[0][:5]}")
        
       # Check if it's a zero vector (indicates failure)
        if (result == 0).all():
            print("⚠️  WARNING: Embedding returned zero vector!")
            return False
        return True
    except Exception as e:
        print(f"❌ Embedding Error: {e}")
        return False

async def test_ingestion():
    """Test actual ingestion"""
    print("\n" + "="*60)
    print("Testing Full Ingestion")
    print("="*60)
    
    # Check RAG engine status
    print(f"RAG Engine Status: {rag_engine.status}")
    if rag_engine.status != "ready":
        print("❌ RAG Engine not ready!")
        return False
    
    # Test text
    test_text = """
    # Test Document
    
    This is a test document for the RAG system.
    It contains some information about testing.
    
    ## Key Points
    
    - Point 1: Testing is important
    - Point 2: Verification is crucial
    - Point 3: Documentation helps
    """
    
    try:
        print(f"Ingesting text (length: {len(test_text)})...")
        await rag_engine.ingest_text(
            text=test_text,
            doc_id="detailed_test_001",
            tags={"test": "true"}
        )
        print("✅ Ingestion completed")
        
        # Wait a bit for async processing
        await asyncio.sleep(2)
        
        # Check if data was actually stored
        print("\nChecking storage...")
        
        # Check Qdrant
        if hasattr(rag_engine.rag, 'chunks_vdb'):
            try:
                # Try to query for our doc
                from qdrant_client import models
                results = rag_engine.rag.chunks_vdb._client.scroll(
                    collection_name=rag_engine.rag.chunks_vdb.final_namespace,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value="detailed_test_001")
                            )
                        ]
                    ),
                    limit=10,
                    with_payload=True
                )
                points, _ = results
                if points:
                    print(f"✅ Found {len(points)} chunks in Qdrant")
                    print(f"   Sample payload: {points[0].payload if points else 'None'}")
                else:
                    print("⚠️  No chunks found in Qdrant!")
            except Exception as e:
                print(f"❌ Error checking Qdrant: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ingestion Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("\n" + "="*60)
    print("🔬 DETAILED RAG INGESTION TEST")
    print("="*60)
    
    # Wait for RAG to be ready
    print("\nWaiting for RAG engine to initialize...")
    max_wait = 30
    for i in range(max_wait):
        if rag_engine.status == "ready":
            print(f"✅ RAG Engine ready after {i} seconds")
            break
        await asyncio.sleep(1)
    else:
        print(f"❌ RAG Engine not ready after {max_wait} seconds")
        print(f"   Status: {rag_engine.status}")
        return
    
    # Run tests
    llm_ok = await test_llm()
    embed_ok = await test_embedding()
    ingest_ok = await test_ingestion()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"LLM:        {'✅ PASS' if llm_ok else '❌ FAIL'}")
    print(f"Embedding:  {'✅ PASS' if embed_ok else '❌ FAIL'}")
    print(f"Ingestion:  {'✅ PASS' if ingest_ok else '❌ FAIL'}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
