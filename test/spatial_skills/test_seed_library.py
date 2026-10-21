from pathlib import Path
import unittest

from spatial_skills import load_registry

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "skills/spatial/manifests/static-v1.json"
IDS = {
    "reference_frame_reasoning", "select_informative_evidence", "track_action_effects",
    "diagnose_spatial_error", "minimal_effective_correction", "repair_without_regression",
    "recover_from_ineffective_edit", "match_objects_and_anchors", "resolve_multiview_pose",
    "render_compare_refine",
}


class SeedLibraryTests(unittest.TestCase):
    def test_ten_reviewed_but_untested_cards(self):
        registry = load_registry(MANIFEST)
        self.assertEqual({c.id for c in registry.list_cards()}, IDS)
        for card in registry.list_cards():
            self.assertEqual((card.kind, card.review_status, card.validation_status),
                             ("static", "reviewed", "untested"))
            self.assertTrue(card.source_refs)
            self.assertTrue(card.adaptation_notes)
            self.assertLessEqual(len(card.teacher_text()), 2000)

    def test_three_shared_four_repair_three_layout(self):
        cards = load_registry(MANIFEST).list_cards()
        self.assertEqual(sum(len(c.task_families) == 2 for c in cards), 3)
        self.assertEqual(sum(c.task_families == ("spatialact_repair",) for c in cards), 4)
        self.assertEqual(sum(c.task_families == ("sceneactbench_layout",) for c in cards), 3)

    def test_dynamic_catalog_empty(self):
        registry = load_registry(MANIFEST.parent / "dynamic-v0.json")
        self.assertEqual(registry.kind, "dynamic")
        self.assertEqual(registry.list_cards(), ())


if __name__ == "__main__":
    unittest.main()
