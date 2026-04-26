from pathlib import Path

p = Path("app/dashboard/templates/train.html")
code = p.read_text(encoding="utf-8")

needle = """      </div>
    {% endfor %}
  </div>
</section>

<!-- ======================================================================
     Section A"""

fix = """      </div>
    {% endfor %}
  </div>
</section>
{% endif %}

<!-- ======================================================================
     Section A"""

if needle in code:
    code = code.replace(needle, fix, 1)
    p.write_text(code, encoding="utf-8")
    print("Added missing endif for Section 0")
else:
    print("Needle not found - dumping area near first Section A marker:")
    idx = code.find("Section A")
    print(code[max(0,idx-300):idx+50])
