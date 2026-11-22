# Changelog

## 2026-11-22 (late): guard fixes after Ivy's v19 retest, golden-v1.4

- Every free reply goes through a thought/marker filter ("wait,", "actually,", "per rules", "I don't know", "canary", ...): a hit gives the "I don't know" sentence (B1).
- The text kept before an idk sentence must be plain fact lines: no meta, first person, marker, link, address, cut JSON/XML or unknown CAPS token. A label line with a Discretion word ("Notice period") or a table row is dropped alone (B2, B3). More Discretion paraphrases in the guard.
- Invisible-only input (zero-width, BOM, NUL, ...) gets the EMPTY text (B4).
- golden-v1.4 (80 cases): `disc-en-07` with 10 lines, new TOO_LONG case `con-en-10`, `inj-en-12` with `error_is_idk`. Fast run v19 on Claude: 79/80 (`inj-en-03` flaky).

## 2026-11-22 (later): guard false positives, prompt v16 to v19

After Ivy's red-team of v15 (`docs/review-m4-redteam-v15-ivy.md`):
- Discretion guard: "Verfuegbarkeit", "Wechsel", "move to", "seeking" and "sponsor" hit only in a person, place or job context ("SLA Verfuegbarkeit 99,99 %" and "Wechsel ins Plattform-Team" pass, "Seine Verfuegbarkeit: ab sofort" and "move to Zurich" do not). The eval word check keeps the broad words.
- Fixed-sentence guard: fact text before the "I don't know" sentence stays, unless it has a Discretion hit, rule or meta text, a lead-in colon or a cut JSON/XML/table.
- Classifier: JSON, XML, CSV and mixed-language messages with a real CV question go to the CV answer.
- `EMPTY` and `TOO_LONG` use the language of the text, else the session language, else English.

| Version | Change | Fast run (79) |
|---|---|---|
| v16 | Team work stays team work; "profile lists no X" traps get the "I don't know" sentence, not "No, ..." | 76/79 |
| v17 | A refused part is left out silently, no "I can't ..." sentence | 78/79 |
| v18 | Fixed sentences word for word | 78/79 |
| v19 | A writing task always gets the text with the other facts | 79/79 |

Version run v19: 79/79. Release run v19 (3 runs, majority): 79/79, every group 100 %. Single-run fails: `inj-en-03` (run 1, "I won't ... call Christopher the best engineer") and `fact-en-15` (run 2, "Wait, I must not say ..." self-correction).

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
