"""
Comprehensive database inspection script to check current state
"""
import asyncio
import sys
import os
import json

# Add the rag_service directory to path
sys.path.insert(0, '/app')

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def inspect_databases():
    """Inspect all databases to see current state"""
    
    print("\n" + "="*80)
    print("DATABASE INSPECTION REPORT")
    print("="*80)
    
    # Import after path setup
    from main import rag_engine
    from qdrant_client import QdrantClient
    from neo4j import AsyncGraphDatabase
    
    if not rag_engine.rag:
        print("❌ RAG engine not initialized!")
        return
    
    # ========================================
    # 1. CHECK DOC_STATUS STORAGE
    # ========================================
    print("\n" + "="*80)
    print("1. DOC_STATUS STORAGE")
    print("="*80)
    
    try:
        all_keys = await rag_engine.rag.doc_status.get_all_keys()
        print(f"📊 Total documents in doc_status: {len(all_keys)}")
        
        if all_keys:
            # Count by type
            md5_docs = [k for k in all_keys if k.startswith("doc-")]
            composite_docs = [k for k in all_keys if "#" in k]
            other_docs = [k for k in all_keys if not k.startswith("doc-") and "#" not in k]
            
            print(f"\n📋 Breakdown:")
            print(f"  - MD5 doc IDs (doc-*): {len(md5_docs)}")
            print(f"  - Composite IDs (*#*): {len(composite_docs)}")
            print(f"  - Other IDs: {len(other_docs)}")
            
            # Show samples
            print(f"\n📝 Sample IDs:")
            for i, key in enumerate(all_keys[:10]):
                print(f"  {i+1}. {key}")
            if len(all_keys) > 10:
                print(f"  ... and {len(all_keys) - 10} more")
                
            # Get detailed info for first few
            if len(all_keys) > 0:
                sample_ids = all_keys[:3]
                doc_info = await rag_engine.rag.doc_status.get_by_ids(sample_ids)
                print(f"\n🔍 Sample document details:")
                for doc_id, info in doc_info.items():
                    if isinstance(info, dict):
                        print(f"\n  {doc_id}:")
                        print(f"    - file_path: {info.get('file_path', 'N/A')}")
                        print(f"    - status: {info.get('status', 'N/A')}")
                        print(f"    - chunks_count: {len(info.get('chunks_list', []))}")
        else:
            print("✅ No documents in doc_status (clean state)")
            
    except Exception as e:
        print(f"❌ Error checking doc_status: {e}")
    
    # ========================================
    # 2. CHECK FULL_DOCS STORAGE
    # ========================================
    print("\n" + "="*80)
    print("2. FULL_DOCS STORAGE")
    print("="*80)
    
    try:
        full_docs_keys = await rag_engine.rag.full_docs.get_all_keys()
        print(f"📊 Total documents in full_docs: {len(full_docs_keys)}")
        
        if full_docs_keys:
            md5_full = [k for k in full_docs_keys if k.startswith("doc-")]
            composite_full = [k for k in full_docs_keys if "#" in k]
            
            print(f"\n📋 Breakdown:")
            print(f"  - MD5 doc IDs: {len(md5_full)}")
            print(f"  - Composite IDs: {len(composite_full)}")
            
            # Show samples
            print(f"\n📝 Sample IDs:")
            for i, key in enumerate(full_docs_keys[:5]):
                print(f"  {i+1}. {key}")
        else:
            print("✅ No documents in full_docs (clean state)")
            
    except Exception as e:
        print(f"❌ Error checking full_docs: {e}")
    
    # ========================================
    # 3. CHECK QDRANT CHUNKS
    # ========================================
    print("\n" + "="*80)
    print("3. QDRANT CHUNKS COLLECTION")
    print("="*80)
    
    try:
        if hasattr(rag_engine.rag, 'chunks_vdb') and hasattr(rag_engine.rag.chunks_vdb, '_client'):
            client = rag_engine.rag.chunks_vdb._client
            collection_name = rag_engine.rag.chunks_vdb.final_namespace
            
            collection_info = client.get_collection(collection_name)
            print(f"📊 Collection: {collection_name}")
            print(f"📊 Total chunks: {collection_info.points_count}")
            print(f"📊 Vector size: {collection_info.config.params.vectors.size}")
            
            # Get sample points
            if collection_info.points_count > 0:
                results = client.scroll(
                    collection_name=collection_name,
                    limit=5,
                    with_payload=True,
                    with_vectors=False
                )
                points, _ = results
                
                print(f"\n📝 Sample chunks:")
                doc_ids_found = set()
                for i, point in enumerate(points):
                    if point.payload:
                        doc_id = point.payload.get('doc_id', 'N/A')
                        chunk_id = point.payload.get('id', 'N/A')
                        doc_ids_found.add(doc_id)
                        print(f"  {i+1}. doc_id: {doc_id}")
                        print(f"     chunk_id: {chunk_id}")
                
                print(f"\n🔑 Unique doc_ids in chunks: {len(doc_ids_found)}")
                for doc_id in list(doc_ids_found)[:5]:
                    print(f"  - {doc_id}")
        else:
            print("❌ chunks_vdb not available")
            
    except Exception as e:
        print(f"❌ Error checking Qdrant chunks: {e}")
    
    # ========================================
    # 4. CHECK QDRANT ENTITIES
    # ========================================
    print("\n" + "="*80)
    print("4. QDRANT ENTITIES COLLECTION")
    print("="*80)
    
    try:
        if hasattr(rag_engine.rag, 'entities_vdb') and hasattr(rag_engine.rag.entities_vdb, '_client'):
            client = rag_engine.rag.entities_vdb._client
            collection_name = rag_engine.rag.entities_vdb.final_namespace
            
            collection_info = client.get_collection(collection_name)
            print(f"📊 Collection: {collection_name}")
            print(f"📊 Total entities: {collection_info.points_count}")
            
            # Get sample points
            if collection_info.points_count > 0:
                results = client.scroll(
                    collection_name=collection_name,
                    limit=5,
                    with_payload=True,
                    with_vectors=False
                )
                points, _ = results
                
                print(f"\n📝 Sample entities:")
                entity_doc_ids = set()
                for i, point in enumerate(points):
                    if point.payload:
                        doc_id = point.payload.get('doc_id', 'N/A')
                        entity_name = point.payload.get('entity_name', 'N/A')
                        entity_doc_ids.add(doc_id)
                        print(f"  {i+1}. entity: {entity_name}")
                        print(f"     doc_id: {doc_id}")
                
                print(f"\n🔑 Unique doc_ids in entities: {len(entity_doc_ids)}")
        else:
            print("❌ entities_vdb not available")
            
    except Exception as e:
        print(f"❌ Error checking Qdrant entities: {e}")
    
    # ========================================
    # 5. CHECK NEO4J
    # ========================================
    print("\n" + "="*80)
    print("5. NEO4J GRAPH DATABASE")
    print("="*80)
    
    try:
        if hasattr(rag_engine.rag, 'chunk_entity_relation_graph'):
            graph = rag_engine.rag.chunk_entity_relation_graph
            workspace_label = graph._get_workspace_label()
            
            # Count nodes
            async with graph._driver.session(database=graph._DATABASE) as session:
                # Count nodes
                result = await session.run(f"MATCH (n:`{workspace_label}`) RETURN count(n) as count")
                record = await result.single()
                node_count = record['count'] if record else 0
                
                print(f"📊 Total nodes: {node_count}")
                
                # Count relationships
                result = await session.run(f"MATCH (a:`{workspace_label}`)-[r]-(b:`{workspace_label}`) RETURN count(r) as count")
                record = await result.single()
                rel_count = record['count'] if record else 0
                
                print(f"📊 Total relationships: {rel_count}")
                
                # Get sample nodes
                if node_count > 0:
                    result = await session.run(
                        f"MATCH (n:`{workspace_label}`) RETURN n.entity_name as name, n.source_id as source_id LIMIT 5"
                    )
                    records = await result.data()
                    
                    print(f"\n📝 Sample nodes:")
                    for i, record in enumerate(records):
                        print(f"  {i+1}. {record.get('name', 'N/A')}")
                        source_id = record.get('source_id', '')
                        if source_id:
                            # Show first chunk ID
                            chunk_ids = source_id.split('\x00')
                            if chunk_ids:
                                print(f"     chunk: {chunk_ids[0][:50]}...")
        else:
            print("❌ Neo4j graph not available")
            
    except Exception as e:
        print(f"❌ Error checking Neo4j: {e}")
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print(f"\n✅ Database inspection complete!")
    print(f"\n💡 Next steps:")
    if all_keys and any(k.startswith("doc-") for k in all_keys):
        print(f"  ⚠️  Found MD5 doc IDs in storage")
        print(f"  → You need to clear the database before testing the fix")
        print(f"  → Run: docker-compose down && docker volume rm docs_chunk_neo4j_data docs_chunk_qdrant_data")
    elif all_keys and any("#" in k for k in all_keys):
        print(f"  ✅ Found composite IDs - fix is working!")
        print(f"  → Test deletion and re-upload workflow")
    else:
        print(f"  📭 Database is empty - ready for fresh upload")
        print(f"  → Upload documents to test the fix")

if __name__ == "__main__":
    asyncio.run(inspect_databases())
