# Grid University — Gen AI Training Program

Welcome! This repository is the submission hub for the **Generative AI** training program at Grid University.

Each course module has its own dedicated branch. You submit your capstone project by opening a **Pull Request** from your personal working branch into the matching module branch. An AI reviewer (Google Gemini, running on every PR) analyzes your code phase-by-phase against the course specification and posts detailed feedback as a PR comment.

---

## Course modules

| Module | Target branch | What you build |
|---|---|---|
| **Prompt Engineering** | [`prompt`](../../tree/prompt) | A conversational app with synthetic data generation + natural-language SQL querying. |
| **Retrieval-Augmented Generation** | [`rag`](../../tree/rag) | A multimodal RAG system over the IFC Annual Report 2024 PDF (text, tables, images). |
| **Agentic Systems** | [`agentic`](../../tree/agentic) | An autonomous research agent built with ADK — plan, execute, critique, refine. |

Each module branch contains a single `README.md` describing the deliverables for that module. The branch is intentionally **empty otherwise** — your PR adds your full project on top of that blank slate, so the reviewer sees exactly what you built and nothing else.

---

## How to submit

1. **Fork** this repository (or create a working branch directly if you have push access).
2. Create a branch off the module you are working on. For example, for the RAG capstone:
   ```bash
   git checkout rag
   git checkout -b <your-name>/rag-submission
   ```
3. Implement your solution on that branch. Commit and push as often as you like.
4. When you are ready for review, open a **Pull Request** targeting the module branch (`prompt`, `rag`, or `agentic`).
5. The AI reviewer runs automatically. It posts a comment on the PR with:
   - an overall verdict (`failed` / `passed_with_notes` / `passed`),
   - a per-phase analysis with concrete file references,
   - a list of actionable items so you know exactly what to fix.
6. If the verdict is `failed`, push more commits — the reviewer re-runs on every push.
7. Once you reach `passed` or `passed_with_notes`, your instructor is notified and will follow up.

---

## What the AI reviewer checks

The reviewer reads your **task specification** (the module branch's `README.md`) and the **rubric** for that module (in `.github/rubrics/`). It then walks through every mandatory phase of the spec and verifies, against the actual code:

- Are all explicitly required technologies actually imported and wired into the running app? (Not just listed in `requirements.txt`.)
- Are all mandatory phases delivered end-to-end? Can the capability be traced from an entrypoint?
- For each gap: does the student substitute an equivalent tool (acceptable, noted) or is the role omitted entirely (failure)?

The reviewer always cites file paths and line numbers when calling something out. It will not penalize you for items the spec labels `(Optional)` or `(optional for interns)`.

---

## Repository layout

```text
main                              ← this branch: workflow, evaluator, rubrics, docs
├── README.md
└── .github/
    ├── workflows/ai-review.yml   ← runs on every PR
    ├── scripts/
    │   ├── evaluate.py           ← Gemini-powered evaluator
    │   └── requirements.txt
    ├── rubrics/
    │   ├── prompt.md             ← per-module grading guidance
    │   ├── rag.md
    │   └── agentic.md
    └── SETUP.md                  ← instructor setup notes

prompt                            ← orphan branch: Module 1 spec only
rag                               ← orphan branch: Module 2 spec only
agentic                           ← orphan branch: Module 3 spec only
```

---

## For instructors

See [`.github/SETUP.md`](.github/SETUP.md) for setup steps: required GitHub Secrets, optional Slack notification, and how to enable branch protection once the workflow is verified.
