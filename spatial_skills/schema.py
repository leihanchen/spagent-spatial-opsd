"""Immutable skill records and strict validation independent of ML frameworks."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import re

FAMILIES = frozenset({"spatialact_repair", "sceneactbench_layout"})
IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*\Z")


def text(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty, trimmed string")
    return value


def strings(value, name, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{name} must be a{' nonempty' if nonempty else ''} list")
    result = tuple(text(v, name) for v in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    return result


@dataclass(frozen=True)
class SkillCard:
    id: str
    version: int
    kind: str
    name: str
    when: str
    task_families: tuple[str, ...]
    trigger_terms: tuple[str, ...]
    preconditions: tuple[str, ...]
    procedure: tuple[str, ...]
    verification: tuple[str, ...]
    failure_lessons: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    source_refs: tuple[str, ...]
    adaptation_notes: str
    parent_skill_id: str | None
    provenance_episode_ids: tuple[str, ...]
    review_status: str
    validation_status: str

    def to_dict(self):
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}

    def teacher_text(self):
        """Only procedural fields are model-visible; audit metadata stays outside."""
        sections = [self.name, f"Applies when: {self.when}"]
        for heading, values in [("Prerequisites", self.preconditions), ("Procedure", self.procedure),
                                ("Verification", self.verification), ("Failure lessons", self.failure_lessons)]:
            if values:
                sections.append(heading + ":\n" + "\n".join(f"- {v}" for v in values))
        return "\n\n".join(sections)


def parse_card(data: dict) -> SkillCard:
    expected = {f.name for f in fields(SkillCard)}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("skill fields must exactly match the SkillCard schema")
    values = dict(data)
    for key in ["id", "name", "when", "adaptation_notes"]:
        text(values[key], key)
    if not IDENTIFIER.fullmatch(values["id"]):
        raise ValueError("id must be snake_case")
    if type(values["version"]) is not int or values["version"] < 1:
        raise ValueError("version must be a positive integer")
    for key, allowed in [("kind", {"static", "dynamic"}), ("review_status", {"draft", "reviewed"}),
                         ("validation_status", {"untested", "supported", "rejected"})]:
        if not isinstance(values[key], str) or values[key] not in allowed:
            raise ValueError(f"invalid {key}")
    nonempty = {"task_families", "trigger_terms", "procedure", "verification", "source_refs"}
    for key in ["task_families", "trigger_terms", "preconditions", "procedure", "verification",
                "failure_lessons", "required_capabilities", "source_refs", "provenance_episode_ids"]:
        values[key] = strings(values[key], key, key in nonempty)
    if not set(values["task_families"]) <= FAMILIES:
        raise ValueError("unknown task family")
    if any(v != v.lower() for v in values["trigger_terms"]):
        raise ValueError("trigger_terms must be lowercase")
    parent = values["parent_skill_id"]
    if parent is not None and (not isinstance(parent, str) or not IDENTIFIER.fullmatch(parent)):
        raise ValueError("invalid parent_skill_id")
    if parent == values["id"]:
        raise ValueError("skill cannot be its own parent")
    if values["kind"] == "dynamic" and not values["provenance_episode_ids"]:
        raise ValueError("dynamic skills require training episode provenance")
    if values["validation_status"] == "supported" and values["review_status"] != "reviewed":
        raise ValueError("supported skills must be reviewed")
    result = SkillCard(**values)
    if len(result.teacher_text()) > 2000:
        raise ValueError("rendered card exceeds 2000 characters")
    return result


@dataclass(frozen=True)
class RetrievalContext:
    task_family: str
    task_text: str
    public_history_text: str
    available_capabilities: tuple[str, ...]

    def __post_init__(self):
        if self.task_family not in FAMILIES:
            raise ValueError("unknown task_family")
        if not isinstance(self.task_text, str) or not isinstance(self.public_history_text, str):
            raise ValueError("task/history text must be strings")
        if not isinstance(self.available_capabilities, (list, tuple)):
            raise ValueError("available_capabilities must be a list or tuple")
        caps = strings(list(self.available_capabilities), "available_capabilities")
        if any(not IDENTIFIER.fullmatch(c) for c in caps):
            raise ValueError("available_capabilities must contain snake_case names")
        object.__setattr__(self, "available_capabilities", caps)


@dataclass(frozen=True)
class Selection:
    selected_ids: tuple[str, ...]
    selected_versions: tuple[int, ...]
    scores: tuple[tuple[str, int], ...]
    excluded: tuple[tuple[str, str], ...]
    manifest_digest: str
    purpose: str
    contains_untested: bool
    reason: str

    def to_dict(self):
        return dict(selected=[dict(id=i, version=v) for i, v in zip(self.selected_ids, self.selected_versions)],
                    scores=dict(self.scores), excluded=dict(self.excluded),
                    manifest_digest=self.manifest_digest, purpose=self.purpose,
                    contains_untested=self.contains_untested, reason=self.reason)
