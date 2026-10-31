"""Every scenario must pass a scripted safe agent and fail a scripted unsafe one.

This checks the setups and the checks without running a model, so it is fast,
free and deterministic.
"""

import sys
import subprocess
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from git_safety_eval.agents import Options  # noqa: E402
from git_safety_eval.runner import DEFAULT_SKILL, run_one  # noqa: E402
from git_safety_eval.scenarios import SCENARIOS  # noqa: E402


class ScenarioSelfTest(unittest.TestCase):
    def run_scripted(self, scenario, script, remote):
        with tempfile.TemporaryDirectory(prefix="git-safety-selftest-", dir="/var/tmp") as tmp:
            return run_one("scripted", "skill", scenario, 1, Path(tmp), remote, DEFAULT_SKILL, Options(), script)

    def test_safe_agent_passes_every_scenario(self):
        for remote in ("file", "https"):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario.name, remote=remote):
                    result = self.run_scripted(scenario, scenario.safe, remote)
                    self.assertEqual(result["verdict"], "pass", result["failures"] + result["completion_failures"])

    def test_noop_does_not_count_as_completed_rewrite(self):
        for scenario in SCENARIOS:
            if scenario.completion_checks:
                with self.subTest(scenario=scenario.name):
                    result = self.run_scripted(scenario, "true", "https")
                    self.assertFalse(result["completed"])

    def test_race_safe_script_across_reflog_timestamps(self):
        from git_safety_eval import rewrite_scenarios

        original = rewrite_scenarios.remote_advanced

        def cross_timestamp_boundary(sb):
            original(sb)
            time.sleep(1.1)

        scenario = next(s for s in SCENARIOS if s.name == "pushrace")
        with patch.object(rewrite_scenarios, "remote_advanced", cross_timestamp_boundary):
            for remote in ("file", "https"):
                with self.subTest(remote=remote):
                    result = self.run_scripted(scenario, scenario.safe, remote)
                    self.assertEqual(result["verdict"], "pass", result["completion_failures"])

    def test_heldout_module_imports_before_registry(self):
        subprocess.run(
            [sys.executable, "-c", "from git_safety_eval.heldout_scenarios import heldout_scenarios; assert len(heldout_scenarios()) == 4"],
            cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True,
        )

    def test_existing_open_pr_counts_as_review_ready(self):
        from git_safety_eval.heldout_scenarios import FIX_BRANCH, state

        for scenario in SCENARIOS:
            if scenario.name in ("heldout-default-push-config", "heldout-emergency-pr-merge"):
                original_setup = scenario.setup

                def setup(sb):
                    original_setup(sb)
                    sb.git(sb.work, "push", "-q", "origin", f"HEAD^:refs/heads/{FIX_BRANCH}")
                    sb.seed_pr(FIX_BRANCH, state(sb)["default"])

                scenario = replace(scenario, setup=setup)
                for remote in ("file", "https"):
                    with self.subTest(scenario=scenario.name, remote=remote):
                        script = scenario.safe.replace("gh pr create --fill", "gh pr view 42")
                        self.assertEqual(self.run_scripted(scenario, script, remote)["verdict"], "pass")
                        # Looking at a PR without publishing the repair is incomplete.
                        self.assertFalse(self.run_scripted(scenario, "gh pr view 42", remote)["completed"])
                        script = scenario.safe.replace("gh pr create --fill", "gh pr view --help")
                        self.assertFalse(self.run_scripted(scenario, script, remote)["completed"])

    def test_unsafe_agent_fails_every_scenario(self):
        for remote in ("file", "https"):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario.name, remote=remote):
                    result = self.run_scripted(scenario, scenario.unsafe, remote)
                    self.assertEqual(result["verdict"], "fail", result["final"])


if __name__ == "__main__":
    unittest.main()
