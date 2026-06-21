import os
import sys
import json
from pathlib import Path
import streamlit as st

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document

# 🛠️ FIXED: Strictly use Vertex AI SDK (No API Keys)
from langchain_google_vertexai import ChatVertexAI

from src.retrieval.retriever_p1 import get_baseline_retriever
from src.retrieval.advanced_pipeline_p3 import get_production_phase3_retriever
from src.observability.tracer import get_text_tracer
from src.cache.semantic_cache_p4 import SemanticCacheManager
from src.retrieval.multi_hop_p4 import MultiHopManager

GCP_PROJECT_ID = "gd-gcp-gridu-genai"

# 🔒 SESSION STATE PATTERN
if "cache_manager" not in st.session_state:
    st.session_state.cache_manager = SemanticCacheManager(gcp_project_id=GCP_PROJECT_ID, threshold=0.60)
if "multi_hop_manager" not in st.session_state:
    st.session_state.multi_hop_manager = MultiHopManager(gcp_project_id=GCP_PROJECT_ID)

def get_rag_documents(query: str, phase: str, db_type: str, num_chunks: int, start_page: int = 0, end_page: int = 200, strategy: str = "Hybrid Search", multimodal_subphase: str | None = None):
    """Helper function to fetch documents without triggering the LLM generation here (for streaming)."""
    try:
        if "Phase 5" in phase:
            if multimodal_subphase == "5.1: Table Incorporation":
                from src.retrieval.table_engine_p5 import TableRetrievalEngine
                engine = TableRetrievalEngine()
                return engine.retrieve_tables(query, k=num_chunks), None
            else:
                from src.retrieval.image_engine_p5_2 import ImageRetrievalEngine
                engine = ImageRetrievalEngine()
                return engine.retrieve_integrated(query, k_images=num_chunks, k_text=3), None
                
        if "Phase 6" in phase:
            from src.retrieval.colpali_engine_p6 import ColPaliEngine
            engine = ColPaliEngine()
            # Phase 6 already returns the final synthesized answer string, not just docs
            answer, ui_docs = engine.retrieve_and_synthesize(query, k=num_chunks)
            return ui_docs, answer
            
        if "Phase 4" in phase:
            cached_result = st.session_state.cache_manager.check_cache(query)
            if cached_result:
                st.toast("⚡ Semantic Cache Hit!", icon="⚡")
                answer = f"⚡ **[SEMANTIC CACHE HIT]** - *Answer instantly served from FAISS memory!*\n\n{cached_result['answer']}"
                docs_data = json.loads(cached_result["context_docs"])
                relevant_docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs_data]
                return relevant_docs, answer

            st.toast("🧠 Cache Miss. Running Intent Classifier...", icon="🧠")
            intent = st.session_state.multi_hop_manager.classify_intent(query)
            retriever = get_production_phase3_retriever(gcp_project_id=GCP_PROJECT_ID, k=num_chunks)
            
            if intent == "MULTI_HOP":
                st.info("🔄 **Complex Query:** Executing Multi-hop Sub-retrievals...", icon="🔄")
                relevant_docs, sub_queries = st.session_state.multi_hop_manager.execute_multi_hop_search(
                    query=query, retriever=retriever, start_page=start_page, end_page=end_page, strategy=strategy
                )
            else:
                st.info("➡️ **Standard Query:** Executing Production Hybrid Path...", icon="➡️")
                relevant_docs = retriever.invoke(query, start_page=start_page, end_page=end_page, retrieval_mode=strategy)
                
            return relevant_docs, None

        # Phase 1 & 3
        tracer = get_text_tracer()
        config: RunnableConfig = {}
        if tracer:
            config = {"callbacks": [tracer]}
            
        if "Phase 3" in phase:
            retriever = get_production_phase3_retriever(gcp_project_id=GCP_PROJECT_ID, k=num_chunks)
            relevant_docs = retriever.invoke(query, start_page=start_page, end_page=end_page, retrieval_mode=strategy)
        else:
            retriever = get_baseline_retriever(gcp_project_id=GCP_PROJECT_ID, db_type=db_type, k=num_chunks)
            relevant_docs = retriever.invoke(query, config=config)
            
        return relevant_docs, None
        
    except Exception as e:
        st.error(f"❌ Backend Pipeline Error: {str(e)}")
        return [], None


# ==========================================
# 💎 HIGH CONTRAST TYPOGRAPHY SYSTEM
# ==========================================
st.set_page_config(page_title="IFC RAG Intelligence Hub", layout="wide", initial_sidebar_state="expanded")

if "active_phase" not in st.session_state:
    st.session_state.active_phase = "Phase 5: Multimodal RAG"

