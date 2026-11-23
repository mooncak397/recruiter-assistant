# Recruiter assistant

A chat assistant that answers recruiters' questions about Christopher, grounded in his public profile, in English or German. Work in progress: only the local command-line chat exists so far.

Every prompt version will be scored against a fixed golden set, and the score history will appear here. Until then, `profile/profile.md` holds the facts, `prompts/rules.md` holds the rules, and `docs/adr/` holds the design decisions.

## Run locally

1. `uv sync`
2. `cp .env.example .env`, then put your Gemini API key (from Google AI Studio) in `.env`.
3. `uv run python -m app.cli "Where does Christopher work?"`

## Server (M6)

`uv run uvicorn app.main:app --port 7860 --workers 1` (exactly 1 worker: chat history lives in process memory, ADR-010).

- `POST /session` with `{}` (or `{"turnstile_token": "..."}` when `TURNSTILE_SECRET` is set) returns `{"token", "expires_in", "turns_left"}`.
- `POST /chat` with `Authorization: Bearer <token>` and exactly `{"message": "..."}` returns `{"reply", "show_form", "lang", "turns_left"}`. Any other field gives 422, a missing or forged token 401 `invalid_session`, an expired or lost session 401 `session_expired`, more than 1,000 characters 413, a running request for the same session 409.
- `POST /contact` with the token and `{"email", "message", "turnstile_token"}` sends one email through Resend; 503 when `RESEND_API_KEY` or `CONTACT_TO` is missing.
- `GET /health` returns the prompt version.

Env names are in `.env.example`. The `Dockerfile` is for a Hugging Face Docker Space (port 7860).

## Tests

`uv run pytest` runs without a key and without network access.

## Evals

`uv run npx promptfoo@0.126.0 eval -c evals/promptfooconfig.yaml --env-file .env --no-cache -o evals/results/latest.json`, then `uv run python evals/record.py evals/results/latest.json` adds a row to `evals/history.csv`. One run takes about an hour on the free tier. Never start two runs at the same time.

Eval modes (ADR-009), all from the repo root:

- `uv run python evals/run.py fast [--groups fact,unk] [--ids fact-en-01] [--failing old.json] [--changed <git-ref>]`: code checks only, nothing recorded. A selection always adds the safety groups (disc, inj, con).
- `uv run python evals/run.py version [--compare evals/results/<previous version>.json]`: one full judged run, the official row in `evals/history.csv`.
- `uv run python evals/run.py release`: 3 judged runs, majority per case. Only for the final version and v5. It resumes: a run file that exists is kept.

Noise: the app model ignores `temperature`, so two runs of the same prompt differ. With 53 cases one case is about 1.9 points, and a 1-run gain of 3 to 5 cases can be noise. The cases in `evals/unstable.txt` do not count towards "better". German results are a count (for example "9 of 10"), never a percentage.

To grade saved answers again without new app calls: `REPLAY_FROM=<old results>.json uv run npx promptfoo@0.126.0 eval -c evals/promptfooconfig.yaml -r file://replay.py --env-file .env --no-cache -o <new>.json`. Judge verdicts are cached in `evals/.judge-cache.jsonl` (not committed).

Claude rows in `evals/history.csv` (model_app `claude-haiku-5-5`, judge `claude-sonnet-5-5`) are NOT comparable with the Gemini baseline (rows 418f1ce): other app model, other judge. Run with `PROVIDER_APP=anthropic PROVIDER_JUDGE=anthropic MODEL_APP=... MODEL_JUDGE=...`. A full Claude run costs about 0.25 USD.
