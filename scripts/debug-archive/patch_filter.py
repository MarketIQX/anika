from pathlib import Path
p = Path('app/tools/gmail_tool.py')
code = p.read_text(encoding='utf-8')

OLD = '''    return (
        f'from:{s.prakasha_email} '
        f'subject:\"Balakrishna and Co\" '
        f'is:unread '
        f'-label:{PROCESSED_LABEL} '
        f'newer_than:7d'
    )'''

NEW = '''    return (
        f'from:{s.prakasha_email} '
        f'subject:\"Balakrishna and Co\" '
        f'-subject:\"Payment\" '
        f'-subject:\"outstanding\" '
        f'-subject:\"Invoice\" '
        f'is:unread '
        f'-label:{PROCESSED_LABEL} '
        f'newer_than:7d'
    )'''

if OLD not in code:
    print('PATTERN NOT FOUND')
else:
    p.write_text(code.replace(OLD, NEW), encoding='utf-8')
    print('Gmail filter tightened — now excludes invoice reminder emails.')
