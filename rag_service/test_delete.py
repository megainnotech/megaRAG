import urllib.request
import json

url_delete = "http://localhost:8000/documents/tag/space_history"
req = urllib.request.Request(url_delete, method="DELETE")

try:
    print(f"Deleting tag 'space_history' at {url_delete}...")
    with urllib.request.urlopen(req) as response:
        print(f"Delete Status Code: {response.getcode()}")
        print(f"Response: {response.read().decode('utf-8')}")

    # Check count again
    url_check = "http://qdrant:6333/collections/lightrag_vdb_chunks/points/count"
    req_check = urllib.request.Request(url_check, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_check, data=b"{}") as response:
         print(f"Count after delete: {response.read().decode('utf-8')}")

except Exception as e:
    print(f"Request failed: {e}")
