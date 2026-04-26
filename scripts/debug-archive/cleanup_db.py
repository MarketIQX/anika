from app.db import execute, fetch_one

# Show the row first
row = fetch_one("SELECT id, key, value FROM firm_knowledge WHERE key = 'signature_block'")
if row:
    print(f"BEFORE — firm_knowledge id={row['id']}:")
    print(f"  key: {row['key']}")
    print(f"  value: {row['value']}")
    print()

    execute("DELETE FROM firm_knowledge WHERE key = 'signature_block'")
    print("DELETED signature_block row from firm_knowledge")

    after = fetch_one("SELECT id FROM firm_knowledge WHERE key = 'signature_block'")
    if after:
        print(f"WARNING — row still present (id={after['id']})")
    else:
        print("Confirmed: row gone")
else:
    print("No signature_block row in firm_knowledge — already clean")

# Show count
from app.db import fetch_all
count = fetch_one("SELECT COUNT(*) n FROM firm_knowledge")
print()
print(f"firm_knowledge count: {count['n']} (was 25)")
