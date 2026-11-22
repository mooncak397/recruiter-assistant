# ADR-007: One English profile, replies in English or German

Status: accepted, 2026-11-22 (languages chosen by the owner).

Options: one English `profile.md`; two profiles (EN and DE); one profile with both languages side by side.

Decision: one English profile. `rules.md` is also in English and holds a language rule plus the fixed sentences in both languages. Official German names (certificates, job titles, school names) stay in the profile as they appear on the CV.

Why: one source of truth, so facts cannot drift between two copies. Two profiles would also double the prompt size and the work for every fact change. Flash-Lite answers well in German from English facts, and the German eval cases measure exactly that.

Language rules in `rules.md`:
- Answer in the language of the recruiter's latest message. Use German for German, English for everything else.
- German uses "Sie" and Swiss spelling ("ss", never "ß"), because the readers are mostly Swiss recruiters.
- Fixed "I don't know" sentences:
  - EN: "I don't have that information about Christopher. You can ask him directly through the contact form."
  - DE: "Dazu habe ich keine Informationen über Christopher. Sie können ihn direkt über das Kontaktformular fragen."
- Fixed relocation sentences (discretion rule, section 6):
  - EN: "Relocation is a possibility for Christopher."
  - DE: "Ein Umzug ist für Christopher eine Möglichkeit."
- `classify` returns `lang` (`en` or `de`). The code uses it to pick the off-topic text, the form intro line and the cap message, so these fixed texts never need the model.

Consequences: if German answers score clearly lower than English ones, a later prompt version may add a short German glossary of Christopher's terms. A second profile stays the last option.
