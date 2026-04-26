from pathlib import Path
import re

files = [
    'app/dashboard/templates/drafts.html',
    'app/dashboard/templates/draft_detail.html',
    'app/dashboard/templates/inbox_detail.html',
]

for f in files:
    p = Path(f)
    text = p.read_text(encoding='utf-8')
    # Remove any line block showing routing_partner
    pattern = re.compile(r'\s*\{%\s*if\s+\w+\.routing_partner\s*%\}.*?\{%\s*endif\s*%\}', re.DOTALL)
    new = pattern.sub('', text)
    if new != text:
        p.write_text(new, encoding='utf-8')
        print('Cleaned:', f)
    else:
        print('No change:', f)
