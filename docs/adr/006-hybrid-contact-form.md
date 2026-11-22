# ADR-006: Contact through a hybrid form; the model only opens it

Status: accepted, 2026-11-22 (owner's choice).

Options:
1. The model extracts the recruiter's address and calls a send tool. Simple to evaluate, but the address goes to the free Gemini tier.
2. A plain contact button with no model involvement. Private, but the assistant has no action left to learn or evaluate.
3. Hybrid: the model decides that the recruiter wants contact and calls `request_contact_form()`, which has no arguments. The browser shows a form, and the form posts straight to `/contact`.

Decision: option 3.

Why: the recruiter's address never reaches Google, and the project keeps a real tool call to measure. The tool's worst case drops to "a form appears when it was not needed".

Consequences:
- `/contact` is a separate endpoint. Anyone can call it directly without the chat, so it carries its own Turnstile token and its own caps.
- The privacy note asks visitors to use the form and not to type contact details into the chat.
- If a recruiter still types an address into the chat, the model opens the form and must not repeat the address in its answer (an eval case checks this).
