#!/usr/bin/env python3
"""Run the git-safety scenarios against Claude Code or Codex. See evals/README.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from git_safety_eval.runner import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
