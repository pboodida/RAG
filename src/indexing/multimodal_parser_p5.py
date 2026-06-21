import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
import pandas as pd
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings

print("🚀 Script started: Imports successful.")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]

print(f"📂 Detected Project Root: {project_root}")

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

def algorithmic_table_extraction(pdf_path: Path) -> list[Document]:
    print(f"📄 Starting extraction function. Target PDF: {pdf_path.name}")
    table_documents = []
    
    old_preview_path = project_root / "data" / "extracted_tables_preview.md"
    if old_preview_path.exists():
        try:
            old_preview_path.unlink()
            print("🗑️ Deleted the old, cached preview file.")
        except Exception as e:
            print(f"⚠️ Could not delete old file: {e}")

    new_preview_path = project_root / "data" / "latest_extracted_tables.md"
    print(f"📝 Will write preview to: {new_preview_path}")
    
    try:
        print("📖 Attempting to open PDF with PyMuPDF...")
        doc = fitz.open(pdf_path)
        print(f"✅ PDF opened successfully. Total pages: {len(doc)}")
    except Exception as e:
        print(f"❌ FATAL ERROR opening PDF: {e}")
        return []

    limit = min(10, len(doc))
    print(f"⚙️ Processing first {limit} pages...")
    
    with open(new_preview_path, "w", encoding="utf-8") as preview_file:
        preview_file.write("# 📊 NEW Geometric Table Extraction Preview (First 10 Pages)\n\n")
        
        for i in range(limit):
            page_num = i + 1
            print(f"👀 Scanning Page {page_num}...")
            page = doc.load_page(i)
            
            table_finder = page.find_tables()
            
            if table_finder is not None and getattr(table_finder, "tables", None):
                print(f"🎯 Found {len(table_finder.tables)} table(s) on Page {page_num}.")
                for table_idx, tab in enumerate(table_finder.tables):
                    try:
                        df = tab.to_pandas()
                        df = df.fillna("").replace({None: ""})
                        markdown_table = df.to_markdown(index=False)
                        final_content = f"### ALGORITHMIC TABLE | Page {page_num} | Index {table_idx + 1}\n\n{markdown_table}"
                        preview_file.write(f"{final_content}\n\n---\n\n")
                        
                        doc_obj = Document(
                            page_content=final_content,
                            metadata={
                                "source": pdf_path.name,
                                "primary_page": page_num,
                                "content_types_handled": "Table",
                                "table_index": table_idx + 1
                            }
                        )
                        table_documents.append(doc_obj)
                    except Exception as e:
                        print(f"⚠️ Could not process table {table_idx+1} on page {page_num}: {e}")
            else:
                print(f"⏭️ No tables detected on Page {page_num}. Skipping.")

    print(f"✅ Extraction complete. Returning {len(table_documents)} documents.")
    return table_documents

def build_multimodal_index():
    print("🛠️ Entering build_multimodal_index()...")
    pdf_path = project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf"
    
    print(f"🔍 Checking for PDF at: {pdf_path}")
    if not pdf_path.exists():
        print(f"❌ Target PDF NOT FOUND at {pdf_path}")
        return

    table_docs = algorithmic_table_extraction(pdf_path)
    
    if not table_docs:
        print("❌ No tables extracted. Aborting index creation.")
        return

    print("🧠 Initializing Google Embeddings...")
    embeddings = VertexAIEmbeddings(model="text-embedding-004")
    
    qdrant_path = project_root / "data" / "vector_store" / "qdrant_multimodal"
    
    print(f"💾 Saving {len(table_docs)} documents to Qdrant at {qdrant_path}...")
    QdrantVectorStore.from_documents(
        documents=table_docs,
        embedding=embeddings,
        path=str(qdrant_path),
        collection_name="ifc_multimodal_tables",
        force_recreate=True
    )
    print("🚀 Phase 5 Table Index built successfully!")

if __name__ == "__main__":
    print("▶️ Main block triggered.")
    build_multimodal_index()
    print("🏁 Script finished.")