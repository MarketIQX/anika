from app.db import fetch_all
print('=== ALL entries ===')
for r in fetch_all('SELECT id, is_active, kind, scope, service_line, confidence, content FROM knowledge_library ORDER BY id DESC'):
    print('id=', r['id'], 'active=', r['is_active'], 'kind=', r['kind'], 'scope=', r['scope'], 'sl=', r['service_line'])
    print('  content:', (r['content'] or '')[:100])

print()
print('=== ALL clarifications ===')
for r in fetch_all('SELECT id, queue_id, question_text, status, answer, answered_at FROM clarifications ORDER BY id DESC'):
    print('clar', r['id'], 'queue=', r['queue_id'], 'status=', r['status'], 'answer=', r['answer'])

print()
print('=== ALL queue items ===')
for r in fetch_all('SELECT id, status, error_text, raw_content FROM teaching_queue ORDER BY id DESC'):
    print('queue', r['id'], 'status=', r['status'], 'err=', r['error_text'])
    print('  raw:', (r['raw_content'] or '')[:80])
