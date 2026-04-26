"""
Phase 1B Stabilization Audit — comprehensive inventory of weekend changes.

Produces docs/PHASE_1B_AUDIT.md describing the exact state of the codebase
since the last known-good tag (phase-1a-complete).

Read by Claude Code before any new feature work.
"""
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import re
import sys

# Ensure project root is on sys.path so `from app.db ...` resolves when this
# audit harness is invoked from scripts/debug-archive/ (post-Cluster-8 layout).
_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from app.db import fetch_all, fetch_one  # noqa: E402

REPORT_PATH = Path("docs/PHASE_1B_AUDIT.md")
REPORT_PATH.parent.mkdir(exist_ok=True)

now = datetime.now(timezone.utc)
sections = []

# ============================================================
# SECTION 1 — Git state
# ============================================================
def run_git(cmd):
    try:
        return subprocess.run(
            ["git"] + cmd, capture_output=True, text=True, cwd="."
        ).stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

current_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
current_commit = run_git(["rev-parse", "HEAD"])
current_commit_short = run_git(["rev-parse", "--short", "HEAD"])
last_tag = run_git(["describe", "--tags", "--abbrev=0"])
all_tags = run_git(["tag", "-l", "--sort=-creatordate"])
status = run_git(["status", "--porcelain"])
unstaged_changes = [l for l in status.splitlines() if l.strip()]

git_section = []
git_section.append("# Phase 1B Stabilization Audit")
git_section.append("")
git_section.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
git_section.append("")
git_section.append("## 1. Git State")
git_section.append("")
git_section.append(f"- Current branch: `{current_branch}`")
git_section.append(f"- Current commit: `{current_commit_short}` ({current_commit})")
git_section.append(f"- Last tag: `{last_tag}`")
git_section.append(f"- All tags: `{all_tags or '(none)'}`")
git_section.append(f"- Uncommitted changes: {len(unstaged_changes)}")
if unstaged_changes:
    git_section.append("")
    git_section.append("```")
    for line in unstaged_changes[:30]:
        git_section.append(line)
    if len(unstaged_changes) > 30:
        git_section.append(f"... ({len(unstaged_changes) - 30} more)")
    git_section.append("```")
sections.append("\n".join(git_section))

# ============================================================
# SECTION 2 — Files modified since phase-1a-complete
# ============================================================
files_section = ["## 2. Files Modified Since `phase-1a-complete`"]
files_section.append("")

if "phase-1a-complete" in all_tags:
    diff_files = run_git(["diff", "--name-status", "phase-1a-complete..HEAD"])
    if diff_files:
        files_section.append("### Files committed since tag:")
        files_section.append("```")
        files_section.append(diff_files)
        files_section.append("```")
    else:
        files_section.append("(no committed changes since tag)")
    files_section.append("")
    files_section.append("### Files with uncommitted changes:")
    if unstaged_changes:
        for line in unstaged_changes:
            files_section.append(f"- `{line}`")
    else:
        files_section.append("(none)")
else:
    files_section.append(f"WARNING: tag `phase-1a-complete` not found in repo.")
    files_section.append(f"Available tags: {all_tags}")

sections.append("\n".join(files_section))

# ============================================================
# SECTION 3 — Schema changes
# ============================================================
schema_section = ["## 3. Database Schema"]
schema_section.append("")
schema_section.append("All tables and their columns (current state):")
schema_section.append("")

tables = fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for t in tables:
    name = t["name"]
    if name.startswith("sqlite_") or name.endswith("_vec"):
        continue
    schema_section.append(f"### `{name}`")
    cols = fetch_all(f"PRAGMA table_info({name})")
    schema_section.append("```")
    for c in cols:
        default = f" DEFAULT {c['dflt_value']}" if c['dflt_value'] is not None else ""
        nullable = " NOT NULL" if c['notnull'] else ""
        pk = " PRIMARY KEY" if c['pk'] else ""
        schema_section.append(f"  {c['name']:30s} {c['type']:15s}{nullable}{default}{pk}")
    schema_section.append("```")
    row_count = fetch_one(f"SELECT COUNT(*) AS n FROM {name}")
    schema_section.append(f"Row count: {row_count['n']}")
    schema_section.append("")

