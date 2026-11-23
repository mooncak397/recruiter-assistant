# Legal drafts: privacy notice and Impressum

These are drafts, not legal advice. Have them checked (for example by a lawyer or a data protection advisory service) before you rely on them.

| File | What it is |
|---|---|
| `privacy.html` | Privacy notice (Datenschutzerklärung), DE and EN on one page. Goes to `web/privacy.html`. |
| `impressum.html` | Impressum page template, DE and EN. Goes to `web/impressum.html`. |
| `impressum-draft.md` | The same Impressum text as plain Markdown, for review. |

Both pages are kept out of `web/` on purpose. Everything in `web/` goes live on the next push, and a privacy notice also has to name the controller with a full name and address (Art. 13(1)(a) GDPR). So neither page can go live until the placeholders are filled.

## What Christopher must provide

1. Full name (`[[NAME]]`).
2. Street and house number (`[[STREET]]`).
3. ZIP code and city (`[[ZIP CITY]]`).
4. A contact email address (`[[EMAIL]]`). It must be one he reads, because Section 5 DDG asks for a way to reach him quickly by electronic means.

## The address question

Section 5 DDG requires an Impressum for "geschäftsmäßige" digital services, which are usually offered for payment. Whether a personal job-application site counts is not settled; many sites that promote a person's professional services are treated as business-like and publish an Impressum to be safe. If an Impressum is needed, it must give a postal address where he can be served legal documents (a "ladungsfähige Anschrift"). A P.O. box is not enough.

If he does not want his home address on the web, the usual options are:

- a mail-forwarding or business-address service that offers an address that can accept legal service (an "Impressum service"), usually for a monthly fee;
- the address of a legal entity he runs, if he has one;
- his home address.

This choice is his. The drafts work with any of them.

## Points to check before going live

- **Gemini terms.** The Gemini API Additional Terms (effective 2026-03-23) allow only Paid Services when an app is offered to users in the European Economic Area, Switzerland or the United Kingdom (section "Use Restrictions"). This site is aimed at recruiters in Germany. Running it on unpaid quota may break those terms. Options: turn on billing for the Gemini API key, or switch to `PROVIDER_APP=anthropic` (already supported in `app/llm.py`). If the provider changes, section 5 of the privacy notice must change too.
- **Render region.** The privacy notice says "US region". Check the region in the Render dashboard; if it is Frankfurt, change sections 5 and 8.
- **Model provider.** The notice describes Google Gemini, the current default. Update it if `PROVIDER_APP` changes.
- **New data flows.** Any new analytics, fonts from a CDN, embeds, cookies or storage use in `web/` means the notice must change before the push.

## Going live

1. Fill every `[[...]]` in both HTML files.
2. Copy them to `web/privacy.html` and `web/impressum.html`.
3. Add a footer to `web/index.html`, after `</main>`:
   ```html
   <footer class="page-foot"><a href="privacy.html">Privacy / Datenschutz</a> · <a href="impressum.html">Impressum</a></footer>
   ```
   and a matching rule in `web/style.css`, for example
   `.page-foot { max-width: 44rem; margin: 0 auto; padding: 0 1rem 1.5rem; font-size: 0.875rem; color: var(--muted); }`
4. Check: `grep -rn '\[\[' web/` must print nothing. Then commit and push.
