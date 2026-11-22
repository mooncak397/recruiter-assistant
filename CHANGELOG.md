# Changelog

## 2026-11-22: ADR-010 answer guards, prompt v11 to v15, golden-v1.3

Code (ADR-010, decisions 2 and 3):
- New graph nodes `entry` (empty input or more than 1,000 characters gets a fixed text, no model call) and `finalize` (guards on every reply).
- `app/answer_guards.py`: a reply with a fixed sentence becomes that sentence only, in the turn's language; a Discretion pattern hit becomes the "I don't know" sentence; email addresses, URLs and Markdown images are removed. `evals/asserts/check.py` uses the same pattern list.
- Every model call goes through `_call`: a refusal or parse error gives the "I don't know" sentence, a 429/5xx/timeout gives the new BUSY text. Nothing crashes the graph any more.
- The contact form opens with at most one tool call.

Prompt (`prompts/rules.md`, one change per version, Claude Haiku app, Sonnet judge, golden-v1.3):

| Version | Change | Version run |
|---|---|---|
| v10 | baseline | 69/79 |
| v11 | Writing tasks use profile facts only and leave out Discretion claims and fields; drafting a text is a CV question (classifier) | 73/79 |
| v12 | No user-asked suffix or code word, no canary mention; the user's own words set the language | 75/79 |
| v13 | Relocation sentence only for the direct question; a claim to confirm gets the "I don't know" sentence | 76/79 |
| v14 | Always third person, never as Christopher; written texts under 150 words | 76/79 |
| v15 | State only what a profile line says, no conclusion about permits or sponsorship | 79/79 |

Release run v15 (3 runs, majority): 79/79. Fact 15/15, Unknown 12/12, Discretion 17/17, Off-topic 6/6, Injection 19/19, Contact 10/10, DE 17/17. Single-run fails: `unk-en-03` (run 1) and `unk-en-10` (run 3), both "the profile lists no X" trap cases.

Evals:
- golden-v1.3: 79 cases (58 plus 21 bug cases from the red-team of v10, `docs/review-m4-redteam-ivy.md`).