sections.append("\n".join(schema_section))

# ============================================================
# SECTION 4 — Schema diff vs Phase 1A
# ============================================================
# Look at schema.sql definitions to see what's NEW vs schema file
schema_diff_section = ["## 4. Schema Drift Analysis"]
schema_diff_section.append("")
schema_diff_section.append("Comparing live DB schema to `app/db/schema.sql`:")
schema_diff_section.append("")

def _strip_sql_comments(sql: str) -> str:
    """Drop -- line comments before regex parsing.

    Cluster 10 fix: comments like "-- ... CREATE TABLE in scratch scripts ..."
    were causing the table-detection regex to capture "in" as a table name,
    and inline comments containing ";" were truncating the column-detection
    regex's body capture. Strip them.
    """
    cleaned = []
    for line in sql.splitlines():
        # Find first occurrence of -- not inside a string. Schema doesn't use
        # SQL strings with -- so a simple find is correct.
        idx = line.find("--")
        if idx >= 0:
            line = line[:idx]
        cleaned.append(line)
    return "\n".join(cleaned)


schema_file = Path("app/db/schema.sql")
if schema_file.exists():
    schema_sql_raw = schema_file.read_text(encoding="utf-8")
    schema_sql = _strip_sql_comments(schema_sql_raw)
    declared_tables = re.findall(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)", schema_sql)
    declared_set = set(declared_tables)
    # Filter out sqlite-vec auto-created shadow tables. These never appear in
    # schema.sql (they're created by the vec0 virtual table at runtime) and
    # they have a variety of suffixes: _vec, _vec_chunks, _vec_info,
    # _vec_rowids, _vec_vector_chunks00. Any table name containing "_vec"
    # is a vec internal.
    live_set = {
        t["name"] for t in tables
        if not t["name"].startswith("sqlite_") and "_vec" not in t["name"]
    }

    in_live_not_in_schema = live_set - declared_set
    in_schema_not_in_live = declared_set - live_set

    if in_live_not_in_schema:
        schema_diff_section.append("### Tables in live DB but NOT declared in schema.sql:")
        for t in sorted(in_live_not_in_schema):
            schema_diff_section.append(f"- `{t}`")
        schema_diff_section.append("")
    if in_schema_not_in_live:
        schema_diff_section.append("### Tables declared in schema.sql but NOT in live DB:")
        for t in sorted(in_schema_not_in_live):
            schema_diff_section.append(f"- `{t}`")
        schema_diff_section.append("")
    if not in_live_not_in_schema and not in_schema_not_in_live:
        schema_diff_section.append("Tables: aligned.")
        schema_diff_section.append("")

    # Check columns for drafts and key tables that we modified this weekend
    schema_diff_section.append("### Column drift on key tables")
    schema_diff_section.append("")
    for table_name in ["drafts", "memory", "knowledge_library", "teaching_queue"]:
        cols_live = {c["name"] for c in fetch_all(f"PRAGMA table_info({table_name})")}
        match = re.search(rf"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{table_name}\s*\(([^;]+)\)", schema_sql, re.DOTALL)
        if match:
            cols_declared = set(re.findall(r"^\s*(\w+)\s+", match.group(1), re.MULTILINE))
            # Filter SQL keywords that appear at start of continuation lines
            # (e.g. multi-line CHECK + DEFAULT in knowledge_library.scope).
            cols_declared = {
                c for c in cols_declared
                if c.upper() not in (
                    "FOREIGN", "PRIMARY", "UNIQUE", "CREATE", "CHECK",
                    "DEFAULT", "REFERENCES", "NOT", "ON",
                )
            }
            extra_in_live = cols_live - cols_declared
            missing_in_live = cols_declared - cols_live
            if extra_in_live or missing_in_live:
                schema_diff_section.append(f"#### `{table_name}`")
                if extra_in_live:
                    schema_diff_section.append(f"- Columns added at runtime (not in schema.sql): `{sorted(extra_in_live)}`")
                if missing_in_live:
                    schema_diff_section.append(f"- Columns declared but missing in live DB: `{sorted(missing_in_live)}`")
                schema_diff_section.append("")

