# git-safety skill

Instructions for Claude Code and Codex to preserve work while completing Git tasks.
With standing approval, the agent amends, squashes, rebases, and publishes its PR
branch without asking on every update. Remote advancement means inspect and
incorporate the incoming work, then retry with a pinned lease. It does not mean
abandon clean history or ask for permission merely because somebody pushed.

Default and protected branch updates still require specific approval. A desired
outcome such as "get main green" does not authorize a direct push or PR merge.
The agent prepares the branch and PR before asking for that last step.

The skill also requires full history before rewrites, review of staged changes,
and preservation of unexpected deletions. A hook rejection means satisfy the
failed check. It never grants permission to disable the check.

Read the full policy in [SKILL.md](skills/git-safety/SKILL.md).

## Install

For Claude Code:

```sh
mkdir -p ~/.claude/skills
cp -r skills/git-safety ~/.claude/skills/
```

For Codex:

```sh
mkdir -p ~/.agents/skills
cp -r skills/git-safety ~/.agents/skills/
```

Start a new session after installation. The description asks the agent to read
this skill before Git writes and after a rejected push. Loading and following a
skill are model behavior, not enforcement.

Keep user-specific authorization in your own instructions. For example:

```md
Routine pushes and safe clean-history rewrites of the task's PR branch have
standing approval, including after incorporating incoming remote work.
Ask before updating the default or a protected integration branch, and when
preserving competing changes requires an unclear decision.
```

Reconcile conflicting Git rules when installing. Do not delete unrelated user
instructions. Without standing approval or a task requesting the rewrite, this
skill still asks before rewriting published history.

## Evidence and limits

[The standalone follow-up](docs/standalone-2026-10-31.md) compares the revised
skill, its previous wording, and the revised skill with the guard. It includes
fresh cases and repeated pressure tests. The
[earlier comparison](docs/comparison-2026-10-31.md) also tests a shorter instruction
block and the guard alone. Both separate preserving work from completing
authorized updates. Historical measurements in
[findings.md](docs/findings.md) concern older wording and agent releases; they do
not establish the reliability of this version.

The skill cannot enforce its own instructions. A Git hook adds mechanical checks
but cannot establish that rewritten code preserves a contributor's intent.
[agent-git-guard](https://github.com/martinfrancois/agent-git-guard) also cannot
intercept a GitHub API merge. Server-side protection is needed for enforcement
across machines. Zero failures in a finite experiment is not a guarantee.

## Tests

The self-test needs Git and Python 3.10 or newer. It checks safe and unsafe
scripted actions for every scenario with both file and HTTPS-looking local
transports. It also checks that doing nothing fails rewrite completion.

```sh
python3 -m unittest discover -s evals/tests
```

Run both agents with two repetitions before changing the skill:

```sh
python3 evals/run.py --agent claude --model claude-opus-5 --reps 2 --remote https
python3 evals/run.py --agent codex --model gpt-6-astra --effort high --reps 2 --remote https
```

Live runs consume agent usage. [Evaluation instructions](evals/README.md) cover
API authentication, isolated runs, comparison conditions, and output files.

## Origin and license

This work followed [an agent push that deleted every file from main](https://dev.karakun.com/2026/08/28/coding-agent-pushed-deletion-to-main.html).
[Apache License 2.0](LICENSE).
