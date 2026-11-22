# Recruiter assistant

A chat assistant that answers recruiters' questions about Christopher, grounded in his public profile, in English or German. Work in progress: only the local command-line chat exists so far.

Every prompt version will be scored against a fixed golden set, and the score history will appear here. Until then, `profile/profile.md` holds the facts, `prompts/rules.md` holds the rules, and `docs/adr/` holds the design decisions.

## Run locally

1. `uv sync`
2. `cp .env.example .env`, then put your Gemini API key (from Google AI Studio) in `.env`.
3. `uv run python -m app.cli "Where does Christopher work?"`

## Tests

`uv run pytest` runs without a key and without network access.

## Evals

`uv run npx promptfoo@0.126.0 eval -c evals/promptfooconfig.yaml --env-file .env --no-cache -o evals/results/latest.json`, then `uv run python evals/record.py evals/results/latest.json` adds a row to `evals/history.csv`. One run takes about an hour on the free tier. Never start two runs at the same time.
