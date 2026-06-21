import os
import sys
import time
import base64
from io import BytesIO
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_qdrant import QdrantVectorStore
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

def extract_and_describe_images(pdf_path: Path) -> list[Document]:
    print(f"🖼️ Extracting Images (Charts/Graphs) from: {pdf_path.name}...")
    image_documents = []
    preview_path = project_root / "data" / "extracted_images_preview.md"

    vision_llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=GCP_PROJECT_ID,
        location="us-central1",
        temperature=0.1
    )

    doc = fitz.open(pdf_path)
    limit = min(20, len(doc)) # Scan first 20 pages

    prompt = """You are an expert financial data analyst.
    Analyze this extracted image. If it is a chart, graph, diagram, or data plot:
    1. Identify the type of chart (e.g., Bar chart, Line graph, Pie chart).
    2. Extract the title, axis labels, and legends.
    3. Describe the key trends, data points, and insights visible in the chart.
    4. Include specific numbers if they are clearly legible.
    If the image is just a logo, decorative background, or plain photo with no data, output EXACTLY the word: SKIP."""

    with open(preview_path, "w", encoding="utf-8") as preview_file:
        preview_file.write("# 📈 Extracted Visual Analytics Preview (First 20 Pages)\n\n")

        for i in range(limit):
            page_num = i + 1
            page = doc.load_page(i)
            # Natively extract image blocks
            image_list = page.get_images(full=True)

            if image_list:
                print(f"👀 Found {len(image_list)} native images on Page {page_num}.")
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Filter out tiny decorative images/logos (< 100x100 pixels)
                        pil_img = Image.open(BytesIO(image_bytes))
                        if pil_img.width < 100 or pil_img.height < 100:
                            continue 
                            
                        # 📁 NEW CODE: Save the physical image file to disk so you can see it!
                        output_dir = project_root / "data" / "extracted_images"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        image_filename = f"page_{page_num}_img_{img_index + 1}.{image_ext}"
                        pil_img.save(output_dir / image_filename)
                        print(f"💾 Saved image asset to: data/extracted_images/{image_filename}")
                        
                        # Convert to base64 (Existing code remains completely untouched)
                        img_str = base64.b64encode(image_bytes).decode("utf-8")

                        message = HumanMessage(
                            content=[
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/{image_ext};base64,{img_str}"}}
                            ]
                        )

                        response = vision_llm.invoke([message])
                        description = str(response.content).strip()

                        if description and "SKIP" not in description.upper():
                            final_content = f"### CHART/GRAPH DESCRIPTION | Page {page_num} | Image {img_index + 1}\n\n{description}"
                            preview_file.write(f"{final_content}\n\n---\n\n")

                            doc_obj = Document(
                                page_content=final_content,
                                metadata={
                                    "source": pdf_path.name,
                                    "primary_page": page_num,
                                    "content_types_handled": "Image/Chart",
                                    "image_index": img_index + 1
                                }
                            )
                            image_documents.append(doc_obj)
                            time.sleep(2) # GCP Rate Limit Protection
                    except Exception as e:
                        print(f"⚠️ Failed to describe an image on page {page_num}: {e}")
            else:
                print(f"⏭️ No images detected on Page {page_num}. Skipping.")

    print(f"✅ Image Verification file created at: {preview_path}")
    return image_documents

def build_image_index():
    pdf_path = project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf"
    if not pdf_path.exists():
        print(f"❌ Target PDF not found at {pdf_path}")
        return

    image_docs = extract_and_describe_images(pdf_path)

    if not image_docs:
        print("❌ No valid charts/graphs found. Aborting index creation.")
        return

    print(f"🧠 Generating Dense Embeddings for {len(image_docs)} chart descriptions...")
    embeddings = VertexAIEmbeddings(
        model="text-embedding-004",
        project=GCP_PROJECT_ID,
        location="us-central1"
    )

    qdrant_path = project_root / "data" / "vector_store" / "qdrant_multimodal_images"

    print("💾 Saving visual chart metadata to Qdrant Collection...")
    QdrantVectorStore.from_documents(
        documents=image_docs,
        embedding=embeddings,
        path=str(qdrant_path),
        collection_name="ifc_multimodal_images",
        force_recreate=True
    )
    print(f"🚀 Phase 5.2 Image Index built successfully!")

if __name__ == "__main__":
    build_image_index()