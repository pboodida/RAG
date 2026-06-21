import os
from pathlib import Path

# FIX: Prevent OpenMP from crashing the Jupyter Kernel / Terminal on Mac
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import VertexAIEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

def get_baseline_retriever(gcp_project_id: str, db_type: str = "faiss", k: int = 5):
    """
    Initializes and returns a LangChain Retriever using the specified vector database.
    
    Args:
        gcp_project_id (str): Your GCP Project ID for Vertex AI auth.
        db_type (str): "faiss" or "qdrant". Defaults to "faiss" for Phase 1 speed.
        k (int): The number of chunks to retrieve per query.
    """
    # 1. 🛠️ FIXED: Use VertexAIEmbeddings using Application Default Credentials (ADC)
    embeddings = VertexAIEmbeddings(
        model="text-embedding-004",  # Ignored the strikethrough, changed model_name to model
        project=gcp_project_id, 
        location="us-central1"
    )
    
    project_root = Path(__file__).resolve().parents[2]
    
    if db_type.lower() == "faiss":
        faiss_path = str(project_root / "data" / "vector_store" / "faiss_p1")
        if not os.path.exists(faiss_path):
            raise FileNotFoundError(f"FAISS database not found at {faiss_path}. Run faiss_indexer.py first.")
            
        # Load local FAISS database
        vector_db = FAISS.load_local(
            folder_path=faiss_path, 
            embeddings=embeddings, 
            allow_dangerous_deserialization=True
        )
        print("✅ Successfully loaded FAISS Baseline Retriever.")
        
    elif db_type.lower() == "qdrant":
        qdrant_path = str(project_root / "data" / "vector_store" / "qdrant_p1")
        if not os.path.exists(qdrant_path):
            raise FileNotFoundError(f"Qdrant database not found at {qdrant_path}. Run qdrant_indexer.py first.")
            
        # Load local Qdrant database using the modern client structure
        qdrant_client = QdrantClient(path=qdrant_path)
        vector_db = QdrantVectorStore(
            client=qdrant_client, 
            collection_name="ifc_annual_report", 
            embedding=embeddings
        )
        print("✅ Successfully loaded Qdrant Baseline Retriever.")
        
    else:
        raise ValueError("Invalid db_type. Please choose 'faiss' or 'qdrant'.")

    # 2. Convert the vector database into a LangChain Retriever interface
    retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )
    
    return retriever

if __name__ == "__main__":
    # --- Quick Sanity Test ---
    gcp_project = "gd-gcp-gridu-genai" 
    
    print("🚀 Testing Baseline Retriever...")
    retriever = get_baseline_retriever(gcp_project_id=gcp_project, db_type="faiss", k=3)
    
    test_query = "What was the total net income for the fiscal year?"
    print(f"\n🔍 Query: '{test_query}'")
    
    results = retriever.invoke(test_query)
    
    print("\n📄 Top Retrieved Chunks:")
    for i, doc in enumerate(results, 1):
        clean_content = doc.page_content.replace("\n", " ")[:150]
        print(f"\n[{i}] Pages: {doc.metadata.get('pages', 'Unknown')} | Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"    Excerpt: {clean_content}...")