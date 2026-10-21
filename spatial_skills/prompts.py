"""Bounded procedural text and nonmutating teacher-only message views."""
from __future__ import annotations

from copy import deepcopy
from typing import Sequence

from .schema import SkillCard


def render_skill_block(cards: Sequence[SkillCard], max_chars: int = 4000) -> str:
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")
    if not cards:
        return ""
    rendered = []
    for card in cards:
        if not isinstance(card, SkillCard):
            raise ValueError("render requires SkillCard records")
        body = card.teacher_text()
        if len(body) > 2000:
            raise ValueError("rendered card exceeds 2000 characters")
        rendered.append(body)
    block = "[Teacher-only procedural guidance]\n\n" + "\n\n---\n\n".join(rendered)
    block += "\n\n[End teacher-only procedural guidance]"
    if len(block) > max_chars:
        raise ValueError("teacher skill block exceeds max_chars; no card was truncated")
    return block


def build_teacher_view(student_messages: list[dict], skill_block: str) -> list[dict]:
    if not isinstance(student_messages, list) or any(
        not isinstance(m, dict) or not isinstance(m.get("role"), str) for m in student_messages
    ):
        raise ValueError("student_messages must be a list of message dictionaries with roles")
    if not isinstance(skill_block, str):
        raise ValueError("skill_block must be text")
    result = deepcopy(student_messages)
    if not skill_block:
        return result
    system = next((m for m in result if m["role"] == "system"), None)
    if system is None:
        result.insert(0, {"role": "system", "content": skill_block})
    elif isinstance(system.get("content"), str):
        system["content"] += "\n\n" + skill_block
    elif isinstance(system.get("content"), list):
        system["content"].append({"type": "text", "text": skill_block})
    else:
        raise ValueError("system content must be text or a content array")
    return result
