#!/usr/bin/env python3
"""
Script to check the status of both Qdrant and Neo4j databases
"""
import urllib.request
import json
from neo4j import GraphDatabase

print("=" * 60)
print("DATABASE STATUS CHECK")
print("=" * 60)

# Check Qdrant
print("\n[1] Checking Qdrant Vector Database...")
print("-" * 60)

qdrant_url = "http://qdrant:6333"
collections_url = f"{qdrant_url}/collections"

try:
    # Get all collections
    req = urllib.request.Request(collections_url, method="GET")
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        collections = result.get('result', {}).get('collections', [])
        
        if collections:
            print(f"✓ Found {len(collections)} collection(s):")
            for coll in collections:
                coll_name = coll['name']
                print(f"\n  Collection: {coll_name}")
                
                # Get point count for each collection
                count_url = f"{qdrant_url}/collections/{coll_name}"
                count_req = urllib.request.Request(count_url, method="GET")
                with urllib.request.urlopen(count_req) as count_response:
                    count_result = json.loads(count_response.read().decode('utf-8'))
                    points_count = count_result.get('result', {}).get('points_count', 0)
                    print(f"  Points count: {points_count}")
        else:
            print("✗ No collections found in Qdrant")
            
except Exception as e:
    print(f"✗ Failed to connect to Qdrant: {e}")

# Check Neo4j
print("\n[2] Checking Neo4j Graph Database...")
print("-" * 60)

neo4j_uri = "bolt://neo4j:7687"
neo4j_user = "neo4j"
neo4j_password = "password"

try:
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()['count']
        print(f"✓ Total nodes: {node_count}")
        
        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()['count']
        print(f"✓ Total relationships: {rel_count}")
        
        # Get node labels
        result = session.run("CALL db.labels()")
        labels = [record['label'] for record in result]
        if labels:
            print(f"\n  Node labels ({len(labels)}):")
            for label in labels:
                # Count nodes for each label
                count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                count = count_result.single()['count']
                print(f"    - {label}: {count} nodes")
        else:
            print("✗ No node labels found")
        
        # Get relationship types
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [record['relationshipType'] for record in result]
        if rel_types:
            print(f"\n  Relationship types ({len(rel_types)}):")
            for rel_type in rel_types:
                # Count relationships for each type
                count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                count = count_result.single()['count']
                print(f"    - {rel_type}: {count} relationships")
        else:
            print("✗ No relationship types found")
            
    driver.close()
    
except Exception as e:
    print(f"✗ Failed to connect to Neo4j: {e}")

print("\n" + "=" * 60)
print("CHECK COMPLETE")
print("=" * 60)
