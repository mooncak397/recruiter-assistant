// Public settings for the chat page. Both values are public by design (no secrets here).
window.CONFIG = {
  // Backend base URL without a trailing slash. Local dev with web/dev/fake_api.py: "http://localhost:8787".
  API_BASE: "https://christopher-recruiter-assistant.onrender.com",
  // Cloudflare Turnstile site key. Empty = no widget (local dev only; the real /contact needs a token).
  // Cloudflare's always-pass test key: "1x00000000000000000000AA".
  TURNSTILE_SITE_KEY: "0x4AAAAAAGOOnMoJHBBQ84fu",
};
