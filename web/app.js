// Chat page logic. Model output is only ever set with textContent, never innerHTML.
(() => {
  const API = (window.CONFIG.API_BASE || "").replace(/\/+$/, "");
  const SITE_KEY = window.CONFIG.TURNSTILE_SITE_KEY || "";

  const T = {
    en: {
      skip: "Skip to the question field",
      title: "Ask about Christopher",
      intro: "Ask about Christopher's experience, skills and projects.",
      langLabel: "Language",
      badge: "AI",
      disclosure: "This is an AI assistant. Its answers come only from Christopher's public CV and can contain mistakes. Please do not type personal details into the chat.",
      waking: "Waking up the assistant. This can take up to a minute.",
      chatTitle: "Conversation",
      chipsLabel: "Try a question",
      chips: ["What is his current role?", "Which programming languages does he use?", "What projects has he built?", "How can I reach him?"],
      gateHint: "Please complete the short security check to start the chat.",
      inputLabel: "Your question",
      placeholder: "Type your question",
      send: "Send",
      you: "You",
      bot: "Assistant",
      thinking: "The assistant is writing...",
      turns: (n) => n === 0 ? "No questions left. Reload the page to start a new chat."
        : n === 1 ? "1 question left in this chat." : `${n} questions left in this chat.`,
      newSession: "Your chat session expired, so a new session has started. Earlier messages are no longer known to the assistant.",
      err403: "The security check failed. Please reload the page and try again.",
      err409: "The assistant is still answering your last message. Please wait a moment.",
      err413: "Your message is too long. Please keep it under 1,000 characters.",
      err429: "Too many messages right now. Please wait a minute and try again.",
      err5xx: "The assistant has a problem right now. Please try again later.",
      errNet: "The assistant cannot be reached. Please check your connection and try again.",
      formTitle: "Message Christopher",
      formHint: "Your message goes to Christopher by email. The AI does not see it.",
      email: "Email",
      message: "Message",
      submit: "Send message",
      sending: "Sending...",
      sent: "Thank you. Your message was sent to Christopher.",
      formInvalid: "Please fill in a valid email address and a message.",
      formCaptcha: "Please complete the security check.",
      formErr: "The message could not be sent. Please try again later.",
      formErr429: "Too many messages were sent today. Please try again tomorrow.",
      formErr503: "The contact form is not available right now. Please try again later.",
    },
    de: {
      skip: "Zum Fragefeld springen",
      title: "Fragen zu Christopher",
      intro: "Fragen Sie nach Christophers Erfahrung, Fähigkeiten und Projekten.",
      langLabel: "Sprache",
      badge: "KI",
      disclosure: "Dies ist ein KI-Assistent. Die Antworten stammen nur aus Christophers öffentlichem Lebenslauf und können Fehler enthalten. Bitte geben Sie keine persönlichen Daten in den Chat ein.",
      waking: "Der Assistent wird gestartet. Das kann bis zu einer Minute dauern.",
      chatTitle: "Unterhaltung",
      chipsLabel: "Beispielfragen",
      chips: ["Was ist seine aktuelle Rolle?", "Welche Programmiersprachen nutzt er?", "Welche Projekte hat er gebaut?", "Wie kann ich ihn erreichen?"],
      gateHint: "Bitte schliessen Sie die kurze Sicherheitsprüfung ab, um den Chat zu starten.",
      inputLabel: "Ihre Frage",
      placeholder: "Ihre Frage eingeben",
      send: "Senden",
      you: "Sie",
      bot: "Assistent",
      thinking: "Der Assistent schreibt...",
      turns: (n) => n === 0 ? "Keine Fragen mehr. Laden Sie die Seite neu, um einen neuen Chat zu starten."
        : n === 1 ? "Noch 1 Frage in diesem Chat." : `Noch ${n} Fragen in diesem Chat.`,
      newSession: "Ihre Chat-Sitzung ist abgelaufen. Eine neue Sitzung wurde gestartet; der Assistent kennt frühere Nachrichten nicht mehr.",
      err403: "Die Sicherheitsprüfung ist fehlgeschlagen. Bitte laden Sie die Seite neu und versuchen Sie es erneut.",
      err409: "Der Assistent beantwortet noch Ihre letzte Nachricht. Bitte warten Sie einen Moment.",
      err413: "Ihre Nachricht ist zu lang. Bitte schreiben Sie weniger als 1000 Zeichen.",
      err429: "Gerade zu viele Nachrichten. Bitte warten Sie eine Minute und versuchen Sie es erneut.",
      err5xx: "Der Assistent hat gerade ein Problem. Bitte versuchen Sie es später noch einmal.",
      errNet: "Der Assistent ist nicht erreichbar. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.",
      formTitle: "Nachricht an Christopher",
      formHint: "Ihre Nachricht geht per E-Mail an Christopher. Die KI sieht sie nicht.",
      email: "E-Mail",
      message: "Nachricht",
      submit: "Nachricht senden",
      sending: "Wird gesendet...",
      sent: "Danke. Ihre Nachricht wurde an Christopher gesendet.",
      formInvalid: "Bitte geben Sie eine gültige E-Mail-Adresse und eine Nachricht ein.",
      formCaptcha: "Bitte schliessen Sie die Sicherheitsprüfung ab.",
      formErr: "Die Nachricht konnte nicht gesendet werden. Bitte versuchen Sie es später noch einmal.",
      formErr429: "Heute wurden zu viele Nachrichten gesendet. Bitte versuchen Sie es morgen erneut.",
      formErr503: "Das Kontaktformular ist gerade nicht verfügbar. Bitte versuchen Sie es später noch einmal.",
    },
  };

  const $ = (id) => document.getElementById(id);
  const log = $("log"), ask = $("ask"), q = $("q"), sendBtn = ask.querySelector("button");
  const chips = $("chips"), notice = $("notice"), typing = $("typing");
  const gate = $("gate"), form = $("contact"), cStatus = $("c-status"), cBtn = form.querySelector("button");

  let lang = (navigator.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
  let token = null;        // session token, kept in memory only, gone on reload
  let turnsLeft = null;
  let noticeKey = null;    // so a language switch re-renders the current notice
  let widgetId = null;     // Turnstile widget in the contact form
  let gateWidget = null;   // Turnstile widget that guards /session
  let tsReady = null, tsWaiter = null;
  let locked = !!SITE_KEY; // no chat until the first session exists

  const t = (k) => T[lang][k];

  function setNotice(key, isError = false) {
    noticeKey = key;
    notice.classList.toggle("error", isError);
    notice.textContent = key ? t(key) : (turnsLeft !== null && turnsLeft <= 5 ? t("turns")(turnsLeft) : "");
  }

  function applyLang() {
    document.documentElement.lang = lang;
    document.title = t("title");
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    q.placeholder = t("placeholder");
    chips.querySelectorAll("button").forEach((b) => b.remove());
    t("chips").forEach((text) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = text;
      b.disabled = locked;
      b.addEventListener("click", () => send(text));
      chips.append(b);
    });
    log.querySelectorAll(".who").forEach((el) => { el.textContent = t(el.dataset.who); });
    if (!$("wake").hidden) $("wake").textContent = t("waking");
    setNotice(noticeKey, notice.classList.contains("error"));
  }

  function addMsg(who, text, msgLang) {
    const li = document.createElement("li");
    li.className = `msg ${who}`;
    const label = document.createElement("span");
    label.className = "who";
    label.dataset.who = who;   // so a language switch can relabel it
    label.textContent = t(who);
    const body = document.createElement("p");
    body.textContent = text;           // plain text only
    if (msgLang) body.lang = msgLang;
    li.append(label, body);
    log.append(li);
    li.scrollIntoView({ block: "end", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  const post = (path, body) => fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) },
    body: JSON.stringify(body),
  });

  const turnstileReady = () => tsReady ??= new Promise((resolve, reject) => {
    window.onTurnstileLoad = resolve;
    const s = document.createElement("script");
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onTurnstileLoad";
    s.async = true;
    s.onerror = reject;
    document.head.append(s);
  });

  // A fresh Turnstile token from the gate widget (tokens are single use). No site key (dev): null.
  function freshToken() {
    if (!SITE_KEY) return Promise.resolve(null);
    return new Promise((resolve, reject) => {
      tsWaiter = resolve;
      gate.hidden = false;
      turnstileReady().then(() => {
        if (gateWidget !== null) return window.turnstile.reset(gateWidget);
        gateWidget = window.turnstile.render("#ts-start", {
          sitekey: SITE_KEY, language: lang,
          callback: (tok) => { if (!tsWaiter) return; gate.hidden = true; tsWaiter(tok); tsWaiter = null; },
        });
      }).catch(reject);
    });
  }

  async function newSession() {
    token = null;
    const ts = await freshToken();
    const res = await post("/session", ts ? { turnstile_token: ts } : {});
    if (!res.ok) throw res;    // the caller maps the status to a text
    token = (await res.json()).token;
  }

  // POST with the session token. On 401 (invalid or expired) get a new session and retry once.
  // Returns [response, renewed].
  async function authed(path, body) {
    if (!token) await newSession();
    const res = await post(path, body);
    if (res.status !== 401) return [res, false];
    await newSession();
    return [await post(path, body), true];
  }

  const errorKey = (status) => ({ 403: "err403", 409: "err409", 413: "err413", 429: "err429" })[status] || "err5xx";

  async function send(text) {
    text = text.trim();
    if (!text || sendBtn.disabled) return;
    addMsg("you", text);
    q.value = "";
    chips.hidden = true;
    setBusy(true);
    setNotice(null);
    try {
      const [res, renewed] = await authed("/chat", { message: text });
      if (!res.ok) { setNotice(errorKey(res.status), true); return; }
      const data = await res.json();
      turnsLeft = typeof data.turns_left === "number" ? data.turns_left : null;
      addMsg("bot", String(data.reply ?? ""), data.lang);
      setNotice(renewed ? "newSession" : null);
      if (data.show_form) showForm();
    } catch (err) {
      setNotice(err instanceof Response ? errorKey(err.status) : "errNet", true);
    } finally {
      setBusy(false);
    }
  }

  function updateControls(busy = false) {
    const done = turnsLeft === 0;
    sendBtn.disabled = busy || done || locked;
    q.disabled = done || locked;
    chips.querySelectorAll("button").forEach((b) => { b.disabled = locked; });
  }

  function setBusy(busy) {
    typing.hidden = !busy;
    updateControls(busy);
    if (!busy && !q.disabled && !form.contains(document.activeElement)) q.focus();  // keep focus in a just-opened form
  }

  function showForm() {
    if (!form.hidden) return;
    form.hidden = false;
    $("contact-title").focus();
    if (SITE_KEY) turnstileReady().then(() => { widgetId = window.turnstile.render("#ts-form", { sitekey: SITE_KEY, language: lang }); });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    cStatus.classList.remove("error", "ok");
    const fail = (key) => { cStatus.textContent = t(key); cStatus.classList.add("error"); };
    if (!form.checkValidity()) {
      fail("formInvalid");
      form.querySelector(":invalid").focus();
      return;
    }
    const tsToken = SITE_KEY ? window.turnstile?.getResponse(widgetId) : null;
    if (SITE_KEY && !tsToken) { fail("formCaptcha"); return; }
    cBtn.disabled = true;
    cStatus.textContent = t("sending");
    try {
      // a 401 is checked before Turnstile on the server, so the retry inside authed() can reuse tsToken
      const [res] = await authed("/contact", { email: $("c-email").value.trim(), message: $("c-msg").value.trim(), turnstile_token: tsToken });
      if (!res.ok) { fail(({ 429: "formErr429", 503: "formErr503" })[res.status] || "formErr"); return; }
      form.querySelectorAll("label, input, textarea, button, .hint, #ts-form").forEach((el) => el.remove());
      cStatus.textContent = t("sent");
      cStatus.classList.add("ok");
    } catch (err) {
      fail(err instanceof Response ? "formErr" : "errNet");
    } finally {
      if (cBtn.isConnected) cBtn.disabled = false;
      if (widgetId !== null && window.turnstile && cBtn.isConnected) window.turnstile.reset(widgetId);  // tokens are single use
    }
  });

  ask.addEventListener("submit", (e) => { e.preventDefault(); send(q.value); });
  q.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(q.value); }
  });
  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => {
    lang = b.dataset.lang;
    applyLang();
  }));

  applyLang();
  updateControls();

  // Production: pass the Turnstile gate and open a session before the first question.
  if (SITE_KEY) {
    newSession()
      .catch((err) => setNotice(err instanceof Response ? errorKey(err.status) : "errNet", true))
      .finally(() => { locked = false; updateControls(); });  // after a failure the next question retries
  }

  // Wake the sleeping backend early; show a note only if it takes longer than a moment.
  const wake = $("wake");
  const wakeTimer = setTimeout(() => { wake.textContent = t("waking"); wake.hidden = false; }, 1500);
  fetch(`${API}/health`).catch(() => {}).finally(() => { clearTimeout(wakeTimer); wake.hidden = true; });
})();
