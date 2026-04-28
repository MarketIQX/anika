# scripts/debug-archive/

Forensic archive of the one-off Python scripts that accumulated at the
project root during the Phase 1B "PowerShell heredoc patches" debugging
weekend (April 23–25, 2026).

## Why these files exist

During Phase 1B, debugging was done by piping inline Python heredocs from
PowerShell into the venv's Python — each session producing a new
`patch_*.py`, `check_*.py`, `diag_*.py`, or `task*_*.py` script that ran
once and was never deleted. They were the day-to-day tool for inspecting
state and applying ad-hoc DB changes. By the end of the weekend, ~190
such scripts were sitting at the project root, drowning the working tree
and obscuring what was actually production code.

## Why they're in git, not deleted

These scripts are the audit trail of how the live anika.db reached its
current shape. Every runtime `ALTER TABLE`, every fixed draft, every
reset password ran through one of these files. Deleting them would
destroy that history.

`scripts/debug-archive/` is **tracked** in git (NOT in `.gitignore`) so
the audit history travels with the repo. If a future investigation needs
to know "where did `knowledge_library.purpose` come from?", grep this
directory.

## What lives here

- `add_*.py` — scripts that added routes, columns, or template files
- `audit_*.py` — one-off audit/inspection scripts
- `check_*.py` — point-in-time state inspections
- `cleanup_*.py` — DB cleanups
- `diag*.py` — diagnostic dumps
- `find_*.py`, `inspect_*.py`, `investigate_*.py` — read-only probes
- `fix_*.py` — one-shot data fixes (e.g. `fix_draft25.py`)
- `patch_*.py`, `step*_*.py`, `task*_*.py` — sequential code patches
- `make_*.py` — template / file generators
- `monitor_*.py`, `live_tracker.py`, `watch.py` — live observability probes
- `qc_*.py`, `triage.py`, `engagement_report.py` — quality reports
- `retest_*.py`, `retry_*.py` — re-run probes for stuck emails
- `show_*.py`, `see_*.py` — code-introspection probes
- `verify_*.py`, `verify.py`, `quick_check.py` — verification probes
- `test_*.py` (root-level) — root-level scratch tests, separate from `tests/`
- `bump.py`, `crosscheck.py`, `clean_partner.py`, `trim.py`, etc. — utilities
- `stabilization_audit.py` — the one-off audit harness used by the
  Cluster 0 / Cluster 10 stabilization sweep

## Reading these for forensics

These scripts assume they're run from the project root via the venv:

```powershell
cd C:\Users\marke\anika-balakrishna
.\.venv\Scripts\python.exe scripts\debug-archive\<filename>
```

Most are read-only probes. A few do mutate state (anything `fix_*` or
`patch_*`). Read before re-running.

## Going forward (Phase 1C and after)

Don't add new scripts here. New tooling lives under `scripts/` proper, or
under `tests/` if it's verifiable code. This archive is closed for new
admissions — its contents are immutable.

April 27 (Phase 1C): added 10 more scripts from Monday's debugging.

April 27–28 (Phase 1C-3): added 13 more scripts from the harvester /
knowledge-graph / filter debugging batch. Note:
`partner_check_now_phase1c3.py` is the evolved version of
`partner_check_now.py` (Phase 1B) — both kept as snapshots so the
probe's evolution (refined time buckets, pending-drafts section,
sent-today report) is preserved per the archive's immutability contract.
