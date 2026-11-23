> **Not in use.** The project is local-only since 2026-11-23, because a public bot would need a legal notice and privacy policy and, for EEA users, paid Gemini API terms. This file only documents the earlier public setup. The URLs below are outdated. For local use, see the README.

# Deploy

The backend runs as a Render web service (Docker, free plan), the chat page runs on GitHub Pages. Do the steps in this order: the Render URL goes into the page config, and the page origin goes into the Render settings.

The backend URL is `https://recruiter-assistant-asig.onrender.com`. The page URL is `https://mooncak397.github.io/recruiter-assistant/`.

## 1. Resend (contact form email)

1. Create an account at https://resend.com.
2. Go to **API Keys**, create a key with "Sending access". Copy it for step 3.
3. Without a verified domain, Resend only sends from `onboarding@resend.dev` and only to the email address of your Resend account. Use that address as `CONTACT_TO`. With your own domain verified, you can also set `CONTACT_FROM`, for example `Recruiter assistant <bot@your-domain>`.

## 2. Cloudflare Turnstile (bot check)

1. Create a free Cloudflare account, open **Turnstile**, click **Add widget**.
2. Hostnames: `mooncak397.github.io` (add `localhost` too if you want to test locally). Mode: **Managed**.
3. Copy the **site key** into `web/config.js` as `TURNSTILE_SITE_KEY`. It is public.
4. Keep the **secret key** for step 3. It is a secret: never put it in the repo.

## 3. Render (backend)

A Hugging Face Space was tried first, but its free CPU tier gave a quota of 0, so the backend moved to Render.

1. Create an account at https://render.com. Click **New → Web Service**.
2. Choose **Public Git Repository** and enter `https://github.com/mooncak397/recruiter-assistant`. Branch: `main`.
3. Language: **Docker** (Render builds the `Dockerfile`). Instance type: **Free**.
4. Under **Environment Variables**, add:
   - `ANTHROPIC_API_KEY` (Claude), or `GEMINI_API_KEY` (Gemini free tier). One is enough.
   - `SESSION_HMAC_KEY`: a random value. Make one with `python3 -c "import secrets; print(secrets.token_hex(32))"`.
   - `RESEND_API_KEY`: from step 1.
   - `TURNSTILE_SECRET`: from step 2.
   - `CONTACT_TO`: the email address that gets the contact messages (see step 1.3).
   - Claude: `PROVIDER_APP=anthropic`. Gemini needs no `PROVIDER_APP` (it is the default).
   - `MODEL_APP` is optional. Without it, the backend uses `claude-haiku-5-5` (Claude) or `gemini-3.5-flash-lite` (Gemini).
   - `PORT=7860` (the port the container listens on).
   - `ALLOWED_ORIGIN=https://mooncak397.github.io` (the origin only: no path, no trailing slash).
   The keys and secrets stay in Render only; never put them in the repo.
5. Click **Deploy Web Service** and wait for the build (a few minutes, **Logs** tab). Render shows the service URL at the top. Then check:
   ```sh
   curl https://recruiter-assistant-asig.onrender.com/health
   ```
   The reply is `{"status":"ok","prompt_version":"..."}`.

A free Render service sleeps after 15 minutes without traffic and needs up to a minute to wake up. The page pings `/health` on load, shows a wake-up note when `/session` takes longer than 4 seconds, and offers a retry button after 90 seconds.

## 4. GitHub Pages (chat page)

1. In `web/config.js`, set `API_BASE` to the Render URL from step 3 (no trailing slash). The `TURNSTILE_SITE_KEY` is set from step 2.3.
2. On GitHub, open the repo **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Commit and push the `web/config.js` change to `main`. A push that changes `web/` starts the **Pages** workflow. You can also start it by hand: **Actions → Pages → Run workflow**.
4. Open `https://mooncak397.github.io/recruiter-assistant/`. Ask one question and send one test message with the contact form.

## Optional: evals in CI

The **CI** workflow runs the tests on every push. Its `evals-fast` job runs only by hand (**Actions → CI → Run workflow**) and needs a repository secret: **Settings → Secrets and variables → Actions → New repository secret**, name `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`. Each run calls the model for every golden case, so it costs money with Claude (a few cents).
