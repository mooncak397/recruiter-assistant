# ADR-005: Models and the free quota split

Status: accepted, 2026-11-22. Numbers must be checked in AI Studio at M1, because Google does not guarantee free limits and changes them often.

Context: in November 2026 the free tier gives roughly 20 requests per day on the Flash models, about 500 per day on Flash-Lite, 0 on Pro, and about 14,400 per day on Gemma 4 (unconfirmed: third-party numbers, see "M1 check" below). Limits count per project and per model, not per key.

Decision:
- App model: the current free Flash-Lite model, name set in `MODEL_APP` env var.
- Judge model for evals: Gemma 4 (`MODEL_JUDGE`), on its own large quota. Using a different model family for the judge also reduces the judge favouring its own answers.
- One turn costs at most 2 Flash-Lite calls (classify + answer or contact). Off-topic replies are fixed text and cost 1. `/contact` costs 0.
- Daily budget in code: 140 live turns (up to 280 calls). One eval run is about 100 calls (53 cases), so two runs a day still fit under about 500.
- When the daily cap is hit, the chat shows a polite "back tomorrow" message with Christopher's LinkedIn link. The contact form keeps working, because it does not use the model.

Consequences: the eval workflow runs only on pull requests that touch `prompts/`, `profile/`, `app/` or `evals/`, plus on release tags, so CI cannot drain the live quota. CI uses its own Gemini key (same project) so it can be revoked on its own.

## M1 check (2026-11-22)

Checked in the Google AI Studio docs (pricing and models pages):
- `gemini-3.5-flash-lite` is a current model. Free tier: input and output "free of charge". "Used to improve our products": yes on the free tier, no on the paid tier. This matches the privacy rule in this project.
- `gemini-3.1-flash-lite` is also current. Older `gemini-2.5-flash` is deprecated and routes to `gemini-3.5-flash-lite` from 2026-12-01.
- Gemma 4 has a free tier, "free of charge". The docs page does not list a Gemma model ID. ListModels with the project key (2026-11-22) shows two Gemma 4 IDs: `gemma-4-31b-it` and `gemma-4-26b-a4b-it`, both with `generateContent`. Use `gemma-4-31b-it` as `MODEL_JUDGE` unless M3 shows a problem.
- Requests per day and per minute are not on the public docs pages. The rate-limit page says limits are shown in the AI Studio dashboard and "not guaranteed". The numbers above ("about 500 per day on Flash-Lite", "about 14,400 on Gemma 4") come from third-party sources and are not confirmed. The dashboard does not show them to the owner either. M3 must measure the real limits: run the eval and watch for 429 responses, then write the measured numbers here.
- `MODEL_APP` has no default in code. `.env.example` suggests `gemini-3.5-flash-lite`.
- Live test (2026-11-22): `gemini-3.5-flash-lite` answers in English and German through the CLI. The model ignores `temperature` (the library warns that it uses fixed sampling defaults), so "temperature 0" in this plan has no effect on this model.
- Observed 2026-11-22 (M3): one full golden run on `gemini-3.5-flash-lite` made 95 model calls (53 cases, one case at a time, 4 s pause, about 12 minutes, about 8 calls per minute) with no 429 response. This shows the free tier allows at least that rate and about 95 calls in one run. It does not show the limit itself. The limit is still unconfirmed. The judge (Gemma 4) has not run yet.
- Official v1 baseline (2026-11-22, `evals/results/v1-baseline.json`): 95 Flash-Lite calls and 30 Gemma 4 judge calls in one run. The app model gave one 429 in the whole run (the provider retried once). `gemma-4-31b-it` often answers 503 "high demand" in spikes. A judge call can need minutes, so `evals/judge.py` retries up to about 150 s per call, and the full run took 51 minutes. Plan for about one hour per run. The real per-day limits are still unknown.
