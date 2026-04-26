from pathlib import Path
p = Path("app/agents/orchestrator.py")
code = p.read_text(encoding="utf-8")

# Add import near the existing guardrails import
OLD_IMP = "from app.guardrails import drafting_paused, kill_switch, topic_blacklist, vip_filter"
NEW_IMP = "from app.guardrails import drafting_paused, kill_switch, structural_validator, topic_blacklist, vip_filter"

if OLD_IMP not in code:
    print("IMPORT PATTERN NOT FOUND — searching for alternatives:")
    for line in code.splitlines():
        if "from app.guardrails" in line:
            print(f"  {line}")
    raise SystemExit(1)

code = code.replace(OLD_IMP, NEW_IMP)
print("Added import for structural_validator")

# Now find the classifier call and insert the validator check BEFORE it runs.
# Look for the classifier invocation.
import re
cls_match = re.search(r"(\n\s+# Classifier.*?classifier\.classify)", code, re.DOTALL)
if cls_match:
    print("Found classifier block around position", cls_match.start())
    print("Context:")
    print(code[max(0,cls_match.start()-200):cls_match.end()+200])

Path("app/agents/orchestrator.py").write_text(code, encoding="utf-8")
print("Import written. Now showing where to insert the validator gate.")
