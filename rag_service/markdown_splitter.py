
import re
from typing import List, Dict, Tuple

def slugify(text: str) -> str:
    """
    Generate a slug from the text compatible with MkDocs (Python-Markdown).
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters
    """
    text = text.lower().strip()
    # Remove non-alphanumeric chars (except spaces and hyphens)
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace whitespace/hyphens with single hyphen
    text = re.sub(r'[-\s]+', '-', text)
    return text

def split_markdown_by_headers(text: str) -> List[Dict[str, str]]:
    """
    Splits markdown text into sections based on headers (#, ##, ###).
    Returns a list of dicts:
    [
        {
            "header": "Section Title",
            "slug": "section-title",
            "content": "# Section Title\n\nContent...",
            "level": 1
        },
        ...
    ]
    The first section might have empty header if content precedes the first header.
    """
    lines = text.split('\n')
    sections = []
    
    current_header = ""
    current_slug = ""
    current_content = []
    current_level = 0
    
    # Regex for headers (1-6 hashes)
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    
    for line in lines:
        match = header_pattern.match(line)
        if match:
            # If we have accumulated content for the previous section, save it
            content = "\n".join(current_content).strip()
            if content or current_header:
                sections.append({
                    "header": current_header,
                    "slug": current_slug,
                    "content": content,
                    "level": current_level
                })
            
            # Start new section
            hashes, title = match.groups()
            current_level = len(hashes)
            current_header = title.strip()
            current_slug = slugify(current_header)
            current_content = [line] # Include the header line in the content
        else:
            current_content.append(line)
            
    # Save the last section
    content = "\n".join(current_content).strip()
    if content or current_header:
        sections.append({
            "header": current_header,
            "slug": current_slug,
            "content": content,
            "level": current_level
        })
        
    return sections
