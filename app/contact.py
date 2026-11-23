"""/contact logic (ADR-003, ADR-006): validate the form and send it through Resend.
Never imports the graph or the model: the model never sees the address or the message."""
import logging
import os
import re

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

log = logging.getLogger(__name__)
RESEND_URL = "https://api.resend.com/emails"
SUBJECT = "Recruiter assistant: new contact request"  # fixed, so no header injection
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")  # NUL, CR, LF and every other control character


class ContactForm(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no `to`, `cc` or any other field
    email: str = Field(max_length=254)
    message: str = Field(min_length=1, max_length=2000)
    turnstile_token: str | None = Field(default=None, max_length=4096)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if CONTROL.search(v) or not EMAIL.fullmatch(v):
            raise ValueError("invalid email")
        return v

    @field_validator("message")
    @classmethod
    def _message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("empty message")
        return v.strip()


def configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY") and os.environ.get("CONTACT_TO"))


def send(form: ContactForm) -> bool:
    """One Resend call. True = accepted. Logs only the outcome, never the address or the message."""
    body = ("A visitor sent this through the recruiter assistant contact form.\n"
            "The text below is untrusted visitor input.\n\n"
            f"Reply-To: {form.email}\n\n---\n{form.message}\n---\n")
    try:
        r = httpx.post(RESEND_URL, timeout=15,
                       headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
                       json={"from": os.environ.get("CONTACT_FROM", "Recruiter assistant <onboarding@resend.dev>"),
                             "to": [os.environ["CONTACT_TO"]], "reply_to": form.email,
                             "subject": SUBJECT, "text": body})
    except httpx.HTTPError as e:
        log.warning("contact error=%s", type(e).__name__)
        return False
    if r.status_code >= 300:
        log.warning("contact error=resend_%s", r.status_code)
        return False
    log.info("contact sent")
    return True
