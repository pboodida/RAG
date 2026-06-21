import os
import sys
import json
import warnings
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any
from types import ModuleType

# ==========================================
# 🛑 SILENCE RAGAS DEPRECATION WARNINGS
# ==========================================
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ==========================================
# 🛠️ TYPE-SAFE RAGAS HOTFIX FOR LANGCHAIN
# ==========================================
class MockChatModule(ModuleType):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.ChatVertexAI = type("ChatVertexAI", (object,), {})

class MockEmbedModule(ModuleType):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.VertexAIEmbeddings = type("VertexAIEmbeddings", (object,), {})

if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MockChatModule("langchain_community.chat_models.vertexai")

if "langchain_community.embeddings.vertexai" not in sys.modules:
    sys.modules["langchain_community.embeddings.vertexai"] = MockEmbedModule("langchain_community.embeddings.vertexai")


# Fix macOS background crashes for ML models
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datasets import Dataset
from ragas import evaluate

# FIX 1: Import the stable, legacy Metric classes (Upper Camel Case)
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall

# FIX 2: Revert to stable LangChain wrappers
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings

from src.retrieval.advanced_pipeline_p3 import get_production_phase3_retriever

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

def load_evaluation_dataset() -> list[dict]:
    """
    Safely loads the Phase 2/3 evaluation dataset from the CSV file.
    Falls back to a structural sample only if the file is completely missing.
    """
    eval_dir = project_root / "data" / "evaluation"
    csv_path = eval_dir / "RAG_evaluation_dataset - convertcsv.csv"
    
    # 1. Try loading your explicit CSV file
    if csv_path.exists():
        print(f"📂 Found target evaluation CSV dataset: {csv_path.name}")
        try:
            df = pd.read_csv(csv_path)
            
            # Rename columns to standard Ragas keys if necessary
            column_mapping = {
                'Question': 'question',
                'Question ': 'question',
                "Ground_Truth_Answer": "ground_truth",
                'Ground Truth': 'ground_truth',
                'Ground_Truth': 'ground_truth',
                'ground_truth': 'ground_truth',
                'Start Page': 'start_page',
                'End Page': 'end_page'
            }
            df = df.rename(columns=column_mapping)
            
            # Fallback default columns if filtering columns are missing in your CSV
            if 'start_page' not in df.columns:
                df['start_page'] = 1
            if 'end_page' not in df.columns:
                df['end_page'] = 150
                
            # Clean up missing rows or empty values safely
            df = df.dropna(subset=['question', 'ground_truth'])
            
            # Convert the dataframe to a list of dictionaries for the pipeline loop
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"⚠️ Error parsing CSV file: {e}. Falling back to baseline benchmarks...")

    print("⚠️ 'RAG_evaluation_dataset - convertcsv.csv' not found in data/evaluation/. Initializing core baseline benchmarking suite...")
    return [
        {
            "question": "What happened to the PCRF income starting in FY24?",
            "ground_truth": "Starting in FY24, the Post-retirement Contribution Reserve Fund (PCRF) income was excluded from Income Available for Designations.",
            "start_page": 1,
            "end_page": 10
        },
        {
            "question": "What were the main drivers for the net income increase?",
            "ground_truth": "The increase in Net Income was principally driven by higher treasury investment returns and advisory services income.",
            "start_page": 1,
            "end_page": 60
        },
        {
            "question": "What strategies is the organization deploying to modernize its framework?",
            "ground_truth": "The WBG is evolving to better address global development challenges by implementing initiatives to increase impact and modernize delivery.",
            "start_page": 1,
            "end_page": 15
        }
    ]


def run_phase3_evaluation():
    print("🚀 Initiating Automated Phase 3 RAGAS Performance Benchmark...")
    
    # 1. Initialize data and retriever components
    eval_data = load_evaluation_dataset()
    retriever = get_production_phase3_retriever(gcp_project_id=GCP_PROJECT_ID, k=4)
    
    # 2. Instantiate native LangChain components
    # 🛠️ FIXED: Swapped to ChatVertexAI and VertexAIEmbeddings with matching argument schemas
    raw_llm = ChatVertexAI(
        model_name="gemini-2.5-flash", 
        project=GCP_PROJECT_ID, 
        location="us-central1"
    )
    
    raw_embeddings = VertexAIEmbeddings(
        model="text-embedding-004",
        project=GCP_PROJECT_ID,
        location="us-central1"
    )
    
    # 3. Use stable LangChain wrappers to satisfy Ragas base classes
    ragas_llm = LangchainLLMWrapper(langchain_llm=raw_llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings=raw_embeddings)
    
    questions = []
    contexts = []
    answers = []
    ground_truths = []
    
    # 4. Process queries through the Phase 3 cluster
    for i, item in enumerate(eval_data, 1):
        query = item["question"]
        gt = item["ground_truth"]
        start_p = item.get("start_page", 1)
        end_p = item.get("end_page", 150)
        
        print(f"\n⚡ [{i}/{len(eval_data)}] Processing Query: '{query}'")
        print(f"⚙️ Active Filters: Pages {start_p} to {end_p} | Strategy: Hybrid Search")
        
        relevant_docs = retriever.invoke(query, start_page=start_p, end_page=end_p, retrieval_mode="Hybrid Search")
        current_contexts = [doc.page_content for doc in relevant_docs]
        
        context_str = "\n\n".join([f"--- Section Element ---\n{c}" for c in current_contexts])
        system_prompt = (
            "You are an expert financial assistant analyzing the IFC Annual Report.\n"
            "Answer the question accurately using ONLY the text context provided below.\n\n"
            f"CONTEXT:\n{context_str}\n\n"
            f"QUESTION: {query}"
        )
        
        if current_contexts:
            response = raw_llm.invoke(system_prompt)
            generated_answer = str(response.content)
        else:
            generated_answer = "No relevant context found within the specified parameters."
            
        questions.append(query)
        contexts.append(current_contexts)
        answers.append(generated_answer)
        ground_truths.append(gt)

    # 5. Format dataset parameters
    data_dict = {
        "question": questions,
        "contexts": contexts,
        "answer": answers,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data_dict)
    
    # 6. Initialize stable metric classes 
    metrics_list = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
        ContextPrecision(llm=ragas_llm),
        ContextRecall(llm=ragas_llm)
    ]
    
    print("\n🧮 Calculating validation metrics via RAGAS Engine...")
    
    # Execute evaluation block
    result: Any = evaluate(
        dataset=dataset,
        metrics=metrics_list
    )
    
    # 7. Save output evaluation report
    df = result.to_pandas()
    output_dir = project_root / "data" / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"phase3_eval_report_{timestamp}.csv"
    df.to_csv(output_dir / csv_filename, index=False)
    
    # 8. Print telemetry summary dashboard
    print("\n📊 ===========================================")
    print("🏆 PHASE 3 HYBRID PERFORMANCE MATRIX SUMMARY")
    print("=============================================")
    # Calculate the average score directly from the dataframe columns
    metric_columns = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for m in metric_columns:
        if m in df.columns:
            # Drop NaN values where evaluation might have been skipped
            score = df[m].dropna().mean()
            print(f"📈 {m.upper():<20} : {score:.4f}")
            
    print("=============================================")
    print(f"✅ Full report saved successfully to: {output_dir / csv_filename}\n")

if __name__ == "__main__":
    run_phase3_evaluation()