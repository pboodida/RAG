# Rubric — RAG Capstone

This rubric governs the AI review for submissions targeting the **`rag`** branch. Apply it together with the generic evaluation philosophy in your system prompt.

---

## Mandatory technical requirements (singletons)

Each item below is named **explicitly** in the spec and is **non-optional**. Verify with `import` + call site in non-test source. Substitution is acceptable when the role is filled by an equivalent tool — note it.

| Requirement | What to look for | Acceptable substitutions |
|---|---|---|
| **Gemini LLM** (2.0 Flash or newer) | `gemini-*` model passed to the SDK; actual `generate_content` calls in retrieval-augmented chains. | A newer Gemini model is fine. A non-Gemini LLM → substitution. |
| **Google GenAI SDK with Vertex AI auth** | `from google import genai` with `vertexai=True` / `project=...` / `location=...`, or `aiplatform.init(...)`. **Spec is explicit: "no API keys".** | If the student uses `genai.Client(api_key=...)` instead, note as substitution. |
| **UI — Streamlit *or* Gradio** | `import streamlit` / `import gradio` plus an entrypoint script. Either one satisfies. | Custom UI that lets a user query the RAG system → substitution. |
| **FAISS** | `import faiss` and an actual `faiss.IndexFlat*` or similar index built from the document embeddings. The spec mandates FAISS *together with* Qdrant for the Phase 1 comparison — both are required. | None for FAISS specifically — Chroma instead of FAISS is a substitution, but then the FAISS-vs-Qdrant comparison required by Phase 1 cannot have happened, which is a separate gap. |
| **Qdrant** | `from qdrant_client` and a real `QdrantClient(...)` instance with collection setup. A `docker-compose.yml` running Qdrant counts as supporting evidence. | Same caveat as FAISS — substituting Qdrant breaks Phase 1's "two-index comparison" requirement. |
| **LangChain** | `from langchain` / `from langchain_core` / `from langchain_community` and actual `RetrievalQA`, `Runnable`, `Chain`, or LCEL composition wiring retrieval and generation. | LlamaIndex used end-to-end → substitution (it fills the RAG-framework role). |
| **Langfuse** | `from langfuse` import in app code; `Langfuse(...)` initialised and used to trace retrieval / generation. Just listing it in `requirements.txt` is not evidence. | LangSmith / OpenTelemetry to a tracing backend → substitution. |
| **RAGAS** | `from ragas` import and an actual call to `ragas.evaluate(...)` against the provided evaluation dataset. A notebook in `notebooks/` counts if it is the phase-2 deliverable. | A custom LLM-as-Judge implementation that produces the same metrics (faithfulness, answer relevance, context precision) → substitution. |
| **Docker** | Real `Dockerfile` with a working entrypoint and/or `docker-compose.yml` defining the services (app + Qdrant). | None. Docker is the requirement. |

---

## Mandatory data parsing (`Parse` — all three required)

The spec calls these out under *Data Parsing Requirements*. All three must be implemented; if any one is missing, mark `Parse` as `delivered_with_gaps` and call out which sub-step is absent.

1. **Text extraction + metadata** — text content of the PDF is extracted and stored with metadata (page number is the minimum bar).
2. **Image extraction + Gemini-generated captions + metadata** — images pulled out, sent to Gemini for descriptive captions, captions indexed for retrieval.
3. **Table extraction in a structured format** — tables saved as `.md` / `.html` / `.json` / `.csv` or summarised, with metadata.

---

## Mandatory phases

Each phase is a checklist item. Verify the capability runs end-to-end (trace from entrypoint inward). A phase with stub files / unwired classes is `missing`.

### Phase 1 — Naive text RAG (`P1`)

- Chunking strategy applied to extracted text.
- Dense embeddings generated for chunks.
- **FAISS index built** with those embeddings.
- **Qdrant index built** with the same embeddings.
- A **FAISS-vs-Qdrant comparison** is documented (notebook, README, or `eval/` report). The comparison should at minimum cover retrieval quality and ease-of-use.
- A retriever module that fetches top-k chunks for a query.
- Streamlit / Gradio UI for entering a query and seeing the answer with retrieved context.
- Langfuse tracing on the retrieval+generation pipeline.

