import requests
import json
import time

BASE_URL = "http://localhost:3001/api/documents"

def test_zip_upload():
    print("\nTesting Zip Upload...")
    try:
        with open("test_mkdocs.zip", "rb") as f:
            files = {'file': f}
            data = {'tags': '{"type":"zip_test"}'}
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 201:
            doc = response.json()
            print(f"Zip Upload Success: {doc['id']}")
            print(f"Type: {doc['type']}")
            print(f"Local Path: {doc['localPath']}")
            if doc['type'] == 'git' and '/docs/' in doc['localPath']:
                 print("Verification: Zip detected as MkDocs and processed correctly.")
                 return True
            else:
                 print("Verification Failed: Doc type or path incorrect.")
                 return False
        else:
            print(f"Zip Upload Failed: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Wait for service a bit
    time.sleep(5)
    test_zip_upload()
