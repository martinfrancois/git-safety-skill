# Agent guide

This repository holds one skill, `skills/git-safety/SKILL.md`, and the harness in `evals/` that
tests it with real agents. The skill's wording is the product; every change to it is judged by the
harness, not by reading it.

## Changing the skill

1. Run the self-test: `python3 -m unittest discover -s evals/tests`.
2. Run the live suite on both agents with at least two runs per situation:
   `python3 evals/run.py --agent claude --model claude-opus-5 --reps 2` and
   `python3 evals/run.py --agent codex --effort high --reps 2`. Both must exit 0.
3. Put the two `summary.md` tables in the pull request.

When the skill fails a situation, write new situations for the kind of failure before changing the
wording, and judge the new wording on those too. Fix the principle the agent misread, not the one
phrase in the failing task.

## Changing the harness

Every situation needs a safe and an unsafe scripted agent, and the self-test must show the safe one
passing and the unsafe one failing. Checks read outcomes from the repositories, never the agent's
own report. `evals/README.md` has the details.

## Rules

- `results/` holds transcripts and sandboxes with local paths; it stays out of git.
- Fixture credentials must not match any real provider's key format, so secret scanners stay quiet.
- `docs/findings.md` reports measurements. Update its numbers only from runs you made, and say
  which agent release and model produced them.
