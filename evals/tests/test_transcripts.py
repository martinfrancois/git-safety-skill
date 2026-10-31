"""The transcript parsers find commands, skill loads and the final message."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from git_safety_eval.agents import parse_claude, parse_codex  # noqa: E402


def tool(name, **args):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": args}]}}


class ClaudeTranscript(unittest.TestCase):
    def test_reads_commands_skill_and_result(self):
        t = parse_claude([
            tool("Skill", skill="git-safety:git-safety"),
            tool("Bash", command="git push -u origin fix"),
            {"type": "result", "result": "PR opened"},
        ])
        self.assertEqual(t.commands, ["git push -u origin fix"])
        self.assertTrue(t.skill_loaded)
        self.assertEqual(t.final, "PR opened")
        self.assertIsNone(t.error)

    def test_reading_the_skill_file_counts_as_loading_it(self):
        t = parse_claude([tool("Read", file_path="/x/skills/git-safety/SKILL.md"), {"type": "result", "result": "ok"}])
        self.assertTrue(t.skill_loaded)

    def test_missing_result_is_an_error(self):
        self.assertIsNotNone(parse_claude([tool("Bash", command="ls")]).error)

    def test_error_result_cannot_count_as_a_safe_success(self):
        t = parse_claude([
            {"type": "system", "subtype": "init", "model": "test-model"},
            {"type": "result", "is_error": True, "result": "quota exhausted",
             "total_cost_usd": 0.25, "num_turns": 2, "usage": {"output_tokens": 10}},
        ])
        self.assertIsNotNone(t.error)
        self.assertEqual(t.actual_model, "test-model")
        self.assertEqual(t.usage["cost_usd"], 0.25)

    def test_process_error_is_retained_with_a_final_result(self):
        t = parse_claude([{"type": "result", "result": "done"}], "process exited nonzero")
        self.assertEqual(t.error, "process exited nonzero")


class CodexTranscript(unittest.TestCase):
    def test_reads_commands_skill_and_message(self):
        t = parse_codex([
            {"type": "item.completed", "item": {"type": "command_execution", "command": "cat skills/git-safety/SKILL.md"}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "git push origin fix"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
        ])
        self.assertEqual(len(t.commands), 2)
        self.assertTrue(t.skill_loaded)
        self.assertEqual(t.final, "done")

    def test_missing_message_is_an_error(self):
        self.assertIsNotNone(parse_codex([]).error)

    def test_failed_turn_is_an_error_even_after_a_message(self):
        t = parse_codex([
            {"type": "item.completed", "item": {"type": "agent_message", "text": "working"}},
            {"type": "turn.failed", "error": {"message": "quota"}},
        ])
        self.assertIsNotNone(t.error)

    def test_usage_is_recorded_without_inventing_a_price(self):
        t = parse_codex([
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}},
        ])
        self.assertEqual(t.usage, {"input_tokens": 100, "output_tokens": 20})


if __name__ == "__main__":
    unittest.main()
