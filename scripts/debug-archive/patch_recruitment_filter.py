from pathlib import Path

# ============================================================
# Patch 1 — schemas.py: add new categories to Literal
# ============================================================
p1 = Path("app/agents/schemas.py")
code1 = p1.read_text(encoding="utf-8")

OLD1 = '''Category = Literal[
    "new_enquiry",
    "existing_client",
    "sensitive",
    "automated",
    "spam",
    "other",
]'''

NEW1 = '''Category = Literal[
    "new_enquiry",
    "existing_client",
    "sensitive",
    "recruitment_enquiry",
    "vendor_pitch",
    "automated",
    "spam",
    "other",
]'''

if OLD1 in code1:
    code1 = code1.replace(OLD1, NEW1)
    p1.write_text(code1, encoding="utf-8")
    print("Patched schemas.py — added recruitment_enquiry + vendor_pitch")
else:
    print("schemas.py OLD not found")


# ============================================================
# Patch 2 — classifier.py: extend INSTRUCTIONS
# ============================================================
p2 = Path("app/agents/classifier.py")
code2 = p2.read_text(encoding="utf-8")

OLD2 = '''Buckets:
- new_enquiry     : a first-contact from someone asking about the firm's services.
                    Not a reply; the sender is not an existing client. This is the
                    ONLY bucket Anika acts on by drafting a reply.
- existing_client : an ongoing thread or a recognized client email asking about
                    their active engagement. Must be handled personally.
- sensitive       : legal notices, tax demands, complaints, disputes, scrutiny
                    under 148, regulatory audits, or any enquiry mentioning a
                    rupee value above 50 lakhs. Escalate to partner; no draft.
- automated       : calendar invites, delivery bounces, no-reply newsletters,
                    billing alerts from services.
- spam            : promotions, phishing, obvious marketing blasts.
- other           : anything that doesn't fit cleanly.'''

NEW2 = '''Buckets:
- new_enquiry         : a first-contact from someone asking about the firm's
                        SERVICES (tax, audit, ROC, NRI, etc.). Not a reply; the
                        sender is not an existing client. This is the ONLY bucket
                        Anika acts on by drafting a reply.
- existing_client     : an ongoing thread or a recognized client email asking
                        about their active engagement. Must be handled personally.
- sensitive           : legal notices, tax demands, complaints, disputes,
                        scrutiny under 148, regulatory audits, or any enquiry
                        mentioning a rupee value above 50 lakhs. Escalate to
                        partner; no draft.
- recruitment_enquiry : someone seeking a JOB, internship, articleship, or any
                        kind of employment at the firm. Mentions of "vacancy",
                        "career", "looking for opportunity", "MBA", "experience
                        in TCS/Infosys", "fresher", CV/resume references.
                        Anika does NOT draft replies to these.
- vendor_pitch        : a sales pitch FROM another company offering services
                        TO the firm — software demos, marketing tools, lead-gen
                        services, partnership proposals where the sender is the
                        seller. Anika does NOT draft replies.
- automated           : calendar invites, delivery bounces, no-reply newsletters,
                        billing alerts from services.
- spam                : promotions, phishing, obvious marketing blasts.
- other               : anything that doesn't fit cleanly.'''

if OLD2 in code2:
    code2 = code2.replace(OLD2, NEW2)
    p2.write_text(code2, encoding="utf-8")
    print("Patched classifier.py — extended INSTRUCTIONS with new buckets")
else:
    print("classifier.py OLD not found")


# ============================================================
# Patch 3 — orchestrator.py: better logging for auto-skip categories
# ============================================================
# The existing branch already auto-skips anything not in (new_enquiry, existing_client).
# We just improve the reasoning_text so logs distinguish recruitment/vendor from spam/other.

p3 = Path("app/agents/orchestrator.py")
code3 = p3.read_text(encoding="utf-8")

OLD3 = '''    if category not in ("new_enquiry", "existing_client"):
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "skip_non_enquiry", "category": category},
            reasoning_text=f"category={category}, Anika does not draft for non-enquiries",
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {"email_id": email_id, "action": "skip_non_enquiry", "category": category}'''

NEW3 = '''    if category not in ("new_enquiry", "existing_client"):
        # Specific reason text per category for clarity in audit logs
        reason_map = {
            "recruitment_enquiry": "job/career enquiry — not a client services request",
            "vendor_pitch": "vendor sales pitch — not a client services request",
            "spam": "classified as spam",
            "automated": "automated/system message",
            "sensitive": "sensitive content — handle personally",
            "other": "does not fit drafting criteria",
        }
        skip_reason = reason_map.get(category, "non-enquiry")
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "skip_non_enquiry", "category": category, "reason": skip_reason},
            reasoning_text=f"category={category}: {skip_reason}; Anika does not draft",
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {"email_id": email_id, "action": "skip_non_enquiry", "category": category, "reason": skip_reason}'''

if OLD3 in code3:
    code3 = code3.replace(OLD3, NEW3)
    p3.write_text(code3, encoding="utf-8")
    print("Patched orchestrator.py — added specific reason mapping")
else:
    print("orchestrator.py OLD not found")


# ============================================================
# Verify imports
# ============================================================
import sys
for mod in list(sys.modules):
    if "agents" in mod or "schemas" in mod or "classifier" in mod or "orchestrator" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import schemas, classifier, orchestrator
    print()
    print("All three modules import cleanly")
    # Verify the new categories
    import inspect
    src = inspect.getsource(schemas)
    if "recruitment_enquiry" in src and "vendor_pitch" in src:
        print("Schemas now includes recruitment_enquiry + vendor_pitch")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
