import urllib.request
import json
import time

url = "http://localhost:8003/ingest"
payload = {
    "doc_id": "apollo_program_wiki",
    "type": "text",
    "text_content": "The Apollo program was an American spaceflight program carried out by NASA, which succeeded in landing the first humans on the Moon from 1969 to 1972.",
    "tags": {"project": "wiki_test"},
    "file_path": "https://en.wikipedia.org/wiki/Apollo_program"
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
