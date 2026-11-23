# web/ — the chat page

Plain HTML, CSS and JavaScript (ADR-004). No build step; GitHub Pages serves this folder as it is.

| File | What it does |
|---|---|
| `index.html` | Page structure: AI note, chat log, question chips, contact form |
| `app.js` | EN/DE texts, chat calls, contact form, error texts |
| `style.css` | Layout, light and dark theme (follows the system setting) |
| `config.js` | `API_BASE` and `TURNSTILE_SITE_KEY` |
| `dev/fake_api.py` | Fake backend for local tests (stdlib only) |

## Run locally

```sh
python web/dev/fake_api.py            # fake backend on http://localhost:8787
python -m http.server 8000 -d web     # page on http://localhost:8000
```

Open http://localhost:8000. To test against the real backend instead, start it with
`uv run uvicorn app.main:app --port 7860 --workers 1` and set `API_BASE` to `http://localhost:7860`.
The backend must allow the page's origin in `ALLOWED_ORIGIN` (for local use: `http://localhost:8000`).

The fake API reacts to a few test words in the chat: `!401`, `!409`, `!429`, `!500`, and
"contact" or "erreichen" to open the form. `python web/dev/fake_api.py 6` gives only 6 turns, so
the turns-left hint shows at once. In the form, a message with `!503` gives the "not set up" error.
`--turnstile` makes `/session` and `/contact` need a Turnstile token, like a backend with
`TURNSTILE_SECRET` set. Use it together with a Cloudflare test site key in `config.js`:
`1x00000000000000000000AA` always passes, `2x00000000000000000000AB` always fails (the chat stays locked).

## Config

Edit `config.js`. Both values are public by design; never put a secret here.

- `API_BASE`: the backend URL without a trailing slash, for example the Render URL `https://recruiter-assistant-asig.onrender.com`.
- `TURNSTILE_SITE_KEY`: the Cloudflare Turnstile site key. With a key, the page shows a security
  check on load and keeps the chat locked until a session exists. Empty means no widget and no lock,
  which only works while the backend has no `TURNSTILE_SECRET` (local dev).

## How it talks to the backend

1. Page load: `GET /health`, which wakes a sleeping Space. A note shows if it takes longer than 1.5 s.
2. Session: with a site key, the page shows the Turnstile widget at once and sends its token as
   `POST /session` with `{"turnstile_token": "..."}`. The question field and chips stay locked until
   the reply `{token, expires_in, turns_left}` arrives. Without a site key it sends `{}` on the first
   question. The token stays in memory only.
3. `POST /chat` with `Authorization: Bearer <token>` and `{"message": "..."}`. A 401 gets a new
   session (the widget runs again for a fresh token), one retry, and a note to the user.
4. When a reply has `show_form: true`, the form shows. It posts `{email, message, turnstile_token}`
   to `/contact` with the same token.

Model replies are set with `textContent` only, never as HTML.
