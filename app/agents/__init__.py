"""Agents — Anika's six-agent architecture.

orchestrator  : top-level control flow (code, with hard safety gates)
classifier    : gpt-4o-mini, 5-way categorization
enricher      : gpt-4o-mini, sender intelligence + service-line routing
drafter       : gpt-4o, writes the reply in Prakash sir's voice
approver      : handles dashboard decisions (approve / edit / reject)
sender        : executes Gmail send with guardrails
learner       : edit classification (lives in cognitive.learning_engine)
"""
