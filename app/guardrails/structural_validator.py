"""Structural validator — Apple-style hard filter."""
from __future__ import annotations
import re


AUTOMATION_DOMAINS = {
    "icicibank.com", "hdfcbank.net", "axisbank.com", "sbi.co.in",
    "zerodha.com", "zerodha.net",
    "taxmann.com", "icai.org",
    "nse.co.in", "bse.co.in", "nseindia.com", "bseindia.com",
    "google.com", "googleworkspace.com", "accounts.google.com",
    "incometax.gov.in", "cpc.incometax.gov.in", "nic.in",
    "investing.com", "dhruvaadvisors.com",
    "mca.gov.in", "gst.gov.in",
    "eazypay.icicibank.com",
}


AUTOMATION_LOCAL_PARTS = {
    "no-reply", "noreply", "donotreply", "do-not-reply",
    "notifications", "notification", "alerts", "alert",
    "support", "system", "automated", "mailer-daemon",
    "postmaster", "bounce",
}


NEGATIVE_SUBJECT_PATTERNS = [
    r"^re:\s", r"^fwd:\s", r"^fw:\s",
    r"payment", r"outstanding", r"invoice", r"statement",
    r"intimation", r"refund", r"otp", r"receipt",
    r"delivered", r"dispatched", r"tracking",
    r"unsubscribe", r"newsletter", r"digest",
    r"salary", r"payslip", r"tds",
    r"contract note", r"margin",
]


NEGATIVE_BODY_PATTERNS = [
    r"this is an automated",
    r"do not reply to this",
    r"unsubscribe",
    r"list-unsubscribe",
    r"you are receiving this because",
    r"click here to unsubscribe",
]


def _sender_domain(email):
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].lower().strip()


def _sender_local(email):
    if not email or "@" not in email:
        return ""
    return email.split("@", 1)[0].lower().strip()


def _has_thread_headers(raw_headers):
    if not raw_headers:
        return False
    return bool(raw_headers.get("In-Reply-To") or raw_headers.get("References"))


def _is_mailing_list(raw_headers):
    if not raw_headers:
        return False
    for key in ("List-Unsubscribe", "List-Id", "Precedence"):
        if raw_headers.get(key):
            return True
    return False


def validate(*, from_email, subject, body_plain, raw_headers=None, is_web_form=False):
    if is_web_form:
        return True, "website_form"
    if _has_thread_headers(raw_headers):
        return False, "is_reply_thread"
    if _is_mailing_list(raw_headers):
        return False, "mailing_list"
    domain = _sender_domain(from_email)
    if domain in AUTOMATION_DOMAINS:
        return False, f"automation_domain:{domain}"
    local = _sender_local(from_email)
    if local in AUTOMATION_LOCAL_PARTS:
        return False, f"automated_local:{local}"
    subj_lc = (subject or "").lower()
    for pat in NEGATIVE_SUBJECT_PATTERNS:
        if re.search(pat, subj_lc):
            return False, f"negative_subject:{pat}"
    body_lc = (body_plain or "").lower()
    for pat in NEGATIVE_BODY_PATTERNS:
        if re.search(pat, body_lc):
            return False, f"negative_body:{pat}"
    if len((body_plain or "").strip()) < 40:
        return False, "body_too_short"
    return True, "ok"
