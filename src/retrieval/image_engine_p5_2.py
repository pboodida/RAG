import os
import sys
from pathlib import Path
from langchain_qdrant import QdrantVectorStore

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
from langchain_core.documents import Document

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import Phase 3 for background context
from src.retrieval.advanced_pipeline_p3 import get_production_phase3_retriever

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

class ImageRetrievalEngine:
    """
    Phase 5.2 - Image Retrieval Engine.
    Queries visual chart descriptions and merges with Phase 3 text context.
    """
    def __init__(self):
        # 🛠️ FIXED: Swapped to VertexAIEmbeddings using ADC
        self.embeddings = VertexAIEmbeddings(
            model="text-embedding-004", # Ignored the strikethrough, changed model_name to model
            project=GCP_PROJECT_ID,
            location="us-central1"
        )
        self.qdrant_path = project_root / "data" / "vector_store" / "qdrant_multimodal_images"
        
        self.vector_store = QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            path=str(self.qdrant_path),
            collection_name="ifc_multimodal_images"
        )
        
        # 🛠️ FIXED: Swapped to ChatVertexAI and set model_name="gemini-2.5-flash"
        self.llm = ChatVertexAI(
            model_name="gemini-2.5-flash", 
            project=GCP_PROJECT_ID, 
            location="us-central1",
            temperature=0.0
        )

    def retrieve_integrated(self, query: str, k_images: int = 2, k_text: int = 3) -> list[Document]:
        print(f"🔍 Searching Chart/Graph Vectors for: '{query}'")
        image_retriever = self.vector_store.as_retriever(search_kwargs={"k": k_images})
        image_docs = image_retriever.invoke(query)
        
        try:
            print("📖 Fetching background text blocks from Phase 3 production index...")
            text_retriever = get_production_phase3_retriever(gcp_project_id=GCP_PROJECT_ID, k=k_text)
            text_docs = text_retriever.invoke(query, start_page=1, end_page=20, retrieval_mode="Hybrid Search")
        except Exception as e:
            text_docs = []
            
        return image_docs + text_docs

    def synthesize_answer(self, query: str, retrieved_docs: list[Document]) -> str:
        if not retrieved_docs:
            return "No relevant visual or textual data points discovered."

        context_str = ""
        for idx, doc in enumerate(retrieved_docs, 1):
            doc_type = doc.metadata.get("content_types_handled", "Text")
            page = doc.metadata.get("primary_page", "Unknown")
            context_str += f"--- BLOCK [{idx}] (Type: {doc_type} | Page {page}) ---\n{doc.page_content}\n\n"

        prompt = f"""You are a senior financial auditor.
Analyze the user query based ONLY on the visual chart descriptions and text fragments provided below.

GROUNDING REQUIREMENTS:
1. If the user asks about visual trends, look closely at the 'Image/Chart' blocks.
2. Combine the visual chart insights with textual background context if available.
3. Explicitly declare if the data source originated from a Graph/Chart description or a textual section.

RETRIEVED DATA BLOCKS:
{context_str}

USER QUESTION: {query}

Provide a structured analysis:"""

        response = self.llm.invoke(prompt)
        return str(response.content)