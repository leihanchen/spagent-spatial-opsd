import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from spatial_skills import load_registry, parse_card


def card(**changes):
    data = dict(
        id="inspect_clearance", version=1, kind="static", name="Inspect clearance",
        when="An object overlaps another object.", task_families=["spatialact_repair"],
        trigger_terms=["overlap"], preconditions=["Public views are available."],
        procedure=["Inspect the affected region."], verification=["Check neighboring constraints."],
        failure_lessons=[], required_capabilities=["observe_scene"],
        source_refs=["https://example.org/source"], adaptation_notes="Original test fixture.",
        parent_skill_id=None, provenance_episode_ids=[], review_status="reviewed",
        validation_status="untested",
    )
    data.update(changes)
    return data


PROFILES = {"schema_version": 1, "profiles": {
    "spatialact_repair": {"capabilities": ["observe_scene", "edit_pose"]},
    "sceneactbench_layout": {"capabilities": ["observe_scene", "render_scene", "edit_pose"]},
}}


class LibraryFixture:
    def __init__(self, path, cards=None, kind="static"):
        self.root = Path(path) / "library"
        (self.root / "manifests").mkdir(parents=True)
        (self.root / "static").mkdir()
        self.profiles = self.root / "profiles.json"
        self.profiles.write_text(json.dumps(PROFILES))
        paths = []
        for i, data in enumerate(cards if cards is not None else [card()]):
            p = self.root / "static" / f"{i}.json"
            p.write_text(json.dumps(data))
            paths.append(f"../static/{i}.json")
        self.manifest = self.root / "manifests" / "library.json"
        self.data = dict(schema_version=1, library_version="fixture-v1", kind=kind,
                         profiles="../profiles.json", cards=paths)
        self.write()

    def write(self):
        self.manifest.write_text(json.dumps(self.data))


class SchemaTests(unittest.TestCase):
    def test_card_round_trip_and_immutable_sequences(self):
        raw = card()
        parsed = parse_card(raw)
        self.assertEqual(parsed.to_dict(), raw)
        raw["procedure"].append("Changed")
        self.assertEqual(len(parsed.procedure), 1)
        with self.assertRaises(AttributeError):
            parsed.name = "Changed"

    def test_invalid_fields_fail(self):
        for patch in [dict(version=True), dict(version=0), dict(kind="other"),
                      dict(task_families=["unknown"]), dict(procedure=[]),
                      dict(verification="not a list"), dict(trigger_terms=["UPPER"]),
                      dict(review_status="approved"), dict(validation_status="effective"),
                      dict(id="not-an-id"), dict(extra="unknown"),
                      dict(procedure=[1]), dict(task_families=[]),
                      dict(kind="dynamic", provenance_episode_ids=[])]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                parse_card(card(**patch))

    def test_dynamic_requires_evidence_and_supported_requires_review(self):
        self.assertEqual(parse_card(card(kind="dynamic", provenance_episode_ids=["train_17"])).kind,
                         "dynamic")
        with self.assertRaises(ValueError):
            parse_card(card(review_status="draft", validation_status="supported"))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_load_no_writes_and_empty_dynamic(self):
        f = LibraryFixture(self.tmp.name)
        before = {str(p): p.read_bytes() for p in f.root.rglob("*") if p.is_file()}
        registry = load_registry(f.manifest, f.profiles)
        self.assertEqual(registry.get("inspect_clearance").version, 1)
        self.assertIsInstance(registry.list_cards(), tuple)
        self.assertEqual(before, {str(p): p.read_bytes() for p in f.root.rglob("*") if p.is_file()})
        f.data.update(kind="dynamic", cards=[])
        f.write()
        self.assertEqual(load_registry(f.manifest).list_cards(), ())

    def test_reject_duplicates_missing_capabilities_and_files(self):
        f = LibraryFixture(self.tmp.name, [card(), card()])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_registry(f.manifest)
        f.data["cards"] = ["../static/missing.json"]
        f.write()
        with self.assertRaises(ValueError):
            load_registry(f.manifest)
        f.data["cards"] = ["../static/0.json"]
        f.write()
        (f.root / "static/0.json").write_text(json.dumps(card(required_capabilities=["secret_oracle"])))
        with self.assertRaisesRegex(ValueError, "capabilit"):
            load_registry(f.manifest)

    def test_reject_path_and_symlink_escape(self):
        f = LibraryFixture(self.tmp.name)
        outside = Path(self.tmp.name) / "outside.json"
        outside.write_text(json.dumps(card()))
        for entry in ["../../outside.json", str(outside)]:
            f.data["cards"] = [entry]
            f.write()
            with self.assertRaisesRegex(ValueError, "root|relative"):
                load_registry(f.manifest)
        link = f.root / "static/link.json"
        link.symlink_to(outside)
        f.data["cards"] = ["../static/link.json"]
        f.write()
        with self.assertRaisesRegex(ValueError, "root"):
            load_registry(f.manifest)

    def test_digest_portable_and_covers_profiles_and_card_content(self):
        f = LibraryFixture(self.tmp.name)
        registry = load_registry(f.manifest)
        copied = Path(self.tmp.name) / "copied"
        shutil.copytree(f.root, copied)
        self.assertEqual(registry.digest, load_registry(copied / "manifests/library.json").digest)
        profiles = copy.deepcopy(PROFILES)
        profiles["profiles"]["spatialact_repair"]["capabilities"].append("new_capability")
        f.profiles.write_text(json.dumps(profiles))
        self.assertNotEqual(registry.digest, load_registry(f.manifest).digest)
        f.profiles.write_text(json.dumps(PROFILES))
        (f.root / "static/0.json").write_text(json.dumps(card(procedure=["A revised procedure."])))
        self.assertNotEqual(registry.digest, load_registry(f.manifest).digest)

    def test_snapshot_roundtrip_and_tamper_detection(self):
        f = LibraryFixture(self.tmp.name)
        registry = load_registry(f.manifest)
        bundle = registry.to_bundle()
        p = Path(self.tmp.name) / "export.json"
        p.write_text(json.dumps(bundle))
        self.assertEqual(load_registry(p).digest, registry.digest)
        bundle["cards"][0]["name"] = "Tampered"
        p.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(ValueError, "digest"):
            load_registry(p)

    def test_import_does_not_load_ml_packages(self):
        command = "import spatial_skills,sys; assert not {'spagent','torch','transformers'} & sys.modules.keys()"
        result = subprocess.run([sys.executable, "-c", command], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
