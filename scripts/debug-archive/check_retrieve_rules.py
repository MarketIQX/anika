from pathlib import Path
import re

code = Path("app/cognitive/library.py").read_text(encoding="utf-8")

# Find the retrieve_rules no-service-line block to see its actual indentation
m = re.search(r"else:\s*rows = fetch_all\(\s*\"\"\"(.*?)\"\"\"", code, re.DOTALL)
if m:
    print("Found retrieve_rules else-branch SQL:")
    print("-" * 60)
    print(m.group(1))
    print("-" * 60)

# Also count where purpose IN appears
count = code.count("purpose IN")
print(f"\npurpose IN appears {count} times total in file")

# Show the exact retrieve_rules function structure
m2 = re.search(r"(def retrieve_rules.*?)(?=\ndef )", code, re.DOTALL)
if m2:
    print()
    print("Full retrieve_rules function:")
    print(m2.group(1))
