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

# Import your Phase 3 text retrieval pipeline dynamically
from src.retrieval.advanced_pipeline_p3 import get_production_phase3_retriever

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

class TableRetrievalEngine:
    """
    Phase 5.1 - Task 3: Integrated Retrieval Engine.
    Queries both the isolated Markdown table collection and merges with Phase 3 text context.
    """
    def __init__(self):
        # 🛠️ FIXED: Swapped to VertexAIEmbeddings (using model instead of model_name to fix Pylance)
        self.embeddings = VertexAIEmbeddings(
            model="text-embedding-004",
            project=GCP_PROJECT_ID,
            location="us-central1"
        )
        self.qdrant_path = project_root / "data" / "vector_store" / "qdrant_multimodal"
        
        # Connect to your newly built Phase 5 table collection
        self.vector_store = QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            path=str(self.qdrant_path),
            collection_name="ifc_multimodal_tables"
        )
        
        # 🛠️ FIXED: Swapped to ChatVertexAI and mapped to model_name
        self.llm = ChatVertexAI(
            model_name="gemini-2.5-flash", 
            project=GCP_PROJECT_ID, 
            location="us-central1",
            temperature=0.0
        )

    def retrieve_tables(self, query: str, k: int = 3) -> list[Document]:
        """
        Executes Task 3 Dual-Route Integrated Retrieval.
        Gathers structural table blocks and legacy text blocks together to preserve full context.
        """
        print(f"🔍 Searching Table Vectors for: '{query}'")
        # 1. Fetch tables from the newly built Phase 5 table store
        table_retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
        table_docs = table_retriever.invoke(query)
        
        # 2. Fetch text chunks from the Phase 3 production retriever to maintain complete context
        try:
            print("📖 Fetching background text blocks from Phase 3 production index...")
            text_retriever = get_production_phase3_retriever(gcp_project_id=GCP_PROJECT_ID, k=3)
            # Scan the corresponding target text page scope
            text_docs = text_retriever.invoke(query, start_page=1, end_page=20, retrieval_mode="Hybrid Search")
        except Exception as e:
            print(f"⚠️ Could not pull Phase 3 text chunks: {e}. Falling back to tables only.")
            text_docs = []
            
        return table_docs + text_docs

    def synthesize_table_answer(self, query: str, retrieved_docs: list[Document]) -> str:
        """Generates a final financial analysis using a strict context grounding prompt."""
        if not retrieved_docs:
            return "No relevant data points discovered in the text or table databases."

        # Merge structural chunks and paragraph chunks systematically
        context_str = ""
        for idx, doc in enumerate(retrieved_docs, 1):
            doc_type = doc.metadata.get("content_types_handled", "Table")
            page = doc.metadata.get("primary_page", "Unknown")
            context_str += f"--- BLOCK [{idx}] (Type: {doc_type} | Page {page}) ---\n{doc.page_content}\n\n"

        prompt = f"""You are a senior financial auditor examining the IFC Annual Report.
Analyze the user query based ONLY on the structured Markdown tables and text fragments provided below.

GROUNDING REQUIREMENTS:
1. For exact numerical answers, look closely at the table grids containing Markdown strings.
2. If executing calculation or calculation steps, state the raw figures you found and trace the math transparently.
3. Explicitly declare if the data source originated from a formatted structural table grid or a textual section.

RETRIEVED DATA BLOCKS:
{context_str}

USER QUESTION: {query}

Provide a structured, accurate analysis:"""

        response = self.llm.invoke(prompt)
        return str(response.content)