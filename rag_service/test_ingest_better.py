import urllib.request
import json
import time

url = "http://localhost:8000/ingest"
content = """
The Apollo program was a United States human spaceflight program carried out by the National Aeronautics and Space Administration (NASA), which succeeded in preparing and landing the first humans on the Moon from 1968 to 1972. It was first conceived during the Eisenhower administration in 1960. The program was named after Apollo, the Greek god of light and music, by NASA manager Abe Silverstein. The Apollo program was the third United States human spaceflight program to fly, preceded by the two-man Project Gemini conceived in 1961 and the single-man Mercury program conceived in 1959.
"""

payload = {
    "doc_id": "apollo_program_wiki",
    "type": "text",
    "text_content": content.strip(),
    "tags": {"project": "space_history"}
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
