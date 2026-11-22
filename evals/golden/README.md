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
- `reference_en`: English reference answer for the judge on German cases.
- `trap: true`: the profile lists no X; the answer is the fixed sentence and never "the profile lists no X".

Files so far: `facts.yaml` (14), `unknown.yaml` (10), `discretion.yaml` (6) = 30 cases.
Still to write: off-topic, injection and contact cases (23).
