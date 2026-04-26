from pathlib import Path

p = Path("app/dashboard/templates/base.html")
code = p.read_text(encoding="utf-8")

# Match the actual current content (Train is 'admin')
OLD = """        {% set all_tabs = [
            ('drafts','Drafts','user'),
            ('inbox','Inbox','user'),
            ('train','Train','admin'),
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
    print("Already patched")
elif OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched: Train->user + added Progress tab")
else:
    print("Still not matching — raw dump:")
    idx = code.find("all_tabs")
    # Grab 400 chars from that point
    print(repr(code[idx:idx+400]))
