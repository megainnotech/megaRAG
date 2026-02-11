import urllib.request
import json

url = "http://qdrant:6333/collections/lightrag_vdb_chunks/points/count"
# Qdrant count API expects POST with empty body or filter
req = urllib.request.Request(url, method="POST", headers={"Content-Type": "application/json"})

try:
    print(f"Checking Qdrant count at {url}...")
    with urllib.request.urlopen(req, data=b"{}") as response:
        print(f"Status Code: {response.getcode()}")
        print(f"Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Request failed: {e}")