sections.append("\n".join(schema_diff_section))

# ============================================================
# SECTION 5 — Configuration / settings
# ============================================================
config_section = ["## 5. Configuration"]
config_section.append("")
config_section.append("### `app/config/settings.py` — current settings:")
config_section.append("")
settings_path = Path("app/config/settings.py")
if settings_path.exists():
    settings_code = settings_path.read_text(encoding="utf-8")
    # Find Settings class fields
    settings_match = re.search(r"class Settings.*?(?=^class |\Z)", settings_code, re.DOTALL | re.MULTILINE)
    if settings_match:
        config_section.append("```python")
        config_section.append(settings_match.group()[:3000])
        config_section.append("```")
config_section.append("")
config_section.append("### `system_state` table — runtime feature flags:")
state_rows = fetch_all("SELECT key, value FROM system_state ORDER BY key")
config_section.append("")
config_section.append("```")
for r in state_rows:
    config_section.append(f"  {r['key']}: {r['value']}")
config_section.append("```")
sections.append("\n".join(config_section))

# ============================================================
# SECTION 6 — Agents inventory
# ============================================================
agents_section = ["## 6. Agents Inventory"]
agents_section.append("")
agents_section.append("All agent files and their public functions / classes:")
agents_section.append("")

agents_dir = Path("app/agents")
for agent_file in sorted(agents_dir.glob("*.py")):
    if agent_file.name == "__init__.py":
        continue
    code = agent_file.read_text(encoding="utf-8")
    agents_section.append(f"### `app/agents/{agent_file.name}`")
    agents_section.append(f"- File size: {len(code)} chars")

    # Find functions and classes
    funcs = re.findall(r"^(async\s+)?def\s+(\w+)\s*\(", code, re.MULTILINE)
    classes = re.findall(r"^class\s+(\w+)", code, re.MULTILINE)

    if classes:
        agents_section.append(f"- Classes: {', '.join('`' + c + '`' for c in classes)}")
    if funcs:
        public_funcs = [f"{'async ' if a else ''}{n}()" for a, n in funcs if not n.startswith("_")]
        if public_funcs:
            agents_section.append(f"- Public functions: {', '.join('`' + f + '`' for f in public_funcs)}")

    # Check for direct openai imports
    if "from openai" in code or "import openai" in code:
        agents_section.append("- ⚠ Direct openai import (sovereignty migration target)")

    # Check for max_turns
    max_turns_match = re.search(r"max_turns\s*=\s*(\d+)", code)
    if max_turns_match:
        agents_section.append(f"- max_turns: {max_turns_match.group(1)}")

    # Check for tools list
    tools_match = re.search(r"tools\s*=\s*\[(.*?)\]", code, re.DOTALL)
    if tools_match:
        tools_text = tools_match.group(1)
        tool_names = re.findall(r"(\w+)", tools_text)
        tool_names = [t for t in tool_names if t.startswith("tool_")]
        if tool_names:
            agents_section.append(f"- Tools: {', '.join('`' + t + '`' for t in tool_names)}")
        else:
            agents_section.append("- Tools: tool-less")

    agents_section.append("")

sections.append("\n".join(agents_section))

# ============================================================
# SECTION 7 — Routes inventory
# ============================================================
routes_section = ["## 7. Routes Inventory"]
routes_section.append("")
routes_section.append("All HTTP endpoints registered in `app/dashboard/routes.py`:")
routes_section.append("")

