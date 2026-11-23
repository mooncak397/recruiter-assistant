# ADR-004: Frontend as plain static files on GitHub Pages

Status: accepted, 2026-11-22.

Update 2026-11-23: superseded. The project is local-only now; the page is no longer hosted on GitHub Pages (see the README).

Options: plain HTML/CSS/JS with no build; a small Vite + framework app; the Space's own Gradio UI.

Decision: plain HTML, CSS and one `app.js`, deployed by `pages.yml`.

Why: one chat box, one contact form and one privacy page do not need a framework. No build step means nothing to break and less for Christopher to maintain. Gradio would look like every other demo and would ignore the GitHub Pages decision.

Consequences: Mila can give it a visual design later without changing the architecture. The Turnstile site key is public by design and sits in `app.js`. The backend allows CORS only from `https://<user>.github.io`. The page has an EN/DE switch for its own fixed texts (intro, form labels, privacy note); the chat follows the recruiter's language on its own.
