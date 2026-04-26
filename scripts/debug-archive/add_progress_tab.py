from pathlib import Path

p = Path("app/dashboard/templates/base.html")
code = p.read_text(encoding="utf-8")

# Find the existing all_tabs list and add teaching-dashboard entry
OLD = """        {% set all_tabs = [
            ('drafts','Drafts','user'),
            ('inbox','Inbox','user'),
            ('train','Train','user'),
            ('analytics','Analytics','admin'),
            ('settings','Settings','user'),
        ] %}"""

NEW = """        {% set all_tabs = [
            ('drafts','Drafts','user'),
            ('inbox','Inbox','user'),
            ('train','Train','user'),
            ('teaching-dashboard','Progress','user'),
            ('analytics','Analytics','admin'),
            ('settings','Settings','user'),
        ] %}"""

if NEW in code:
    print("Already added")
elif OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Added Progress tab (teaching-dashboard) to main navbar")
else:
    print("Old nav block not found — dumping:")
    idx = code.find("all_tabs")
    if idx >= 0:
        print(code[idx:idx+400])

# Verify
check = p.read_text(encoding="utf-8")
if "'teaching-dashboard'" in check:
    print("Verified: Progress tab in base.html")
