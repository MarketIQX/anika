from pathlib import Path
import re
import os

# Find the notification logic — where does Anika tell Prakash sir a draft is ready?
print("=" * 80)
print("Searching for notification email logic")
print("=" * 80)

# Common patterns for sending notification
patterns = ["notify", "notification", "send_email", "send_notification", "notification_template"]

for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        for pat in patterns:
            if pat in content.lower():
                # Find the function that does this
                for m in re.finditer(rf"(async )?def\s+(\w*{pat}\w*)\s*\(", content, re.IGNORECASE):
                    print(f"  {fp}: {m.group()}")

print()
print("=" * 80)
print("Searching for orchestrator's 'notification sent' message")
print("=" * 80)
# We saw "new_enquiry drafted and notification sent" in the log earlier
# That's the orchestrator log. Find what fires the notification.
orch = Path("app/agents/orchestrator.py").read_text(encoding="utf-8")
m = re.search(r"notification sent.*", orch, re.IGNORECASE)
if m:
    # Show 30 lines around it
    idx = m.start()
    start = max(0, idx - 1500)
    print(orch[start:idx+200])

print()
print("=" * 80)
print("Templates folder — any notification email templates?")
print("=" * 80)
for f in os.listdir("app/dashboard/templates"):
    if "notif" in f.lower() or "email" in f.lower() or "alert" in f.lower():
        print(f"  Found: {f}")
