from pathlib import Path
code = Path('app/agents/teaching_learner.py').read_text(encoding='utf-8')
# Find the SYSTEM prompt
import re
# Look for any docstring/multi-line string that has 'classify' or 'ambiguity' in it
matches = re.findall(r'(\"\"\".*?\"\"\"|\'\'\'.*?\'\'\')', code, re.DOTALL)
for i, m in enumerate(matches):
    if 'classif' in m.lower() or 'ambig' in m.lower() or 'clarif' in m.lower():
        print('--- match', i, '(', len(m), 'chars) ---')
        print(m[:1500])
        print()
