from pathlib import Path
p = Path("app/dashboard/templates/draft_detail.html")
if not p.exists():
    print("draft_detail.html not found — checking directory:")
    import os
    for f in os.listdir("app/dashboard/templates"):
        if "draft" in f.lower():
            print(f"  {f}")
else:
    content = p.read_text(encoding="utf-8")
    print(f"File size: {len(content)} chars")
    print()
    print("First 60 lines:")
    print("-" * 80)
    for i, line in enumerate(content.splitlines()[:60], 1):
        print(f"{i:3d}| {line}")
