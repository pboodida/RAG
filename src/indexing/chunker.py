import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """Applies cleaning strategies to normalize extracted text content."""
    if not text:
        return ""
    # Remove weird layout control characters or multiple consecutive newlines
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    # Normalize multiple spaces into a single space
    text = re.sub(r' +', ' ', text)
    return text.strip()

def chunk_text_data(input_json_path: str, output_json_path: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    print(f"🔄 Loading structured text data from: {input_json_path}")
    
    if not os.path.exists(input_json_path):
        raise FileNotFoundError(f"Parsed JSON not found at {input_json_path}. Please execute Phase 0 first.")
        
    with open(input_json_path, "r", encoding="utf-8") as f:
        parsed_blocks = json.load(f)
        
    print(f"🧹 Cleaning text and applying Structure-Aware Chunking (Size: {chunk_size}, Overlap: {chunk_overlap})...")
    
    final_chunks = []
    current_chunk_text = ""
    current_chunk_metadata: Dict[str, Any] = {}
    pages_in_chunk = set()
    content_types_in_chunk = set()
    
    for block in parsed_blocks:
        raw_content = block.get("content", "")
        cleaned_content = clean_text(raw_content)
        
        if not cleaned_content:
            continue
            
        page_num = block.get("page_number", "Unknown")
        content_type = block.get("content_type", "text")
        
        # If adding this block exceeds the chunk size and we already have content, flush the current chunk
        if len(current_chunk_text) + len(cleaned_content) > chunk_size and current_chunk_text:
            final_chunks.append({
                "chunk_id": f"chunk_{len(final_chunks) + 1}",
                "content": current_chunk_text.strip(),
                "metadata": {
                    "pages": list(pages_in_chunk),
                    "primary_page": list(pages_in_chunk)[0] if pages_in_chunk else "Unknown",
                    "content_types_handled": list(content_types_in_chunk),
                    "source": block["metadata"]["source"]
                }
            })
            
            # Handle standard sliding window overlap by rolling back text
            # We take the tail end of the text based on the requested overlap size
            overlap_text = current_chunk_text[-chunk_overlap:] if len(current_chunk_text) > chunk_overlap else current_chunk_text
            current_chunk_text = overlap_text + "\n" + cleaned_content
            
            # Reset chunk tracking variables
            pages_in_chunk = {page_num}
            content_types_in_chunk = {content_type}
        else:
            # Append block text to the active chunk
            if current_chunk_text:
                current_chunk_text += "\n" + cleaned_content
            else:
                current_chunk_text = cleaned_content
                
            pages_in_chunk.add(page_num)
            content_types_in_chunk.add(content_type)
            
    # Flush any remaining text left over at the end of the loop
    if current_chunk_text:
        final_chunks.append({
            "chunk_id": f"chunk_{len(final_chunks) + 1}",
            "content": current_chunk_text.strip(),
            "metadata": {
                "pages": list(pages_in_chunk),
                "primary_page": list(pages_in_chunk)[0] if pages_in_chunk else "Unknown",
                "content_types_handled": list(content_types_in_chunk),
                "source": parsed_blocks[-1]["metadata"]["source"] if parsed_blocks else "Unknown"
            }
        })

    # Save processed chunks to a separate JSON file
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_chunks, f, indent=4)
        
    print(f"✅ Preprocessing complete! Created {len(final_chunks)} isolated text chunks.")
    print(f"💾 Saved cleanly to {output_json_path}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    input_file = str(project_root / "data" / "processed" / "parsed_text_docling.json")
    output_file = str(project_root / "data" / "processed" / "text_chunks.json")
    
    chunk_text_data(input_file, output_file, chunk_size=1200, chunk_overlap=250)