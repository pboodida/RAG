# Instructor setup guide

This guide walks you through everything needed to operate the AI review pipeline. Order matters — the workflow is inert until step 2 is complete.

---

## 1. Secrets — required & optional

Go to **Settings → Secrets and variables → Actions** in the repository and add the following.

### Required

| Secret | How to obtain | Notes |
|---|---|---|
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> → **Create API key** | Choose the GCP project `gd-gcp-techlead-experiments` if AI Studio asks. Quotas and billing are governed by the AI Studio key — verify quota in AI Studio before the first wave of submissions. |

### Optional

| Secret | How to obtain | Notes |
|---|---|---|
| `SLACK_WEBHOOK_URL` | <https://api.slack.com/apps> → create a Slack app for your workspace → **Incoming Webhooks** → activate → **Add New Webhook to Workspace** → choose the channel you want notifications in. Copy the URL. | If this secret is missing, the workflow simply skips the notification step. No errors. |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

---

## 2. Confirm the workflow runs

After secrets are in place, smoke-test the pipeline:

1. Check out the `prompt` branch locally.
2. Create a throwaway branch: `git checkout -b smoke-test`.
3. Add a tiny placeholder file (e.g., a `README.md` with the words "Smoke test"), commit, push.
4. Open a PR `smoke-test → prompt`.
5. Watch **Actions → AI Review**. The job should:
   - Run `evaluate.py` against the rubric for `prompt`.
   - Post a single review comment on the PR (verdict will be `failed` because there is no real submission, which is expected).
   - Skip Slack (because the verdict is `failed`) or send a notification (because the verdict is `passed_with_notes`/`passed`, which the AI is unlikely to give an empty PR but you can verify Slack later with a real submission).
6. Delete the throwaway PR and branch.

If the run fails before reaching the evaluator step, the most likely cause is a typo in the `GEMINI_API_KEY` secret or quota exhaustion on the AI Studio key.

---

## 3. Course delivery — student instructions

Students should be added as **Triage** or **Write** collaborators on this repo so they can push branches directly (the workflow runs cleanly on internal-branch PRs). Avoid the fork-PR flow — it requires a `pull_request_target` setup that we deliberately did not enable.

Share the top-level `README.md` with them — it covers the submission flow.

---

## 4. (Later) Enable branch protection

Once you have confirmed the pipeline works end-to-end with at least one real submission, lock the module branches.

For each of `prompt`, `rag`, `agentic`:

**Settings → Branches → Add branch ruleset** (or, on classic UI, **Add rule**):

- **Branch name pattern:** `prompt` (and one ruleset per branch, or use `{prompt,rag,agentic}` if your plan supports rulesets with multiple targets).
- **Require a pull request before merging** — ✓
  - **Required approvals:** 1 (the instructor)
  - **Dismiss stale pull-request approvals when new commits are pushed** — ✓
- **Require status checks to pass before merging** — ✓
  - **Require branches to be up to date before merging** — ✓
  - **Required checks:** add `review` (this is the job name from `ai-review.yml`).
- **Restrict who can push to matching branches** — ✓ (limit to instructors / maintainers; this prevents direct pushes around the PR flow).
- **Block force pushes** — ✓
- **Restrict deletions** — ✓

> Until you enable this, anyone with `Write` access can merge a PR without review. That is intentional during the bring-up phase so you can shake out issues without ceremony.

---

## 5. (Future) Upgrade from AI Studio API key to Vertex AI

The course spec asks students to use Vertex AI on the GCP project `gd-gcp-techlead-experiments`. The reviewer pipeline is configured to use **AI Studio API keys** instead, because creating a Vertex-AI-enabled service account requires IAM admin rights on the project that the current operator does not have.

When that role is available, switch the pipeline to Vertex AI as follows:

1. Have a GCP-project admin create a service account in `gd-gcp-techlead-experiments` (e.g., `ai-reviewer-sa`) with role `roles/aiplatform.user`.
2. Generate a JSON key and add it as a GitHub secret named `GCP_SA_KEY`.
3. Also add `GCP_PROJECT_ID` = `gd-gcp-techlead-experiments`.
4. Modify `.github/workflows/ai-review.yml` — add a Google-auth step before the evaluator:
   ```yaml
   - name: Google auth
     uses: google-github-actions/auth@v2
     with:
       credentials_json: ${{ secrets.GCP_SA_KEY }}
   ```
5. Modify `.github/scripts/evaluate.py` — replace `genai.Client(api_key=...)` with `genai.Client(vertexai=True, project=os.environ["GCP_PROJECT_ID"], location="us-central1")` and drop the `GEMINI_API_KEY` env var.

This is a 10-minute change once the IAM is unblocked.

---

## 6. Re-running a review

A student's review re-runs automatically on every `synchronize` event (i.e., every new push to the PR head branch). The bot updates its existing PR comment in place rather than creating a new one each time. There is nothing to clean up.

If you want to force a re-review without a code change, push an empty commit:

```bash
git commit --allow-empty -m "Trigger AI re-review"
git push
```

---

## 7. Cost monitoring

Watch the AI Studio API key's usage at <https://aistudio.google.com/apikey>. A single review consumes roughly:

- ~50–250k input tokens (depending on submission size — capped at 800k bytes of code by the evaluator).
- ~3–10k output tokens.

For Gemini 3.1 Pro Preview pricing, see <https://ai.google.dev/pricing>. If costs become a concern, swap the model in `evaluate.py` from `gemini-3.1-pro-preview` to `gemini-2.5-flash` — it loses some depth in the analysis but keeps the structure.
