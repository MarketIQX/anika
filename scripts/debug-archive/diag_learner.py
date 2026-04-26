from app.db import fetch_all
rows = fetch_all('SELECT id, kind, content, scope, service_line, confidence FROM knowledge_library WHERE is_active=1 ORDER BY id DESC LIMIT 5')
for r in rows:
    print('id=', r['id'], 'kind=', r['kind'], 'scope=', r['scope'], 'sl=', r['service_line'], 'conf=', r['confidence'])
    print('  content:', r['content'])

print()
print('=== Pending clarifications ===')
c = fetch_all('SELECT id, queue_id, question_text, status FROM clarifications WHERE status=? ORDER BY id DESC LIMIT 5', ('pending',))
for r in c:
    print('clar', r['id'], 'q:', r['question_text'])

print()
print('=== Recent queue items ===')
q = fetch_all('SELECT id, status, error_text FROM teaching_queue ORDER BY id DESC LIMIT 5')
for r in q:
    print('queue', r['id'], 'status=', r['status'], 'err=', r['error_text'])
