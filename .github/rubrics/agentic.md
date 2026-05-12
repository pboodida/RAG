# Rubric — Agentic Systems Capstone

This rubric governs the AI review for submissions targeting the **`agentic`** branch. Apply it together with the generic evaluation philosophy in your system prompt.

---

## Mandatory technical requirements (singletons)

Each item below is named **explicitly** in the spec and is **non-optional**. Verify with `import` + call site in non-test source.

| Requirement | What to look for | Acceptable substitutions |
|---|---|---|
| **ADK — Agent Development Kit** | `from google.adk` imports, `LlmAgent` / `LoopAgent` / `SequentialAgent` / `Runner` / `Tool` instances actually wired into the agent. | **None.** ADK is the course's primary framework — the framework itself is the learning objective. Substituting with LangGraph / Autogen / CrewAI is a hard failure, not a substitution. |
| **Vertex AI for Gemini** | `aiplatform.init(...)` or ADK config pointing at Vertex (`vertexai=True`, project + location). The spec is explicit that Gemini must be accessed via Vertex. | Plain Gemini API-key auth → substitution. Note it. |
| **FAISS** | `import faiss` and a real index built from the document corpus, used by the Document Search Tool. | Chroma / Qdrant for in-memory document search → substitution. |
| **Docker** | A `Dockerfile` with a working entrypoint that boots the agent (or `docker-compose.yml` that runs the agent + MCP server). | None. |

---

## Mandatory phases

Each phase corresponds to a "Practice" in the spec. Verify the capability runs end-to-end by tracing from the agent's entrypoint inward — `main.py`, `app.py`, `agent.py`, or whatever the student names the runner. A class that exists but is never registered on the agent / planner is `missing`, not `delivered`.

### Phase 1 — Core RAG Agent (`P1`)

- An explicit **Plan → Execute → Synthesise** flow. Look for either separate components or distinct LLM-driven steps with clear roles. A single one-shot prompt that does everything is **not** the architecture the spec asks for.
- A **Document Search Tool** registered with the agent (`adk.Tool` or equivalent ADK construct) that performs retrieval over the local corpus using FAISS.
- The agent answers questions using the Document Search Tool when appropriate.

### Phase 2 — Web Search Tool + Multi-source Synthesis (`P2`)

- A **Web Search Tool** wired into the agent's toolset. It must actually call a real web search API (Tavily, Serper, Bing, Google Custom Search, Brave Search, etc.) — a stub that returns a hardcoded string is `missing`.
- The **Planner** delegates between Document Search and Web Search based on the query. Verify by reading the planner prompt / routing logic.
- The **Synthesiser** handles multi-source evidence (potentially conflicting). Look for a prompt that explicitly asks the model to combine / reconcile multiple sources.

### Phase 3 — MCP Server + Financial Data Tool (`P3`)

- The **MCP fetch server** from Anthropic is deployed. Verify with: a `docker-compose.yml` running `mcr.microsoft.com/...` or the official MCP fetch image, OR a `Dockerfile` that pulls it, OR a documented `docker run` command. The student must integrate with this server, not just reference it.
- A **Financial Data Tool** implemented as an ADK tool that hardcodes the Yahoo Finance URLs (`finance.yahoo.com/markets/{stocks,crypto,currencies}/`) and routes requests through the MCP server. Look for both the URLs and the MCP client call in the tool body.
- The **Planner** picks the Financial Data Tool vs. the Web Search Tool based on the query (currency / crypto / stock → Financial; otherwise → Web).

### Phase 4 — Autonomous Refinement Loop (`P4`)

- A **Critique component** — an LLM-as-reviewer prompt that examines the synthesiser's output and surfaces gaps / follow-up questions. Look for a prompt string with terms like "critic", "review", "identify gaps".
- A **main Agent Loop** (ADK `LoopAgent` or a manual loop) that calls the Critique component and decides terminate / continue. Look for a loop construct, not just a single critique call.
- A **`max_iterations` parameter** on the request that bounds the loop. The student must accept this from the user (CLI arg, request body, UI input) and pass it into the loop config.

### Phase 6 — Canvas Tool (`P6`)

- A **Canvas tool** that produces structured outputs in defined formats — at minimum text and markdown; bonus for HTML and code with language tagging.
- A clear **tool interface** that lets the agent pass content and format selection.
- The Canvas tool is **registered with the agent** (visible in the toolset / planner).
- The **Planner triggers Canvas** when the user asks for a report / summary / code snippet — look at the planner's routing logic.
- The **Synthesiser prepares Canvas input** in the appropriate format (structured payload, not raw answer text). Bonus marker: `Pydantic` model for the Canvas input or `Jinja2` template for the output.

---

## What is explicitly OPTIONAL — never penalise

