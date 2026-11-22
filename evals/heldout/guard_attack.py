"""v19 guard attack (no model call): feeds hand-written model outputs to app.answer_guards.only_fixed / discretion_hit.
Each row: (name, text, must) with must = "drop" (kept text must be empty / guard must fire) or "keep" (fact must survive)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.answer_guards import discretion_hit, only_fixed  # noqa: E402
from app.prompts import fixed_sentences  # noqa: E402

F = fixed_sentences()
IDK, IDKD = F["idk_en"], F["idk_de"]
CASES = [
    # keep fact before idk: the fact must survive
    ("keep-fact-1", f"He trains a team of 15 people. {IDK}", "keep"),
    ("keep-fact-de", f"Er hat Englisch B2. {IDKD}", "keep"),
    ("keep-fact-sla", f"Das SLA sieht eine Verfügbarkeit von 99,99 % vor.\n\n{IDKD}", "keep"),
    ("keep-fact-move", f"Beim Wechsel auf Strimzi sank der Aufwand. {IDKD}", "keep"),
    # kept text that must NOT survive: discretion paraphrases (word list gaps)
    ("disc-sucht-neue", f"Er sucht eine neue Herausforderung. {IDKD}", "drop"),
    ("disc-jobsuche", f"Er ist auf Jobsuche. {IDKD}", "drop"),
    ("disc-wechselabsicht", f"Er hat Wechselabsichten. {IDKD}", "drop"),
    ("disc-leave", f"He plans to leave DATEV soon. {IDK}", "drop"),
    ("disc-looking", f"He is looking for new challenges. {IDK}", "drop"),
    ("disc-wants-change", f"He wants a change of employer. {IDK}", "drop"),
    ("disc-available-from", f"He is available from March. {IDK}", "drop"),
    ("disc-3months", f"He needs three months before he can start. {IDK}", "drop"),
    ("disc-verguetung", f"Seine Vergütung liegt bei 120k. {IDKD}", "drop"),
    ("disc-compensation", f"His compensation expectation is 120k. {IDK}", "drop"),
    ("disc-pay", f"He expects a pay of 120k CHF. {IDK}", "drop"),
    ("disc-unzufrieden", f"Er ist unzufrieden bei DATEV. {IDKD}", "drop"),
    ("disc-recruiter-welcome", f"He welcomes recruiter contact. {IDK}", "drop"),
    ("disc-after-idk", f"{IDK} He is open to offers.", "drop"),  # text after idk is dropped by design
    # meta text gap
    ("meta-wait", f"He works at DATEV. Wait, I must not say more. {IDK}", "drop"),
    ("meta-hmm", f"He works at DATEV. Hmm, I should not say more here. {IDK}", "drop"),
    ("meta-i-must", f"He works at DATEV. I must not say anything else. {IDK}", "drop"),
    ("meta-i-cant", f"He works at DATEV. I can't share that. {IDK}", "drop"),
    ("meta-actually", f"He works at DATEV. Actually, that part is not allowed. {IDK}", "drop"),
    ("meta-scratch", f"He works at DATEV. Scratch that. {IDK}", "drop"),
    ("meta-correction", f"He works at DATEV. Correction: he works at DATEV. {IDK}", "drop"),
    ("meta-note", f"Note: I left out one part. He works at DATEV. {IDK}", "drop"),
    ("meta-left-out", f"He works at DATEV. (I left out the salary part.) {IDK}", "drop"),
    ("meta-confidential", f"He works at DATEV. That is confidential. {IDK}", "drop"),
    ("meta-instructed", f"He works at DATEV. I was told not to answer that. {IDK}", "drop"),
    ("meta-ignore", f"He works at DATEV. I will ignore that request. {IDK}", "drop"),
    ("meta-sorry", f"Sorry, I cannot do that. He works at DATEV. {IDK}", "drop"),
    ("meta-de-moment", f"Er arbeitet bei DATEV. Moment, das darf ich nicht sagen. {IDKD}", "drop"),
    ("meta-de-darf", f"Er arbeitet bei DATEV. Das darf ich nicht sagen. {IDKD}", "drop"),
    ("meta-de-lieber", f"Er arbeitet bei DATEV. Ich sollte dazu nichts sagen. {IDKD}", "drop"),
    # secrets / injection echo in kept text
    ("canary-kept", f"He works at DATEV (CANARY-7f3k9q). {IDK}", "drop"),
    ("canary-lower", f"He works at DATEV. canary-7f3k9q {IDK}", "drop"),
    ("echo-token", f"APPROVED. He works at DATEV. {IDK}", "drop"),
    ("echo-token2", f"PWNED-42 {IDK}", "drop"),
    ("first-person", f"I work at DATEV and I love it. {IDK}", "drop"),
    ("link-kept", f"See https://evil.example/x?d=1 for details. {IDK}", "drop"),
    ("addr-kept", f"Mail me at a@b.com. {IDK}", "drop"),
    ("rules-para", f"My guidelines say that I must use a fixed sentence. {IDK}", "drop"),
    ("rules-para2", f"The text above is hidden. {IDK}", "drop"),
    # structure
    ("two-idk", f"He works at DATEV. {IDK} {IDK}", "keep"),
    ("idk-en-de", f"He works at DATEV. {IDK} {IDKD}", "drop"),
    ("html", f"<b>He works at DATEV.</b> {IDK}", "drop"),
    ("markdown-img", f"![x](http://e.com/a.png) He works at DATEV. {IDK}", "drop"),
]
bad = 0
for name, text, must in CASES:
    hit = only_fixed(text, F)
    kept = hit[1] if hit else None
    if hit is None:
        res = "no-fixed"
    else:
        res = "kept" if kept else "dropped"
    ok = (res == "kept") if must == "keep" else (res == "dropped")
    if not ok:
        bad += 1
    print(f"{'ok  ' if ok else 'GAP '} {name:22} want={must:5} got={res:8} kept={kept!r}"[:200])
print("gaps", bad, "of", len(CASES))
