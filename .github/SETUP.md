# Professor setup guide

This guide walks you through everything needed to operate the AI review pipeline. Order matters — the workflow is inert until step 1 is complete.

---

## 0. Operating principle — branches never merge

The module branches (`prompt`, `rag`, `agentic`) are **evaluation targets only**. Pull Requests opened against them must **never be merged**. Treat each PR as a per-student review thread:

1. Student opens the PR. Two AI reviewers run in parallel and post sticky comments.
2. Student iterates by pushing more commits. The bots re-run and update their comments in place.
3. Once both reviewers reach `passed` or `passed_with_notes`, you read the code + reviews on the PR thread.
4. **You close the PR without merging.** No code from any submission ever lands on a module branch.

This keeps each module branch a clean, empty target forever. It also means you can ignore the **Merge pull request** button entirely — step 4 in branch-protection setup (below) blocks it for safety.

---

## 1. Required secrets

Go to **Settings → Secrets and variables → Actions** in the repository and add the following.

| Secret | How to obtain |
|---|---|
| `ANTHROPIC_API_KEY` | <https://console.anthropic.com/settings/keys> → **Create Key**. If the org already provides an `ANTHROPIC_API_KEY` at the organization level, you do not need to add it here. |
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> → **Create API key**. Verify the quota in AI Studio before the first wave of submissions. |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

---

## 2. Confirm the workflow runs

Smoke-test the pipeline:

1. Clone the repo locally.
2. `git checkout prompt && git checkout -b smoke-test`.
3. Add a tiny placeholder file (anything will do), commit, push.
4. Open a PR `smoke-test → prompt`.
5. Watch **Actions → AI Review**. You should see two jobs running in parallel — `Review (Claude)` and `Review (Gemini)`. Each finishes by posting a sticky comment on the PR.
6. Verdicts will be `failed` because there is no real submission — that is expected.
7. **Close the PR without merging** and delete the throwaway branch.

If a job fails before reaching the model call, the most likely cause is a missing or typo'd API-key secret.

---

## 3. Course delivery — student instructions

Students should be added as **Triage** or **Write** collaborators on this repo so they can push branches directly (the workflow runs cleanly on internal-branch PRs). Avoid the fork-PR flow — it requires a `pull_request_target` setup that we deliberately did not enable.

Share the top-level [`README.md`](https://github.com/griddynamics/gridu-genai/blob/main/README.md) with them — it covers the submission flow and includes the no-merge warning at the top.

---

## 4. (Recommended) Enable branch protection

Once you have confirmed the pipeline works end-to-end, lock the module branches so PRs can be reviewed but cannot be merged accidentally.

For each of `prompt`, `rag`, `agentic`:

**Settings → Branches → Add branch ruleset** (or, on classic UI, **Add rule**):

- **Branch name pattern:** `prompt` (one ruleset per branch, or use `{prompt,rag,agentic}` if your plan supports rulesets with multiple targets).
- **Require a pull request before merging** — ✓ (this keeps direct pushes blocked even though no one would normally push).
- **Restrict who can push to matching branches** — ✓, leave the bypass list empty so even maintainers go through PRs.
- **Block force pushes** — ✓.
- **Restrict deletions** — ✓.
- **Require status checks to pass before merging** — leave OFF. We are not gating merge with the AI verdict, because merging is not part of the workflow.

> The simplest hard guarantee against accidental merges is the org-level GitHub setting **Allow merge commits / squash / rebase = OFF** on this repo (Settings → General → Pull Requests). That disables the "Merge pull request" button for everyone. Combine with the rules above for full protection.

---

## 5. (Future) Upgrade Gemini to Vertex AI auth

The course spec asks students to use Vertex AI through a GCP project. The Gemini reviewer currently uses an **AI Studio API key** because creating a Vertex-AI-enabled service account requires IAM admin rights on the GCP project that the current operator does not have.

When the IAM role is available, switch the Gemini job in `.github/workflows/ai-review.yml` to use Workload Identity Federation (no JSON key in secrets):

1. Have a GCP-project admin create a service account with the `roles/aiplatform.user` role.
2. Configure a WIF pool that trusts this repository (`google-github-actions/auth@v2` with `workload_identity_provider`).
3. In the `gemini` job, add the auth step before `run-gemini-cli` and set the action's auth inputs:
   ```yaml
   - uses: google-github-actions/auth@v2
     with:
       workload_identity_provider: projects/.../providers/...
       service_account: ai-reviewer-sa@PROJECT.iam.gserviceaccount.com
   - uses: google-github-actions/run-gemini-cli@v0.1.22
     with:
       use_vertex_ai: true
       gcp_project_id: <PROJECT_ID>
       gcp_location: us-central1
       gemini_model: gemini-3.1-pro-preview
       prompt: ${{ env.REVIEW_PROMPT }}
   ```
4. Drop the `gemini_api_key` input and remove the `GEMINI_API_KEY` secret.

---

## 6. (Future) Notifications

There are currently **no automatic notifications**. You check the repository's Pull Requests tab for new submissions and the AI verdicts on each.

Once the pipeline has passed Grid Dynamics' internal security review, the workflow can be extended to push notifications to:

- **Slack** — via an Incoming Webhook, gated on the AI verdict.
- **Email** — via SendGrid or an equivalent provider.
- **GitHub Issues / Projects** — auto-create a tracking item for each `passed*` submission so you have a follow-up backlog without leaving GitHub.

These are deliberately deferred until security review approves Grid Dynamics' use of an external messaging integration with the AI review pipeline.

---

## 7. Re-running a review

A review re-runs automatically on every `synchronize` event (i.e., every new push to the PR head branch). Each bot updates its existing sticky comment in place rather than creating a new one each time. There is nothing to clean up.

If you want to force a re-review without a code change, push an empty commit:

```bash
git commit --allow-empty -m "Trigger AI re-review"
git push
```

---

## 8. Cost monitoring

Both reviewers analyse the full submission on every PR push. Per-review cost depends on submission size. Watch usage at:

- **Claude (`claude-opus-4-7`)** — <https://console.anthropic.com/settings/usage>.
- **Gemini (`gemini-3.1-pro-preview`)** — <https://aistudio.google.com/apikey>.

If costs become a concern, downgrade the models in `.github/workflows/ai-review.yml`:

- Claude: `--model claude-sonnet-4-6` instead of `claude-opus-4-7`.
- Gemini: `gemini_model: gemini-2.5-flash` instead of `gemini-3.1-pro-preview`.

Both swaps trade some depth for cheaper, faster reviews.
