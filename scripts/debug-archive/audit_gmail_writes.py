from pathlib import Path
import re

p = Path("app/agents/orchestrator.py")
code = p.read_text(encoding="utf-8")

# Look for all Gmail mutations
print("=" * 80)
print("Gmail mutations in orchestrator.py")
print("=" * 80)

patterns = [
    r"mark_as_read",
    r"add_label",
    r"remove_label",
    r"modify",
    r"gmail_tool\.",
    r"\.users\(\)\.messages\(\)",
]

for pat in patterns:
    for m in re.finditer(pat, code):
        start = max(0, m.start() - 100)
        end = min(len(code), m.end() + 200)
        print(f"--- '{pat}' at position {m.start()} ---")
        print(code[start:end])
        print()

# Also check poll_gmail.py
print("=" * 80)
print("Gmail mutations in poll_gmail.py")
print("=" * 80)
p2 = Path("app/jobs/poll_gmail.py")
code2 = p2.read_text(encoding="utf-8")
for pat in patterns:
    for m in re.finditer(pat, code2):
        start = max(0, m.start() - 100)
        end = min(len(code2), m.end() + 200)
        print(f"--- '{pat}' at position {m.start()} ---")
        print(code2[start:end])
        print()

# Also check gmail_tool.py for the modification functions
print("=" * 80)
print("Gmail tool — what functions modify Gmail state?")
print("=" * 80)
p3 = Path("app/tools/gmail_tool.py")
if p3.exists():
    code3 = p3.read_text(encoding="utf-8")
    for m in re.finditer(r"def (\w+)\(", code3):
        fn = m.group(1)
        if any(x in fn.lower() for x in ["mark", "label", "modify", "add", "remove"]):
            print(f"  Function: {fn}")