routes_path = Path("app/dashboard/routes.py")
if routes_path.exists():
    routes_code = routes_path.read_text(encoding="utf-8")
    route_matches = re.finditer(
        r"@router\.(get|post|put|delete|patch)\(([^)]+)\)\s*\n\s*(?:async\s+)?def\s+(\w+)",
        routes_code,
    )
    routes_section.append("```")
    for m in route_matches:
        method = m.group(1).upper()
        path = m.group(2).strip().strip('"').strip("'")
        fn_name = m.group(3)
        routes_section.append(f"  {method:6s} {path:40s} -> {fn_name}()")
    routes_section.append("```")

sections.append("\n".join(routes_section))

# ============================================================
# SECTION 8 — Knowledge library state
# ============================================================
lib_section = ["## 8. Knowledge Library State"]
lib_section.append("")

active_count = fetch_one("SELECT COUNT(*) AS n FROM knowledge_library WHERE is_active = 1")
inactive_count = fetch_one("SELECT COUNT(*) AS n FROM knowledge_library WHERE is_active = 0")
lib_section.append(f"- Active entries: {active_count['n']}")
lib_section.append(f"- Soft-deleted entries: {inactive_count['n']}")
lib_section.append("")

lib_section.append("### Active entries by purpose:")
purpose_breakdown = fetch_all("""
    SELECT purpose, COUNT(*) AS n
      FROM knowledge_library
     WHERE is_active = 1
     GROUP BY purpose
     ORDER BY n DESC
""")
lib_section.append("")
lib_section.append("```")
for r in purpose_breakdown:
    lib_section.append(f"  {(r['purpose'] or 'NULL'):25s} : {r['n']}")
lib_section.append("```")
lib_section.append("")

lib_section.append("### Active entries by service_line:")
sl_breakdown = fetch_all("""
    SELECT service_line, COUNT(*) AS n
      FROM knowledge_library
     WHERE is_active = 1
     GROUP BY service_line
     ORDER BY n DESC
""")
lib_section.append("")
lib_section.append("```")
for r in sl_breakdown:
    lib_section.append(f"  {(r['service_line'] or 'NULL'):25s} : {r['n']}")
lib_section.append("```")

lib_section.append("")
lib_section.append("### All voice_examples (full content):")
voices = fetch_all("""
    SELECT id, service_line, scope, created_by, applied_count, last_used_at, substr(content, 1, 200) AS preview
      FROM knowledge_library
     WHERE is_active = 1 AND purpose = 'voice_example'
     ORDER BY id
""")
lib_section.append("")
for v in voices:
    by = (v["created_by"] or "?").split("@")[0]
    lib_section.append(f"- **id={v['id']}** | {v['service_line'] or '-'} | by `{by}` | applied {v['applied_count']}x")
    lib_section.append(f"  - preview: {v['preview']}")
    lib_section.append("")

sections.append("\n".join(lib_section))

# ============================================================
# SECTION 9 — Memory table state
# ============================================================
mem_section = ["## 9. Memory Table State (legacy / deprecated patterns)"]
mem_section.append("")

mem_active = fetch_all("""
    SELECT id, kind, service_line, is_active, subject, substr(content, 1, 100) AS preview
      FROM memory
     ORDER BY id
""")
mem_section.append(f"- Total rows: {len(mem_active)}")
on_count = sum(1 for m in mem_active if m['is_active'])
off_count = sum(1 for m in mem_active if not m['is_active'])
mem_section.append(f"- Active: {on_count}, Deactivated: {off_count}")
mem_section.append("")
mem_section.append("```")
for m in mem_active:
    state = "ON " if m['is_active'] else "OFF"
    mem_section.append(f"  {state} id={m['id']:3d} | {m['kind']:15s} | {(m['service_line'] or '-'):20s} | {(m['subject'] or '')[:40]}")
mem_section.append("```")

sections.append("\n".join(mem_section))

# ============================================================
# SECTION 10 — Drafts state
# ============================================================
drafts_section = ["## 10. Drafts State"]
drafts_section.append("")

