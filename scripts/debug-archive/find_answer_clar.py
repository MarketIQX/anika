from pathlib import Path
code = Path('app/cognitive/teaching.py').read_text(encoding='utf-8')
import re
# Find the answer_clarification function
m = re.search(r'(async def answer_clarification.*?)(?=\nasync def |\ndef |\Z)', code, re.DOTALL)
if m:
    print(m.group(1))
else:
    print('NOT FOUND — looking for any function with answer_clarif:')
    for line in code.split('\n'):
        if 'answer_clarif' in line:
            print(line)
