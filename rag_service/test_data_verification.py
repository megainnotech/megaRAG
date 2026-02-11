
import requests
import json
import time
import os
import sys
from neo4j import GraphDatabase

# Config
API_URL = "http://localhost:8000"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

def test_ingestion():
    doc_id = f"test_verify_{int(time.time())}"
    print(f"--- Starting Ingestion Test for DocID: {doc_id} ---")
    sys.stdout.flush()
    
    payload = {
        "doc_id": doc_id,
        "type": "text",
        "text_content": f"Verification content for {doc_id}. Checking database persistence for Neo4j and Qdrant.",
        "tags": {"project": "verification_test"}
    }
    
    # 1. Ingest
    try:
        print(f"Sending POST request to {API_URL}/ingest...")
        resp = requests.post(f"{API_URL}/ingest", json=payload, timeout=10)
        print(f"Response Status: {resp.status_code}")
        print(f"Response Body: {resp.text}")
        if resp.status_code != 200:
            print("Ingestion failed.")
            return
    except Exception as e:
        print(f"Ingestion request error: {e}")
        return

    print("Waiting 10 seconds for async processing...")
    sys.stdout.flush()
    time.sleep(10)
    
    # 2. Check Neo4j
    print("\n--- Checking Neo4j ---")
    try:
        print(f"Connecting to Neo4j at {NEO4J_URI}...")
        with GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH) as driver:
            try:
                driver.verify_connectivity()
                print("Neo4j connectivity verified.")
            except Exception as e:
                 print(f"Neo4j connectivity check failed: {e}")
                 # Continue to try query anyway? No, return if connectivity fails.
                 
            records, summary, keys = driver.execute_query(
                "MATCH (n) RETURN count(n) as count", 
            )
            count = records[0]["count"]
            print(f"Total Neo4j Node Count: {count}")
    except Exception as e:
        print(f"Neo4j Check Failed: {e}")

    # 3. Check Qdrant
    print("\n--- Checking Qdrant ---")
    try:
        print(f"Connecting to Qdrant at {QDRANT_URL}...")
        res = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        if res.status_code == 200:
             collections = res.json().get("result", {}).get("collections", [])
             print(f"Found {len(collections)} collections.")
             for col_info in collections:
                 name = col_info['name']
                 count_res = requests.post(f"{QDRANT_URL}/collections/{name}/points/count", json={"exact": True}, timeout=5)
                 count = count_res.json().get("result", {}).get("count", 0)
                 print(f" - Collection '{name}': {count} points")
        else:
            print(f"Failed to list collections: {res.status_code}")
    except Exception as e:
        print(f"Qdrant Check Failed: {e}")
            
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_ingestion()
