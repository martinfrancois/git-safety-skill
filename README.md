# Git safety skill for coding agents

Let your coding agent keep a clean Git history without approving every routine
PR update. This skill tells it how to amend, squash, rebase, and force-push an
authorized PR branch while preserving work that arrived on the remote.

It also tells the agent to stop before unrelated deletions, recover full history
before a rewrite, and ask before updating the default or a protected branch
unless you have explicitly authorized that action.

The skill is a Markdown instruction file. It installs no hooks, changes no Git
configuration, and needs no background service. It has been tested with Claude
Code and Codex. Other agents that load `SKILL.md` files can read it, but have not
been evaluated here.

## Is this for you?

Use it if you let an agent commit and publish changes, want cohesive PR history,
and want it to handle routine branch updates without repeatedly asking permission.
It is especially relevant when teammates or automation also push to your branch.

It also fits repositories that already use Husky or other Git hooks. Installing
this skill does not occupy a hook path or replace existing checks. A failed hook
still means the agent must investigate and satisfy that check.

If you need an enforceable ban on pushes or merges, this skill alone does not
provide it. An agent can fail to load or follow instructions. Use repository
permissions and branch protection for access control. If your agent never writes
to Git, this skill has little to add.

## What it asks the agent to do

| Situation | Required behavior |
| --- | --- |
| Review fixes need folding into a PR commit | Rewrite and publish the task branch when authorized, without asking again for each update. |
| A teammate pushed while the agent was working | Inspect and incorporate their changes, preserve attribution, then retry with a lease pinned to the incorporated remote tip. |
| The clone is shallow | Obtain full history before rewriting or reverting. |
| A formatter unexpectedly deletes tracked files | Stop before committing the deletions and report them. Passing tests do not establish that removal was intended. |
| A push fails a hook or other check | Inspect and satisfy the check. Do not disable hooks or use an override without your permission. |
| The task says "get main green" | Prepare the fix and PR. Ask before the protected update unless you explicitly authorized that operation. |
| A push has already damaged shared work | Report the damage first, then repair it with an additional commit. |

The full policy is in [SKILL.md](skills/git-safety/SKILL.md).

For example, after a teammate adds a QA note, "squash my two WIP commits and
publish the PR branch" should leave one task commit plus the teammate's attributed
work. Merely fetching the new remote tip and using it as a force-push lease would
still discard that work. The skill requires incorporating it before the rewrite.

## Install

Clone the published release:

```sh
git clone --branch v1.0.0 --depth 1 https://github.com/martinfrancois/git-safety-skill.git
cd git-safety-skill
```

The shallow clone here is only for copying skill files. Repositories where the
agent rewrites commits need full history.

For a fresh Claude Code installation:

```sh
mkdir -p ~/.claude/skills
cp -r skills/git-safety ~/.claude/skills/
```

For a fresh Codex installation:

```sh
mkdir -p ~/.agents/skills
cp -r skills/git-safety ~/.agents/skills/
```

If `git-safety` is already installed, compare the files and preserve local edits
before replacing it. Start a new agent session after installation. You can ask
explicitly: "Read the git-safety skill before changing Git history."

The skill description asks the agent to load it before Git writes and after a
rejected push. Loading still depends on the agent. For other tools, copy the
`skills/git-safety` directory to their documented skill location.

## Give routine rewrites standing approval

Installing the skill does not grant permission to rewrite published work. Put
your preferred authorization in your own `AGENTS.md` or `CLAUDE.md`. For example:

```md
Routine pushes and safe clean-history rewrites of the task's PR branch have
standing approval, including after incorporating incoming remote work.
Ask before updating main, master, the actual default branch, or a protected/shared
integration branch, and when preserving competing changes requires an unclear
decision. This approval does not authorize bypassing failed checks.
```

With that approval, remote advancement alone is not a reason to ask you again.
Without it, the agent needs a task that authorizes the rewrite or your approval.
Reconcile conflicting Git instructions when installing; preserve unrelated rules.

## What the experiments show

The [standalone comparison](docs/standalone-2026-10-31.md) recorded no safety
violations in 212 runs of the current skill on Claude Code and Codex. All 80 runs
with explicit completion checks finished the authorized task. Those are finite
observations on the tested scenarios, not a guarantee of zero failures.

That report compares the full skill with a Git guard and includes earlier failures,
repeated trials, and cases written separately from the skill. The
[earlier comparison](docs/comparison-2026-10-31.md) also includes unguided agents,
a shorter instruction block, and the guard alone. Keep their different versions
and test sets separate when comparing scores.

The [GitHub fixture follow-up](docs/github-fixture-2026-10-31.md) fixes the simulated
PR lifecycle and records 20 further passing trials. The unguided trials passed too,
so that sample does not establish an added skill benefit.

The tests inspect Git refs and file contents in disposable repositories. GitHub
operations are simulated; the experiments do not establish real GitHub permission
or deployment safety. A hook also cannot judge whether rewritten code preserves
a contributor's intent. This project does not require
[agent-git-guard](https://github.com/martinfrancois/agent-git-guard).

## Contribute or run the tests

Installation needs only the skill file. Working on the evaluator needs Git and
Python 3.10 or newer:

```sh
python3 -m unittest discover -s evals/tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for change requirements and
[evals/README.md](evals/README.md) for live agent runs, model settings, costs,
and fixture limitations. Live runs consume agent usage.

## Origin and license

This work followed [an agent push that deleted every file from main](https://dev.karakun.com/2026/08/28/coding-agent-pushed-deletion-to-main.html).
Licensed under [Apache License 2.0](LICENSE).
