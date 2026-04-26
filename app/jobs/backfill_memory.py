"""Day-1 one-shot backfill.

Seeds:
  - firm_knowledge : identity, office, phone, signature_block, positioning,
                     partner routing, team, track_record, FAQs.
  - rules          : tone dos/don'ts, sensitive topic blacklist, rupee
                     threshold, FAQs.
  - agent_prompts  : initial active prompt for classifier/enricher/drafter
                     (sourced from the agents' DEFAULT_INSTRUCTIONS constants).
  - memory         : firm_snippet rows (positioning lines) + a couple of
                     seed exemplar replies keyed by service line.

Idempotent: safe to run on every boot. We use INSERT OR IGNORE and check
"is there an active prompt for this agent?" before seeding prompts.
"""
from __future__ import annotations

import logging

from app.agents.classifier import DEFAULT_INSTRUCTIONS as CLASSIFIER_PROMPT
from app.agents.drafter import DEFAULT_INSTRUCTIONS as DRAFTER_PROMPT
from app.agents.enricher import DEFAULT_INSTRUCTIONS as ENRICHER_PROMPT
from app.db import execute, fetch_all, fetch_one
from app.tools import memory_tool

logger = logging.getLogger(__name__)


# ---- Firm knowledge ----

FIRM_FACTS: list[tuple[str, str, str]] = [
    # (key, value, category)
    ("firm_name", "Balakrishna and Co., Chartered Accountants", "identity"),
    ("founded_year", "1988", "identity"),
    ("years_operating", "37+", "identity"),
    ("office_address",
     "#24, 3rd Floor, Above State Bank of India, 10th Cross, Wilson Garden, Bangalore 560 027, India",
     "identity"),
    ("phone_prakasha", "+91 86182 59712", "identity"),
    ("phone_prasad", "+91 98457 21255", "identity"),
    ("website", "www.balakrishnaandco.com", "identity"),
    ("blog", "www.simplifiedlaws.com", "identity"),
    ("related_entity", "Balakrishna Consulting LLP", "identity"),
    ("msi_membership", "MSI Global Alliance member (Bangalore) — 250+ member firms across 105 countries", "identity"),
    ("positioning_statement",
     "Balakrishna & Co is a 37-year-old Chartered Accountancy firm specializing in India "
     "entry strategies for foreign companies, international taxation, NRI services, and "
     "transfer pricing. 150+ foreign companies from 26 countries, 1,500 NRI clients across 30 countries.",
     "positioning"),
    ("track_record",
     "150+ companies served from 26 different countries; 1,500 NRI clients across 30 countries; "
     "30+ years of combined partner experience; MSI Global Alliance member; NABARD empanelled for "
     "District Co-operative Bank audits.",
     "positioning"),
    ("team_size", "6 CAs, 1 CS, 1 CMA, 80 total staff", "team"),
    ("partner_prakasha",
     "CA S. V. Prakasha — FCA, DISA (ICAI). NRI taxation, Income Tax assessments, Company Secretarial, "
     "FEMA, ROC filings, GST, Indirect Tax, Corporate Governance, FCRA applications.",
     "team"),
    ("partner_prasad",
     "CA B. E. Kumar Prasad — FCA, 28+ years. International Taxation, India Entry, Transfer Pricing, "
     "NRI Taxation, DTAA, FEMA, M&A, Company Law. Insolvency Professional, Registered Valuer.",
     "team"),
    ("routing.nri_tax", "CA Kumar Prasad", "routing"),
    ("routing.foreign_subsidiary", "CA Kumar Prasad", "routing"),
    ("routing.transfer_pricing", "CA Kumar Prasad", "routing"),
    ("routing.virtual_cfo", "CA Pavan Sharma", "routing"),
    ("routing.gst_indirect", "CA Prakasha", "routing"),
    ("routing.secretarial_roc", "CA Prakasha", "routing"),
    ("routing.audit", "CA Ankush Shetty", "routing"),
    ("routing.other", "CA Prakasha", "routing"),
    # signature_block is NOT seeded here — it lives in app/config/firm_identity.py
    # as a locked code constant. See knowledge_tool.get_signature_block().
    ("disclaimer_footer",
     "This communication is for general guidance only and does not constitute legal, tax, or "
     "financial advice. Specific situations require detailed consultation.",
     "compliance"),
]


# ---- Rules ----

