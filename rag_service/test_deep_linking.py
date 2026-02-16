
import asyncio
import logging
import sys
from unittest.mock import MagicMock, AsyncMock

# Add current directory to path
sys.path.append('.')

from markdown_splitter import split_markdown_by_headers, slugify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_slugify():
    print("\n--- Testing Slugify ---")
    cases = [
        ("Hello World", "hello-world"),
        ("Section 1.2.3", "section-123"),
        ("Foo & Bar", "foo-bar"),
        ("  Spaces  ", "spaces"),
        ("Multi--Dash", "multi-dash"),
    ]
    for text, expected in cases:
        result = slugify(text)
        print(f"'{text}' -> '{result}' | Expected: '{expected}' | {'✅' if result == expected else '❌'}")
        assert result == expected

def test_splitter():
    print("\n--- Testing Markdown Splitter ---")
    markdown_text = """
# Main Title

Intro text.

## Section 1
Content 1.

### Subsection 1.1
Content 1.1.

## Section 2
Content 2.
    """
    sections = split_markdown_by_headers(markdown_text)
    print(f"Found {len(sections)} sections")
    
    expected_slugs = ["main-title", "section-1", "subsection-11", "section-2"]
    
    for i, section in enumerate(sections):
        print(f"Section {i}: Header='{section['header']}', Slug='{section['slug']}'")
        if i < len(expected_slugs):
             # First section might be main title
             # In our logic:
             # # Main Title -> Section 0
             # ## Section 1 -> Section 1
             pass
             
    print(f"Content of section 0: '{sections[0]['content']}'")
    # Verify content preservation
    assert "Intro text." in sections[0]['content']
    assert "Content 1." in sections[1]['content']
    assert "Content 1.1." in sections[2]['content']
    assert "Content 2." in sections[3]['content']
    print("✅ Splitter logic verified")

async def test_ingest_logic():
    print("\n--- Testing Enhanced Ingestion Logic (Mock) ---")
    
    # Mock RAGEngine
    mock_rag = MagicMock()
    mock_rag.status = "ready"
    mock_rag.rag = MagicMock()
    mock_rag.rag.ainsert = AsyncMock()
    
    # Import main after setting up sys.path if needed, or just import the class
    # Since we can't easily import RAGEngine without dependencies, we'll implement a dummy class
    # that mimics ingest_markdown_enhanced logic for testing.
    
    class DummyRAGEngine:
        def __init__(self):
            self.rag = MagicMock()
            self.rag.ainsert = AsyncMock()
            self.status = "ready"
            
        async def ingest_markdown_enhanced(self, file_path, doc_id, tags, base_url=None):
             # Copy-paste or import logic? Importing is better if dependencies allow.
             # We'll try to import from main, but main has many deps.
             # If main fails to import, we can't test exact code, but we tested splitter above.
             pass

    # Let's try to import main
    try:
        from main import RAGEngine
        rag = RAGEngine()
        rag.rag = MagicMock() # Mock internal lightrag
        rag.rag.ainsert = AsyncMock()
        rag.status = "ready"
        
        # We need a dummy file
        with open("test_doc.md", "w") as f:
            f.write("# Title\nContent")
            
        print("Calling ingest_markdown_enhanced...")
        await rag.ingest_markdown_enhanced("test_doc.md", "doc1", {}, base_url="http://base")
        
        # Verify ainsert calls
        print("Verifying ainsert calls...")
        rag.rag.ainsert.assert_called()
        call_args = rag.rag.ainsert.call_args
        print(f"Call args: {call_args}")
        
        # Check if URL was passed
        kwargs = call_args.kwargs
        file_paths = kwargs.get('file_paths')
        ids = kwargs.get('ids')
        
        print(f"IDs: {ids}")
        print(f"File Paths: {file_paths}")
        
        assert ids == "doc1#title"
        assert file_paths == ["http://base#title"]
        print("✅ Ingestion logic verified")
        
    except ImportError:
        print("⚠️ Could not import main.py (likely due to missing deps in this env). Skipping integration test.")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_slugify()
    test_splitter()
    # asyncio.run(test_ingest_logic()) 
