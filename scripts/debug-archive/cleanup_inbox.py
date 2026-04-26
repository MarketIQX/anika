from app.db import execute, fetch_all

pattern = "subject LIKE '%Payment%' OR subject LIKE '%outstanding%' OR subject LIKE '%Invoice%'"

# Find the target email IDs first
ids_rows = fetch_all("SELECT id FROM raw_emails WHERE " + pattern)
target_ids = [r["id"] for r in ids_rows]
print("Target email IDs to remove:", len(target_ids))

if target_ids:
    id_list = "(" + ",".join(str(i) for i in target_ids) + ")"

    # Discover all tables that reference raw_emails
    fks = fetch_all("SELECT name FROM sqlite_master WHERE type='\''table'\''")
    print("Checking all tables for email_id references...")

    # Delete from common child tables (ignore errors if table doesnt exist or no match)
    child_tables = ["classifications", "enrichments", "drafts", "reasoning_log", "approvals", "sent_log", "memory", "access_log"]
    for t in child_tables:
        try:
            cur = execute("DELETE FROM " + t + " WHERE email_id IN " + id_list)
            print("  Deleted from", t)
        except Exception as e:
            print("  Skipped", t, ":", str(e)[:80])

    # Now delete from raw_emails
    execute("DELETE FROM raw_emails WHERE id IN " + id_list)
    print("Deleted from raw_emails")

# Show results
rem = fetch_all("SELECT COUNT(*) n FROM raw_emails")
print()
print("Remaining raw_emails:", rem[0]["n"])
print("Last 5 remaining:")
for r in fetch_all("SELECT id, subject FROM raw_emails ORDER BY id DESC LIMIT 5"):
    print(" ", r["id"], (r["subject"] or "")[:60])
