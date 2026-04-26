from app.db import execute, fetch_all
# Delete stale clarifications + stuck queues
execute('DELETE FROM clarifications WHERE queue_id IN (3,4)')
execute('DELETE FROM teaching_queue WHERE id IN (3,4)')
# Also purge the soft-deleted bad id=3 entry (was 'fee 15000' universal)
execute('DELETE FROM knowledge_library WHERE id=3')
print('Cleaned up. Remaining:')
for r in fetch_all('SELECT id, kind, content FROM knowledge_library WHERE is_active=1'):
    print(' ', r['id'], r['kind'], (r['content'] or '')[:60])
