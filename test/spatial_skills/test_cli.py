import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from spatial_skills import load_registry
from test_schema_registry import LibraryFixture, card

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "skills/spatial/manifests/static-v1.json"


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "spatial_skills.cli", *map(str, args)],
                              capture_output=True, text=True, cwd=ROOT)

    def test_lint_and_list_explicit_manifest(self):
        r = self.run_cli("lint", "--manifest", STATIC)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["card_count"], 10)
        self.assertEqual(len(json.loads(self.run_cli("list", "--manifest", STATIC).stdout)), 10)
        self.assertNotEqual(self.run_cli("lint").returncode, 0)

    def test_errors_are_nonzero_and_actionable(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = LibraryFixture(tmp, [card(version=0)])
            r = self.run_cli("lint", "--manifest", f.manifest)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("version", r.stderr)
            self.assertNotIn("Traceback", r.stderr)

    def test_select_and_render_validation_examples(self):
        for fixture, ident in [("repair.json", "repair_without_regression"),
                               ("layout.json", "render_compare_refine")]:
            ctx = ROOT / "test/spatial_skills/fixtures" / fixture
            base = ["--manifest", STATIC, "--context", ctx]
            ordinary = self.run_cli("select", *base)
            self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
            self.assertEqual(json.loads(ordinary.stdout)["selected"], [])
            r = self.run_cli("select", *base, "--purpose", "validation")
            self.assertEqual(r.returncode, 0, r.stderr)
            selected = json.loads(r.stdout)
            self.assertEqual(selected["selected"], [dict(id=ident, version=1)])
            self.assertTrue(selected["contains_untested"])
            rendered = self.run_cli("render", *base, "--purpose", "validation")
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertIn("[Teacher-only procedural guidance]", rendered.stdout)
            self.assertIn("untested", rendered.stderr)

    def test_export_roundtrip_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "library.json"
            args = ["export", "--manifest", STATIC, "--output", output]
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 0, r.stderr)
            original = output.read_bytes()
            self.assertEqual(load_registry(output).digest, load_registry(STATIC).digest)
            self.assertNotEqual(self.run_cli(*args).returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(self.run_cli(*args, "--overwrite").returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(self.run_cli("lint", "--manifest", output).returncode, 0)

    def test_context_rejects_private_extra_fields_and_wrong_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "context.json"
            context = dict(task_family="spatialact_repair", task_text="overlap",
                           public_history_text="", available_capabilities=["observe_scene"])
            for patch in [dict(ground_truth="hidden"), dict(available_capabilities="observe_scene")]:
                output.write_text(json.dumps(dict(context, **patch)))
                r = self.run_cli("select", "--manifest", STATIC, "--context", output)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