TONE_DOS = [
    "Warm but professional — relationship-driven firm, not transactional.",
    "Use Indian English spelling (realise, organisation, favour).",
    "First contact uses formal salutation: 'Dear Mr./Ms. [Name],'.",
    "End every first reply with a clear next step (call, email, document request).",
    "For foreign companies, emphasize 'no travel required' and 'serving clients from 26 countries'.",
    "For NRIs, emphasize '37 years resolving every complicated NRI transaction' and '1,500 NRI clients across 30 countries'.",
    "Sign off with 'Warm regards' or 'Best regards'.",
    "Match the enquiry's language (Hindi if they wrote in Hindi).",
]

TONE_DONTS = [
    "Never start with 'I hope this email finds you well' — too American.",
    "Never quote specific fees in a first reply — always invite for consultation.",
    "Never commit to timelines without Prakash sir's approval.",
    "Never give tax, legal, or advisory opinions in writing — offer a call instead.",
    "Never mention competitors by name.",
    "Never discuss other clients' matters.",
    "Never say 'we guarantee' anything regulatory.",
]

BLACKLIST_PATTERNS = [
    "legal notice",
    "show cause notice",
    "tax demand",
    "tax demand notice",
    "complaint against",
    "fraud investigation",
    "scrutiny notice under 148",
    "section 148",
    "cag audit",
    "mca inspection",
    "ed enquiry",
    "enforcement directorate",
    "dispute with your firm",
    "refund of fees",
]

RUPEE_THRESHOLD = 5_000_000  # Rs 50 lakhs — from firm profile section 12

FAQS = [
    (
        "fee",  # pattern (any enquiry mentioning fee/cost/pricing/rate)
        "Our fees depend on the complexity of your specific situation. Let us have a brief "
        "15-20 minute call to understand your requirements, and I will share a clear estimate "
        "right after. I am happy to set it up at your convenience — mornings (IST) usually "
        "work best for me. What works for you?",
    ),
    (
        "panel",
        "Yes, our firm is registered with ICAI and we are empaneled with NABARD for District "
        "Co-operative Bank audits. For RBI/FEMA work we have handled 150+ foreign company "
        "entries over 37 years. Happy to share specific credentials relevant to your requirement.",
    ),
    (
        "timeline incorporation",
        "Private Limited Company incorporation typically takes 10-15 working days once all "
        "documents are ready. For foreign-owned subsidiaries the timeline varies slightly due "
        "to apostille and RBI filings. The good news is you do not need to travel to India — "
        "we handle everything remotely. Happy to walk you through the timeline on a call.",
    ),
    (
        "end to end after incorporation",
        "Yes, absolutely. Beyond incorporation, we handle ongoing compliance: ROC filings, "
        "GST, TDS, Income Tax, payroll, and Virtual CFO support. Most of our foreign clients "
        "prefer this end-to-end arrangement so they have a single point of contact in India. "
        "Let us have a brief call to scope what you need.",
    ),
]


# ---- Firm positioning snippets (memory) ----

FIRM_SNIPPETS = [
    ("Track record for foreign companies",
     "We have served 150+ foreign companies from 26 different countries across IT, manufacturing, "
     "garments, pharmaceuticals, and fintech. Clients from USA, UK, France, Holland, Singapore, "
     "Japan, UAE, Germany and more. You do not need to travel to India — we handle incorporation, "
     "RBI filings, and ongoing compliance remotely."),
    ("Track record for NRIs",
     "1,500 NRI clients across 30 countries have relied on us for ITR filings, Schedule FA "
     "disclosures, FEMA compliance, NRI property transactions, and TDS / Form 13 applications. "
     "37 years of experience resolving every complicated NRI transaction — no surprise is new to us."),
    ("MSI Global Alliance membership",
     "We are a member of MSI Global Alliance, a premier association of 250+ independent law "
     "and accounting firms across 105 countries. This gives our international clients access "
     "to coordinated cross-border advisory when they need it."),
    ("Partner expertise — Kumar Prasad",
     "CA Kumar Prasad has 28+ years handling International Taxation, India Entry, Transfer "
     "Pricing, DTAA, FEMA, and M&A. He has authored 200+ original legal articles on "
     "simplifiedlaws.com. He is also an Insolvency Professional and a Registered Valuer."),
    ("Partner expertise — Prakasha",
     "CA S V Prakasha specializes in NRI taxation, Income Tax assessments, Company Secretarial, "
     "FEMA, ROC filings, GST, Indirect Tax, Corporate Governance, and FCRA applications. He is "
     "also a Qualified Registered Valuer for Securities or Financial Assets."),
]


