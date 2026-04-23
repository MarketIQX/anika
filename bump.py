from app.db import execute, fetch_one
from app.agents.enricher import DEFAULT_INSTRUCTIONS

execute('UPDATE agent_prompts SET is_active=0 WHERE agent_name=?', ('enricher',))
execute('INSERT INTO agent_prompts (agent_name, version, prompt_text, is_active, change_note) VALUES (?, ?, ?, ?, ?)', ('enricher', 2, DEFAULT_INSTRUCTIONS, 1, 'Added tool-call budget and fallback defaults'))

row = fetch_one("SELECT version, LENGTH(prompt_text) as len FROM agent_prompts WHERE agent_name='enricher' AND is_active=1")
print('Active prompt: v', row[0], '(', row[1], 'chars)')
full = fetch_one("SELECT prompt_text FROM agent_prompts WHERE agent_name='enricher' AND is_active=1")
has_budget = 'BUDGET' in full[0]
print('Contains BUDGET:', has_budget)
