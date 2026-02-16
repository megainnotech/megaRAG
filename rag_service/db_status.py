import urllib.request
import json

print("\n=== DATABASE STATUS ===\n")

# Check Qdrant
print("QDRANT VECTOR DATABASE:")
print("-" * 40)
try:
    collections = ['lightrag_vdb_chunks', 'lightrag_vdb_entities', 'lightrag_vdb_relationships']
    for coll in collections:
        url = f"http://qdrant:6333/collections/{coll}"
        req = urllib.request.Request(url, method="GET")
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        count = data['result']['points_count']
        print(f"  {coll}: {count} points")
except Exception as e:
    print(f"  Error: {e}")

print("\nNEO4J GRAPH DATABASE:")
print("-" * 40)
print("  Run manually: docker-compose exec neo4j cypher-shell -u neo4j -p password")
print("  Query: MATCH (n) RETURN count(n)")
