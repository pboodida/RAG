import os
import sys
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Fix macOS background crashes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ==========================================
# FIX: Mock the deprecated LangChain module so Ragas doesn't crash on boot
# ==========================================
from unittest.mock import MagicMock
sys.modules['langchain_community.chat_models.vertexai'] = MagicMock()

# Ensure we can import from the root src folder
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from src.retrieval.retriever_p1 import get_baseline_retriever

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

# Compatibility wrappers for modern RAGAS versions
try:
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    USE_WRAPPERS = True
except ImportError:
    USE_WRAPPERS = False

load_dotenv()
GCP_PROJECT_ID = "gd-gcp-gridu-genai"

def generate_rag_prediction(query, retriever, llm):
    """Feeds a query through the Phase 1 RAG pipeline to get predictions for evaluation."""
    docs = retriever.invoke(query)
    contexts = [doc.page_content for doc in docs]
    context_str = "\n\n".join(contexts)
    
    system_prompt = (
        "You are an expert financial assistant analyzing the IFC Annual Report.\n"
        "Answer the question accurately using ONLY the text context provided below.\n\n"
        f"CONTEXT:\n{context_str}\n\n"
        f"QUESTION: {query}"
    )
    
    response = llm.invoke(system_prompt)
    return str(response.content), contexts

def run_evaluation(dataset_path: str, output_path: str, db_type="faiss"):
    print(f"🚀 Loading Evaluation Dataset from: {dataset_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Please place it in data/evaluation/")
        
    df = pd.read_csv(dataset_path)

    print("🧠 Initializing Gemini for Generation AND Judging...")
    # 🛠️ FIXED: Initialized Vertex AI classes with correct arguments
    llm = ChatVertexAI(model_name="gemini-2.5-flash", project=GCP_PROJECT_ID, location="us-central1")
    embeddings = VertexAIEmbeddings(model="text-embedding-004", project=GCP_PROJECT_ID, location="us-central1")
    
    # We are evaluating Phase 1, so we pull the Phase 1 retriever
    retriever = get_baseline_retriever(gcp_project_id=GCP_PROJECT_ID, db_type=db_type, k=4)

    # RAGAS expects a very specific dictionary format
    data_for_ragas = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    print(f"🔄 Generating Pipeline Responses (Evaluating {len(df)} questions)...")
    
    for i, (idx, row) in enumerate(df.iterrows()):
        question = str(row["Question"])
        ground_truth = str(row["Ground_Truth_Answer"])
        
        print(f"  [{i+1}/{len(df)}] Asking: {question[:50]}...")
        answer, contexts = generate_rag_prediction(question, retriever, llm)
        
        data_for_ragas["question"].append(question)
        data_for_ragas["answer"].append(answer)
        data_for_ragas["contexts"].append(contexts)
        data_for_ragas["ground_truth"].append(ground_truth)
        
        time.sleep(1) 

    # Convert the dictionary to a HuggingFace Dataset object
    dataset = Dataset.from_dict(data_for_ragas)

    print("\n⚖️ Initiating LLM-as-a-Judge Evaluation Framework...")
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    # Evaluate the pipeline using Gemini as the Judge
    if USE_WRAPPERS:
        eval_llm = LangchainLLMWrapper(llm)
        eval_embeddings = LangchainEmbeddingsWrapper(embeddings)
        result = evaluate(dataset=dataset, metrics=metrics, llm=eval_llm, embeddings=eval_embeddings)
    else:
        result = evaluate(dataset=dataset, metrics=metrics, llm=llm, embeddings=embeddings)

    # Use # type: ignore to bypass Pylance's missing stub for to_pandas()
    eval_df = result.to_pandas() # type: ignore
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    eval_df.to_csv(output_path, index=False)

    print(f"\n✅ Evaluation Complete! Detailed metrics saved to: {output_path}")
    
    print("\n📊 FINAL RAGAS PIPELINE SCORES (0.0 to 1.0):")
    for metric in metrics:
        if metric.name in eval_df.columns:
            print(f" - {metric.name.capitalize()}: {eval_df[metric.name].mean():.4f}")

if __name__ == "__main__":
    dataset_file = str(project_root / "data" / "evaluation" / "RAG_evaluation_dataset - convertcsv.csv")
    output_file = str(project_root / "data" / "evaluation" / "phase1_ragas_results.csv")
    
    # We test the FAISS index by default as it represents our Phase 1 baseline
    run_evaluation(dataset_file, output_file, db_type="faiss")