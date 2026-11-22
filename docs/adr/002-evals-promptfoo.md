# ADR-002: Evals with promptfoo in CI; LangSmith only as an optional local tracer

Status: accepted, 2026-11-22.

Context: evals must run in GitHub Actions on every prompt change, and the score history must be public.

Options:
1. promptfoo only. YAML config and test cases in git, runs with `npx` in Actions without an account, deterministic assertions plus `llm-rubric` with a separate grader provider, JSON output we can commit. MIT licence; OpenAI bought the company in March 2026 and the repo says it stays open source with multi-provider support.
2. LangSmith only. Good traces and datasets, but datasets and results live in LangSmith's cloud. A public score needs shared links to a vendor UI, and CI needs an account and key.
3. Both in CI. Two tools to learn and two places for results.

Decision: promptfoo is the single source of eval truth: golden set, CI gate, public history. LangSmith is optional during development for tracing only, switched on by `LANGSMITH_TRACING=true` in Christopher's local `.env`. It is never needed in CI.

Why: the score has to live in the repo next to the prompt it measures. promptfoo keeps cases, config and results as files, so the history is reproducible by anyone who clones the repo.

Consequences:
- promptfoo calls the real LangGraph graph through a Python provider (`file://evals/provider.py`). We test the whole system (routing, tool decision, answer), not a bare prompt.
- Pin the promptfoo version in the workflow. A new grader version could move scores without a prompt change.
- Hiring managers know LangSmith, so the README mentions that traces were used during development. That is honest and costs nothing.
