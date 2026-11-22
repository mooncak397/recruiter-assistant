# ADR-005: Models and the free quota split

Status: accepted, 2026-11-22. Numbers must be checked in AI Studio at M1, because Google does not guarantee free limits and changes them often.

Context: in November 2026 the free tier gives roughly 20 requests per day on the Flash models, about 500 per day on Flash-Lite, 0 on Pro, and about 14,400 per day on Gemma 4. Limits count per project and per model, not per key.

Decision:
- App model: the current free Flash-Lite model, name set in `MODEL_APP` env var.
- Judge model for evals: Gemma 4 (`MODEL_JUDGE`), on its own large quota. Using a different model family for the judge also reduces the judge favouring its own answers.
- One turn costs at most 2 Flash-Lite calls (classify + answer or contact). Off-topic replies are fixed text and cost 1. `/contact` costs 0.
- Daily budget in code: 140 live turns (up to 280 calls). One eval run is about 100 calls (53 cases), so two runs a day still fit under about 500.
- When the daily cap is hit, the chat shows a polite "back tomorrow" message with Christopher's LinkedIn link. The contact form keeps working, because it does not use the model.

Consequences: the eval workflow runs only on pull requests that touch `prompts/`, `profile/`, `app/` or `evals/`, plus on release tags, so CI cannot drain the live quota. CI uses its own Gemini key (same project) so it can be revoked on its own.
