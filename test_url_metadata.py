
import requests
import json
import time
import os

BASE_URL = "http://localhost:8003" # host port mapped to 8000

def test_ingest_and_query():
    print("1. Creating dummy file...")
    # I can't write to public_data directly from this script unless I use the write_to_file tool separately
    # or assume the script runs where public_data is accessible.
    # But I can use the ingset text endpoint! 
    # Wait, the requirement was about file paths.
    # Text ingestion doesn't have a file path to construct URL from unless I lie in the request?
    # No, let's use type 'file'.
    # I will ask the agent to create the file first.
    
    doc_id = f"test-doc-{int(time.time())}"
    filename = "test_url_metadata.txt"
    
    print(f"2. Ingesting type='file' doc_id={doc_id} filename={filename}")
    payload = {
        "doc_id": doc_id,
        "type": "file",
        "local_path": filename,
        "tags": {"project": "test"}
    }
    
    try:
        res = requests.post(f"{BASE_URL}/ingest", json=payload)
        print(f"Ingest Status: {res.status_code}")
        print(f"Ingest Response: {res.text}")
        
        if res.status_code != 200:
            return

        print("3. Waiting for ingestion (10s)...")
        time.sleep(10)
        
        print("4. Querying...")
        query_payload = {
            "query": "What is in the test file?",
            "mode": "hybrid",
            "llm_config": {
                "type": "local", # fast
                "model": "llama3" # or whatever is available, or use public if key set
                # Let's use direct mode? No, we need RAG to test URL retrieval.
            } 
        }
        # Actually, let's just use default config which main.py sets up.
        
        res = requests.post(f"{BASE_URL}/query", json=query_payload, stream=True)
        print(f"Query Status: {res.status_code}")
        
        print("Query Response Stream:")
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(decoded_line)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ingest_and_query()
