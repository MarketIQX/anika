from pathlib import Path
import re

print("=" * 80)
print("AUDIT: Does Anika inform Prakash sir when she lacks knowledge?")
print("=" * 80)

# 1. Humility Layer — exists, but where does it fire?
print()
print("1. HUMILITY LAYER — where it fires today")
print("-" * 80)

routes = Path("app/dashboard/routes.py").read_text(encoding="utf-8")
if "humility_layer.articulate_uncertainty" in routes:
    # Find the context
    idx = routes.find("humility_layer.articulate_uncertainty")
    print("Found humility_layer call. Context (100 chars before + 200 after):")
    print(routes[max(0,idx-100):idx+300])
    print()

# Check drafter.py — does it have any uncertainty signaling?
drafter = Path("app/agents/drafter.py").read_text(encoding="utf-8")
print("2. DRAFTER — does it signal low-confidence drafts?")
print("-" * 80)
has_uncertainty = "uncertainty" in drafter.lower() or "confidence" in drafter.lower()
has_humility = "humility" in drafter.lower()
has_flag_for_user = "needs_training" in drafter.lower() or "insufficient_data" in drafter.lower() or "cold_start" in drafter.lower()
print(f"  'uncertainty' or 'confidence' in drafter.py: {has_uncertainty}")
print(f"  'humility' in drafter.py:                    {has_humility}")
print(f"  Flags for needs-training / cold-start:      {has_flag_for_user}")

# Check drafter output schema
print()
m = re.search(r"class\s+DrafterOutput.*?(?=\n\nclass|\n\ndef|\Z)", drafter, re.DOTALL)
if m:
    print("DrafterOutput schema:")
    print(m.group()[:1000])

# 3. When Drafter has no voice_example for a service line — what does it do?
print()
print("3. DRAFTER behavior when library has NO voice_example for service_line")
print("-" * 80)

# Find the prompt assembly logic
assembly_match = re.search(r"def assemble.*?(?=\ndef )", drafter, re.DOTALL)
if assembly_match:
    print("Prompt assembly function (first 1500 chars):")
    print(assembly_match.group()[:1500])

# 4. Does Drafter's output or reasoning bubble up to user?
print()
print("4. Does the UI surface 'Anika needs training' flag?")
print("-" * 80)
drafts_tmpl = Path("app/dashboard/templates/drafts.html")
if drafts_tmpl.exists():
    content = drafts_tmpl.read_text(encoding="utf-8")
    has_flag_display = "training" in content.lower() or "uncertain" in content.lower() or "confidence" in content.lower()
    print(f"  drafts.html has training/uncertainty display: {has_flag_display}")

# Look at draft_detail.html too
detail_tmpl = Path("app/dashboard/templates/draft_detail.html")
if detail_tmpl.exists():
    content = detail_tmpl.read_text(encoding="utf-8")
    has_flag_display = "training" in content.lower() or "uncertain" in content.lower() or "confidence" in content.lower()
    print(f"  draft_detail.html has training/uncertainty display: {has_flag_display}")

# 5. Current state — what service lines have voice_examples?
print()
print("5. CURRENT VOICE COVERAGE by service line")
print("-" * 80)
from app.db import fetch_all
voice_coverage = fetch_all("""
    SELECT COALESCE(service_line, '_universal') sl, COUNT(*) n
      FROM knowledge_library
     WHERE is_active = 1 AND purpose = 'voice_example'
     GROUP BY service_line
""")
for r in voice_coverage:
    print(f"  {r['sl']:25s} | {r['n']} voice_examples")

# Service lines that have had drafts BUT have no voice_example
print()
print("  Service lines that have generated drafts but have NO voice_examples:")
naked = fetch_all("""
    SELECT DISTINCT e.likely_service_line, COUNT(d.id) draft_count
      FROM drafts d
      JOIN enrichments e ON e.email_id = d.email_id
     WHERE e.likely_service_line IS NOT NULL
       AND e.likely_service_line NOT IN (
           SELECT DISTINCT service_line FROM knowledge_library
            WHERE is_active=1 AND purpose='voice_example' AND service_line IS NOT NULL
       )
     GROUP BY e.likely_service_line
""")
for r in naked:
    print(f"    {r['likely_service_line']:25s} | {r['draft_count']} drafts generated without learned voice")
