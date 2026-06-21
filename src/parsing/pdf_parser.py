import os
import json
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.accelerator_options import AcceleratorOptions

def parse_pdf_text_with_docling(pdf_path: str, output_dir: str):
    print(f"🚀 Starting Text & Metadata Parsing using Docling for: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}. Please place it in data/raw/")
        
    # ==========================================
    # FIX 3: Force Docling to use CPU on Mac to avoid the MPS float64 crash
    # ==========================================
    # Set up the accelerator to use the CPU
    accelerator_options = AcceleratorOptions(num_threads=4, device="cpu")
    
    # Pass the accelerator into the specific PDF pipeline options
    pipeline_options = PdfPipelineOptions(accelerator_options=accelerator_options)
    
    # Initialize Docling Converter with our custom pipeline options
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    print("Converting document (this preserves structural layout, running on CPU)...")
    result = converter.convert(pdf_path)
    doc = result.document
    
    parsed_data = []
    
    # 1. Collect Global Document Metadata
    global_metadata = {
        "source": os.path.basename(pdf_path),
        "document_name": getattr(doc, "name", "Unknown")
    }
    
    print(f"📄 Document Conversion Complete. Extracting semantic structure...")
    
    # 2. Extract Text and Consider Document Structure
    valid_text_labels = ["paragraph", "title", "section_header", "page_header", "text"]
    
    for item, level in doc.iterate_items():
        label = getattr(item, "label", None)
        
        # Convert label to string just in case it is an Enum
        label_str = str(label).lower() if label else ""
        
        # Check if any valid text label is within the stringified Enum
        if any(v in label_str for v in valid_text_labels):
            
            # Safely extract text content
            text_content = getattr(item, "text", "")
            if not text_content or not str(text_content).strip():
                continue
                
            # Safely extract page number
            page_no = "Unknown"
            provs = getattr(item, "prov", []) 
            
            if provs and isinstance(provs, list) and len(provs) > 0:
                page_no = getattr(provs[0], "page_no", "Unknown")
            
            # Append block with metadata
            parsed_data.append({
                "page_number": page_no,
                "content_type": label_str,
                "content": str(text_content).strip(),
                "metadata": {
                    "source": global_metadata["source"],
                    "page": page_no,
                    "structure_level": level
                }
            })
            
    # 3. Save as Structured JSON
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "parsed_text_docling.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=4)
        
    print(f"✅ Extracted {len(parsed_data)} structured text blocks using Docling.")
    print(f"💾 Saved cleanly to {output_file}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raw_pdf = str(project_root / "data" / "raw" / "ifc-annual-report-2024-financials.pdf")
    processed_dir = str(project_root / "data" / "processed")
    
    parse_pdf_text_with_docling(raw_pdf, processed_dir)