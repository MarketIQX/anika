from pathlib import Path
p = Path('app/dashboard/templates/train.html')
code = p.read_text(encoding='utf-8')

# Find the options-rendering block and inject a freetext fallback after the buttons.
OLD = '''{% if c.options and c.options|length > 0 %}
            {% for opt in c.options %}
              <button type="submit" name="answer" value="{{ opt }}"
                      class="px-3 py-1.5 bg-white border border-yellow-300 text-yellow-900 rounded text-sm hover:bg-yellow-100">
                {{ opt }}
              </button>
            {% endfor %}
          {% else %}
            <input type="text" name="answer" required
                   class="flex-1 border border-yellow-300 rounded p-2 text-sm"
                   placeholder="Your answer" />
            <button type="submit" class="px-3 py-1.5 bg-yellow-600 text-white rounded text-sm">Submit</button>
          {% endif %}'''

NEW = '''{% if c.options and c.options|length > 0 %}
            {% for opt in c.options %}
              <button type="submit" name="answer" value="{{ opt }}"
                      class="px-3 py-1.5 bg-white border border-yellow-300 text-yellow-900 rounded text-sm hover:bg-yellow-100">
                {{ opt }}
              </button>
            {% endfor %}
            <div class="basis-full mt-2 flex gap-2 items-center">
              <span class="text-xs text-slate-500">Other:</span>
              <input type="text" name="answer"
                     class="flex-1 border border-yellow-300 rounded p-1.5 text-sm"
                     placeholder="Type a different answer..." />
              <button type="submit" class="px-3 py-1.5 bg-yellow-600 text-white rounded text-sm">Submit</button>
            </div>
          {% else %}
            <input type="text" name="answer" required
                   class="flex-1 border border-yellow-300 rounded p-2 text-sm"
                   placeholder="Your answer" />
            <button type="submit" class="px-3 py-1.5 bg-yellow-600 text-white rounded text-sm">Submit</button>
          {% endif %}'''

if OLD not in code:
    print('PATTERN NOT FOUND — need manual inspection.')
else:
    p.write_text(code.replace(OLD, NEW), encoding='utf-8')
    print('Freetext fallback added to clarification cards.')
