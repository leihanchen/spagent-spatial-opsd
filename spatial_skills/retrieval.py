"""Deterministic teacher-only selection from public task/history text."""
from __future__ import annotations

import re

from .registry import SkillRegistry
from .schema import RetrievalContext, Selection


def select_skills(registry: SkillRegistry, context: RetrievalContext, purpose: str = "training") -> Selection:
    if purpose not in {"training", "validation"}:
        raise ValueError("purpose must be training or validation")
    available = set(context.available_capabilities)
    text = (context.task_text + "\n" + context.public_history_text).lower()
    excluded, scores = [], []
    for card in registry.list_cards():
        reason = None
        if card.kind != "static":
            reason = "dynamic_disabled"
        elif context.task_family not in card.task_families:
            reason = "task_family"
        elif not set(card.required_capabilities) <= available:
            reason = "missing_capabilities"
        elif card.validation_status == "rejected":
            reason = "rejected"
        elif card.review_status != "reviewed":
            reason = "not_reviewed"
        elif purpose == "training" and card.validation_status != "supported":
            reason = "not_behaviorally_supported"
        if reason:
            excluded.append((card.id, reason))
            continue
        score = sum(term == "*" or bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text))
                    for term in card.trigger_terms)
        if score:
            scores.append((card.id, score))
        else:
            excluded.append((card.id, "no_trigger"))
    ranked = sorted(scores, key=lambda item: (-item[1], item[0]))
    chosen = tuple(registry.get(item[0]) for item in ranked[:1])
    excluded.extend((ident, "lower_rank") for ident, _ in ranked[1:])
    return Selection(
        selected_ids=tuple(c.id for c in chosen), selected_versions=tuple(c.version for c in chosen),
        scores=tuple(sorted(scores)), excluded=tuple(sorted(excluded)), manifest_digest=registry.digest,
        purpose=purpose, contains_untested=any(c.validation_status == "untested" for c in chosen),
        reason="selected" if chosen else "no_eligible_match",
    )
