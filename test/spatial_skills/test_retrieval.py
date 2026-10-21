import dataclasses
import json
import tempfile
import unittest

from spatial_skills import RetrievalContext, load_registry
from spatial_skills.retrieval import select_skills
from test_schema_registry import LibraryFixture, card


def context(text="overlap", family="spatialact_repair", caps=("observe_scene",)):
    return RetrievalContext(family, text, "", caps)


class RetrievalTests(unittest.TestCase):
    def registry(self, cards, kind="static"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return load_registry(LibraryFixture(tmp.name, cards, kind).manifest)

    def test_untested_only_explicit_validation(self):
        registry = self.registry([card()])
        self.assertFalse(select_skills(registry, context()).selected_ids)
        selected = select_skills(registry, context(), purpose="validation")
        self.assertEqual(selected.selected_ids, ("inspect_clearance",))
        self.assertTrue(selected.contains_untested)
        self.assertEqual(selected.manifest_digest, registry.digest)
        with self.assertRaises(ValueError):
            select_skills(registry, context(), purpose="typo")

    def test_supported_and_draft_rejected_and_dynamic_exclusions(self):
        for patch, reason in [(dict(review_status="draft"), "not_reviewed"),
                              (dict(validation_status="rejected"), "rejected"),
                              (dict(kind="dynamic", provenance_episode_ids=["train_1"]), "dynamic_disabled")]:
            registry = self.registry([card(**patch)], kind=patch.get("kind", "static"))
            selected = select_skills(registry, context(), "validation")
            self.assertFalse(selected.selected_ids)
            self.assertEqual(dict(selected.excluded)["inspect_clearance"], reason)
        selected = select_skills(self.registry([card(validation_status="supported")]), context())
        self.assertEqual(selected.selected_ids, ("inspect_clearance",))
        self.assertFalse(selected.contains_untested)

    def test_filters_family_capability_and_no_match(self):
        registry = self.registry([card(validation_status="supported")])
        for ctx, reason in [(context(family="sceneactbench_layout"), "task_family"),
                            (context(caps=()), "missing_capabilities"),
                            (context("nothing relevant"), "no_trigger")]:
            selected = select_skills(registry, ctx)
            self.assertFalse(selected.selected_ids)
            self.assertEqual(dict(selected.excluded)["inspect_clearance"], reason)

    def test_stable_ties_distinct_phrases_case_and_word_boundaries(self):
        registry = self.registry([card(id="z_skill", validation_status="supported"),
                                  card(id="a_skill", validation_status="supported")])
        selected = select_skills(registry, context("OVERLAP overlap"))
        self.assertEqual(selected.selected_ids, ("a_skill",))
        self.assertEqual(dict(selected.scores), {"z_skill": 1, "a_skill": 1})
        self.assertFalse(select_skills(registry, context("overlapping")).selected_ids)
        self.assertEqual(select_skills(registry, context("overlap")),
                         select_skills(registry, context("overlap")))

    def test_history_trigger_and_explicit_task_wide_trigger(self):
        registry = self.registry([card(validation_status="supported")])
        ctx = RetrievalContext("spatialact_repair", "inspect", "an overlap was observed", ["observe_scene"])
        self.assertTrue(select_skills(registry, ctx).selected_ids)
        wildcard = self.registry([card(trigger_terms=["*"], validation_status="supported")])
        self.assertTrue(select_skills(wildcard, context("unrelated task text")).selected_ids)

    def test_selection_and_context_are_immutable_and_public_only(self):
        registry = self.registry([card(validation_status="supported")])
        before = registry.to_bundle()
        caps = ["observe_scene"]
        ctx = RetrievalContext("spatialact_repair", "overlap", "", caps)
        caps.clear()
        selected = select_skills(registry, ctx)
        self.assertEqual(selected.selected_versions, (1,))
        self.assertEqual(before, registry.to_bundle())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            selected.reason = "Changed"
        with self.assertRaises(TypeError):
            RetrievalContext("spatialact_repair", "", "", (), ground_truth="secret")


if __name__ == "__main__":
    unittest.main()
