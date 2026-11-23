// Settings for the chat page. Local use only: no public version is hosted any more (see README).
// For local runs set API_BASE to "http://localhost:7860" and use the Turnstile test key below. Both values are public by design (no secrets here).
window.CONFIG = {
  // Backend base URL without a trailing slash. Local dev with web/dev/fake_api.py: "http://localhost:8787".
  API_BASE: "https://recruiter-assistant-asig.onrender.com",
  // Cloudflare Turnstile site key. Empty = no widget (local dev only; the real /contact needs a token).
  // Cloudflare's always-pass test key: "1x00000000000000000000AA".
  TURNSTILE_SITE_KEY: "0x4AAAAAAGOOnMoJHBBQ84fu",
};
