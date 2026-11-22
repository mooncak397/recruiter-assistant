# ADR-003: Email through the Resend API, sandbox sender, recipient fixed in code

Status: accepted, 2026-11-22.

Options:
1. Resend free plan: 100 emails per day, 3,000 per month, no card. Without a verified domain, the sender `onboarding@resend.dev` can only send to the account owner's own address. That restriction is exactly our rule.
2. Gmail SMTP with an app password. Needs 2FA and an app password that gives access to the whole Gmail account. SMTP from HF Spaces may be blocked.
3. Brevo or a similar free API. Works, but needs sender verification and offers no advantage here.

Decision: Resend. The recipient is the Resend account address, held in the secret `CONTACT_TO`. The `/contact` request model has no recipient field and rejects unknown fields. The recruiter's address from the form goes into `Reply-To`, so Christopher just presses reply.

Why: the HTTPS API works from HF Spaces, the key can only send email (no inbox access), and the sandbox limit enforces the fixed recipient on the provider side too. That gives two layers.

Consequences: if Christopher later buys a domain, he verifies it in Resend and changes the sender. Nothing else changes. Resend keeps send logs for 30 days on the free plan; the privacy note says so.
