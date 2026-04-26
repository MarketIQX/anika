from pathlib import Path
p = Path('app/cognitive/teaching.py')
code = p.read_text(encoding='utf-8')

OLD = '''    unit_preview = (row.get(\"unit_preview\") or \"\").strip()
    if not unit_preview:
        return {\"status\": \"answered\", \"action\": \"no-op\"}'''

NEW = '''    unit_preview = (row.get(\"unit_preview\") or \"\").strip()
    if not unit_preview:
        # Fallback: use the queue's raw_content when Learner didn't
        # persist a unit_preview snapshot.
        queue_row = fetch_one(\"SELECT raw_content FROM teaching_queue WHERE id=?\", (row[\"queue_id\"],))
        unit_preview = (queue_row[\"raw_content\"] if queue_row else \"\").strip()
    if not unit_preview:
        return {\"status\": \"answered\", \"action\": \"no-op-empty-content\"}'''

if OLD not in code:
    print('PATTERN NOT FOUND')
else:
    p.write_text(code.replace(OLD, NEW), encoding='utf-8')
    print('answer_clarification patched — now falls back to queue raw_content.')