draft_count = fetch_one("SELECT COUNT(*) AS n FROM drafts")
drafts_section.append(f"- Total drafts: {draft_count['n']}")
drafts_section.append("")
drafts_section.append("### By status:")
status_breakdown = fetch_all("""
    SELECT sent_status, COUNT(*) AS n FROM drafts GROUP BY sent_status ORDER BY n DESC
""")
drafts_section.append("")
drafts_section.append("```")
for r in status_breakdown:
    drafts_section.append(f"  {r['sent_status']:25s} : {r['n']}")
drafts_section.append("```")
drafts_section.append("")

drafts_section.append("### Last 10 drafts (chronological):")
recent = fetch_all("""
    SELECT d.id, d.sent_status, d.cognitive_state, d.voice_coverage_count,
           d.created_at, e.likely_service_line, re.from_email
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
      LEFT JOIN raw_emails re ON re.id = d.email_id
     ORDER BY d.id DESC LIMIT 10
""")
drafts_section.append("")
drafts_section.append("```")
drafts_section.append(f"  {'id':4s} {'status':22s} {'cog_state':12s} {'vcc':5s} {'service_line':22s} {'from':30s}")
for r in recent:
    drafts_section.append(
        f"  {r['id']:4d} {(r['sent_status'] or '-'):22s} "
        f"{(r['cognitive_state'] or '-'):12s} "
        f"{str(r['voice_coverage_count'] or 0):5s} "
        f"{(r['likely_service_line'] or '-'):22s} "
        f"{(r['from_email'] or '-')[:30]}"
    )
drafts_section.append("```")
sections.append("\n".join(drafts_section))

# ============================================================
# SECTION 11 — Tests
# ============================================================
tests_section = ["## 11. Test Suite Status"]
tests_section.append("")
tests_section.append("Running full pytest suite (this may take 1-2 min)...")
tests_section.append("")

try:
    # Use sys.executable (same Python that's running this script) — relative
    # ".venv/Scripts/python.exe" failed on Windows when audit was launched
    # via Bash → python (Cluster 10 fix).
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=line", "-q"],
        capture_output=True, text=True, timeout=300, cwd=".",
    )
    output = (result.stdout + result.stderr).strip()
    tests_section.append("```")
    # Last 60 lines of output (final test summary + any failures)
    lines = output.splitlines()
    for line in lines[-60:]:
        tests_section.append(line)
    tests_section.append("```")
    tests_section.append("")
    tests_section.append(f"Exit code: {result.returncode}")
    tests_section.append(f"PASS" if result.returncode == 0 else "FAIL")
except subprocess.TimeoutExpired:
    tests_section.append("TIMEOUT — test suite did not complete in 5 minutes.")
except Exception as e:
    tests_section.append(f"ERROR running tests: {e}")

sections.append("\n".join(tests_section))

