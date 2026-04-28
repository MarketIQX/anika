"""Classifier agent — 5-way categorization of incoming emails.

Uses gpt-4o-mini and structured output (ClassifierOutput), plus a
deterministic pre-LLM rule check for unambiguous recruitment / vendor
patterns that gpt-4o-mini was historically unreliable at routing.
"""
from __future__ import annotations

import json
import re

from agents import Agent, Runner

from app.agents.schemas import ClassifierOutput
from app.cognitive import reasoning_log
from app.config import get_settings
from app.tools import knowledge_tool


# --------------------------------------------------------------------------
# Pre-LLM deterministic patterns (Cluster 7f).
#
# WHY this exists: the prompt-only approach was unreliable on gpt-4o-mini
# for clear-cut recruitment emails. The model would recognize the
# recruitment intent in its own reasoning ("first-contact application for
# an internship") then still pick new_enquiry. Cluster 13 + 7f smoke tests
# both confirmed this.
#
# The patterns below are LOW-FALSE-POSITIVE: they only fire on phrases
# that are essentially impossible in a service-line enquiry. When ANY of
# these phrases appears in the subject or body, we classify deterministically
# without calling the LLM. This is faster, cheaper, more reliable, and
# auditable — every classification produced this way carries a reasoning
# string explaining which rule fired.
#
# The LLM is still called when the patterns don't match — for everything
# the rules can't decide on, the model still does the work.
# --------------------------------------------------------------------------


_RECRUITMENT_PATTERNS = [
    # Signal phrases — combinations that overwhelmingly indicate recruitment.
    re.compile(r"\barticleship\b", re.IGNORECASE),
    re.compile(r"\binternship\b", re.IGNORECASE),
    re.compile(r"please\s+find\s+(?:my|attached)\s+(?:cv|resume|profile)", re.IGNORECASE),
    re.compile(r"\b(?:cv|resume)\s+attached\b", re.IGNORECASE),
    re.compile(r"\bkindly\s+consider\s+my\s+(?:application|candidature|profile)", re.IGNORECASE),
    re.compile(r"\bi\s+(?:would\s+like\s+to|wish\s+to)\s+apply\b", re.IGNORECASE),
    re.compile(r"\b(?:looking|searching)\s+for\s+(?:an?\s+)?(?:opportunity|opening|vacancy|position|job)\b", re.IGNORECASE),
    re.compile(r"\bca\s+(?:inter|final|fresher)\b", re.IGNORECASE),
    re.compile(r"\b(?:experience|worked)\s+(?:at|with)\s+(?:tcs|infosys|wipro|deloitte|kpmg|pwc|ey|grant\s+thornton)", re.IGNORECASE),
    # Production gap surfaced by draft 44 (preethinjeevan97@gmail.com):
    # "Hello Sir, Is there any vacancies in your firm." Earlier "looking for
    # vacancy" pattern required a verb anchor that this phrasing skipped.
    # Also matches "any vacancy at your office", "any vacancies in your company".
    re.compile(r"\bany\s+vacanc(?:y|ies)\s+(?:in|at)\s+your\s+(?:firm|company|office)\b", re.IGNORECASE),
    # Direct-ask phrasings: "looking for a job in your firm",
    # "any positions at your firm", "role with your company".
    re.compile(r"\b(?:job|position|role)\s+(?:in|at|with)\s+your\s+(?:firm|company)\b", re.IGNORECASE),
    # Hiring-question phrasings paired with a CA-specific anchor:
    # "Are you hiring CA freshers?", "hiring articleship students",
    # "hiring CS interns" (CS anchor is enough). Anchor required so the
    # word "hiring" alone in unrelated contexts (payroll advice, etc.)
    # doesn't trigger.
    re.compile(r"\bhiring\b.*?\b(?:CA|CS|articleship|fresher)\b", re.IGNORECASE),
]


_VENDOR_PATTERNS = [
    # Sender pitching their product/service TO the firm.
    re.compile(r"\bschedule\s+a\s+(?:quick\s+)?(?:demo|call\s+to\s+show)", re.IGNORECASE),
    re.compile(r"\b(?:30|15|20)[-\s]minute\s+(?:demo|walkthrough|call)\b", re.IGNORECASE),
    re.compile(r"\bbook\s+a\s+(?:demo|call)\s+(?:to\s+show|with\s+me)", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:work|partner)\s+with\s+\d+\+?\s+(?:ca|chartered|firms)", re.IGNORECASE),
    re.compile(r"\bhelp\s+your\s+(?:firm|practice)\s+(?:grow|scale)", re.IGNORECASE),
    re.compile(r"\bwhite[\s-]label\b", re.IGNORECASE),
    re.compile(r"\bpartnership\s+opportunity\b", re.IGNORECASE),
    re.compile(r"\blead[\s-]?gen(?:eration)?\b", re.IGNORECASE),
]


