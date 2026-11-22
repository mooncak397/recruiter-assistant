# Golden set, version golden-v1

Cases are YAML. Each case has `id`, `lang`, `vars.message`, `route`, `expected` and `assert`.
The `assert` keys are shorthand, and M3 turns them into promptfoo asserts:

- `icontains-any`: at least one listed word is in the answer.
- `also_icontains_any`, `also_icontains_any_2`: a second (third) `icontains-any` that must also pass.
- `not-icontains`: none of the listed words may appear.
- `fixed_sentence_en`, `fixed_sentence_de`: the exact "I don't know" sentence from `prompts/rules.md`.
- `not_fixed_sentence_en`: the English sentence must not appear (German cases).
- `contains_exact`: the exact relocation sentence from `prompts/rules.md`.
- `lang_de`: the answer is German (checked by `evals/asserts/lang.py`).
- `fixed_off_topic_en`, `fixed_off_topic_de`: the answer is exactly the fixed off-topic text in `app/texts.py`.
- `tool_called`: `true` = `request_contact_form` must be called. Without it the tool must NOT be called (any call on another case is a false call).
- `reference_en`: English reference answer for the judge on German cases.
- `route` may be a list: any listed route passes (used for injection cases).
- `trap: true`: the profile lists no X; the answer is the fixed sentence and never "the profile lists no X".

Files: `facts.yaml` (14), `unknown.yaml` (10), `discretion.yaml` (6), `offtopic.yaml` (6), `injection.yaml` (9), `contact.yaml` (8) = 53 cases. 43 EN, 10 DE.
Zoe wrote the first three files. Finn wrote the last three.
