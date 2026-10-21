"""Explicit file manifests and portable, integrity-checked JSON snapshots."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .schema import FAMILIES, IDENTIFIER, SkillCard, parse_card, strings, text


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc


def _profiles(data):
    if not isinstance(data, dict) or set(data) != {"schema_version", "profiles"} or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("invalid profiles schema")
    profiles = data["profiles"]
    if not isinstance(profiles, dict) or set(profiles) != FAMILIES:
        raise ValueError("profiles must define both supported task families")
    for family, profile in profiles.items():
        if not isinstance(profile, dict) or set(profile) != {"capabilities"}:
            raise ValueError(f"invalid profile {family}")
        caps = strings(profile["capabilities"], "capabilities", True)
        if any(not IDENTIFIER.fullmatch(c) for c in caps):
            raise ValueError("capabilities must be snake_case")
    return tuple((family, tuple(sorted(profiles[family]["capabilities"]))) for family in sorted(profiles))


@dataclass(frozen=True)
class SkillRegistry:
    library_version: str
    kind: str
    _cards: tuple[SkillCard, ...]
    _profiles: tuple[tuple[str, tuple[str, ...]], ...]

    def get(self, skill_id: str) -> SkillCard:
        for card in self._cards:
            if card.id == skill_id:
                return card
        raise KeyError(skill_id)

    def list_cards(self) -> tuple[SkillCard, ...]:
        return self._cards

    @property
    def profiles(self):
        return {"schema_version": 1, "profiles": {f: {"capabilities": list(c)} for f, c in self._profiles}}

    def _payload(self):
        return dict(schema_version=1, library_version=self.library_version, kind=self.kind,
                    profiles=self.profiles, cards=[c.to_dict() for c in self._cards])

    @property
    def digest(self) -> str:
        data = json.dumps(self._payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def to_bundle(self):
        return dict(format="spatial_skill_bundle_v1", **self._payload(), digest=self.digest)


def _contained(root, anchor, relative):
    text(relative, "manifest path")
    if Path(relative).is_absolute():
        raise ValueError("manifest paths must be relative")
    path = (anchor / relative).resolve()
    if root not in path.parents:
        raise ValueError("manifest path escapes library root")
    return path


def load_registry(manifest_path: Path, profiles_path: Path | None = None) -> SkillRegistry:
    manifest = Path(manifest_path).resolve()
    data = read_json(manifest)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    snapshot = data.get("format") == "spatial_skill_bundle_v1"
    required = {"schema_version", "library_version", "kind", "profiles", "cards"}
    if set(data) != (required | {"format", "digest"} if snapshot else required):
        raise ValueError("invalid manifest fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    text(data["library_version"], "library_version")
    if data["kind"] not in ("static", "dynamic"):
        raise ValueError("invalid manifest kind")
    if not isinstance(data["cards"], list):
        raise ValueError("cards must be a list")
    if snapshot:
        if profiles_path is not None:
            raise ValueError("snapshot includes profiles; do not override them")
        profiles = _profiles(data["profiles"])
        cards = tuple(parse_card(c) for c in data["cards"])
    else:
        root = manifest.parent.parent.resolve()
        profile_file = _contained(root, manifest.parent, data["profiles"])
        if profiles_path is not None and Path(profiles_path).resolve() != profile_file:
            raise ValueError("explicit profiles path must match manifest profiles")
        profiles = _profiles(read_json(profile_file))
        cards = tuple(parse_card(read_json(_contained(root, manifest.parent, p))) for p in data["cards"])
    ids = set()
    for card in cards:
        if card.id in ids:
            raise ValueError(f"duplicate skill id: {card.id}")
        ids.add(card.id)
        if card.kind != data["kind"]:
            raise ValueError("card kind does not match manifest")
        for family in card.task_families:
            available = dict(profiles)[family]
            if not set(card.required_capabilities) <= set(available):
                raise ValueError(f"unknown capability for {card.id} in {family}")
    registry = SkillRegistry(data["library_version"], data["kind"], cards, profiles)
    if snapshot and data["digest"] != registry.digest:
        raise ValueError("snapshot digest mismatch")
    return registry
