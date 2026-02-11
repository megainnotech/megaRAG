import urllib.request
import json

url = "http://localhost:8000/query"
payload = {
    "query": "Who named the Apollo program?",
    "mode": "naive",
    "llm_config": {
        "type": "public",
        "model": "gpt-4o-mini"
    }
}
headers = {"Content-Type": "application/json"}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers)

try:
    print(f"Sending Naive query to {url}...")
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        resp_data = response.read().decode('utf-8')
        print(f"Response: {resp_data}")
except Exception as e:
    print(f"Query request failed: {e}")
