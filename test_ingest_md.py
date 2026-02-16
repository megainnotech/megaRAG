#!/usr/bin/env python3
"""
Test script to ingest markdown files directly into the RAG system
"""
import asyncio
import requests
import json
import time

# Configuration
RAG_SERVICE_URL = "http://localhost:8003"

def check_rag_status():
    """Check if RAG service is ready"""
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/health")
        data = response.json()
        print(f"🏥 Health Status: {data}")
        return data.get("ready", False)
    except Exception as e:
        print(f"❌ RAG service not accessible: {e}")
        return False

def ingest_file(file_path, doc_id, ingest_type="text", tags=None):
    """Ingest a single markdown file"""
    print(f"\n{'='*60}")
    print(f"📁 Ingesting: {file_path}")
    print(f"📝 Doc ID: {doc_id}")
    print(f"🏷️  Tags: {tags}")
    print(f"{'='*60}")
    
    try:
        # Read the markdown file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📊 Content length: {len(content)} characters")
        
        # Prepare request payload
        payload = {
            "doc_id": doc_id,
            "type": ingest_type,
            "text_content": content,
            "tags": tags or {}
        }
        
        # Send to RAG service
        print(f"\n⏳ Sending to RAG service...")
        response = requests.post(
            f"{RAG_SERVICE_URL}/ingest",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ingestion accepted: {result}")
            return True
        else:
            print(f"❌ Ingestion failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        return False

def check_databases():
    """Check if data appears in databases"""
    print(f"\n{'='*60}")
    print("🔍 CHECKING DATABASES")
    print(f"{'='*60}")
    
    # Note: This would need to be run inside the container
    # For now, we'll just indicate that manual checking is needed
    print("\n📌 To check databases, run:")
    print("   docker-compose exec -T rag_service python db_status.py")
    print("\n📌 Or check Qdrant collections:")
    print("   curl http://localhost:6333/collections")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 RAG INGESTION TEST")
    print("="*60)
    
    # Check service health
    print("\n1️⃣  Checking RAG service status...")
    if not check_rag_status():
        print("❌ RAG service is not ready. Please start the service first.")
        exit(1)
    print("✅ RAG service is ready!")
    
    # Test file path
    test_file = "C:\\Users\\prem\\.gemini\\antigravity\\scratch\\docs_chunk\\test_data\\promptguard-idl-main\\README.md"
    
    # Test ingestion
    print("\n2️⃣  Testing markdown file ingestion...")
    success = ingest_file(
        file_path=test_file,
        doc_id="test_readme_001",
        ingest_type="text",
        tags={"project": "promptguard", "type": "docs"}
    )
    
    if success:
        print("\n3️⃣  Waiting for processing (10 seconds)...")
        time.sleep(10)
        
        print("\n4️⃣  Ingestion request completed!")
        check_databases()
    else:
        print("\n❌ Ingestion failed!")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)
