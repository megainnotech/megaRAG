import requests
import json

RAG_URL = "http://localhost:8003/query"

def query_rag(text, mode="hybrid"):
    print(f"\n❓ Querying: {text} (Mode: {mode})")
    try:
        response = requests.post(
            RAG_URL,
            json={
                "query": text,
                "mode": mode,
                # We can try clear config to see if default is better
                "llm_config": {
                    "max_tokens": 4000,
                    "temperature": 0.5,
                    "model": "gpt-4o" # Try to force a better model if supported
                }
            },
            stream=True
        )
        
        print("📝 Response stream:")
        full_answer = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_str = decoded_line[6:]
                    try:
                        data = json.loads(json_str)
                        if data['type'] == 'status':
                            print(f"  [STATUS] {data['content']}")
                        elif data['type'] == 'answer':
                            content = data['content']
                            # Some implementations stream tokens, others send full answer
                            if content:
                                print(f"  [ANSWER CHUNK] {content[:50]}..." if len(content) > 50 else f"  [ANSWER CHUNK] {content}")
                                full_answer = content
                        elif data['type'] == 'sources':
                            print(f"  [SOURCES] {data['content']}")
                        elif data['type'] == 'error':
                            print(f"  ❌ ERROR: {data['content']}")
                    except json.JSONDecodeError:
                        pass
                
        print(f"\n✅ Final Answer:\n{full_answer}\n")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    # Test with a query relevant to the README.md properly ingested
    query_rag("How does PromptGuard handle parallel processing?", mode="hybrid")
    query_rag("What are the key components of the lab environment?", mode="naive")
