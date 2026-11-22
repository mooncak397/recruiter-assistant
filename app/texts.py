"""Fixed texts the code picks by language, so the model never writes them (ADR-007).
Swiss German: "Sie", never "ß"."""

OFF_TOPIC = {
    "en": "I can only answer questions about Christopher's professional background. "
          "Please ask about his CV, or use the contact form to reach him.",
    "de": "Ich kann nur Fragen zum beruflichen Hintergrund von Christopher beantworten. "
          "Fragen Sie mich gern zu seinem Lebenslauf, oder nutzen Sie das Kontaktformular.",
}

FORM_INTRO = {
    "en": "Happy to help. Please use the contact form below to send Christopher a message.",
    "de": "Gern. Bitte nutzen Sie das Kontaktformular unten, um Christopher eine Nachricht zu senden.",
}

# ADR-010: code-chosen texts for the entry, error and scrub paths. ASCII only.
EMPTY = {
    "en": "Please type a question about Christopher's professional background.",
    "de": "Bitte schreiben Sie eine Frage zum beruflichen Hintergrund von Christopher.",
}

TOO_LONG = {
    "en": "Your message is too long. Please keep it under 1,000 characters.",
    "de": "Ihre Nachricht ist zu lang. Bitte schreiben Sie weniger als 1000 Zeichen.",
}

BUSY = {
    "en": "The assistant is busy right now. Please try again in a minute, or use the contact form.",
    "de": "Der Assistent ist gerade ausgelastet. Bitte versuchen Sie es in einer Minute noch einmal, "
          "oder nutzen Sie das Kontaktformular.",
}

SESSION_LIMIT = {
    "en": "This chat has reached its limit. Please reload the page to start a new chat, or use the contact form.",
    "de": "Dieser Chat hat sein Limit erreicht. Bitte laden Sie die Seite neu, oder nutzen Sie das Kontaktformular.",
}

ADDR_REMOVED = {"en": "(address removed)", "de": "(Adresse entfernt)"}

LINK_REMOVED = {"en": "(link removed)", "de": "(Link entfernt)"}
