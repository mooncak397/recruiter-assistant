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
