import os
import sys
import json
from pathlib import Path

# Fix macOS background crashes for ML models
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.documents import Document
from langchain_community.retrievers.bm25 import BM25Retriever

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import VertexAIEmbeddings

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import CrossEncoder

class UnifiedPhase3Pipeline:
    """
    The ultimate Phase 3 Engine: Combines Page Filtering, Multi-Strategy Search 
    (Sparse, Dense, or Hybrid RRF Fusion), and Cross-Encoder Re-ranking.
    """
    def __init__(self, gcp_project_id: str, final_k: int = 4, rrf_c: int = 60):
        self.final_k = final_k
        self.rrf_c = rrf_c
        
        # 1. Initialize Dense Components (Qdrant with Vertex AI Embeddings via ADC)
        self.embeddings = VertexAIEmbeddings(
            model="text-embedding-004", # Ignored the strikethrough, changed model_name to model
            project=gcp_project_id, 
            location="us-central1"
        )
        self.qdrant_path = str(project_root / "data" / "vector_store" / "qdrant_p1")
        self.qdrant_client = QdrantClient(path=self.qdrant_path)
        self.vector_db = QdrantVectorStore(
            client=self.qdrant_client, 
            collection_name="ifc_annual_report", 
            embedding=self.embeddings
        )
        
        # 2. Initialize Sparse Components (BM25)
        self.raw_chunks_path = project_root / "data" / "processed" / "text_chunks.json"
        self.all_documents = self._load_raw_json_documents()
        
        # 3. Initialize Re-ranking Component (Cross-Encoder)
        print("🧠 Initializing Native HuggingFace Cross-Encoder...")
        self.reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def _load_raw_json_documents(self) -> list[Document]:
        """Helper to safely construct LangChain Document objects from data disk."""
        with open(self.raw_chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        docs: list[Document] = []
        for item in data:
            docs.append(Document(page_content=str(item["content"]), metadata=dict(item.get("metadata", {}))))
        return docs

    def invoke(self, query: str, start_page: int | None = None, end_page: int | None = None, retrieval_mode: str = "Hybrid Search") -> list[Document]:
        # --- PHASE 3 / TASK 2: METADATA PRE-FILTERING ---
        # A. Filter BM25 Documents in memory
        filtered_sparse_docs = []
        for doc in self.all_documents:
            page = doc.metadata.get("primary_page", 0)
            if start_page is not None and page < start_page:
                continue
            if end_page is not None and page > end_page:
                continue
            filtered_sparse_docs.append(doc)
            
        if not filtered_sparse_docs:
            return []
            
        bm25_retriever = BM25Retriever.from_documents(filtered_sparse_docs)
        bm25_retriever.k = 15
        
        # B. Build Qdrant DB Filters dynamically
        must_conditions = []
        if start_page is not None:
            must_conditions.append(rest.FieldCondition(key="metadata.primary_page", range=rest.Range(gte=start_page)))
        if end_page is not None:
            must_conditions.append(rest.FieldCondition(key="metadata.primary_page", range=rest.Range(lte=end_page)))
        qdrant_filter = rest.Filter(must=must_conditions) if must_conditions else None
        
        dense_retriever = self.vector_db.as_retriever(search_kwargs={"k": 15, "filter": qdrant_filter})

        candidates: list[Document] = []

        # --- MULTI-STRATEGY ROUTING CONTROL ---
        if "Sparse Only" in retrieval_mode:
            candidates = bm25_retriever.invoke(query)
            
        elif "Dense Only" in retrieval_mode:
            candidates = dense_retriever.invoke(query)
            
        else:
            # Execute Hybrid Search with Reciprocal Rank Fusion (RRF)
            sparse_results = bm25_retriever.invoke(query)
            dense_results = dense_retriever.invoke(query)

            rrf_scores: dict[str, float] = {}
            doc_map: dict[str, Document] = {}

            for rank, doc in enumerate(sparse_results, 1):
                content = doc.page_content
                doc_map[content] = doc
                rrf_scores[content] = rrf_scores.get(content, 0.0) + (1.0 / (self.rrf_c + rank))

            for rank, doc in enumerate(dense_results, 1):
                content = doc.page_content
                doc_map[content] = doc
                rrf_scores[content] = rrf_scores.get(content, 0.0) + (1.0 / (self.rrf_c + rank))

            sorted_by_rrf = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
            candidates = [doc_map[content] for content in sorted_by_rrf[:30]]

        if not candidates:
            return []

        # --- PHASE 3 / TASK 1: DEEP CROSS-ENCODER RE-RANKING ---
        pairs = [[query, doc.page_content] for doc in candidates]
        scores = self.reranker_model.predict(pairs)
        
        for doc, score in zip(candidates, scores):
            doc.metadata["relevance_score"] = float(score)
            
        reranked_docs = sorted(candidates, key=lambda x: x.metadata["relevance_score"], reverse=True)
        return reranked_docs[:self.final_k]

def get_production_phase3_retriever(gcp_project_id: str, k: int = 4) -> UnifiedPhase3Pipeline:
    return UnifiedPhase3Pipeline(gcp_project_id=gcp_project_id, final_k=k)