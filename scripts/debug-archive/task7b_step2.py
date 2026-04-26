from pathlib import Path
import re
import json

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# 1. Add new imports at the top of the route section (after existing app.agents imports)
# Find the existing app.agents import line
if "from app.agents import purpose_classifier" not in code:
    # Add imports near other app.agents imports
    insertion_point = "from app.agents import approver"
    replacement = (
        "from app.agents import approver\n"
        "from app.agents import purpose_classifier, humility_layer"
    )
    if insertion_point in code:
        code = code.replace(insertion_point, replacement)
        print("Added imports for purpose_classifier and humility_layer")
    else:
        print("WARNING: Could not find existing import anchor")

# 2. Replace the entire train_teach function body
OLD_ROUTE = '@router.post("/train/teach")\nasync def train_teach(\n    request: Request,\n    content: str = Form(""),\n    files: list[UploadFile] = File(default_factory=list),\n    user: User = Depends(require_user),\n):\n    """Accept a text paste and/or one-or-more files. One queue row per input."""\n    import time\n\n    uploads_dir = teaching._ensure_uploads_dir()\n    created_ids: list[int] = []\n    errors: list[str] = []\n\n    content = (content or "").strip()\n    if content:\n        qid = teaching.enqueue_text(raw_content=content, created_by=user.email)\n        try:\n            await teaching.finalize_queue(qid)\n        except Exception as e:  # noqa: BLE001\n            errors.append(f"text: {e}")\n        created_ids.append(qid)\n\n    for uf in files:'

if OLD_ROUTE not in code:
    print("OLD route block not found. Trying alternative match strategy...")
    # Try a looser match
    idx = code.find('@router.post("/train/teach")')
    if idx >= 0:
        # Find end of the function
        end_marker = "# --- Clarifications"
        end_idx = code.find(end_marker, idx)
        print(f"Found route at {idx}, end at {end_idx}")
        current_body = code[idx:end_idx]
        print("First 400 chars of current route:")
        print(current_body[:400])
else:
    print("OLD route found — proceeding with replacement")

# We'll do a simpler block replacement using the route + ending landmark
start_pattern = '@router.post("/train/teach")'
end_pattern = '# --- Clarifications'

start_idx = code.find(start_pattern)
end_idx = code.find(end_pattern, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f"Landmarks not found: start={start_idx}, end={end_idx}")
else:
    old_section = code[start_idx:end_idx]
    print(f"Found old section: {len(old_section)} chars")

    NEW_SECTION = '''@router.post("/train/teach")
async def train_teach(
    request: Request,
    content: str = Form(""),
    files: list[UploadFile] = File(default_factory=list),
    user: User = Depends(require_user),
):
    """Accept a text paste and/or one-or-more files.

    NEW FLOW (Phase 1B):
      1. Create queue row with status='awaiting_confirmation'
      2. Run purpose_classifier to propose purpose
      3. If confidence < 0.5, also run humility_layer
      4. Store proposals on the queue row
      5. Do NOT finalize_queue yet — user must confirm via /train/teach/confirm
    """
    import json as _json
    import time

    uploads_dir = teaching._ensure_uploads_dir()
    created_ids: list[int] = []
    errors: list[str] = []

    async def _classify_and_persist(qid: int, raw_text: str, filename: str | None, mime: str | None):
        """Run classifier + optional humility, write back to queue row."""
        try:
            proposal = await purpose_classifier.classify_purpose(
                content=raw_text,
                filename=filename,
                file_mime=mime,
            )
        except Exception as e:
            errors.append(f"queue {qid} classify: {str(e)[:80]}")
            return

        humility_json = None
        if proposal.confidence < 0.5:
            try:
                articulation = await humility_layer.articulate_uncertainty(
                    content=raw_text,
                    classifier_reasoning=proposal.reasoning,
                    filename=filename,
                )
                humility_json = _json.dumps(articulation.model_dump())
            except Exception as e:
                errors.append(f"queue {qid} humility: {str(e)[:80]}")

        execute(
            """
            UPDATE teaching_queue SET
                anika_proposed_purpose = ?,
                anika_proposed_confidence = ?,
                anika_reasoning = ?,
                anika_suggested_sl = ?,
                anika_suggested_custom = ?,
                humility_articulation = ?,
                status = ?,
                awaiting_confirmation = 1
             WHERE id = ?
            """,
            (
                proposal.proposed_purpose,
                proposal.confidence,
                proposal.reasoning,
                proposal.suggested_service_line,
                proposal.suggested_custom_label,
                humility_json,
                "awaiting_confirmation",
                qid,
            ),
        )

    content = (content or "").strip()
    if content:
        qid = teaching.enqueue_text(raw_content=content, created_by=user.email)
        await _classify_and_persist(qid, content, None, None)
        created_ids.append(qid)

    for uf in files:
        if not uf.filename:
            continue
        body = await uf.read()
        if len(body) > file_extractors.MAX_UPLOAD_BYTES:
            errors.append(f"{uf.filename}: exceeds 50 MB limit")
            continue
        stem = Path(uf.filename).stem
        suffix = Path(uf.filename).suffix.lower()
        stamp = int(time.time() * 1000)
        safe_name = f"{stamp}__{stem}{suffix}"
        target = uploads_dir / safe_name
        target.write_bytes(body)
        try:
            extracted = file_extractors.extract(target)
        except file_extractors.FileTooLargeError as e:
            errors.append(f"{uf.filename}: {e}")
            continue
        except file_extractors.ExtractionError as e:
            errors.append(f"{uf.filename}: {e}")
            continue
        qid = teaching.enqueue_file(
            raw_content=extracted.text,
            file_mime=uf.content_type,
            original_filename=uf.filename,
            stored_path=str(target.relative_to(uploads_dir.parent.parent)),
            created_by=user.email,
        )
        await _classify_and_persist(qid, extracted.text, uf.filename, uf.content_type)
        created_ids.append(qid)

    access_log.log(
        action="teach_submit",
        user_email=user.email,
        target=",".join(str(i) for i in created_ids),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )

    flash = "; ".join(errors)[:300] if errors else ""
    qs = f"?flash={flash}" if flash else ""
    return RedirectResponse(f"/train{qs}", status_code=303)


'''

    code = code[:start_idx] + NEW_SECTION + code[end_idx:]
    p.write_text(code, encoding="utf-8")
    print(f"Route replaced. New file size: {len(code)} chars")

# Verify the file still imports cleanly
import sys
sys.path.insert(0, ".")
try:
    # Clear cache
    for mod in list(sys.modules):
        if mod.startswith("app.dashboard"):
            del sys.modules[mod]
    from app.dashboard import routes as _routes_check
    print()
    print("Route module imports cleanly - syntax OK")
except Exception as e:
    print()
    print(f"IMPORT ERROR: {e}")
