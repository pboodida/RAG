import os
import io
import json
import base64
from pathlib import Path
from PIL import Image

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.accelerator_options import AcceleratorOptions

from langchain_core.messages import HumanMessage

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI

def pil_to_base64(img: Image.Image) -> str:
    """Converts a PIL Image to a base64 string for Gemini."""
    buffered = io.BytesIO()
    # Convert to RGB if it's in a different mode to avoid PNG save errors
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def extract_and_caption_images(pdf_path: str, output_dir: str, gcp_project_id: str):
    print(f"🚀 Starting Multimodal Image Parsing for: {pdf_path}")
    
    # 1. INITIALIZE GEMINI 2.5 FLASH (Vertex AI Auth - No API Keys via ADC)
    print("Initializing Gemini 2.5 Flash via Vertex AI...")
    llm = ChatVertexAI(
        model_name="gemini-2.5-flash", 
        project=gcp_project_id, 
        location="us-central1"
    )

    # 2. CONFIGURE DOCLING FOR IMAGE EXTRACTION (Mac CPU Safe)
    accelerator_options = AcceleratorOptions(num_threads=4, device="cpu")
    # explicitly tell Docling to generate image crops
    pipeline_options = PdfPipelineOptions(
        accelerator_options=accelerator_options,
        generate_picture_images=True 
    )
    
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    
    print("Scanning document for images and charts...")
    result = converter.convert(pdf_path)
    doc = result.document
    
    parsed_images = []
    
    # We turn the generator into a list so we can look "backwards" and "forwards"
    items_list = list(doc.iterate_items())
    
    for i, (item, level) in enumerate(items_list):
        label = str(getattr(item, "label", "")).lower()
        
        # If the item is a picture, figure, or chart
        if "picture" in label or "figure" in label or "image" in label:
            
            # ==========================================
            # FIX: Safely retrieve the get_image method to bypass Pylance
            # ==========================================
            get_image_method = getattr(item, "get_image", None)
            
            if not get_image_method:
                continue
                
            # Safely invoke the method
            img = get_image_method(doc)
            if not img:
                continue
                
            print(f"🖼️ Found Image! Sending to Gemini 2.5 Flash for captioning...")
            
            # 3. ASK GEMINI TO CAPTION THE IMAGE
            base64_img = pil_to_base64(img)
            prompt = (
                "You are an expert financial analyst. Please describe this image from an annual report in detail. "
                "If it is a chart or graph, summarize the key numbers, trends, and takeaways."
            )
            
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                ]
            )
            
            try:
                caption_response = llm.invoke([message])
                # safely extract the string content
                caption = str(caption_response.content) 
            except Exception as e:
                print(f"⚠️ Gemini Vertex AI Error: {str(e)}")
                caption = "Caption generation failed."

            # 4. OPTIONAL TASK: GRAB THE TEXT ABOVE AND BELOW
            text_above = "None"
            text_below = "None"
            
            # Look backwards for the nearest text
            for j in range(i-1, -1, -1):
                prev_label = str(getattr(items_list[j][0], "label", "")).lower()
                if "paragraph" in prev_label or "text" in prev_label or "title" in prev_label:
                    text_above = str(getattr(items_list[j][0], "text", "")).strip()
                    break
                    
            # Look forwards for the nearest text
            for j in range(i+1, len(items_list)):
                next_label = str(getattr(items_list[j][0], "label", "")).lower()
                if "paragraph" in next_label or "text" in next_label or "title" in next_label:
                    text_below = str(getattr(items_list[j][0], "text", "")).strip()
                    break

            # 5. SAFELY GET PAGE NUMBER
            page_no = "Unknown"
            provs = getattr(item, "prov", []) 
            if provs and isinstance(provs, list) and len(provs) > 0:
                page_no = getattr(provs[0], "page_no", "Unknown")

            # 6. SAVE TO OUR DATASET
            parsed_images.append({
                "page_number": page_no,
                "gemini_caption": caption,
                "context_above": text_above,
                "context_below": text_below,
                "metadata": {
                    "source": os.path.basename(pdf_path),
                    "image_size": img.size, # (width, height)
                    "structure_level": level
                }
            })
            
            print(f"✅ Caption generated for image on page {page_no}.")

    # Save Results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "parsed_images.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_images, f, indent=4)
        
    print(f"\n🎉 Successfully processed and captioned {len(parsed_images)} images!")
    print(f"💾 Saved cleanly to {output_file}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raw_pdf = str(project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf")
    processed_dir = str(project_root / "data" / "processed")
    
    gcp_project = "gd-gcp-gridu-genai" 
    
    extract_and_caption_images(raw_pdf, processed_dir, gcp_project)