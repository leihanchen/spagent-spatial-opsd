import copy
from dataclasses import replace
import json
import unittest

from spatial_skills import parse_card
from spatial_skills.prompts import build_teacher_view, render_skill_block
from test_schema_registry import card


class PromptBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.skill = parse_card(card(procedure=["TEACHER_ONLY_CANARY: inspect the public scene."]))

    def test_render_hides_audit_metadata(self):
        block = render_skill_block([self.skill])
        self.assertIn("TEACHER_ONLY_CANARY", block)
        self.assertIn("Applies when:", block)
        self.assertIn("Verification:", block)
        for private in ["https://example.org/source", "Original test fixture.", "validation_status", "untested"]:
            self.assertNotIn(private, block)
        self.assertEqual(render_skill_block([]), "")

    def test_budget_rejects_whole_card_without_truncation(self):
        with self.assertRaises(ValueError):
            render_skill_block([self.skill], max_chars=10)
        with self.assertRaises(ValueError):
            render_skill_block([replace(self.skill, procedure=("x" * 2100,))])
        with self.assertRaises(ValueError):
            render_skill_block([], max_chars=0)

    def test_teacher_preserves_multimodal_history_and_student_object(self):
        for system in [[], [{"role": "system", "content": "Shared rules."}],
                       [{"role": "system", "content": [{"type": "text", "text": "Shared rules."}]}]]:
            messages = copy.deepcopy(system) + [
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "image.png"}},
                                               {"type": "text", "text": "Repair the scene."}]},
                {"role": "assistant", "content": "sampled tokens", "tool_calls": [{"id": "call_1"}]},
                {"role": "tool", "tool_call_id": "call_1", "content": "updated scene"},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "updated.png"}}]},
            ]
            before = json.dumps(messages)
            block = render_skill_block([self.skill])
            teacher = build_teacher_view(messages, block)
            self.assertEqual(json.dumps(messages), before)
            self.assertNotIn("TEACHER_ONLY_CANARY", before)
            self.assertIn("TEACHER_ONLY_CANARY", json.dumps(teacher))
            if not system:
                teacher.pop(0)
            elif isinstance(system[0]["content"], str):
                teacher[0]["content"] = teacher[0]["content"][:-len("\n\n" + block)]
            else:
                teacher[0]["content"].pop()
            self.assertEqual(teacher, messages)
            teacher[-1]["content"][0]["image_url"]["url"] = "mutated"
            self.assertEqual(json.dumps(messages), before)

    def test_empty_block_is_an_independent_unchanged_copy(self):
        messages = [{"role": "user", "content": "task"}]
        result = build_teacher_view(messages, "")
        self.assertEqual(result, messages)
        self.assertIsNot(result, messages)
        self.assertIsNot(result[0], messages[0])

    def test_unsupported_system_content_fails_explicitly(self):
        with self.assertRaises(ValueError):
            build_teacher_view([{"role": "system", "content": {"text": "unknown"}}], "skill")
        with self.assertRaises(ValueError):
            build_teacher_view("not messages", "skill")


if __name__ == "__main__":
    unittest.main()
