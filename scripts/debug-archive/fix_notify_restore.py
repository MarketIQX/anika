from pathlib import Path

p = Path("app/tools/notify_tool.py")
code = p.read_text(encoding="utf-8")

# Fix 1 — variable name: 'subj' -> 'subject' inside notify_draft_ready
OLD_BAD_TRY = '''    try:
        gmail_tool.send_email(get_settings().notify_email, subj, body)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to send sensitive-bypass notification: %s", e)
        return False'''

NEW_GOOD_TRY = '''    try:
        gmail_tool.send_email(get_settings().notify_email, subject, body)
        logger.info("Notification sent for draft %s", draft_id)
        return True
    except Exception as e:  # noqa: BLE001 — we want all failures logged, never raised to caller
        logger.error("Failed to send notification for draft %s: %s", draft_id, e)
        return False


def notify_sensitive_bypass(
    email_id: int,
    from_email: str,
    subject: str,
    reason: str,
) -> bool:
    """Alert Prakash sir when Anika has bypassed an enquiry as 'sensitive'.

    No draft is created; this is a priority flag for manual handling.
    """
    base = get_settings().anika_public_base_url.rstrip("/")
    url = f"{base}/inbox/{email_id}"
    subj = f"Anika: sensitive enquiry — please handle directly"
    body = (
        f"Sir, Anika detected a sensitive enquiry and did not draft a reply.\\n\\n"
        f"From:    {from_email}\\n"
        f"Subject: {subject}\\n"
        f"Reason:  {reason}\\n\\n"
        f"Open in Anika: {url}\\n\\n"
        f"— Anika"
    )
    try:
        gmail_tool.send_email(get_settings().notify_email, subj, body)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to send sensitive-bypass notification: %s", e)
        return False'''

if OLD_BAD_TRY in code:
    code = code.replace(OLD_BAD_TRY, NEW_GOOD_TRY)
    p.write_text(code, encoding="utf-8")
    print("Fixed: variable name + restored notify_sensitive_bypass function")
else:
    print("OLD_BAD_TRY not found — current state may differ")

# Verify both functions exist
import sys
for mod in list(sys.modules):
    if "notify_tool" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.tools import notify_tool

print()
print("Verification:")
print(f"  notify_draft_ready exists:        {hasattr(notify_tool, 'notify_draft_ready')}")
print(f"  notify_sensitive_bypass exists:   {hasattr(notify_tool, 'notify_sensitive_bypass')}")

# Count def lines
fn_count = code.count("\ndef ") + (1 if code.startswith("def ") else 0)
print(f"  Total 'def ' in file:             {fn_count}")
print(f"  Final file size:                  {len(code)} chars")
