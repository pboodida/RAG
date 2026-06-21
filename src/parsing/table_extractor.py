import os
import json
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.accelerator_options import AcceleratorOptions

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI

def extract_and_summarize_tables(pdf_path: str, output_dir: str, gcp_project_id: str):
    print(f"🚀 Starting Table Parsing & Summarization for: {pdf_path}")
    
    # 1. INITIALIZE GEMINI 2.5 FLASH (Vertex AI Auth via ADC)
    print("Initializing Gemini 2.5 Flash via Vertex AI...")
    llm = ChatVertexAI(
        model_name="gemini-2.5-flash", 
        project=gcp_project_id, 
        location="us-central1"
    )

    # 2. CONFIGURE DOCLING FOR TABLES (Mac CPU Safe)
    accelerator_options = AcceleratorOptions(num_threads=4, device="cpu")
    # Explicitly enable advanced table structure recognition
    pipeline_options = PdfPipelineOptions(
        accelerator_options=accelerator_options,
        do_table_structure=True 
    )
    
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    
    print("Scanning document for financial tables...")
    result = converter.convert(pdf_path)
    doc = result.document
    
    parsed_tables = []
    items_list = list(doc.iterate_items())
    
    for i, (item, level) in enumerate(items_list):
        label = str(getattr(item, "label", "")).lower()
        
        # Check if the item is explicitly labeled as a table
        if "table" in label:
            
            # Safely get the export_to_markdown method to bypass Pylance errors
            export_method = getattr(item, "export_to_markdown", None)
            if not export_method:
                continue
                
            # Execute the method to get the raw Markdown representation
            md_table = export_method()
            if not md_table or not md_table.strip():
                continue
                
            print(f"📊 Found Table! Sending Markdown to Gemini 2.5 Flash for analysis...")
            
            # 3. SUMMARIZE THE TABLE WITH GEMINI
            prompt = (
                "You are an expert financial analyst. Analyze the following markdown table from an annual report. "
                "Provide a brief, comprehensive summary of what this table represents and its key numerical takeaways.\n\n"
                f"Table Markdown:\n{md_table}"
            )
            
            try:
                summary_response = llm.invoke(prompt)
                summary = str(summary_response.content)
            except Exception as e:
                print(f"⚠️ Gemini Vertex AI Error: {str(e)}")
                summary = "Summary generation failed."

            # 4. OPTIONAL TASK: GRAB THE TEXT ABOVE AND BELOW
            text_above = "None"
            text_below = "None"
            
            # Look backwards
            for j in range(i-1, -1, -1):
                prev_label = str(getattr(items_list[j][0], "label", "")).lower()
                if "paragraph" in prev_label or "text" in prev_label or "title" in prev_label:
                    text_above = str(getattr(items_list[j][0], "text", "")).strip()
                    break
                    
            # Look forwards
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
            parsed_tables.append({
                "page_number": page_no,
                "table_markdown": md_table,
                "gemini_summary": summary,
                "context_above": text_above,
                "context_below": text_below,
                "metadata": {
                    "source": os.path.basename(pdf_path),
                    "structure_level": level
                }
            })
            
            print(f"✅ Table processed, formatted as Markdown, and summarized on page {page_no}.")

    # Save Results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "parsed_tables.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_tables, f, indent=4)
        
    print(f"\n🎉 Successfully processed {len(parsed_tables)} tables!")
    print(f"💾 Saved cleanly to {output_file}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raw_pdf = str(project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf")
    processed_dir = str(project_root / "data" / "processed")
    
    gcp_project = "gd-gcp-gridu-genai" 
    
    extract_and_summarize_tables(raw_pdf, processed_dir, gcp_project)