def _pre_llm_classify(subject: str, body: str) -> tuple[str, str] | None:
    """Return (category, reasoning) if a deterministic pattern matches, else None.

    Only returns recruitment_enquiry or vendor_pitch — the two categories
    the LLM was unreliable at. Everything else falls through to the LLM.
    """
    text = f"{subject or ''}\n{body or ''}"
    for pat in _RECRUITMENT_PATTERNS:
        m = pat.search(text)
        if m:
            return (
                "recruitment_enquiry",
                f"Pre-LLM rule fired: matched recruitment pattern {pat.pattern!r} "
                f"(text: {m.group(0)!r}). Sender is asking for employment at the "
                f"firm, not for the firm's services.",
            )
    for pat in _VENDOR_PATTERNS:
        m = pat.search(text)
        if m:
            return (
                "vendor_pitch",
                f"Pre-LLM rule fired: matched vendor-pitch pattern {pat.pattern!r} "
                f"(text: {m.group(0)!r}). Sender is pitching their product/service "
                f"to the firm, not buying from the firm.",
            )
    return None


DEFAULT_INSTRUCTIONS = """You are Anika's Classifier. Categorize the incoming email into exactly one bucket.

CRITICAL: ASK YOURSELF "WHO IS ASKING WHAT FROM WHOM?"

The single most important question for every email is the direction of the
ask. Get this right and the bucket follows.

  - Sender asking the firm for paid professional SERVICES (tax filing,
    audit, ROC, NRI advisory, GST, etc.)             → enquiry track
  - Sender asking the firm for EMPLOYMENT
    (articleship, internship, job, position)        → recruitment_enquiry
  - Sender pitching THEIR product/service TO the firm
    (selling software, lead-gen, demos, partnerships)  → vendor_pitch

Polite framing ("respected sir, I would like to enquire about your firm")
does NOT change the underlying direction. A job applicant who writes
"I would like to enquire about an articleship opportunity" is still
asking for a JOB, not for the firm's services. Classify as
recruitment_enquiry.

DECISION RULES (apply in this priority order — first match wins):

1. SENSITIVE (highest priority — protects firm from liability)
   Keywords: "legal notice", "show cause notice", "tax demand", "scrutiny
   notice under 148", "section 148", "complaint against", "dispute with",
   "fraud investigation", "ED enquiry", "CAG audit", "MCA inspection",
   or any rupee value above 50 lakhs / 5,000,000.
   → category = sensitive

2. RECRUITMENT (overrides new_enquiry default)
   Triggers ANY of:
     - mentions of articleship / internship / vacancy / job / position
       / opening / opportunity to work AT the firm
     - "I am a CA Inter / CA Final / MBA / B.Com / fresher"
     - "experience at <company>" describing the SENDER's career history
     - CV / resume / "find attached my profile" / portfolio
     - "looking for opportunity", "would like to apply", "considering me",
       "kindly consider my application"
     - "respected sir/madam" + brief background + ask to be considered
   → category = recruitment_enquiry
   (Even if framed as "enquiry" — direction-of-ask is what matters.)

3. VENDOR PITCH (overrides new_enquiry default)
   Triggers ANY of:
     - "we offer", "our software", "our platform", "our services",
       "we help firms like yours" — sender is the seller
     - "schedule a quick demo", "book a call to show", "30-minute walkthrough"
     - "lead generation", "partnership opportunity", "white-label",
       "reseller", "affiliate program"
     - "we work with X CA firms", "we can help your firm grow"
     - Generic outreach from sales@, marketing@, growth@, partnerships@,
       business@ addresses pitching a product
   → category = vendor_pitch
   (Even if politely framed — sender is selling TO the firm, not buying
   FROM it.)

4. EXISTING CLIENT
   Threaded replies (subject "Re:" / "Fwd:") OR sender clearly references
   a prior engagement / past correspondence with the firm.
   → category = existing_client

5. AUTOMATED
   Calendar invites, delivery bounces, no-reply newsletters, billing
   alerts, OTPs, statement notifications.
   → category = automated

6. SPAM
   Mass promotion, phishing, lottery / prize claims, obvious marketing.
   → category = spam

7. NEW ENQUIRY (the FALLTHROUGH bucket — only after rules 1-6 fail)
   First-contact from someone asking the firm to provide a paid
   professional SERVICE. Sender is the buyer; firm is the seller.
   Examples: "I am an NRI and need help with my ITR", "We are a US
   company looking to set up an Indian subsidiary", "Need GST
   registration for my new business".
   This is the ONLY bucket Anika acts on by drafting a reply.
   → category = new_enquiry

8. OTHER — anything that doesn't fit any rule cleanly.

CONFIDENCE & REASONING:
- Use `confidence` in [0, 1]. < 0.6 confidence must still commit to a
  bucket, but the reasoning should call out the ambiguity.
- Reasoning is one or two sentences, chain-of-thought style. State the
  direction-of-ask explicitly when classifying recruitment_enquiry or
  vendor_pitch — e.g. "Sender is asking for an articleship at the firm,
  so recruitment_enquiry overrides new_enquiry."

Output MUST conform exactly to the ClassifierOutput schema.
"""


