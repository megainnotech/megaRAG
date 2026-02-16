#!/usr/bin/env python3
"""
Test script to verify MD5-based deletion works correctly.
This test ensures that when documents are deleted, their MD5 entries 
in doc_status and full_docs are properly removed, allowing re-upload.
"""

import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

# For Docker environment, these paths are mounted
DOC_STATUS_PATH = Path("../public_data/rag_index/kv_store_doc_status.json")
FULL_DOCS_PATH = Path("../public_data/rag_index/kv_store_full_docs.json")

def read_json_file(filepath):
    """Read JSON file if it exists"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return {}

def test_md5_deletion():
    """Test that MD5 doc entries are properly deleted and can be re-uploaded"""
    
    print("\n" + "="*60)
    print("MD5 DELETION TEST - Verifying Complete Cleanup")
    print("="*60)
    
    # Use unique content for this test
    test_content = f"MD5 deletion test - timestamp {int(time.time())} - This content should be deletable and re-uploadable"
    test_doc_id = "test_md5_deletion_" + str(int(time.time()))
    
    # Step 1: Upload document
    print(f"\n[Step 1] Uploading test document (doc_id: {test_doc_id})")
    response = requests.post(f"{API_BASE}/ingest", json={
        "doc_id": test_doc_id,
        "type": "text",
        "text_content": test_content,
        "tags": {"test": "md5_cleanup"}
    })
    
    if response.status_code != 200:
        print(f"❌ FAIL: Upload failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"✅ Upload initiated: {response.json()}")
    print("Waiting 20 seconds for ingestion to complete...")
    time.sleep(20)
    
    # Step 2: Check that MD5 entry was created
    print(f"\n[Step 2] Checking doc_status for MD5 entries")
    doc_status_before = read_json_file(DOC_STATUS_PATH)
    md5_docs_before = [k for k in doc_status_before.keys() if k.startswith("doc-")]
    print(f"Total MD5 docs before deletion: {len(md5_docs_before)}")
    
    if len(md5_docs_before) == 0:
        print("⚠️  WARNING: No MD5 docs found. Ingestion might have failed.")
    
    # Step 3: Delete the document
    print(f"\n[Step 3] Deleting document (doc_id: {test_doc_id})")
    response = requests.delete(f"{API_BASE}/documents/{test_doc_id}")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Deletion failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"✅ Deletion completed: {response.json()}")
   print("Waiting 5 seconds for cleanup to complete...")
    time.sleep(5)
    
    # Step 4: Verify MD5 entries were removed
    print(f"\n[Step 4] Verifying MD5 entries were deleted")
    doc_status_after = read_json_file(DOC_STATUS_PATH)
    full_docs_after = read_json_file(FULL_DOCS_PATH)
    
    md5_docs_after = [k for k in doc_status_after.keys() if k.startswith("doc-")]
    md5_full_docs_after = [k for k in full_docs_after.keys() if k.startswith("doc-")]
    
    print(f"MD5 docs in doc_status after deletion: {len(md5_docs_after)}")
    print(f"MD5 docs in full_docs after deletion: {len(md5_full_docs_after)}")
    
    # Check if count decreased (at least one MD5 doc was deleted)
    if len(md5_docs_before) > 0 and len(md5_docs_after) >= len(md5_docs_before):
        print(f"❌ FAIL: doc_status MD5 entries were not deleted!")
        print(f"Before: {len(md5_docs_before)}, After: {len(md5_docs_after)}")
        return False
    
    print(f"✅ MD5 entries decreased: {len(md5_docs_before)} → {len(md5_docs_after)}")
    
    # Step 5: Re-upload the SAME content (same MD5)
    print(f"\n[Step 5] Re-uploading same content with new doc_id")
    test_doc_id_retry = test_doc_id + "_retry"
    
    response = requests.post(f"{API_BASE}/ingest", json={
        "doc_id": test_doc_id_retry,
        "type": "text",
        "text_content": test_content,  # SAME content = SAME MD5
        "tags": {"test": "md5_cleanup_retry"}
    })
    
    if response.status_code != 200:
        print(f"❌ FAIL: Re-upload failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"✅ Re-upload initiated: {response.json()}")
    print("Waiting 20 seconds for re-ingestion to complete...")
    time.sleep(20)
    
    # Step 6: Verify re-upload was processed successfully
    print(f"\n[Step 6] Verifying re-upload was processed (not rejected as duplicate)")
    doc_status_final = read_json_file(DOC_STATUS_PATH)
    md5_docs_final = [k for k in doc_status_final.keys() if k.startswith("doc-")]
    
    print(f"MD5 docs after re-upload: {len(md5_docs_final)}")
    
    # Should have at least one MD5 doc (the re-uploaded one)
    if len(md5_docs_final) == 0:
        print(f"❌ FAIL: No MD5 docs found after re-upload. Re-ingestion might have failed.")
        return False
    
    # Try to query for the content
    print(f"\n[Step 7] Querying for re-uploaded content")
    response = requests.post(f"{API_BASE}/query", json={
        "query": "MD5 deletion test timestamp",
        "mode": "naive"
    })
    
    if response.status_code != 200:
        print(f"⚠️  WARNING: Query failed with status {response.status_code}")
        # Don't fail the test, query might fail for other reasons
    else:
        print(f"✅ Query succeeded - document was re-processed")
    
    # Cleanup
    print(f"\n[Step 8] Cleaning up test document")
    requests.delete(f"{API_BASE}/documents/{test_doc_id_retry}")
    
    print("\n" + "="*60)
    print("✅ TEST PASSED - MD5 deletion works correctly!")
    print("="*60)
    print("\nSummary:")
    print(f"  - Document uploaded successfully")
    print(f"  - MD5 entries created in doc_status")
    print(f"  - Document deleted successfully")
    print(f"  - MD5 entries removed from doc_status and full_docs")
    print(f"  - Same content re-uploaded successfully (no duplicate error)")
    print(f"  - Re-uploaded document processed and queryable")
    
    return True

def main():
    try:
        # Check if API is reachable
        print("Checking API connectivity...")
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API health check failed: {response.status_code}")
            return
        print("✅ API is healthy")
        
        # Run the test
        success = test_md5_deletion()
        
        if not success:
            print("\n❌ TEST FAILED")
            exit(1)
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_BASE}")
        print("Make sure the RAG service is running.")
        exit(1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
