import requests
import time

API_BASE = "http://localhost:8001"

def test_document_deletion():
    """Test complete document deletion from Neo4j and Qdrant"""
    
    print("\n=== Document Deletion Test ===\n")
    
    # Step 1: Ingest a test document
    print("Step 1: Ingesting test document...")
    ingest_payload = {
        "doc_id": "test_delete_doc_001",
        "type": "text",
        "text_content": "This is a test document about artificial intelligence and machine learning. AI is transforming how we build software.",
        "tags": {"main": "test_deletion", "category": "ai"}
    }
    
    response = requests.post(f"{API_BASE}/ingest", json=ingest_payload)
    print(f"Ingestion response: {response.json()}")
    
    # Wait for ingestion to complete
    print("Waiting for ingestion to complete (10 seconds)...")
    time.sleep(10)
    
    # Step 2: Verify document is indexed by querying
    print("\nStep 2: Verifying document is findable...")
    query_payload = {
        "query": "artificial intelligence",
        "mode": "hybrid"
    }
    
    response = requests.post(f"{API_BASE}/query", json=query_payload)
    query_result = response.json()
    print(f"Query result (should find content): {query_result[:200]}...")
    
    # Step 3: Delete the document
    print("\nStep 3: Deleting document...")
    doc_id = "test_delete_doc_001"
    response = requests.delete(f"{API_BASE}/documents/{doc_id}")
    print(f"Deletion response: {response.json()}")
    
    # Wait a bit for deletion to process
    time.sleep(2)
    
    # Step 4: Verify document is no longer findable
    print("\nStep 4: Verifying document is deleted...")
    response = requests.post(f"{API_BASE}/query", json=query_payload)
    query_after_delete = response.json()
    print(f"Query result after delete (should not find deleted content): {query_after_delete[:200]}...")
    
    # Step 5: Check tag manager
    print("\nStep 5: Checking tag manager...")
    response = requests.get(f"{API_BASE}/tags")
    tags_result = response.json()
    print(f"Tags after deletion: {tags_result}")
    
    # Check if test_deletion tag still has our doc_id
    test_tag_docs = tags_result.get("test_deletion", [])
    if doc_id in test_tag_docs:
        print(f"❌ FAIL: doc_id {doc_id} still in tag manager!")
    else:
        print(f"✅ PASS: doc_id {doc_id} properly removed from tag manager")
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    try:
        test_document_deletion()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
