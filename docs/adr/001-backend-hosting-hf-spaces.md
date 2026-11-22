# ADR-001: Backend hosting on Hugging Face Spaces (Docker)

Status: accepted, 2026-11-22.

Context: GitHub Pages serves static files only, so the Gemini key needs a backend. It must be free, run Python, and survive long idle periods, because recruiter traffic is sparse.

Options:
1. Hugging Face Spaces, Docker SDK, free CPU Basic (2 vCPU, 16 GB RAM). Sleeps after 48 hours without traffic; a visit wakes it in about 10 to 60 seconds. Secrets live in the Space settings.
2. Render free web service. Sleeps after 15 minutes without traffic and needs about a minute to wake. 750 free instance hours per month. Render's docs say not to use free instances for production.
3. Cloudflare Workers. Free and fast, but Python Workers run on Pyodide and LangChain/LangGraph support there is poor.

Decision: Hugging Face Spaces with Docker and FastAPI.

Why: with sparse traffic, Render would be asleep for almost every recruiter visit. A Space stays awake for two days after each visit, so a recruiter who returns finds it warm. It is also a known place in the ML community, which helps the portfolio.

Consequences:
- The frontend calls `GET /health` when the page opens and shows "Waking up the assistant..." until it answers. That hides most of the cold start while the visitor reads the intro.
- No keep-alive pinging. HF has flagged accounts for aggressive pings, and it is not needed.
- The Space disk is not persistent. Fine, because we store nothing.
- The Space must be public so the browser can call it. The code is public anyway; the secrets are not.
- HF Spaces restricts outbound connections, and SMTP ports are known to fail there. This is one more reason for an HTTPS email API (ADR-003).
