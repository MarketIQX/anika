from app.db import fetch_one, execute

d = fetch_one("SELECT body FROM drafts WHERE id = 25")
body = d['body']

# Find "Warm regards," — this is the start of the STALE signature
cut_at = body.find("\nWarm regards,")
if cut_at < 0:
    print("'Warm regards,' marker not found — no change needed")
else:
    # Keep everything before "Warm regards,"
    # Then the canonical signature appended by ensure_signature
    clean_body = body[:cut_at].rstrip()

    # Now re-apply the canonical signature
    from app.config.firm_identity import SIGNATURE_BLOCK
    final_body = f"{clean_body}\n\n{SIGNATURE_BLOCK}"

    execute("UPDATE drafts SET body = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 25", (final_body,))
    print("Fixed Draft 25 — removed stale signature, kept canonical")
    print()
    print("NEW BODY (last 400 chars):")
    print("-" * 70)
    d2 = fetch_one("SELECT body FROM drafts WHERE id = 25")
    print(d2['body'][-400:])
    print("-" * 70)

    # Verify signature count
    body_new = d2['body']
    for marker in ["Warm regards,", "Yours faithfully,", "Best regards,"]:
        count = body_new.count(marker)
        if count > 0:
            print(f"  '{marker}' appears {count} time(s)")
