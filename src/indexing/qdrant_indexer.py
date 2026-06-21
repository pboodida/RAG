import os
import json
import time
from pathlib import Path
from langchain_core.documents import Document

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import VertexAIEmbeddings

# Import the new dedicated QdrantVectorStore class from the new package
from langchain_qdrant import QdrantVectorStore

def build_qdrant_index(chunks_json_path: str, vector_store_dir: str, gcp_project: str):
    print(f"🚀 Loading Text Chunks from: {chunks_json_path}")
    
    if not os.path.exists(chunks_json_path):
        raise FileNotFoundError("text_chunks.json not found! Run chunker.py first.")
        
    with open(chunks_json_path, "r", encoding="utf-8") as f:
        chunk_data = json.load(f)
        
    documents = [
        Document(page_content=item["content"], metadata=item["metadata"]) 
        for item in chunk_data
    ]
    print(f"📦 Loaded {len(documents)} document chunks.")

    print("🧠 Initializing Vertex AI Embeddings (text-embedding-004)...")
    
    # 🛠️ FIXED: Use VertexAIEmbeddings using Application Default Credentials
    embeddings = VertexAIEmbeddings(
        model="text-embedding-004",  # Ignored the strikethrough, changed model_name to model
        project=gcp_project,
        location="us-central1"
    )
    
    os.makedirs(vector_store_dir, exist_ok=True)

    print("\n⚡ Building Qdrant Vector Index (Local Disk)...")
    start_time = time.time()
    qdrant_path = os.path.join(vector_store_dir, "qdrant_p1")
    
    # Use the new QdrantVectorStore class to build the database
    QdrantVectorStore.from_documents(
        documents, 
        embeddings, 
        path=qdrant_path, 
        collection_name="ifc_annual_report"
    )
    qdrant_time = time.time() - start_time
    print(f"✅ Qdrant Index successfully saved to {qdrant_path} (Took {qdrant_time:.2f}s)")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    chunks_file = str(project_root / "data" / "processed" / "text_chunks.json")
    vs_dir = str(project_root / "data" / "vector_store")
    
    gcp_project_id = "gd-gcp-gridu-genai" 
    build_qdrant_index(chunks_file, vs_dir, gcp_project_id)