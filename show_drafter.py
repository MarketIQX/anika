from app.db import fetch_one
r = fetch_one("SELECT version, prompt_text FROM agent_prompts WHERE agent_name='drafter' AND is_active=1")
print('Active drafter version:', r['version'])
print('---PROMPT---')
print(r['prompt_text'])
