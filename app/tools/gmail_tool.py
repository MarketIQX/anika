"""Gmail I/O — read new messages, send approved replies, send notifications.

Why these three responsibilities in one module:
- They share the same OAuth token and service client.
- The reading side feeds the agents, the sending side closes the loop, and
  the notification side is just "send" with a different body — same pipe.

Scopes requested (principle of least privilege):
    gmail.readonly, gmail.modify, gmail.send, gmail.labels, gmail.compose

Failure modes:
- Token missing → raises RuntimeError; caller (dashboard or startup) must
  trigger the OAuth flow manually.
- Token expired → google-auth auto-refreshes; the fresh token is persisted
  to disk so the next process start picks it up.
- Gmail API 429/5xx → caller should retry with backoff.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.compose",
]


@dataclass
class InboxMessage:
    """Normalized view of a single Gmail message."""

    message_id: str
    thread_id: str
    from_email: str
    from_name: str
    to_email: str
    cc: str
    subject: str
    body_plain: str
    body_html: str
    snippet: str
    received_at: str  # ISO-8601 UTC
    is_reply_in_thread: bool


def _credentials_dict() -> dict[str, Any]:
    """Build the installed-app client_config dict from env vars.

    Why env-built config: we don't want the `client_secret.json` file in the
    repo; CLIENT_ID / CLIENT_SECRET live in `.env` only.
    """
    s = get_settings()
    return {
        "installed": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _load_credentials() -> Credentials:
    """Load stored OAuth credentials, refreshing if needed. No browser prompts here."""
    s = get_settings()
    if not s.token_path.exists():
        raise RuntimeError(
            f"Gmail token not found at {s.token_path}. Run `python -m app.tools.gmail_tool auth` "
            f"(or the OAuth link on the dashboard) to grant access."
        )
    creds = Credentials.from_authorized_user_file(str(s.token_path), GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials) -> None:
    get_settings().token_path.write_text(creds.to_json(), encoding="utf-8")


def authorize_interactive() -> Credentials:
    """Run the installed-app OAuth flow to mint fresh credentials.

    Opens a local browser window. Call this manually from the dashboard
    "Connect Gmail" button or from a one-time CLI invocation.
    """
    s = get_settings()
    if s.credentials_path.exists():
        # Prefer a full client_secret.json if present — matches Google's docs.
        flow = InstalledAppFlow.from_client_secrets_file(
            str(s.credentials_path), GMAIL_SCOPES
        )
    else:
        flow = InstalledAppFlow.from_client_config(_credentials_dict(), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    logger.info("Gmail OAuth token saved at %s", s.token_path)
    return creds


def has_credentials() -> bool:
    """Return True if a persisted OAuth token file exists."""
    return get_settings().token_path.exists()


def _build_service():
    creds = _load_credentials()
    # cache_discovery=False silences the "file_cache is only supported" warning.
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


# The label we apply once Anika has handled a message. Using a label instead
# of removing UNREAD means the inbox stays "fresh" for Prakash sir — he can
# read the notification himself and not fight Anika over read state.
PROCESSED_LABEL = "Anika/Processed"


def _default_query() -> str:
    """Build the Gmail search that picks up website-form notifications only.

    Targeted because:
      - The website mailer sends FROM prakasha@balakrishnaandco.com with
        Subject: "Balakrishna and Co" — so both filters together uniquely
        identify form submissions (normal sent mail has other subjects).
      - `-label:Anika/Processed` excludes messages Anika has already handled.
      - `is:unread` is kept as a belt-and-braces fallback if the label goes
        missing for any reason (manual deletion, migration).
      - `newer_than:7d` caps lookback; a missed 7-day-old enquiry isn't
        actionable anyway.
    """
    s = get_settings()
    # Two-clause query joined with OR:
    #   A) Website-form notifications (self-sent with fixed subject)
    #   B) Direct new enquiries TO prakasha@balakrishnaandco.com:
    #        - NOT a reply (Gmail operator: -"Re:" -"Fwd:" in subject)
    #        - NOT from known automation domains
    #        - NOT in promotions/updates/social/forums Gmail categories
    return (
        "("
        f'(from:{s.prakasha_email} subject:"Balakrishna and Co" '
        f'-subject:"Payment" -subject:"outstanding" -subject:"Invoice")'
        " OR "
        f'(to:{s.prakasha_email} '
        f'-from:{s.prakasha_email} '
        f'-subject:"Re:" -subject:"Fwd:" -subject:"FW:" '
        f'-subject:"Payment" -subject:"outstanding" -subject:"Invoice" '
        f'-subject:"Statement" -subject:"Intimation" -subject:"Refund" '
        f'-subject:"OTP" -subject:"Receipt" -subject:"Account" '
        f'-from:*@icicibank.com -from:*@zerodha.com '
        f'-from:*@taxmann.com -from:*@nse.co.in -from:*@bse.co.in '
        f'-from:*@google.com -from:*@googleworkspace.com '
        f'-from:*@incometax.gov.in -from:*@cpc.incometax.gov.in '
        f'-from:no-reply@* -from:noreply@* -from:donotreply@* '
        f'-from:*@dhruvaadvisors.com -from:*@investing.com '
        f'-category:promotions -category:updates '
        f'-category:social -category:forums)'
        ") "
        f'is:unread '
        f'-label:{PROCESSED_LABEL} '
        f'newer_than:7d'
    )


def list_recent_message_ids(
    query: str | None = None,
    max_results: int = 20,
) -> list[str]:
    """Return Gmail message IDs matching a query.

    Default query (`_default_query()`) targets only the website-form mailer
    and excludes anything Anika has already labelled.
    """
    svc = _build_service()
    q = query if query is not None else _default_query()
    try:
        resp = svc.users().messages().list(
            userId="me", q=q, maxResults=max_results
        ).execute()
    except HttpError as e:
        logger.error("Gmail list failed: %s", e)
        return []
    return [m["id"] for m in resp.get("messages", [])]


def fetch_message(message_id: str) -> InboxMessage:
    """Fetch a single message and normalize into InboxMessage.

    Raises:
        HttpError if Gmail API errors out.
    """
    svc = _build_service()
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    return _normalize_message(msg)


def _header(headers: list[dict], name: str) -> str:
    name_lc = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lc:
            return h.get("value", "")
    return ""


def _decode_body_part(part: dict) -> str:
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    raw = base64.urlsafe_b64decode(data.encode("ascii") + b"==")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _extract_bodies(payload: dict) -> tuple[str, str]:
    """Return (plain, html) — walks MIME parts recursively."""
    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            plain_chunks.append(_decode_body_part(part))
        elif mime == "text/html":
            html_chunks.append(_decode_body_part(part))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    plain = "\n".join(c for c in plain_chunks if c)
    html = "\n".join(c for c in html_chunks if c)

    # If we only got HTML (e.g., marketing emails), derive plain text for the LLM.
    if not plain and html:
        plain = BeautifulSoup(html, "lxml").get_text(separator="\n").strip()
    return plain, html


def _normalize_message(msg: dict) -> InboxMessage:
    payload = msg.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    from_raw = _header(headers, "From")
    from_name, from_email = parseaddr(from_raw)
    plain, html = _extract_bodies(payload)

    internal_ms = int(msg.get("internalDate", "0") or 0)
    # Gmail returns ms since epoch; convert to ISO-8601 UTC.
    from datetime import datetime, timezone
    received_at = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )

    labels = msg.get("labelIds", []) or []
    in_reply_to = _header(headers, "In-Reply-To")
    references = _header(headers, "References")
    is_reply = bool(in_reply_to or references)

    return InboxMessage(
        message_id=msg["id"],
        thread_id=msg["threadId"],
        from_email=from_email.lower(),
        from_name=from_name,
        to_email=parseaddr(_header(headers, "To"))[1].lower(),
        cc=_header(headers, "Cc"),
        subject=_header(headers, "Subject"),
        body_plain=plain.strip(),
        body_html=html.strip(),
        snippet=msg.get("snippet", ""),
        received_at=received_at,
        is_reply_in_thread=is_reply,
    )


# Cache the Gmail label-id for PROCESSED_LABEL so we don't hit labels.list
# on every poll cycle. Cleared when the process restarts.
_PROCESSED_LABEL_ID: str | None = None


def _labels_list(svc) -> list[dict[str, Any]]:
    return svc.users().labels().list(userId="me").execute().get("labels", []) or []


def get_or_create_label(name: str = PROCESSED_LABEL) -> str:
    """Return the Gmail label id for `name`, creating it if missing.

    Uses a module-level cache so the labels.list call happens at most once
    per process. Labels created here are nestable — "Anika/Processed" shows
    up as a sub-label under an "Anika" parent in Prakash sir's sidebar.
    """
    global _PROCESSED_LABEL_ID
    if _PROCESSED_LABEL_ID and name == PROCESSED_LABEL:
        return _PROCESSED_LABEL_ID

    svc = _build_service()
    # Gmail label name comparison is case-insensitive.
    name_lc = name.lower()
    for lbl in _labels_list(svc):
        if (lbl.get("name") or "").lower() == name_lc:
            lid = lbl["id"]
            if name == PROCESSED_LABEL:
                _PROCESSED_LABEL_ID = lid
            return lid

    # Not found — create it. labelListVisibility 'labelShow' keeps it in the
    # sidebar; messageListVisibility 'show' keeps the chip on message rows.
    created = svc.users().labels().create(
        userId="me",
        body={
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    lid = created["id"]
    if name == PROCESSED_LABEL:
        _PROCESSED_LABEL_ID = lid
    logger.info("Created Gmail label %r (id=%s)", name, lid)
    return lid


def mark_as_processed(message_id: str) -> None:
    """Apply the Anika/Processed label so we don't re-process this message.

    Why not remove UNREAD: read-state belongs to Prakash sir. If Anika were
    to mark things as read, his inbox would quietly empty itself and he'd
    lose the cue that an enquiry arrived.
    """
    svc = _build_service()
    try:
        label_id = get_or_create_label()
    except HttpError as e:
        logger.warning("Failed to resolve %s label: %s", PROCESSED_LABEL, e)
        return
    try:
        svc.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
            # NOTE: we deliberately do NOT pass removeLabelIds — UNREAD stays.
        ).execute()
    except HttpError as e:
        logger.warning("Failed to label %s as processed: %s", message_id, e)


# Backwards-compatible alias. Existing callers and tests that still refer
# to `mark_as_read` will now apply the label instead — which is the correct
# behaviour.  When all callers have migrated, drop this.
def mark_as_read(message_id: str) -> None:
    """Deprecated — apply the Anika/Processed label (UNREAD is preserved)."""
    mark_as_processed(message_id)


# --------------------------------------------------------------------------
# Sending
# --------------------------------------------------------------------------


def _build_mime(to_email: str, subject: str, body: str, thread_headers: dict[str, str] | None = None) -> str:
    """Return a base64url-encoded MIME message ready for Gmail API."""
    mime = MIMEMultipart("alternative")
    mime["To"] = to_email
    mime["From"] = get_settings().prakasha_email
    mime["Subject"] = subject
    if thread_headers:
        for k, v in thread_headers.items():
            if v:
                mime[k] = v
    mime.attach(MIMEText(body, "plain", "utf-8"))
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
    return raw


def send_email(
    to_email: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict[str, str]:
    """Send a plain-text email from prakasha@balakrishnaandco.com.

    Args:
        to_email: recipient.
        subject: message subject.
        body: plain-text body (signature already appended by Drafter).
        thread_id: Gmail threadId to keep the reply threaded.
        in_reply_to, references: RFC-5322 headers for proper threading.

    Returns:
        dict with keys `id` (Gmail message id) and `threadId`.
    Raises:
        HttpError on API failure — caller should retry or escalate.
    """
    svc = _build_service()
    headers = {"In-Reply-To": in_reply_to or "", "References": references or ""}
    raw = _build_mime(to_email, subject, body, headers)
    body_obj: dict[str, Any] = {"raw": raw}
    if thread_id:
        body_obj["threadId"] = thread_id
    resp = svc.users().messages().send(userId="me", body=body_obj).execute()
    return {"id": resp.get("id", ""), "threadId": resp.get("threadId", "")}


# --------------------------------------------------------------------------
# CLI entrypoint for one-time OAuth
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "auth":
        authorize_interactive()
        print("Gmail OAuth complete — token saved.")
    else:
        print("Usage: python -m app.tools.gmail_tool auth")
