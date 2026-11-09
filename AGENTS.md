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

## Contributing for someone else

martinfrancois's rule for outside contributions, and for any agent working for an outside
contributor: contributors shouldn't spend time on pull requests that collide with someone else's
work or that he wouldn't accept. So a contribution takes one of three paths (see "Three ways to
contribute" in `CONTRIBUTING.md`):

- Small fix (bug fix, typo, docs improvement or similar): open a pull request directly, no issue
  needed. If an issue for it exists, claim it first as below.
- Existing issue: check its assignees and linked pull requests, post `/take` on the issue, and
  start only once the assignment comes back. Never open a pull request for an issue that isn't
  assigned to the contributor you work for, and don't start on one that someone else holds or that
  an open pull request already addresses.
- New feature: open a thread in the Ideas category of GitHub Discussions. Wait until martinfrancois
  approves it and opens an issue, then claim that issue with `/take`. Never open a feature pull
  request without an approved issue assigned to your contributor.