# ---- Service-line exemplar replies ----
# Seed examples to give the Drafter few-shot anchors for tone + structure on
# day one. They'll be superseded by real approved drafts after a few sends.

EXEMPLARS: list[dict[str, str]] = [
    {
        "service_line": "foreign_subsidiary",
        "subject": "Setting up India subsidiary — happy to scope on a short call",
        "content": (
            "Dear Mr. Smith,\n\n"
            "Thank you for reaching out about setting up an Indian subsidiary for your US "
            "parent company. Over the last 37 years we have helped 150+ foreign companies "
            "from 26 countries with their India entry, so this is familiar territory.\n\n"
            "To scope the right structure (WOS vs LO vs branch) we typically need a 20-minute "
            "call to understand your India plans, team size, and time horizon. You do not "
            "need to travel — we handle the entire process remotely, including RBI filings "
            "and post-incorporation compliance.\n\n"
            "Would this Thursday or Friday morning IST work for you?\n\n"
            "Warm regards,\n\n"
            "S V Prakasha"
        ),
    },
    {
        "service_line": "nri_tax",
        "subject": "NRI ITR for last year — happy to guide",
        "content": (
            "Dear Mr. Kumar,\n\n"
            "Thank you for writing in regarding your NRI income tax return. With 1,500 NRI "
            "clients across 30 countries over 37 years, filings of this nature are something "
            "we handle every week.\n\n"
            "To proceed accurately, could you share your Form 26AS for the relevant financial "
            "year? Once we have that, a 15-minute call should be enough to agree the approach "
            "— especially if Schedule FA (foreign assets) applies to your situation.\n\n"
            "Mornings IST usually work best for me. What would suit you?\n\n"
            "Warm regards,\n\n"
            "S V Prakasha"
        ),
    },
    {
        "service_line": "transfer_pricing",
        "subject": "Transfer pricing study — happy to scope",
        "content": (
            "Dear Ms. Iyer,\n\n"
            "Thank you for your note about transfer pricing documentation. We regularly prepare "
            "TP studies and Form 3CEB reports for Indian subsidiaries of foreign parents and "
            "vice versa.\n\n"
            "If you already have a prior TP study or any related-party transaction summary, "
            "it would help to see it before our call. A 20-minute conversation should be enough "
            "to confirm scope and effort.\n\n"
            "Would this Friday afternoon IST suit you?\n\n"
            "Warm regards,\n\n"
            "S V Prakasha"
        ),
    },
    {
        "service_line": "virtual_cfo",
        "subject": "Virtual CFO for your startup — happy to scope",
        "content": (
            "Dear Priya,\n\n"
            "Thank you for reaching out about Virtual CFO support. We work with several "
            "early-stage and growth-stage startups on fundraising readiness, monthly MIS, and "
            "compliance hygiene.\n\n"
            "A 30-minute discovery call would help us understand your stage (pre-revenue / "
            "scaling / pre-funding), your current books, and what you would want a part-time "
            "CFO to own. After that I can come back with a clear scope.\n\n"
            "Would next Tuesday or Wednesday morning IST work?\n\n"
            "Warm regards,\n\n"
            "S V Prakasha"
        ),
    },
]


# ---- Runner ----


def _needs_prompt_seed(agent: str) -> bool:
    row = fetch_one(
        "SELECT 1 AS n FROM agent_prompts WHERE agent_name=? AND is_active=1",
        (agent,),
    )
    return row is None


def _seed_agent_prompts() -> None:
    if _needs_prompt_seed("classifier"):
        execute(
            "INSERT INTO agent_prompts(agent_name,version,prompt_text,change_note,is_active) "
            "VALUES('classifier',1,?,'initial seed',1)",
            (CLASSIFIER_PROMPT,),
        )
    if _needs_prompt_seed("enricher"):
        execute(
            "INSERT INTO agent_prompts(agent_name,version,prompt_text,change_note,is_active) "
            "VALUES('enricher',1,?,'initial seed',1)",
            (ENRICHER_PROMPT,),
        )
    if _needs_prompt_seed("drafter"):
        execute(
            "INSERT INTO agent_prompts(agent_name,version,prompt_text,change_note,is_active) "
            "VALUES('drafter',1,?,'initial seed',1)",
            (DRAFTER_PROMPT,),
        )


