from pathlib import Path
p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

OLD = """        SELECT r.id, r.from_email, r.from_name, r.subject, r.received_at,
               c.category, c.confidence,
               d.id AS draft_id, d.sent_status
          FROM raw_emails r
          LEFT JOIN classifications c ON c.email_id = r.id
          LEFT JOIN drafts d ON d.email_id = r.id
         WHERE COALESCE(r.subject,'') NOT LIKE '%Payment%'
           AND COALESCE(r.subject,'') NOT LIKE '%outstanding%'
           AND COALESCE(r.subject,'') NOT LIKE '%Invoice%'
         ORDER BY r.received_at DESC
         LIMIT 50"""

NEW = """        SELECT r.id, r.from_email, r.from_name, r.subject, r.received_at,
               c.category, c.confidence,
               d.id AS draft_id, d.sent_status,
               r.is_web_form
          FROM raw_emails r
          LEFT JOIN classifications c ON c.email_id = r.id
          LEFT JOIN drafts d ON d.email_id = r.id
         WHERE (c.category = 'new_enquiry' OR r.is_web_form = 1)
           AND COALESCE(r.subject,'') NOT LIKE '%Payment%'
           AND COALESCE(r.subject,'') NOT LIKE '%outstanding%'
           AND COALESCE(r.subject,'') NOT LIKE '%Invoice%'
         ORDER BY r.received_at DESC
         LIMIT 50"""

if OLD not in code:
    print("PATTERN NOT FOUND")
else:
    p.write_text(code.replace(OLD, NEW), encoding="utf-8")
    print("Inbox view now shows ONLY new enquiries + website forms.")
