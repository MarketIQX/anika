from pathlib import Path

p = Path("app/agents/drafter.py")
code = p.read_text(encoding="utf-8")

# Update the single caller — unpack 3 values instead of 2, pass coverage to orchestrator
OLD = '''    service_line = enrichment.likely_service_line
    prompt, used_ids = assemble_prompt(service_line=service_line, enquiry_body=body_plain)'''

NEW = '''    service_line = enrichment.likely_service_line
    prompt, used_ids, coverage = assemble_prompt(service_line=service_line, enquiry_body=body_plain)'''

if OLD in code:
    code = code.replace(OLD, NEW)
    print("Updated caller to unpack 3 values")
else:
    print("OLD not found — searching context:")
    idx = code.find("prompt, used_ids = assemble_prompt")
    if idx >= 0:
        print(code[max(0,idx-100):idx+200])

# Also — we need to persist cognitive_state on the draft row after it's created.
# Find the draft INSERT in drafter.py and add cognitive_state + voice_coverage_count
# Look for the INSERT INTO drafts statement
import re
insert_match = re.search(r'execute\(\s*["\']INSERT INTO drafts.*?\)', code, re.DOTALL)
if insert_match:
    print()
    print("Found INSERT INTO drafts:")
    print(insert_match.group()[:400])

# Look for where the draft_id is obtained after insert — that's where we attach cognitive state
# Find _save_draft or similar
m = re.search(r"def _save_draft.*?(?=\ndef |\nasync def )", code, re.DOTALL)
if m:
    print()
    print("_save_draft function (first 1500 chars):")
    print(m.group()[:1500])

# Write
p.write_text(code, encoding="utf-8")

# Import check
import sys
for mod in list(sys.modules):
    if "drafter" in mod or "app.agents" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.agents import drafter
print()
print("drafter imports cleanly")
