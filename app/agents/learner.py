"""Learner — thin re-export of the cognitive learning engine.

Kept as a separate module so the agent roster in the architecture doc
(orchestrator, classifier, enricher, drafter, approver, sender, learner)
maps 1:1 to files under app/agents/. The implementation lives in
app.cognitive.learning_engine.
"""
from app.cognitive.learning_engine import (
    classify_edit,
    compute_delta,
    evolve_drafter_prompt,
    on_edit,
    record_corrected_fact,
    summarise_recent_learning,
)

__all__ = [
    "classify_edit",
    "compute_delta",
    "evolve_drafter_prompt",
    "on_edit",
    "record_corrected_fact",
    "summarise_recent_learning",
]
