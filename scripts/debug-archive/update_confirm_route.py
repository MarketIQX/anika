from pathlib import Path

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Replace the finalize_queue call in /train/teach/confirm with finalize_with_purpose
OLD = '''    # No correction → finalize queue (create library entry with confirmed purpose)
    # Pass the user-confirmed purpose to finalize_queue so the Learner knows the context.
    try:
        await teaching.finalize_queue(
            queue_id,
            confirmed_purpose=confirmed_purpose,
            custom_label=(custom_label or None),
            service_line=(service_line or None),
        )
    except TypeError:
        # finalize_queue may not accept new kwargs yet - fall back to old signature
        # Store the confirmation data on queue, finalize without new args
        await teaching.finalize_queue(queue_id)'''

NEW = '''    # No correction → finalize with user-confirmed purpose (creates library entry)
    try:
        await teaching.finalize_with_purpose(
            queue_id,
            confirmed_purpose=confirmed_purpose,
            custom_label=(custom_label or None),
            service_line=(service_line or None),
            created_by=user.email,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"finalize failed: {e}"},
            status_code=500,
        )'''

if OLD in code:
    code = code.replace(OLD, NEW)
    print("Updated /train/teach/confirm to use finalize_with_purpose")
else:
    print("Old block not found. Searching for finalize_queue call in confirm route...")
    import re
    m = re.search(r"await teaching\.finalize_queue[^)]+\)", code)
    if m:
        print(f"Found at position {m.start()}: {m.group()}")

# Also update the /train/review-rule/{id}/decide endpoint to use finalize_with_purpose
# It currently calls bare finalize_queue which doesn't work
# Find it and replace
OLD2 = '''    # Finalize the queue (creates the library entry)
    try:
        await teaching.finalize_queue(queue_id)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"finalize failed: {e}"}, status_code=500)'''

NEW2 = '''    # Finalize the queue with the user-confirmed purpose
    try:
        # Re-read queue to get user_confirmed_purpose from Phase 1B flow
        q_row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
        # Use target_purpose from the meta_rule we just saved as confirmed purpose
        confirmed = final_target if decision in ("accept", "edit") else (q_row.get("anika_proposed_purpose") or "reference_material")
        await teaching.finalize_with_purpose(
            queue_id,
            confirmed_purpose=confirmed,
            service_line=final_sl if decision in ("accept", "edit") else None,
            created_by=user.email,
        )
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"finalize failed: {e}"}, status_code=500)'''

if OLD2 in code:
    code = code.replace(OLD2, NEW2)
    print("Updated /train/review-rule/{id}/decide to use finalize_with_purpose")
else:
    print("OLD2 block not found (maybe already different)")

p.write_text(code, encoding="utf-8")

# Verify import
import sys
for mod in list(sys.modules):
    if "app.dashboard" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.dashboard import routes as _r
    print()
    print("Route module imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
