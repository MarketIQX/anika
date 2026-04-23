"""Parser for Balakrishna & Co website-form notifications.

The firm's website form submits enquiries through a mailer that emails the
submission TO prakasha@balakrishnaandco.com with Subject: "Balakrishna and Co".
The From header is also prakasha@balakrishnaandco.com (the website sends
on behalf of the domain), and the body is an HTML mailer containing the
actual enquirer's details:

    <div id="mailsub" class="notification">
        ...
        Congratulation! You receive <TOPIC> from <email>. Details here:
        Name: <name>
        Phone Number: <phone>
        Email: <email>
        IP Address: <ip>
        Message: <the actual message>
    </div>

Without parsing, the orchestrator would "reply" to Prakash sir's own address
(because that's the From), and the classifier would see a useless HTML blob.
This module pulls out the real enquirer so Anika can work with clean inputs.

Detection is deliberately generous (any of the marker patterns match) because
the mailer occasionally reshuffles the layout.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class WebFormEnquiry:
    """Clean view of a website-form submission."""

    sender_email: str
    sender_name: str
    phone: str
    ip_address: str
    message: str


# Markers — any of these hitting means "probably a web form".
_HTML_ANCHOR = re.compile(r'id\s*=\s*["\']mailsub["\']', re.IGNORECASE)
_PLAIN_ANCHOR_1 = re.compile(r"You receive", re.IGNORECASE)
_PLAIN_ANCHOR_2 = re.compile(r"Details here\s*:", re.IGNORECASE)


def is_web_form(body_plain: str | None, body_html: str | None) -> bool:
    """Return True if the email looks like a website-form notification."""
    plain = body_plain or ""
    html = body_html or ""
    if html and _HTML_ANCHOR.search(html):
        return True
    if plain and _PLAIN_ANCHOR_1.search(plain) and _PLAIN_ANCHOR_2.search(plain):
        return True
    # The plain-text rendering of the HTML mailer usually contains the
    # markers too — check the already-derived plain as well for html forms
    # that got flattened upstream.
    if html and _PLAIN_ANCHOR_1.search(html) and _PLAIN_ANCHOR_2.search(html):
        return True
    return False


# Patterns we look for, in order of preference for the "enquirer identity".
# Accept loose whitespace and a few common label variants the mailer has used.
_LABEL_PATTERNS: dict[str, re.Pattern[str]] = {
    "sender_name":  re.compile(r"^\s*Name\s*:\s*(.+?)\s*$",          re.IGNORECASE | re.MULTILINE),
    "sender_email": re.compile(r"^\s*Email\s*:\s*(\S+@\S+?)\s*$",     re.IGNORECASE | re.MULTILINE),
    "phone":        re.compile(r"^\s*Phone(?:\s*Number)?\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
    "ip_address":   re.compile(r"^\s*IP(?:\s*Address)?\s*:\s*(\S+?)\s*$", re.IGNORECASE | re.MULTILINE),
    "message":      re.compile(r"^\s*Message\s*:\s*([\s\S]+?)\s*$",   re.IGNORECASE | re.MULTILINE),
}

# Fallback email extractor for the "... from <email>. Details here:" opener.
_FROM_OPENER = re.compile(
    r"from\s+([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", re.IGNORECASE
)

_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)


def _html_to_plain(html: str) -> str:
    """Flatten HTML to line-oriented plain text for regex scanning.

    We split on <br>, <tr>, and block-level tags so the mailer's table-based
    layout becomes one field per line.
    """
    soup = BeautifulSoup(html, "lxml")
    # Drop style/script.
    for tag in soup(["style", "script"]):
        tag.decompose()
    # Force a newline at each row/cell/paragraph/break so "Name: X" and
    # "Email: Y" don't collapse onto one line.
    for br in soup.find_all(["br"]):
        br.replace_with("\n")
    for block in soup.find_all(["tr", "p", "div", "li", "td"]):
        block.append("\n")
    return soup.get_text(separator=" ", strip=False)


def _extract_message(text: str) -> str:
    """Pull the Message: field — may span multiple lines."""
    # Look for "Message:" and take everything up to the end-of-block or the
    # next known label. The mailer doesn't include labels AFTER Message,
    # so eof/end-of-text is the normal terminator.
    m = re.search(
        r"Message\s*:\s*([\s\S]+?)(?=\n\s*(?:Name|Phone|Email|IP|Subject|Topic)\s*:|\Z)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return ""
    body = m.group(1).strip()
    # Collapse runs of whitespace the HTML flattening left behind.
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n\s*", "\n\n", body)
    return body.strip()


def _first(pattern: re.Pattern[str], text: str) -> str:
    m = pattern.search(text)
    return (m.group(1) or "").strip() if m else ""


def parse(body_plain: str | None, body_html: str | None) -> WebFormEnquiry | None:
    """Return a WebFormEnquiry if this email is a web-form notification, else None.

    Tries the plain body first, then falls back to HTML-derived plain text.
    """
    if not is_web_form(body_plain, body_html):
        return None

    # Build the text we'll regex over. Prefer a plain representation —
    # the HTML mailer's plain-text counterpart (Gmail auto-generates one)
    # is usually tidy enough on its own. If not, flatten the HTML.
    sources: list[str] = []
    if body_plain:
        sources.append(body_plain)
    if body_html:
        sources.append(_html_to_plain(body_html))
    text = "\n".join(s for s in sources if s)

    sender_name = _first(_LABEL_PATTERNS["sender_name"], text)
    sender_email = _first(_LABEL_PATTERNS["sender_email"], text)
    phone = _first(_LABEL_PATTERNS["phone"], text)
    ip_address = _first(_LABEL_PATTERNS["ip_address"], text)
    message = _extract_message(text)

    # Fallbacks — email from the "from <email>" opener line, name from the
    # email's local-part when Name isn't present in the form.
    if not sender_email:
        opener = _FROM_OPENER.search(text)
        if opener:
            sender_email = opener.group(1)
    if not sender_email:
        # Last-ditch: any email-shaped token in the text.
        generic = _EMAIL_RE.search(text)
        if generic:
            sender_email = generic.group(0)
    if not sender_email:
        # If we can't find an email at all, we can't meaningfully reply.
        # Treat as not-a-web-form so the orchestrator falls through to its
        # default behaviour (which will likely classify it as automated).
        return None

    if not sender_name:
        local = sender_email.split("@", 1)[0]
        # Prettify "first.last" -> "First Last"; leave "chandrika" alone.
        sender_name = local.replace(".", " ").replace("_", " ").strip().title() or local

    return WebFormEnquiry(
        sender_email=sender_email.lower(),
        sender_name=sender_name,
        phone=phone,
        ip_address=ip_address,
        message=message,
    )
