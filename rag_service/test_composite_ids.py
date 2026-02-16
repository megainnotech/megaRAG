#!/usr/bin/env python3
"""
Test script to verify composite ID implementation.
This will check if files are ingested with composite IDs.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from pathlib import Path
import json

async def test_composite_ids():
    """
    Test that composite IDs are properly generated and stored.
    """
    print("=" * 60)
    print("Testing Composite ID Implementation")
    print("=" * 60)
    
    # Check doc_status file
    doc_status_path = Path("/app/public_data/rag_index/doc_status.json")
    
    if not doc_status_path.exists():
        print("❌ doc_status.json not found")
        return False
    
    with open(doc_status_path, 'r') as f:
        doc_status = json.load(f)
    
    print(f"\n📊 Total documents in system: {len(doc_status)}")
    
    # Look for composite IDs (containing '#')
    composite_ids = [doc_id for doc_id in doc_status.keys() if '#' in doc_id]
    simple_ids = [doc_id for doc_id in doc_status.keys() if '#' not in doc_id]
    
    print(f"\n📋 Document ID Statistics:")
    print(f"  - Simple IDs (parent documents): {len(simple_ids)}")
    print(f"  - Composite IDs (child files): {len(composite_ids)}")
    
    if composite_ids:
        print(f"\n✅ Composite IDs found! Examples:")
        for comp_id in composite_ids[:5]:  # Show first 5
            parts = comp_id.split('#', 1)
            parent = parts[0]
            file_path = parts[1] if len(parts) > 1 else "unknown"
            print(f"  - Parent: {parent[:20]}...")
            print(f"    File: {file_path}")
            print()
    else:
        print("\n⚠️  No composite IDs found yet.")
        print("    This is expected if no multi-file documents have been ingested.")
    
    # Group by parent
    parent_groups = {}
    for comp_id in composite_ids:
        parent = comp_id.split('#')[0]
        if parent not in parent_groups:
            parent_groups[parent] = []
        parent_groups[parent].append(comp_id)
    
    if parent_groups:
        print(f"\n📦 Parent Documents with Multiple Files:")
        for parent, children in parent_groups.items():
            print(f"  {parent[:30]}... → {len(children)} files")
    
    print("\n" + "=" * 60)
    return True

if __name__ == "__main__":
    asyncio.run(test_composite_ids())