### Phase 2 — RAGAS evaluation (`P2`)

- The evaluation uses the provided Q&A dataset at `resources/datasets/rag_evaluation_dataset.csv` (or a copy with identical structure if the student forked it).
- Metrics computed by RAGAS (faithfulness, answer relevance, context precision/recall) are recorded somewhere reviewable — a report file, notebook output, or a UI page.
- The student must run this **after each subsequent phase** per the spec. If only one phase's eval exists, flag it as a gap but not a missing phase.

### Phase 3 — Cross-encoder re-ranking + metadata integration (`P3`)

- **Cross-encoder re-ranking** of top-N results from the base retriever (look for `sentence-transformers` cross-encoder models like `cross-encoder/ms-marco-MiniLM-*`, or `cohere.rerank`, or similar).
- **Metadata integration** in retrieval — at minimum: page number, section, content type — used for filtering (e.g., "search only in pages 10–20").

> Sparse / hybrid retrieval (BM25 + dense) is `(optional for interns)`. Do **not** flag it as missing.

### Phase 5.1 — Multimodal tables (`P5.1`)

- Table indexing and retrieval pipeline distinct from plain-text retrieval.
- Querying tabular data — a prompt path that handles "what was Net Income in FY24?" against the extracted tables.
- Retrieval pipeline searches across **both** text chunks and table representations in a unified manner.

### Phase 5.2 — Multimodal images (`P5.2`)

- Image extraction with Gemini-generated descriptions (overlaps with `Parse` step 2).
- Image descriptions included in the retrieval search space.
- A prompt path that lets the LLM answer a query using the image-derived textual info ("Show me the trend of IFC's Net Income from FY22 to FY24").

### Phase 6 — ColPali-like multimodal RAG (`P6`)

- Document pages rendered as images and segmented into patches.
- A VLM / multimodal embedding model used to generate embeddings (look for `colpali`, `paligemma`, `llava`, `gpt-4v`, or similar). Just a multimodal LLM call at inference time is **not** enough — there must be a patch-level embedding step.
- **Late-interaction / MaxSim retrieval** (ColBERT-style) implemented or imported (e.g., `colpali_engine`, `pylate`).
- Multimodal LLM is called with the retrieved visual context (image patches or full pages).
- Source attribution back to a page or patch in the response.
- A documented comparison with the previous (text-only or text+table+image-description) pipeline.

---

## What is explicitly OPTIONAL — never penalise

- **Phase 4 in its entirety** — Semantic caching, Multi-hop retrieval — labelled `(optional for interns)`.
- **Sparse / hybrid retrieval (BM25)** in Phase 3 — labelled `(optional for interns)`.
- **Document structure detection for advanced chunking** in Phase 1 — labelled `(Optional)`.
- **Image-to-text association** in Data Parsing — labelled `(Optional)`.
- **Custom re-ranking approaches** (graph-based, LLM as expert) in Phase 3 — labelled `(Optional)`.
- **Plotting functionality** in Phase 5.1 — labelled `(Optional)`.
- **LLM-as-Judge** in Phase 2 is *experimentation*, not a mandatory deliverable.

---

## Common tripwires for this module

- **FAISS or Qdrant in `requirements.txt` but only one index is actually built.** That breaks the Phase 1 comparison requirement; treat it as a P1 gap.
- **The "comparison" is just one sentence in the README** ("FAISS was faster"). That's not a real comparison — flag it as weak. Real comparison = a notebook or report with concrete numbers / retrieval-quality data.
- **`ragas` package imported but no actual `evaluate(...)` call against the dataset.** Treat as `missing`.
- **Phase 6 attempted but only a multimodal LLM call** (no patch-level embeddings, no late-interaction retrieval). Treat as `delivered_with_gaps` and call out the missing pieces — patches, embeddings, MaxSim.
- **`langchain` in `requirements.txt` but the student wrote raw calls to Gemini.** That's the LangChain singleton missing — note `substituted` with the actual framework used (or `missing` if there is none).
- **Langfuse client is initialised but never receives an event.** That's `delivered_with_gaps` for the singleton — the wiring exists, but tracing is silent.

