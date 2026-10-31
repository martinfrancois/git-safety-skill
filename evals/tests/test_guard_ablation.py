"""A failed command is not evidence that a guard preserved the remote."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guard_ablation import CASES, run_case


class GuardAblationTest(unittest.TestCase):
    def evaluate(self, hook_body, command=None, should_allow=False):
        with tempfile.TemporaryDirectory(prefix="guard-ablation-test-", dir="/var/tmp") as tmp:
            root = Path(tmp)
            hook = root / "hook"
            hook.write_text("#!/bin/sh\n" + hook_body + "\n")
            case = next(case for case in CASES if case.name == "main-push")
            case = replace(case, command=command or case.command, should_allow=should_allow)
            return run_case(root, "test", hook, case)

    def test_hook_refusal_requires_unchanged_remote(self):
        row = self.evaluate("exit 1")
        self.assertTrue(row["refused"])
        self.assertTrue(row["correct"])
        self.assertFalse(row["remote_changed"])
        self.assertIsNone(row["error"])

    def test_allowed_push_requires_expected_remote_update(self):
        row = self.evaluate("exit 0", should_allow=True)
        self.assertTrue(row["allowed"])
        self.assertTrue(row["correct"])
        self.assertEqual(row["after"], row["expected"])

    def test_error_after_update_never_counts_as_protection(self):
        row = self.evaluate("exit 0", "git push origin feature:main; exit 1")
        self.assertTrue(row["remote_changed"])
        self.assertFalse(row["refused"])
        self.assertFalse(row["correct"])
        self.assertIsNotNone(row["error"])

    def test_failure_before_hook_never_counts_as_protection(self):
        row = self.evaluate("exit 0", "git push missing-remote feature:main")
        self.assertFalse(row["remote_changed"])
        self.assertFalse(row["refused"])
        self.assertFalse(row["correct"])
        self.assertIsNotNone(row["error"])


if __name__ == "__main__":
    unittest.main()
