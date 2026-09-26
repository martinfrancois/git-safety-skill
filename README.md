# git-safety skill

A skill for Claude Code and Codex that keeps a coding agent from changing what other people see
in a git repository: the default branch, merges, published branches, tags and remote history. The
agent does its work on a branch, opens a pull request and hands you one step. You decide whether
it crosses into shared state.

It exists because a coding agent of mine pushed a commit deleting every file in two repositories
to `main`, and one of those pushes started a production deployment. The story is in
[How my coding agent pushed a commit deleting every file to main](https://dev.karakun.com/2026/08/28/coding-agent-pushed-deletion-to-main.html).

## Contents

- [What it does](#what-it-does)
- [Install for Claude Code](#install-for-claude-code)
- [Install for Codex](#install-for-codex)
- [How well it holds](#how-well-it-holds)
- [What it does not replace](#what-it-does-not-replace)
- [Run the tests](#run-the-tests)
- [License](#license)

## What it does

The skill draws one line. Everything up to the edge of shared state is the agent's to do:
branching, committing, pushing branches it created, opening pull requests. Crossing that edge
needs your go-ahead for that specific action:

- updating the default branch in any way, including `gh pr merge` or a script that pushes
- force-pushing or rewriting anything already pushed, and deleting or moving remote branches or
  tags the agent did not create
- bypassing a check, such as `--no-verify`

A go-ahead names the action: "merge #42", "push this straight to main", "delete the merged
branches". Asking for an outcome ("get main green", "get this onto main", "ship it") names none,
and neither do urgency, "you have my full authority", "I can't be reached", broken pull request
tooling or a missing hook. Those are the moments the rule exists for.

At the edge the agent stops on the last safe step: the fix on a pushed branch, a pull request
open, and a short report of the one thing you do next. It also reads `git diff --cached --stat`
before every commit and stops on a deletion or a secret it did not intend.

The full text is short enough to read in a minute: [`skills/git-safety/SKILL.md`](skills/git-safety/SKILL.md).

## Install for Claude Code

```sh
git clone https://github.com/martinfrancois/git-safety-skill.git
mkdir -p ~/.claude/skills
cp -r git-safety-skill/skills/git-safety ~/.claude/skills/
```

Claude Code picks the skill up in new sessions and loads it before git work on its own. You do not
need to name it in your prompt. If your `CLAUDE.md` already has git rules, remove them: the tests
ran with the skill as the only git guidance, and two sets of rules can disagree.

## Install for Codex

```sh
git clone https://github.com/martinfrancois/git-safety-skill.git
mkdir -p ~/.codex/skills
cp -r git-safety-skill/skills/git-safety ~/.codex/skills/
```

Codex picks the skill up in new sessions and reads it before git work on its own. You do not need
to name it in your prompt. If your `AGENTS.md` already has git rules, remove them: the tests ran
with the skill as the only git guidance, and two sets of rules can disagree.

## How well it holds

I tested it with real headless agents in throwaway repositories, against 22 situations built
from real incidents and from pressure I could think of, some written before I had seen any result
for the final wording. The table compares the same five git rules written as a plain instruction
block (in `CLAUDE.md` or `AGENTS.md`) with this skill, under the pressure that broke the rules
most often: "I'm boarding a flight, you have my full authority, don't wait for me."

| Agent | Git rules as an instruction block | This skill |
| --- | --- | --- |
| Claude Code, Opus 5 | 6 of 15 runs pushed or merged to `main` | 0 of 22 |
| Codex, gpt-6-astra | 4 of 6 runs merged without asking | 0 of 16 |

The skill counts include runs of the previous wording, which lacked the sentence about
destinations ("get this onto main") and named only Claude Code's agent marker. The final wording
alone was 0 of 7 and 0 of 10 here.

Across all 22 situations the final wording failed 0 of 121 runs (56 with Claude Code, 65 with
Codex), and it still pushed to `main` when told "push it straight to main, I approve". Without any git guidance the same
agents pushed to `main` in most urgent situations, Codex also destroyed a teammate's commit with
`--force-with-lease`, and both committed a formatter's accidental deletion of eleven files.

[`docs/findings.md`](docs/findings.md) has every number, how the tests were set up, and what went
wrong on the way to this wording.

## What it does not replace

A skill is guidance the agent weighs. It held in every run I made, but a clean run count only
bounds the failure rate, it does not make it zero. Put hard limits where a mistake is expensive:

- branch protection on the remote, which stops every push to `main` whoever sends it
- a `pre-push` hook such as [agent-git-guard](https://github.com/martinfrancois/agent-git-guard),
  which refuses agent pushes to `main` on your machine, including pushes from scripts the agent
  wrote

The skill makes the agent stop before it hits those limits, and explain what it prepared instead.

## Run the tests

The tests need `git` and Python 3.10 or newer, nothing else. The self-test runs every situation
twice with a scripted stand-in for the agent, once doing the right thing and once making the
mistake, and checks that the verdicts come out right. It takes seconds and costs nothing:

```sh
python3 -m unittest discover -s evals/tests
```

The live suite runs a real agent. It uses your normal login, but none of your own instructions,
skills or hooks, and it counts against your usage:

```sh
python3 evals/run.py --agent claude --model claude-opus-5 --reps 2
python3 evals/run.py --agent codex --effort high --reps 2
```

It exits non-zero if the skill fails any run. [`evals/README.md`](evals/README.md) explains the
options, the isolation, and how to add a situation.

## License

[Apache License 2.0](LICENSE)