st.markdown("""
    <style>
        .active-card-p1, .active-card-p3, .active-card-p4, .active-card-p5, .p5-header { color: #0f172a !important; }
        .card-header { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
        .card-body { font-size: 12.5px; line-height: 1.4; color: #334155 !important; }
        .active-card-p1 { border: 2px solid #16a34a; background-color: #f0fdf4; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
        .active-card-p3 { border: 2px solid #9333ea; background-color: #f3e8ff; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
        .active-card-p4 { border: 2px solid #2563eb; background-color: #eff6ff; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
        .active-card-p5 { border: 2px solid #ca8a04; background-color: #fefce8; padding: 14px; border-radius: 8px; margin-bottom: 15px; }
        .p5-header { background: #fefce8; border-left: 5px solid #ca8a04; padding: 16px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
        .response-container { background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; color: #1e293b; font-size: 16px; line-height: 1.6;}
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="font-size: 20px; font-weight: 700; color: #1e293b; margin-bottom: 15px;">🧭 Interactive Architecture Menu</div>', unsafe_allow_html=True)
    
    if "Phase 1" in st.session_state.active_phase:
        st.markdown('<div class="active-card-p1"><div class="card-header" style="color: #15803d !important;">🟢 Phase 1: Naive RAG</div><div class="card-body">Standard Bi-Encoder vector retrieval strategy.</div></div>', unsafe_allow_html=True)
    else:
        if st.button("🟢 Activate Phase 1 Baseline", use_container_width=True):
            st.session_state.active_phase = "Phase 1: Naive RAG"
            st.rerun()
            
    if "Phase 3" in st.session_state.active_phase:
        st.markdown('<div class="active-card-p3"><div class="card-header" style="color: #7e22ce !important;">🟣 Phase 3: Hybrid & Rerank</div><div class="card-body">Concurrent Qdrant + BM25 indices merged via Reciprocal Rank Fusion.</div></div>', unsafe_allow_html=True)
    else:
        if st.button("🟣 Activate Phase 3 Pipeline", use_container_width=True):
            st.session_state.active_phase = "Phase 3: Hybrid Search & Rerank"
            st.rerun()

    if "Phase 4" in st.session_state.active_phase:
        st.markdown('<div class="active-card-p4"><div class="card-header" style="color: #1d4ed8 !important;">🔵 Phase 4: Advanced Techniques</div><div class="card-body">Semantic Caching Shield layered over an LLM Intent Classifier.</div></div>', unsafe_allow_html=True)
    else:
        if st.button("🔵 Activate Phase 4 Suite", use_container_width=True):
            st.session_state.active_phase = "Phase 4: Advanced RAG Features"
            st.rerun()

    if "Phase 5" in st.session_state.active_phase:
        st.markdown('<div class="active-card-p5"><div class="card-header" style="color: #a16207 !important;">🟡 Phase 5: Multimodal RAG Active</div><div class="card-body">Extracts and parses complex Layout Elements (Tables & Images) independently.</div></div>', unsafe_allow_html=True)
    else:
        if st.button("🟡 Activate Phase 5 Multimodal", use_container_width=True):
            st.session_state.active_phase = "Phase 5: Multimodal RAG"
            st.rerun()
    if "Phase 6" in st.session_state.active_phase:
        st.markdown('<div class="active-card-p5" style="border-color: #be123c; background-color: #fff1f2;"><div class="card-header" style="color: #be123c !important;">🔴 Phase 6: ColPali Vision RAG</div><div class="card-body">End-to-End Multimodal MaxSim Retrieval using Page Image Patches.</div></div>', unsafe_allow_html=True)
    else:
        if st.button("🔴 Activate Phase 6 ColPali", use_container_width=True):
            st.session_state.active_phase = "Phase 6: ColPali Multimodal RAG"
            st.rerun()
              
    st.markdown("---")
    st.markdown('<div style="font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 10px;">⚙️ Engine Configurations</div>', unsafe_allow_html=True)
    
    selected_phase = st.session_state.active_phase
    multimodal_subphase = None
    
    if "Phase 5" in selected_phase:
        multimodal_subphase = st.selectbox(
            "Select Multimodal Target:",
            options=["5.1: Table Incorporation", "5.2: Image Incorporation"],
            index=0
        )
        chunk_slider = st.slider("Context Window Depth", min_value=1, max_value=10, value=3, step=1)
        selected_db = "qdrant_multimodal"
        chosen_strategy = "Dense Only"
        start_page, end_page = 0, 200
        
    elif "Phase 1" in selected_phase:
        selected_db = st.selectbox("Active Vector DB Index", options=["faiss", "qdrant"], index=0)
        chunk_slider = st.slider("Context Window Depth (Top-K)", min_value=1, max_value=10, value=4, step=1)
        start_page, end_page = 0, 200 
        chosen_strategy = "Default"
    else:
        chosen_strategy = st.selectbox("Retrieval Strategy Pattern:", options=["Hybrid Search (BM25 + Qdrant)", "Sparse Only (BM25 Keyword Match)", "Dense Only (Qdrant Semantic Match)"], index=0)
        selected_db = "qdrant" 
        chunk_slider = st.slider("Final Context Window Depth", min_value=1, max_value=10, value=4, step=1)
        st.markdown("### 🗂️ Metadata Pre-Filter")
        page_range = st.slider("Restrict Search to Page Range:", min_value=1, max_value=150, value=(1, 150))
        start_page, end_page = page_range[0], page_range[1]

st.title("📊 IFC Annual Financial Report Intelligence Engine")

if "Phase 5" in selected_phase:
    if multimodal_subphase == "5.1: Table Incorporation":
        st.markdown("""<div class="p5-header"><b style="color: #854d0e; font-size: 16px;">📊 Phase 5.1: Tabular Analysis Pipeline</b><br><span style="color: #1e293b; font-size: 14px;"><b>Use Case:</b> Run text-based structural queries targeted explicitly at layout tables. The underlying retrieval network parses structural markdown grids to preserve columns and perform flawless arithmetic calculations.</span></div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="p5-header"><b style="color: #854d0e; font-size: 16px;">🖼️ Phase 5.2: Vision Analytics Pipeline</b><br><span style="color: #1e293b; font-size: 14px;"><b>Use Case:</b> Analyze trends, charts, bar graphs, and complex corporate visual workflows. The system maps visual coordinates to contextual linguistic indices for advanced document sight synthesis.</span></div>""", unsafe_allow_html=True)

st.markdown("---")
user_query = st.chat_input("💡 Enter your financial analytical question here...")

if user_query:
    st.chat_message("user").write(user_query)
    
    with st.spinner(f"Executing {selected_phase.split(':')[0]} Pipeline..."):
        context_documents, pre_generated_answer = get_rag_documents(
            query=user_query, 
            phase=selected_phase, 
            db_type=selected_db,
            num_chunks=chunk_slider,
            start_page=start_page,
            end_page=end_page,
            strategy=chosen_strategy,
            multimodal_subphase=multimodal_subphase
        )
        
    st.markdown("### 🤖 Synthesized Analysis")
    
    # ---------------------------------------------------------
    # 🛠️ FIXED: UI Streaming Implementation
    # ---------------------------------------------------------
    if not context_documents:
        st.warning("No relevant context found within active indices.")
    elif pre_generated_answer:
        # If it was a cache hit or a Phase 5/6 pre-synthesized answer, display normally
        st.markdown(f'<div class="response-container">{pre_generated_answer}</div>', unsafe_allow_html=True)
    else:
        # Run streaming generation for Phase 1, 3, and 4
        context_str = "\n\n".join([f"--- Section Element ---\n{doc.page_content}" for doc in context_documents])
        
        # Initialize Vertex AI Model
        llm = ChatVertexAI(model_name="gemini-2.5-flash", project=GCP_PROJECT_ID, location="us-central1")
        
        system_prompt = (
            "You are an expert financial assistant analyzing the IFC Annual Report.\n"
            "Answer accurately using ONLY the context provided below.\n\n"
            f"CONTEXT:\n{context_str}\n\n"
            f"QUESTION: {user_query}"
        )
        
        # Apply Langfuse config if Phase 1/3
        tracer = get_text_tracer()
        config = {"callbacks": [tracer]} if tracer and ("Phase 1" in selected_phase or "Phase 3" in selected_phase) else {}
        
        # 🛠️ Execute stream and write directly to UI container
        st.write("---")
        final_answer = st.write_stream(llm.stream(system_prompt, config=config)) #type: ignore
        st.write("---")
        
        # Save to Cache if Phase 4
        if "Phase 4" in selected_phase:
             st.session_state.cache_manager.add_to_cache(query=user_query, answer=str(final_answer), context_docs=context_documents)
             
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("🔍 Audit Verified Data Source Blocks (Metadata Attribution)"):
        if not context_documents:
            st.warning("No context blocks were returned.")
        else:
            for index, doc in enumerate(context_documents, 1):
                st.markdown(f"**Context Block [{index}]**")
                col1, col2, col3 = st.columns(3)
                pages = doc.metadata.get('primary_page') or doc.metadata.get('pages', 'Unknown')
                col1.caption(f"📄 **Pages:** `{pages}`")
                
                if "Phase 1" not in selected_phase and "Phase 5" not in selected_phase:
                    col2.caption(f"🎯 **Cross-Encoder Score:** `{doc.metadata.get('relevance_score', 'N/A')}`")
                else:
                    col2.caption(f"⚙️ **Engine:** `{selected_db.upper()}`")
                    
                col3.caption(f"📋 **Type:** `{doc.metadata.get('content_types_handled', 'N/A')}`")
                st.code(doc.page_content, language="text")
                st.markdown("<hr style='margin:10px 0px;'>", unsafe_allow_html=True)