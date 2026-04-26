from pathlib import Path
p = Path("app/agents/orchestrator.py")
code = p.read_text(encoding="utf-8")

OLD = """    # Classifier first — agentic decision.
    cls = await classifier.classify("""

NEW = """    # Hard safety gate #5 — Structural validator (Apple-style).
    # Rejects non-enquiries BEFORE spending an LLM call. If structure says no,
    # we log + mark processed + skip. Website forms bypass (is_web_form=True).
    sv_ok, sv_reason = structural_validator.validate(
        from_email=msg.from_email,
        subject=msg.subject,
        body_plain=msg.body_plain,
        raw_headers=getattr(msg, "raw_headers", None),
        is_web_form=is_web_form,
    )
    if not sv_ok:
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={
                "email_id": email_id,
                "from_email": msg.from_email,
                "subject": msg.subject,
            },
            output_obj={
                "action": "skip_structural_validator",
                "reason": sv_reason,
            },
            reasoning_text=f"structural validator rejected: {sv_reason}",
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {
            "email_id": email_id,
            "action": "skip_structural_validator",
            "reason": sv_reason,
            "is_web_form": is_web_form,
        }

    # Classifier first — agentic decision.
    cls = await classifier.classify("""

if OLD not in code:
    print("CLASSIFIER PATTERN NOT FOUND")
else:
    p.write_text(code.replace(OLD, NEW), encoding="utf-8")
    print("Structural validator gate inserted before classifier call.")
