
import requests
import json

def probe(url, method='GET', data=None):
    print(f"Probing {method} {url}")
    try:
        if method == 'GET':
            resp = requests.get(url, timeout=30)
        else:
            resp = requests.post(url, json=data, timeout=60, stream=True)
        
        print(f"Status: {resp.status_code}")
        # print(f"Headers: {resp.headers}")
        try:
            # Read all chunks
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.strip():
                        print(f"Chunk: {decoded}")
        except:
            print("Body: <could not read>")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

probe('http://localhost:8003/docs')
probe('http://localhost:8003/query', 'POST', {'query': 'What is PromptGuard?', 'mode': 'hybrid'})
