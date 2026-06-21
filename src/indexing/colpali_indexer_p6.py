import os
import sys
from pathlib import Path
import fitz  # PyMuPDF

# 🍏 1. MAC GPU OPTIMIZATIONS: Remove the memory allocation ceiling for MPS
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
if torch.backends.mps.is_available():
    target_device = "mps"
    print("🍏 Apple Silicon (MPS) detected! Leveraging Mac GPU acceleration.")
else:
    target_device = "cpu"
    print("⚠️ MPS not available. Defaulting to CPU.")

from byaldi import RAGMultiModalModel

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def build_colpali_index():
    print(f"🚀 Initializing Phase 6: ColPali Vision Retriever on {target_device.upper()}...")
    
    # Load model directly into Mac GPU (MPS) memory
    RAG = RAGMultiModalModel.from_pretrained(
        "vidore/colqwen2-v1.0",
        device=target_device
    )
    
    raw_pdf_path = project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf"
    short_pdf_path = project_root / "data" / "raw" / "ifc_p6_subset.pdf"
    
    print(f"✂️ Creating a 10-page visual subset from {raw_pdf_path.name}...")
    doc = fitz.open(raw_pdf_path)
    short_doc = fitz.open()
    short_doc.insert_pdf(doc, from_page=0, to_page=9)
    short_doc.save(short_pdf_path)
    short_doc.close()
    
    print(f"🖼️ Ingesting visual patches into ColPali multi-vector space via GPU...")
    RAG.index(
        input_path=str(short_pdf_path),
        index_name="ifc_colpali_index",
        store_collection_with_index=True, 
        overwrite=True
    )
    
    print("✅ Phase 6 ColPali Index successfully built using Mac GPU acceleration!")

if __name__ == "__main__":
    build_colpali_index()