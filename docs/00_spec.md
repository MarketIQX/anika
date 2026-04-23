# Anika — Business & Functional Specification

**Version:** 1.0
**Owner:** MarketIQX (AK Sharma)
**Client:** Balakrishna & Co (CA S.V. Prakasha)
**Mailbox:** `prakasha@balakrishnaandco.com`
**Last updated:** April 21, 2026

---

## 1. Problem statement

CA S.V. Prakasha receives ~80–120 new enquiries per month at `prakasha@balakrishnaandco.com` from NRIs, foreign companies, and startups across four service lines. Each first-reply currently takes 12–18 minutes of partner time drafting manually. Replies are often delayed by hours or days because Prakash sir handles them between client work — costing Balakrishna & Co. mandates that competitors win by replying faster.

Across a typical month, this is **20–30 hours of senior partner time spent on work that can be delegated without loss of quality, if the delegation preserves his writing voice and requires only his final approval.**

## 2. Solution, in one sentence

Anika is a self-evolving agentic AI system that reads every new enquiry arriving at `prakasha@balakrishnaandco.com`, drafts a reply in Prakash sir's writing style, and presents it on his WhatsApp for one-tap approval. Nothing sends without his explicit tap.

## 3. Functional scope — what Anika does

1. Monitors `prakasha@balakrishnaandco.com` inbox continuously via Gmail Push.
2. Classifies every incoming email into one of five categories. Acts only on `new_enquiry`.
3. Enriches the enquiry with sender intelligence (identity, country, service fit, urgency, past history).
4. Drafts a reply in Prakash sir's voice, matched to one of four service lines.
5. Sends a WhatsApp approval card to his phone with sender summary + draft + three actions (Send / Edit / Reject).
6. On approval, sends the reply via Gmail API from `prakasha@balakrishnaandco.com`. Reply appears in his Sent folder with his signature.
7. Logs every action with full reasoning chain for audit.
8. Learns from every edit. Self-updates its drafting prompt in real-time after each approval cycle.

## 4. Non-goals — what Anika explicitly does NOT do

- Does not auto-send. Ever. No category, no condition, no time of day.
- Does not reply to existing email threads (only first-contact enquiries).
- Does not handle complaints, legal notices, tax demands, or enquiries above configurable rupee thresholds.
- Does not give tax, legal, or advisory opinions. Acknowledges, confirms fit, asks one clarifier, proposes next step.
- Does not replace the firm's CRM or mailbox.
- Does not share data with any LLM outside OpenAI.

## 5. Service lines (Drafter's decision matrix)

| Service line | Typical enquiry signal | Default next step proposed |
|---|---|---|
| NRI taxation | "NRI", "OCI", "foreign income", "property sale in India", "repatriation", "ITR for last year" | Request Form 26AS + offer 15-min call |
| Foreign subsidiary incorporation | "set up Indian entity", "open subsidiary in India", "foreign parent" | Offer 20-min strategy call |
| Transfer pricing | "transfer pricing", "TP study", "arm's length", "related party transactions" | Request TP documentation + offer call |
| Virtual CFO / startup | "fundraising", "valuation", "startup", "part-time CFO", "virtual CFO" | Offer 30-min discovery call |

## 6. User journey

**The 15-second loop (Prakash sir's perspective):**
1. Enquiry arrives in Gmail (he does not need to see it first)
2. WhatsApp notification on his phone — sender summary (2 lines) + draft reply
3. He reads draft in ~10 seconds
4. Taps **✓ Send** — reply goes out. Done.
5. OR taps **✎ Edit** — types instruction in natural language → new draft generated → approves
6. OR taps **✗ Reject** — enquiry marked for his direct handling in Gmail

**The silent loop (Anika's perspective):**
1. Listens to Gmail Pub/Sub webhook
2. Routes through Classifier → Enricher → Memory retrieval → Drafter → Approver
3. Waits for WhatsApp decision
4. On approval, Sender agent fires Gmail API
5. Writes reasoning log + updates Memory core
6. Learning engine detects edit deltas → updates Drafter prompt in real-time

## 7. Success criteria (Month 1 targets)

| Metric | Target |
|---|---|
| Avg response time to new enquiry | <2 hours (from 18-48 hrs) |
| Partner time per reply | <30 seconds (from 12-18 min) |
| Classifier accuracy | ≥95% |
| Drafts approved without edit | ≥60% by Month 1 end, ≥80% by Month 3 |
| False sends (sent without approval) | 0 — architecturally impossible |
| System uptime | ≥99% |

## 8. Commercial

- **One-time build fee:** ₹15,000 (waived if Month 1 continues to Month 2)
- **Monthly service fee:** ₹3,500 (covers all MarketIQX infrastructure and operations)
- **OpenAI API costs:** Absorbed by MarketIQX under current arrangement (~₹800–1,200/month)
- **Commercial model:** Month-to-month, cancellable with 30 days notice
