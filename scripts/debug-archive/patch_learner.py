from pathlib import Path

p = Path('app/agents/teaching_learner.py')
code = p.read_text(encoding='utf-8')

# Find the system prompt string that starts with 'You are Anika\'s Learner'
# Replace the ambiguity/confidence section with stricter rules.

OLD_SECTION = '''CLARIFICATION POLICY — be conservative, prefer asking.
For every unit with confidence < 0.8, generate ONE clarification question.'''

NEW_SECTION = '''CLARIFICATION POLICY — be RUTHLESSLY skeptical. Over-clarifying is SAFER than wrong storage.

HARD AMBIGUITY TRIGGERS — confidence MUST be < 0.8, MUST generate clarification:
  - Any fee, amount, number, or rupee value WITHOUT an explicit service line named in the same unit
  - Content shorter than 15 words total
  - Words like "fee", "cost", "price", "charge", "rate" without a specific service context
  - A figure like "15000" or "Rs. X" where the service is not stated in the same line
  - A past email snippet where the service being discussed is not obvious from the text itself
  - Any entry that could plausibly apply to multiple service lines

CONFIDENCE SCORING RULES (be ruthlessly honest, do NOT default to 0.9):
  - Full sentence naming service line AND clear intent → 0.9+
  - Clear intent but service line missing → 0.3-0.6 (ALWAYS clarify)
  - Fragment, amount only, or ambiguous verb → 0.1-0.3 (ALWAYS clarify)
  - Very short input (under 15 words) → max 0.4 regardless

UNIVERSAL SCOPE RULE — apply ONLY when the unit provably applies to ALL service lines. If you would label something universal but cannot prove it applies to NRI tax AND foreign subsidiary AND GST AND audit AND everything else, flag it as a clarification instead. When in doubt about scope, ASK.

For every unit with confidence < 0.8, generate ONE clarification question.'''

if OLD_SECTION not in code:
    print('OLD section not found. Dumping area around CLARIFICATION:')
    i = code.find('CLARIFICATION')
    if i >= 0:
        print(code[i:i+600])
else:
    new_code = code.replace(OLD_SECTION, NEW_SECTION)
    p.write_text(new_code, encoding='utf-8')
    print('Learner prompt hardened. Written', len(new_code), 'chars.')
