# Grid University — Gen AI Training Program

Welcome! This repository is the submission hub for the **Generative AI** training program at Grid University.

Each course module has its own dedicated branch. You submit your capstone project by opening a **Pull Request** from your personal working branch into the matching module branch. **Two AI reviewers run in parallel on every PR** — Claude and Gemini — each posting its own detailed feedback as a PR comment.

> ⚠️ **Pull Requests are evaluation-only.** The module branches (`prompt`, `rag`, `agentic`) exist solely as targets for review. **They are never merged.** Your professor reads your code and the AI reviews on the PR thread, then closes the PR. No code from a submission ever lands on a module branch.

---

## Course modules

| Module | Target branch | What you build |
|---|---|---|
| **Prompt Engineering** | [`prompt`](https://github.com/griddynamics/gridu-genai/tree/prompt) | A conversational app with synthetic data generation + natural-language SQL querying. |
| **Retrieval-Augmented Generation** | [`rag`](https://github.com/griddynamics/gridu-genai/tree/rag) | A multimodal RAG system over the IFC Annual Report 2024 PDF (text, tables, images). |
| **Agentic Systems** | [`agentic`](https://github.com/griddynamics/gridu-genai/tree/agentic) | An autonomous research agent built with ADK — plan, execute, critique, refine. |

Each module branch contains a `README.md` describing the deliverables and a `resources/` directory with the course-provided materials for that module. The branch is otherwise empty — your PR adds your full project on top of that blank slate, so the reviewers see exactly what you built and nothing else.

---

## How to submit

1. **Fork** this repository (or create a working branch directly if you have push access).
2. Create a branch off the module you are working on. For example, for the RAG capstone:
   ```bash
   git checkout rag
   git checkout -b <user-ldap-id>/rag-submission
   ```
3. Implement your solution on that branch. Commit and push as often as you like.
4. When you are ready for review, open a **Pull Request** targeting the module branch (`prompt`, `rag`, or `agentic`).
5. Two AI reviewers run automatically:
   - **Claude** (`claude-opus-4-7`) — posts its review as a single sticky comment.
   - **Gemini** (`gemini-3.1-pro-preview`) — posts its review as a second sticky comment.

   Each review includes an overall verdict (`failed` / `passed_with_notes` / `passed`), a technical-requirements table, a per-phase analysis with concrete file references, and a list of action items.
6. If a reviewer says `failed`, push more commits — both bots re-run on every push and update their existing comments in place.
7. Once you reach `passed` or `passed_with_notes`, request final review from your professor. They will read the PR, your code, and the AI feedback, then close the PR (without merging — see the warning at the top).

---

## What the AI reviewers check

Both reviewers read:

- the **task specification** — the `README.md` of the module branch you are PR-ing into;
- the **rubric** for that module — [`.github/rubrics/prompt.md`](https://github.com/griddynamics/gridu-genai/blob/main/.github/rubrics/prompt.md), [`.github/rubrics/rag.md`](https://github.com/griddynamics/gridu-genai/blob/main/.github/rubrics/rag.md), or [`.github/rubrics/agentic.md`](https://github.com/griddynamics/gridu-genai/blob/main/.github/rubrics/agentic.md).

They then walk through every mandatory phase of the spec and verify, against the actual code:

- Are all explicitly required technologies actually imported and wired into the running app? (Not just listed in `requirements.txt`.)
- Are all mandatory phases delivered end-to-end? Can the capability be traced from an entrypoint?
- For each gap: does the student substitute an equivalent tool (acceptable, noted) or is the role omitted entirely (failure)?

The reviewers cite file paths and line numbers when calling something out. They will not penalize you for items the spec labels `(Optional)` or `(optional for interns)`.

---

## Repository layout

```text
main                              ← this branch: workflow, rubrics, docs
├── README.md
└── .github/
    ├── workflows/ai-review.yml   ← two parallel reviewer jobs (Claude + Gemini)
    ├── rubrics/
    │   ├── prompt.md             ← per-module grading guidance
    │   ├── rag.md
    │   └── agentic.md
    └── SETUP.md                  ← professor setup notes

prompt                            ← orphan branch: Module 1 spec + resources
rag                               ← orphan branch: Module 2 spec + resources
agentic                           ← orphan branch: Module 3 spec
```

---

## For professors

See [`.github/SETUP.md`](https://github.com/griddynamics/gridu-genai/blob/main/.github/SETUP.md) for setup steps: required GitHub Secrets, the no-merge policy, and how to enable branch protection once the workflow is verified.
