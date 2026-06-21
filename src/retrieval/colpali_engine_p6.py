import os
import sys
from typing import Any, List, Dict
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI

# 🍏 MAC GPU OPTIMIZATIONS
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
target_device = "mps" if torch.backends.mps.is_available() else "cpu"

from byaldi import RAGMultiModalModel

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

class ColPaliEngine:
    def __init__(self):
        print(f"🔧 Loading ColPali Index into Mac GPU ({target_device.upper()}) memory...")
        self.rag = RAGMultiModalModel.from_index("ifc_colpali_index", device=target_device)
        
        # 🛠️ FIXED: Swapped to ChatVertexAI and mapped to model_name
        self.vision_llm = ChatVertexAI(
            model_name="gemini-2.5-flash", 
            project=GCP_PROJECT_ID, 
            location="us-central1",
            temperature=0.0
        )

    def retrieve_and_synthesize(self, query: str, k: int = 2) -> tuple[str, list[Document]]:
        print(f"🔍 Executing ColPali visual MaxSim search on GPU for: '{query}'")
        
        # We explicitly cast the results to Any to bypass Byaldi's overly strict type stubs
        raw_results: Any = self.rag.search(query, k=k)
        
        # Byaldi sometimes wraps single queries in an extra list, let's unpack safely
        if isinstance(raw_results, list) and len(raw_results) > 0 and isinstance(raw_results[0], list):
            results = raw_results[0]
        else:
            results = raw_results
            
        if not results:
            return "No visually relevant pages found in the ColPali index.", []

        # 🛠️ FIXED: Explicitly declare the list type as holding Any dictionary structure
        message_content: List[Dict[str, Any]] = [
            {
                "type": "text", 
                "text": f"You are a multimodal financial analyst. Answer the user's question using ONLY the visual document pages provided below. Question: {query}"
            }
        ]
        
        docs_for_ui: list[Document] = []
        
        for res in results:
            # Safely extract attributes regardless of how Byaldi returns the object
            base64_img = getattr(res, "base64", None)
            page_num = getattr(res, "page_num", "Unknown")
            score = float(getattr(res, "score", 0.0))
            
            if base64_img:
                message_content.append(
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                    }
                )
            
            doc = Document(
                page_content=f"🖼️ [VISUAL PAGE RENDERED]\n\nColPali successfully matched visual patches on this page via GPU.\nRelevance MaxSim Score: {score}",
                metadata={
                    "content_types_handled": "ColPali Visual Image Patch",
                    "primary_page": page_num,
                    "colpali_score": round(score, 3)
                }
            )
            docs_for_ui.append(doc)
            
        message = HumanMessage(content=message_content)  # type: ignore
        
        print("🧠 Passing retrieved images to Gemini for synthesis...")
        response = self.vision_llm.invoke([message])
        
        return str(response.content), docs_for_ui