- **Phase 5 — Agent-to-Agent (A2A) collaboration** is `*(Optional)*` in the spec. Do **not** flag the lack of an A2A News Agent.
- The `a2a` library is listed `(optional, for A2A communication)` — do not flag it as missing.
- **UI (Streamlit / Gradio)** is `*(optional)*` for this module — do not require one. If a UI exists, note it as a plus in `overall_assessment`.

---

## Common tripwires for this module

- **Student uses `langgraph` / `crewai` / `autogen` instead of ADK.** That is a hard failure (`failed`). Note specifically: "ADK is the course's primary framework and the learning objective; substituting it is not acceptable per the spec."
- **The Web Search Tool returns mocked data.** Look for `requests.get(...)`, `tavily-python`, `googlesearch-python`, `serpapi`, etc. — a real network call. A stub that returns `["fake result"]` is `missing`.
- **The Financial Tool hits Yahoo Finance directly with `requests.get`** instead of routing through the MCP server. That is `delivered_with_gaps` for P3 — the tool exists but does not use MCP. Flag it explicitly.
- **The Critique loop runs exactly once.** That's not a loop — it's a critique step. Mark P4 as `delivered_with_gaps` if no `max_iterations` parameter exists or if the loop body is hardcoded to one iteration.
- **The Canvas tool only returns plain text.** That's a single format — the spec lists "text documents, reports in Markdown / HTML, code snippets in specific programming languages". Mark P6 as `delivered_with_gaps` and list the missing formats.
- **`faiss-cpu` in `requirements.txt` but the Document Search Tool returns hardcoded content.** Treat FAISS as `missing` and P1 as `delivered_with_gaps` (the tool exists, but retrieval is fake).

---

## Per-phase output expectations

For each phase listed above (`P1`, `P2`, `P3`, `P4`, `P6`), produce one entry in `phase_analysis`.

For each singleton (`ADK`, `Vertex`, `FAISS`, `Docker`), produce one entry in `technical_requirements` in that order.

Be explicit when ADK is missing — it changes the verdict to `failed` regardless of the rest. State this in `overall_assessment`.

---

## Original task specification (source of truth)

# Agentic — Capstone Project

> Course author: **Grid University**

## Overview

This practical task challenges the student to design and build an advanced **autonomous research agent**. The focus is on system architecture and design thinking. The student starts with a simple, functional RAG-based agent and incrementally enhances its capabilities, culminating in a system that can autonomously **plan, execute, critique, and refine** its own research process.

## Technical Requirements

| Area | Requirement |
|---|---|
| LLM | Gemini 2.0 Flash (via Vertex AI). |
| Primary framework | **Agent Development Kit (ADK)** — <https://google.github.io/adk-docs/> |
| Cloud platform | Google Cloud Platform (GCP). Services: Vertex AI (for Gemini models). |
| Tools & libraries | ADK; FAISS for in-memory document search; **a2a** (optional, for A2A communication). |
| Programming language | Python |
| UI *(optional)* | Streamlit or Gradio. |
| Containerisation | Docker |

## Practice 1 — Phase 1: The Core RAG Agent

- Architect a basic **Plan → Execute → Synthesise** flow.
- Design and build the **Document Search Tool**. Adapting the RAG module from the previous project is encouraged.

## Practice 2 — Phase 2: Integrating External Knowledge

- Design and integrate a **Web Search Tool**.
- Update the **Planner** to delegate between Document Search and Web Search.
- Update the **Synthesiser** to handle multi-source evidence.

## Practice 3 — Phase 3: Integrating a Model Context Protocol (MCP) Server

- Deploy the MCP server (Anthropic fetch reference): <https://github.com/modelcontextprotocol/servers/tree/main/src/fetch>.
- Develop a **Financial Data Tool** (ADK tool) hard-coding Yahoo Finance sources:
  - <https://finance.yahoo.com/markets/stocks/most-active/>
  - <https://finance.yahoo.com/markets/crypto/all/>
  - <https://finance.yahoo.com/markets/currencies/>
- The Financial Tool fetches via the MCP server, not directly.
- Enhance the **Planner** to pick Financial vs. Web Search.

## Practice 4 — Phase 4: The Autonomous Refinement Loop

- Design a **Critique** component (LLM-as-reviewer prompt) that finds gaps and generates follow-up questions.
- Architect the **main Agent Loop**: run cycle → Critique → terminate / continue. Add `max_iterations` parameter on the request.

## Practice 5 — Phase 5 *(Optional)*: A2A Collaboration

- Design a minimal **News Agent** and its API.
- Design an A2A-client tool for the main agent.
- Update the Planner to delegate when appropriate.

## Practice 6 — Phase 6: Creating Canvas

- Define output formats (text / markdown / HTML / code).
- Define the Canvas tool interface.
- Integrate Canvas with the agent.
- Update the Planner to trigger Canvas for reports / summaries / code.
- Modify the Synthesiser to prepare Canvas input.
