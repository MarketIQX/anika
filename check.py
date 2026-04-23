from app.db import fetch_one
r = fetch_one("SELECT version, LENGTH(prompt_text) as len FROM agent_prompts WHERE agent_name='drafter' AND is_active=1")
print('Active drafter v', r['version'], 'len', r['len'])
