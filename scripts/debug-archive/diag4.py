from app.db import fetch_all
import json
rows = fetch_all('''
  SELECT rl.input_json, rl.output_json, rl.reasoning_text, rl.latency_ms, rl.error_text
  FROM reasoning_log rl
  JOIN raw_emails r ON rl.email_id = r.id
  WHERE rl.agent_name = 'enricher' AND r.from_email LIKE '%shivank%'
''')
for r in rows:
    print('=== INPUT ==='); print((r['input_json'] or '')[:500])
    print('=== OUTPUT ==='); print((r['output_json'] or '')[:500])
    print('=== REASONING ==='); print((r['reasoning_text'] or '')[:500])
    print(f"=== ERROR: {r['error_text']}")
    print(f"=== LATENCY: {r['latency_ms']}ms")