def _instructions() -> tuple[str, int | None]:
    p = knowledge_tool.get_active_prompt("classifier")
    if p:
        return p["prompt_text"], int(p["version"])
    return DEFAULT_INSTRUCTIONS, None


def _build_agent() -> tuple[Agent, int | None]:
    text, version = _instructions()
    agent = Agent(
        name="Classifier",
        instructions=text,
        model=get_settings().openai_model_classifier,
        output_type=ClassifierOutput,
    )
    return agent, version


async def classify(
    *,
    email_id: int,
    from_email: str,
    from_name: str,
    subject: str,
    body_plain: str,
    is_reply_in_thread: bool,
) -> ClassifierOutput:
    """Classify a single email and persist the classification + reasoning log.

    Cluster 7f flow:
      1. Run deterministic pre-LLM patterns first. If they match a recruitment
         or vendor signal, short-circuit and persist that classification —
         no LLM call needed.
      2. Otherwise, hand off to the LLM agent as before.

    The pre-LLM path still produces a reasoning_log row (status='ok',
    model='pre_llm_rule') so the audit trail is complete and the dashboard
    can show why a given email was classified that way.
    """
    payload = {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "is_reply_in_thread": is_reply_in_thread,
        "body": body_plain[:6000],  # cap to keep tokens predictable
    }

    # ---- (1) Deterministic pre-LLM rules ----
    pre = _pre_llm_classify(subject, body_plain)
    if pre is not None:
        rule_category, rule_reasoning = pre
        with reasoning_log.timed(
            agent_name="classifier",
            input_obj=payload,
            email_id=email_id,
            model="pre_llm_rule",
            prompt_version=None,
        ) as ctx:
            output = ClassifierOutput(
                category=rule_category,
                confidence=0.99,  # rule fired — high confidence by construction
                reasoning=rule_reasoning,
            )
            ctx["output"] = output.model_dump()
            ctx["reasoning"] = output.reasoning

        from app.db import execute

        execute(
            """
            INSERT INTO classifications
              (email_id, category, confidence, reasoning, model, prompt_version)
            VALUES (?,?,?,?,?,?)
            """,
            (email_id, output.category, output.confidence, output.reasoning,
             "pre_llm_rule", None),
        )
        return output

    # ---- (2) LLM agent for everything the rules can't decide ----
    agent, version = _build_agent()
    user_input = (
        "Classify this email. Return JSON matching ClassifierOutput.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    with reasoning_log.timed(
        agent_name="classifier",
        input_obj=payload,
        email_id=email_id,
        model=get_settings().openai_model_classifier,
        prompt_version=version,
    ) as ctx:
        result = await Runner.run(agent, input=user_input, max_turns=2)
        output: ClassifierOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Persist the classification.
    from app.db import execute

    execute(
        """
        INSERT INTO classifications
          (email_id, category, confidence, reasoning, model, prompt_version)
        VALUES (?,?,?,?,?,?)
        """,
        (
            email_id,
            output.category,
            output.confidence,
            output.reasoning,
            get_settings().openai_model_classifier,
            version,
        ),
    )
    return output
