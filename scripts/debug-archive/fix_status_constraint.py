from pathlib import Path

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Change status='awaiting_confirmation' to status='processing' in 2 places
# (inside _classify_and_persist and /train/teach/confirm)

replacements = [
    ('"awaiting_confirmation",\n                qid,', '"processing",\n                qid,'),
]

changes = 0
for old, new in replacements:
    if old in code:
        code = code.replace(old, new)
        changes += 1
        print(f"Replaced pattern: {old[:50]}...")

# Also fix the /train/teach/confirm route status update
old_confirm = '''execute(
        """UPDATE teaching_queue SET
              awaiting_confirmation = 0,
              status = ?
           WHERE id = ?""",
        ("confirmed", queue_id),
    )'''

new_confirm = '''execute(
        """UPDATE teaching_queue SET
              awaiting_confirmation = 0,
              status = ?
           WHERE id = ?""",
        ("approved", queue_id),
    )'''

if old_confirm in code:
    code = code.replace(old_confirm, new_confirm)
    changes += 1
    print("Fixed /train/teach/confirm status update")

p.write_text(code, encoding="utf-8")
print(f"\nTotal replacements: {changes}")

# Verify
count_aw = code.count("'awaiting_confirmation'") + code.count('"awaiting_confirmation"')
# The only remaining references should be in SQL queries filtering by awaiting_confirmation column
print(f'References to the STRING "awaiting_confirmation" in code (status values): {count_aw}')
print("(These should all be column-name usages, not status values)")

# Show lines with "awaiting_confirmation" string for sanity check
print("\nRemaining lines with 'awaiting_confirmation' string:")
for i, line in enumerate(code.splitlines(), 1):
    if "awaiting_confirmation" in line:
        print(f"  L{i}: {line.strip()[:100]}")
