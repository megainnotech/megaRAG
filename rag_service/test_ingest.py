import urllib.request
import json
import time

url = "http://localhost:8000/ingest"
payload = {
    "doc_id": "test_persist_004_py",
    "type": "text",
    "text_content": "Verification content from Python script. Async init check.",
    "tags": {"project": "python_test"}
}
headers = {"Content-Type": "application/json"}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers)

try:
    print(f"Sending request to {url}...")
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        print(f"Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Request failed: {e}")