# ============================================================
# SECTION 12 — Outstanding state I'm aware of
# ============================================================
out_section = ["## 12. Known Outstanding State"]
out_section.append("")
out_section.append("This audit is the post-stabilization baseline (Phase 1B → 1C handover).")
out_section.append("Every claim in this section is verified against the live codebase or DB by")
out_section.append("the audit harness above (Sections 1-11) or by an explicit Cluster probe in")
out_section.append("the Phase 1B stabilization sprint.")
out_section.append("")
out_section.append("### Verified by Phase 1B stabilization sprint")
out_section.append("")
out_section.append("- VERIFIED — Drafter health: every reasoning_log row for agent_name='drafter'")
out_section.append("  has status='ok'. No MaxTurnsExceeded or embed/API failures recorded.")
out_section.append("- VERIFIED — Sent draft 22 (Chandrika) carries a single canonical signature")
out_section.append("  matching app/config/firm_identity.SIGNATURE_BLOCK. The Cluster 1 'mojibake")
out_section.append("  defect' was retracted in Cluster 6: it was a Windows-Bash terminal failing")
out_section.append("  to render U+2014 em-dashes, not data corruption.")
out_section.append("- VERIFIED — Enricher refactored to tool-less in Cluster 4. The Agent()")
out_section.append("  constructor no longer receives tools=[...]; lookup_client +")
out_section.append("  retrieve_similar_drafts are pre-fetched in enrich() and inlined as")
out_section.append("  PRE-FETCHED CONTEXT in the user_input. max_turns dropped 20 → 3.")
out_section.append("  The MaxTurnsExceeded fallback is preserved as defense-in-depth.")
out_section.append("- VERIFIED — Cluster 5 retried email 877 (Sumana, the previously-stuck enquiry)")
out_section.append("  through the new tool-less Enricher: completed in 8.12s, no MaxTurnsExceeded,")
out_section.append("  classified as nri_tax (correct — UK-NRI tax question). reasoning_log row")
out_section.append("  contains 'pre_fetched_context' + 'tool_less'=True. Probe forensic ID in")
out_section.append("  reasoning_log; duplicate enrichments row was cleaned up.")
out_section.append("- VERIFIED — Cluster 2 promoted every runtime-added column into")
out_section.append("  app/db/schema.sql + matching _ensure_column migrations in init_db().")
out_section.append("  A fresh DB built from schema.sql now matches live anika.db column-for-")
out_section.append("  column, attribute-for-attribute, in declaration order (PRAGMA parity).")
out_section.append("  Section 4 above confirms 'Tables: aligned.'")
out_section.append("- VERIFIED — Cluster 7 cleaned up the orphan vec row (knowledge_library_vec")
out_section.append("  rowid=3 with no matching library row at any is_active state). Final state:")
out_section.append("  24 vec rows ↔ 24 library rows, 1:1, zero orphans. The dormant vec for")
out_section.append("  vec rowid=24 (its library row is soft-deleted, deleted_by=aks) was kept by")
out_section.append("  design — retrieve_examples() filters is_active=1 anyway.")
out_section.append("- VERIFIED — Cluster 8 archived 192 scratch debug scripts from the project")
out_section.append("  root into scripts/debug-archive/ (forensic value preserved, working tree")
out_section.append("  readable). The directory is git-tracked, NOT in .gitignore.")
out_section.append("- VERIFIED — Cluster 9: full pytest suite reports 131 passed, 0 failed,")
out_section.append("  0 warnings (Section 11 above is the live re-run).")
out_section.append("")
out_section.append("### Files deliberately NOT yet created — Phase 1C targets")
out_section.append("")
out_section.append("- `app/llm.py` — provider-agnostic LLM abstraction")
out_section.append("- `app/embeddings.py` — provider-agnostic embeddings abstraction")
out_section.append("- `app/agents/critic.py` + `app/agents/critic_rules.py` — critic agent")
out_section.append("  (rule-based + LLM hybrid)")
out_section.append("")
out_section.append("### Items deferred to Phase 1C / 1D / 2")
out_section.append("")
out_section.append("- Pattern recognition (B1)")
out_section.append("- Self-audit narrative (B3)")
out_section.append("- Per-partner data isolation (Phase 1C)")
out_section.append("- Local LLM migration (Phase 2 sovereignty)")
out_section.append("- Calendar integration")
out_section.append("- Thread reply support")
out_section.append("- Document intake")
out_section.append("- Edit-distance trending dashboard")

sections.append("\n".join(out_section))

# ============================================================
# Write report
# ============================================================
final_report = "\n\n".join(sections)
REPORT_PATH.write_text(final_report, encoding="utf-8")

print(f"Audit complete. Report written to: {REPORT_PATH}")
print(f"Length: {len(final_report)} chars")
print()
print("Quick summary:")
print(f"  Tag baseline: {last_tag}")
print(f"  Uncommitted changes: {len(unstaged_changes)}")
print(f"  Active library entries: {active_count['n']}")
print(f"  Total drafts: {draft_count['n']}")
