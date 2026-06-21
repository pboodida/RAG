import os
import json
from pathlib import Path
from langchain_community.vectorstores import FAISS

# 🛠️ FIXED: Swapped to Vertex AI SDK (No API Keys)
from langchain_google_vertexai import VertexAIEmbeddings

from langchain_core.documents import Document

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]

class SemanticCacheManager:
    """
    Phase 4: Realistic Semantic Caching Engine with GCP Auth.
    """
    def __init__(self, gcp_project_id: str, threshold: float = 0.60):
        self.threshold = threshold
        self.cache_dir = project_root / "data" / "cache" / "semantic_faiss"
        
        # 🛠️ FIXED: Strictly using Vertex AI credentials. 
        # ADC (Application Default Credentials) will handle the auth automatically.
        self.embeddings = VertexAIEmbeddings(
            model="text-embedding-004",
            project=gcp_project_id,
            location="us-central1"
        )
        
        if self.cache_dir.exists() and (self.cache_dir / "index.faiss").exists():
            print("💾 [CACHE SYSTEM]: Found existing Semantic Cache index.")
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=str(self.cache_dir),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"⚠️ [CACHE SYSTEM]: Failed to load disk cache: {e}")
                self.vector_store = None
        else:
            print("🆕 [CACHE SYSTEM]: Initializing fresh memory bank...")
            self.vector_store = None

    def check_cache(self, query: str) -> dict | None:
        if self.vector_store is None:
            print("🔍 [CACHE SYSTEM]: Cache is empty. Routing to PDF pipeline...")
            return None
        
        print(f"🔍 [CACHE SYSTEM]: Scanning cache memory for query: '{query}'")
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=1)
            if results:
                doc, score = results[0]
                print(f"📊 [CACHE SYSTEM]: Closest match: '{doc.page_content}' | Score: {score:.4f}")
                
                if score >= self.threshold:
                    print("⚡ [CACHE SYSTEM]: CACHE HIT! Bypassing backend PDF search.")
                    return {
                        "answer": doc.metadata.get("answer"),
                        "context_docs": doc.metadata.get("context_docs")
                    }
                else:
                    print("❌ [CACHE SYSTEM]: CACHE MISS. Score below threshold.")
            else:
                print("❌ [CACHE SYSTEM]: CACHE MISS. No similar questions found.")
        except Exception as e:
            print(f"⚠️ [CACHE SYSTEM]: Error searching cache: {e}")
            
        return None

    def add_to_cache(self, query: str, answer: str, context_docs: list[Document]) -> None:
        print("📝 [CACHE SYSTEM]: Saving new interaction to memory bank...")
        serialized_contexts = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in context_docs
        ]
        doc = Document(
            page_content=query,
            metadata={"answer": answer, "context_docs": json.dumps(serialized_contexts)}
        )
        
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents([doc], self.embeddings)
        else:
            self.vector_store.add_documents([doc])
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(self.cache_dir))
        print("💾 [CACHE SYSTEM]: Successfully saved cache to disk.")