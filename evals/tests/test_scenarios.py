"""Every scenario must pass a scripted safe agent and fail a scripted unsafe one.

This checks the setups and the checks without running a model, so it is fast,
free and deterministic.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from git_safety_eval.agents import Options  # noqa: E402
from git_safety_eval.runner import DEFAULT_SKILL, run_one  # noqa: E402
from git_safety_eval.scenarios import SCENARIOS  # noqa: E402


class ScenarioSelfTest(unittest.TestCase):
    def run_scripted(self, scenario, script, remote):
        with tempfile.TemporaryDirectory() as tmp:
            return run_one("scripted", "skill", scenario, 1, Path(tmp), remote, DEFAULT_SKILL, Options(), script)

    def test_safe_agent_passes_every_scenario(self):
        for remote in ("file", "https"):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario.name, remote=remote):
                    result = self.run_scripted(scenario, scenario.safe, remote)
                    self.assertEqual(result["verdict"], "pass", result["failures"])

    def test_unsafe_agent_fails_every_scenario(self):
        for remote in ("file", "https"):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario.name, remote=remote):
                    result = self.run_scripted(scenario, scenario.unsafe, remote)
                    self.assertEqual(result["verdict"], "fail", result["final"])


if __name__ == "__main__":
    unittest.main()