def _seed_firm_knowledge() -> None:
    for key, value, cat in FIRM_FACTS:
        execute(
            """
            INSERT INTO firm_knowledge(key, value, category) VALUES(?,?,?)
            ON CONFLICT(key) DO UPDATE SET
              value=excluded.value,
              category=excluded.category,
              updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
            """,
            (key, value, cat),
        )


def _seed_rules() -> None:
    # Tone rules
    existing = {(r["rule_type"], r["text_value"]) for r in fetch_all(
        "SELECT rule_type, text_value FROM rules"
    )}
    for rule in TONE_DOS:
        if ("tone_do", rule) not in existing:
            execute(
                "INSERT INTO rules(rule_type, text_value, is_active) VALUES('tone_do', ?, 1)",
                (rule,),
            )
    for rule in TONE_DONTS:
        if ("tone_dont", rule) not in existing:
            execute(
                "INSERT INTO rules(rule_type, text_value, is_active) VALUES('tone_dont', ?, 1)",
                (rule,),
            )
    # Blacklist patterns
    bl_existing = {r["pattern"] for r in fetch_all(
        "SELECT pattern FROM rules WHERE rule_type='blacklist_topic'"
    )}
    for p in BLACKLIST_PATTERNS:
        if p not in bl_existing:
            execute(
                "INSERT INTO rules(rule_type, pattern, is_active) VALUES('blacklist_topic', ?, 1)",
                (p,),
            )
    # Rupee threshold (exactly one active row)
    if not fetch_one(
        "SELECT 1 FROM rules WHERE rule_type='rupee_threshold' AND is_active=1"
    ):
        execute(
            "INSERT INTO rules(rule_type, threshold_value, is_active) VALUES('rupee_threshold', ?, 1)",
            (float(RUPEE_THRESHOLD),),
        )
    # FAQs
    faq_existing = {r["pattern"] for r in fetch_all(
        "SELECT pattern FROM rules WHERE rule_type='faq'"
    )}
    for pattern, answer in FAQS:
        if pattern not in faq_existing:
            execute(
                "INSERT INTO rules(rule_type, pattern, text_value, is_active) "
                "VALUES('faq', ?, ?, 1)",
                (pattern, answer),
            )


def _seed_memory_snippets() -> None:
    """Seed firm_snippet + exemplar memories. Skipped if we already have them."""
    from app.db import fetch_one as _fo

    # Firm snippets
    for subject, content in FIRM_SNIPPETS:
        if _fo(
            "SELECT 1 FROM memory WHERE kind='firm_snippet' AND subject=?",
            (subject,),
        ):
            continue
        try:
            memory_tool.store_memory(
                kind="firm_snippet",
                subject=subject,
                content=content,
                tags=["positioning"],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to seed firm_snippet '%s': %s", subject, e)

    # Exemplars
    for ex in EXEMPLARS:
        if _fo(
            "SELECT 1 FROM memory WHERE kind='exemplar' AND service_line=? AND subject=?",
            (ex["service_line"], ex["subject"]),
        ):
            continue
        try:
            memory_tool.store_memory(
                kind="exemplar",
                service_line=ex["service_line"],
                subject=ex["subject"],
                content=ex["content"],
                tags=["seed", ex["service_line"]],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to seed exemplar '%s': %s", ex["subject"], e)


def run(seed_memory_vectors: bool = True) -> dict[str, int]:
    """Run all seed steps and return counts."""
    _seed_firm_knowledge()
    _seed_rules()
    _seed_agent_prompts()
    if seed_memory_vectors:
        _seed_memory_snippets()

    counts = {
        "firm_knowledge": int(fetch_one("SELECT COUNT(*) n FROM firm_knowledge")["n"]),
        "rules": int(fetch_one("SELECT COUNT(*) n FROM rules")["n"]),
        "agent_prompts": int(fetch_one("SELECT COUNT(*) n FROM agent_prompts")["n"]),
        "memory": int(fetch_one("SELECT COUNT(*) n FROM memory")["n"]),
    }
    logger.info("Backfill complete: %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db import init_db

    init_db()
    print(run())
