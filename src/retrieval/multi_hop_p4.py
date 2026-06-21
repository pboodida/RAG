import os
# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI
from langchain_core.documents import Document

# Fix macOS background crashes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class MultiHopManager:
    """
    Phase 4: Intent Classification and Multi-hop Retrieval Engine.
    """
    def __init__(self, gcp_project_id: str):
        self.gcp_project_id = gcp_project_id
        # 🛠️ FIXED: Swapped to ChatVertexAI and set model_name="gemini-2.5-flash"
        self.reasoning_llm = ChatVertexAI(
            model_name="gemini-2.5-flash", 
            project=gcp_project_id, 
            location="us-central1"
        )

    def classify_intent(self, query: str) -> str:
        """Determines if the query is a simple lookup or a complex multi-part question."""
        prompt = f"""Analyze the following question. 
Does it require looking up a single specific financial fact or metric (NORMAL)?
Or does it require synthesizing multiple distinct pieces of information, comparing different concepts, or reasoning across multiple steps (MULTI_HOP)? 

Respond strictly with a single word: NORMAL or MULTI_HOP.

Question: {query}"""
        
        try:
            response = self.reasoning_llm.invoke(prompt)
            # Safe-cast content to string to appease type-checkers
            content_str = str(response.content).strip().upper()
            
            if "MULTI_HOP" in content_str:
                return "MULTI_HOP"
            return "NORMAL"
        except Exception:
            return "NORMAL"

    def generate_sub_queries(self, query: str) -> list[str]:
        """Breaks a complex question down into actionable sub-searches."""
        prompt = f"""Break the following complex question down into 2 distinct, simple sub-questions that can be searched individually in a financial report.
Return ONLY the sub-questions, each on a new line. Do not use bullet points, numbers, or introductory text.

Complex Question: {query}"""
        
        response = self.reasoning_llm.invoke(prompt)
        # Safe-cast content to string before applying string operations
        content_str = str(response.content)
        
        sub_queries = [q.strip() for q in content_str.split('\n') if q.strip()]
        return sub_queries

    def execute_multi_hop_search(self, query: str, retriever, start_page: int, end_page: int, strategy: str) -> tuple[list[Document], list[str]]:
        """Executes iterative retrieval for complex questions and merges the context."""
        sub_queries = self.generate_sub_queries(query)
        all_unique_docs = []
        seen_content = set()
        
        for sq in sub_queries:
            docs = retriever.invoke(sq, start_page=start_page, end_page=end_page, retrieval_mode=strategy)
            
            for d in docs:
                if d.page_content not in seen_content:
                    seen_content.add(d.page_content)
                    all_unique_docs.append(d)
                    
        return all_unique_docs, sub_queries