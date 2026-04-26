from pathlib import Path

p = Path("app/dashboard/templates/train.html")
code = p.read_text(encoding="utf-8")

# Find the Train page header section and add a "Manage rules" link next to it
# Look for the flex container holding the h1
OLD = '''<div class="flex items-start justify-between mb-4">
  <div>
    <h1 class="text-2xl font-semibold">Train Anika</h1>
    <p class="text-sm text-slate-600 mt-1">
      Teach Anika the way you'd onboard a junior CA'''

NEW = '''<div class="flex items-start justify-between mb-4">
  <div>
    <h1 class="text-2xl font-semibold">Train Anika</h1>
    <p class="text-sm text-slate-600 mt-1">
      Teach Anika the way you'd onboard a junior CA'''

# Different approach — add a header action bar just after the h1 div closes.
# We want: the h1 block stays as-is, but add a "Manage rules" link button to the right.
# Find the opening flex div and modify the drafting_paused span to include rules link.

if "Manage rules" in code:
    print("Already has Manage rules link")
else:
    # Inject after the paused-drafting span section
    marker = '<span class="px-3 py-1.5 bg-amber-100 text-amber-900 rounded text-xs font-medium">Drafting paused</span>\n  {% endif %}\n</div>'
    if marker in code:
        new_marker = '''<span class="px-3 py-1.5 bg-amber-100 text-amber-900 rounded text-xs font-medium">Drafting paused</span>
  {% endif %}
  <div class="flex items-center gap-2 ml-auto">
    <a href="/train/rules"
       class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded text-sm font-medium">
      📋 Manage rules
    </a>
  </div>
</div>'''
        code = code.replace(marker, new_marker)
        p.write_text(code, encoding="utf-8")
        print("Added 'Manage rules' link to Train page header")
    else:
        # Fallback: look for closing of first-div header block
        import re
        # Look for the {% if drafting_paused %} block — inject rules button after it
        idx = code.find('{% if drafting_paused %}')
        if idx >= 0:
            # Find the </div> that closes the header flex container
            end_idx = code.find('</div>', idx)
            end_idx = code.find('</div>', end_idx + 6)  # second </div> closes the whole flex
            insertion = '''
  <div class="flex items-center gap-2 ml-auto">
    <a href="/train/rules"
       class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded text-sm font-medium">
      📋 Manage rules
    </a>
  </div>'''
            # Insert before the second </div>
            code = code[:end_idx] + insertion + "\n" + code[end_idx:]
            p.write_text(code, encoding="utf-8")
            print("Added 'Manage rules' link (fallback path)")
        else:
            print("Could not find injection point — manual inspection needed")

# Verify by reading back
check = Path("app/dashboard/templates/train.html").read_text(encoding="utf-8")
if "Manage rules" in check:
    print("Verified: Manage rules link present in train.html")
else:
    print("WARNING: link NOT present — check template")
