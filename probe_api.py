
import requests
import json

def probe(url, method='GET', data=None):
    print(f"Probing {method} {url}")
    try:
        if method == 'GET':
            resp = requests.get(url, timeout=5)
        else:
            resp = requests.post(url, json=data, timeout=5, stream=True)
        
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        try:
            print(f"Body: {resp.text[:500]}")
        except:
            print("Body: <could not read>")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

probe('http://localhost:8000/docs')
probe('http://localhost:8000/query', 'POST', {'query': 'test', 'mode': 'hybrid'})
probe('http://localhost:8000/query/', 'POST', {'query': 'test', 'mode': 'hybrid'}) # Trailing slash
probe('http://127.0.0.1:8000/query', 'POST', {'query': 'test', 'mode': 'hybrid'})
