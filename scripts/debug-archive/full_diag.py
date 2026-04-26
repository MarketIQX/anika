from app.db import fetch_all
rows = fetch_all('SELECT id, kind, content, scope, service_line, confidence, is_active FROM knowledge_library ORDER BY id DESC')
print('=== ALL entries (active + deleted) ===')
for r in rows:
    print('id=', r['id'], 'active=', r['is_active'], 'kind=', r['kind'], 'scope=', r['scope'], 'sl=', r['service_line'], 'conf=', r['confidence'])
    print('  content:', r['content'])

print()
print('=== ALL clarifications ===')
c = fetch_all('SELECT id, queue_id, question_text, status, answer FROM clarifications ORDER BY id DESC')
for r in c:
    print('clar id=', r['id'], 'status=', r['status'], 'q:', r['question_text'])

print()
print('=== ALL queue items ===')
q = fetch_all('SELECT id, source_type, status, error_text, raw_content FROM teaching_queue ORDER BY id DESC')
for r in q:
    print('queue', r['id'], 'type=', r['source_type'], 'status=', r['status'])
    print('  raw:', (r['raw_content'] or '')[:100])