---

## Per-phase output expectations

For each phase listed above (`P1`, `P2`, `P3`, `P5.1`, `P5.2`, `P6`), produce one entry in `phase_analysis`.

For each singleton in the table at the top, produce one entry in `technical_requirements` (in the order shown). Also add one row labelled "Data parsing (text / images / tables)" summarising the `Parse` checklist.

Cite file paths in every evidence string. "no `from ragas` import anywhere in `app/`" is a good absence note; "RAGAS not found" is not.

---

## Original task specification (source of truth)

# Retrieval-Augmented Generation (RAG) — Capstone Project

> Course author: **Grid University**

## Overview

This practical task guides the student through designing, implementing, and evaluating a sophisticated Retrieval-Augmented Generation (RAG) system. The system is built to interact with the **`ifc-annual-report-2024-financials.pdf`** document. The student starts by developing a RAG system focused on textual data, then progressively enhances it to incorporate and query information from tables and images (charts/graphs) within the document. The task also explores advanced retrieval strategies, re-ranking, and robust evaluation techniques to optimise the RAG system's performance and accuracy in answering complex questions about the financial report.

## Dataset

The primary dataset is the **IFC Annual Report 2024 — Financials PDF** (`resources/documents/ifc-annual-report-2024-financials.pdf`). This document provides a rich source of textual content, tabular data, and visual data.

## Technical Requirements

| Area | Requirement |
|---|---|
| LLM | Gemini 2.0 Flash (or newer). |
| SDK | Google GenAI SDK with Vertex AI auth — **no API keys**. |
| UI | Streamlit or Gradio. |
| Vector DB | FAISS, Qdrant. |
| PDF processing | Docling / PyMuPDF / Gemini multimodal capabilities. |
| RAG framework | LangChain. |
| Containerisation | Docker. |
| Observability / Eval | Langfuse for observability, RAGAS for evaluation. |

## Data Parsing Requirements

1. Extract all textual data + metadata.
2. Extract all image data; Gemini-generated captions + metadata.
3. Extract all table data in structured format (`.md`, `.html`, `.json`, `.csv`) or summarise + metadata.

## Practice 1 — Phase 1: Text-Based RAG (Naive RAG)

- Extract text, clean and chunk.
- Generate dense embeddings; FAISS index + Qdrant index with same embeddings; compare.
- Retriever for top-k chunks.
- Streamlit / Gradio UI.
- Langfuse tracing.

## Practice 2 — Phase 2: RAG Pipeline Evaluation

- Use `resources/datasets/rag_evaluation_dataset.csv`.
- Evaluate with RAGAS (context relevance, faithfulness, answer relevance, etc.).
- Run after every subsequent phase.

## Practice 3 — Phase 3: Hybrid Search & Re-ranking

- Cross-encoder re-ranking of top-N results.
- Metadata integration (page, section, content type) usable for filtering.
- *(optional for interns)* Sparse / hybrid (BM25 + dense).

## Practice 4 — Phase 4: Advanced RAG Techniques *(all optional for interns)*

- Semantic caching.
- Multi-hop retrieval.

## Practice 5 — Multimodal RAG

### Phase 5.1: Tables

- Table indexing & retrieval.
- Querying tabular data with prompts that handle calculations / extraction.
- Integrated retrieval across text + tables.

### Phase 5.2: Images (Charts & Graphs)

- Image extraction + Gemini captions.
- Retrieval includes image descriptions.

## Practice 6 — Phase 6: ColPali-like Multimodal RAG

- Pages → images → patches.
- VLM multimodal embeddings (PaliGemma, ColPali, LLaVA, GPT-4V, ...).
- Late-interaction / MaxSim retrieval.
- Multimodal LLM with visual context.
- Source attribution back to page/patch.
- Comparison vs. previous pipeline.
