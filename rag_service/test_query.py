import urllib.request
import json

url = "http://localhost:8003/query"
# Use 'naive' or 'local' mode for faster response if 'hybrid' is slow
payload = {
    "query": "What is the Apollo program?",
    "mode": "hybrid",
    "llm_config": {
        "type": "public",
        "model": "gpt-4o-mini"
    }
}
headers = {"Content-Type": "application/json"}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers)

try:
    print(f"Sending query to {url}...")
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        resp_data = response.read().decode('utf-8')
        print(f"Response: {resp_data}")
except Exception as e:
    print(f"Query request failed: {e}")
