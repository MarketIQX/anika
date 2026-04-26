from pathlib import Path
import re

p = Path("app/agents/humility_layer.py")
code = p.read_text(encoding="utf-8")

# 1. Add Literal import if missing
if "from typing import Literal" not in code:
    code = code.replace(
        "from agents import Agent, Runner",
        "from typing import Literal\n\nfrom agents import Agent, Runner",
    )
    print("Added Literal import")
else:
    print("Literal import already present")

# 2. Use regex to find and replace the str annotation (handles any whitespace variation)
pattern = re.compile(
    r'(    best_guess_purpose:\s*)str(\s*=\s*Field\(\s*\n\s*description=)"[^"]*"(\s*\n\s*\))',
    re.MULTILINE
)

new_block = (
    r'\1Literal[\n'
    r'        "voice_example", "classifier_example", "document_type",\n'
    r'        "question_template", "workflow_rule", "firm_fact",\n'
    r'        "firm_policy", "reference_material",\n'
    r'    ]\2"Her best guess among the 8 purposes. MUST be one of the 8 literals. If content needs a new category, pick the closest literal and set suggested_custom_label."\3'
)

new_code, n = pattern.subn(new_block, code)
if n == 0:
    print("Regex did not match. Dumping current annotation:")
    i = code.find("best_guess_purpose")
    print(code[i:i+300])
else:
    p.write_text(new_code, encoding="utf-8")
    print(f"Replaced {n} occurrence(s).")

# 3. Verify
print()
print("=== Verification ===")
check = p.read_text(encoding="utf-8")
for i, line in enumerate(check.splitlines(), 1):
    if "best_guess_purpose" in line and i < 50:
        print(f"L{i}: {line}")

# 4. Import test
import sys
for mod_name in list(sys.modules):
    if "humility_layer" in mod_name:
        del sys.modules[mod_name]
sys.path.insert(0, ".")
from app.agents import humility_layer
print()
ann = humility_layer.UnknownArticulation.model_fields["best_guess_purpose"].annotation
print(f"Annotation: {ann}")
