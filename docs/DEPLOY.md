# Deploy

The backend runs as a Hugging Face Docker Space, the chat page runs on GitHub Pages. Do the steps in this order: the Space URL goes into the page config, and the page origin goes into the Space settings.

Replace `<hf-user>` with your Hugging Face user name. The Space URL is `https://<hf-user>-recruiter-assistant.hf.space` (lowercase; dots and underscores in the name become dashes). The page URL is `https://mooncak397.github.io/recruiter-assistant/`.

## 1. Resend (contact form email)

1. Create an account at https://resend.com.
2. Go to **API Keys**, create a key with "Sending access". Copy it for step 3.
3. Without a verified domain, Resend only sends from `onboarding@resend.dev` and only to the email address of your Resend account. Use that address as `CONTACT_TO`. With your own domain verified, you can also set `CONTACT_FROM`, for example `Recruiter assistant <bot@your-domain>`.

## 2. Cloudflare Turnstile (bot check)

1. Create a free Cloudflare account, open **Turnstile**, click **Add widget**.
2. Hostnames: `mooncak397.github.io` (add `localhost` too if you want to test locally). Mode: **Managed**.
3. Copy the **site key** into `web/config.js` as `TURNSTILE_SITE_KEY`. It is public.
4. Keep the **secret key** for step 3. It is a secret: never put it in the repo.

## 3. Hugging Face Space (backend)

1. Create an account at https://huggingface.co and go to **New Space**.
2. Name: `recruiter-assistant`. SDK: **Docker**, template **Blank**. Hardware: **CPU basic (free)**. Visibility: public is fine, the code is public on GitHub anyway.
3. In the Space, open **Settings → Variables and secrets**. Add these as **secrets**:
   - `ANTHROPIC_API_KEY` (Claude), or `GEMINI_API_KEY` (Gemini free tier). One is enough.
   - `SESSION_HMAC_KEY`: a random value. Make one with `python3 -c "import secrets; print(secrets.token_hex(32))"`.
   - `RESEND_API_KEY`: from step 1.
   - `TURNSTILE_SECRET`: from step 2.
   - `CONTACT_TO`: the email address that gets the contact messages (see step 1.3).
4. Add these as **variables** (not secret):
   - Claude: `PROVIDER_APP=anthropic` and `MODEL_APP=claude-haiku-5-5`.
   - Gemini: `MODEL_APP=gemini-3.5-flash-lite` (the provider default is Gemini, so no `PROVIDER_APP`).
   - `ALLOWED_ORIGIN=https://mooncak397.github.io` (the origin only: no path, no trailing slash).
5. Create a Hugging Face access token with **write** permission: **Settings → Access Tokens**.
6. Push the repo to the Space, from the repo folder:
   ```sh
   git remote add space https://huggingface.co/spaces/<hf-user>/recruiter-assistant
   git push --force space main
   ```
   Git asks for a user name (your HF user name) and a password (the write token from step 5). `--force` is only for this first push: it replaces the starter README that the new Space has. Later pushes are a normal `git push space main`. The front matter at the top of `README.md` tells the Space to build the `Dockerfile` on port 7860.
7. Wait for the build (Space page, **Logs** tab, a few minutes). Then check:
   ```sh
   curl https://<hf-user>-recruiter-assistant.hf.space/health
   ```
   The reply is `{"status":"ok","prompt_version":"..."}`.

A free Space sleeps after 48 hours without traffic. The page calls `/health` on load to wake it; the first answer then takes about a minute.

## 4. GitHub Pages (chat page)

1. In `web/config.js`, set `API_BASE` to `https://<hf-user>-recruiter-assistant.hf.space` (no trailing slash). The `TURNSTILE_SITE_KEY` is set from step 2.3.
2. On GitHub, open the repo **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Commit and push the `web/config.js` change to `main`. A push that changes `web/` starts the **Pages** workflow. You can also start it by hand: **Actions → Pages → Run workflow**.
4. Open `https://mooncak397.github.io/recruiter-assistant/`. Ask one question and send one test message with the contact form.

## Optional: evals in CI

The **CI** workflow runs the tests on every push. Its `evals-fast` job runs only by hand (**Actions → CI → Run workflow**) and needs a repository secret: **Settings → Secrets and variables → Actions → New repository secret**, name `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`. Each run calls the model for every golden case, so it costs money with Claude (a few cents).
