from app.db import fetch_all
print('=== unit_preview content ===')
for r in fetch_all('SELECT id, queue_id, unit_preview, target_unit_index FROM clarifications'):
    print('clar', r['id'], 'queue=', r['queue_id'], 'unit_idx=', r['target_unit_index'])
    print('  preview:', repr(r['unit_preview']))
