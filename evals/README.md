# Evaluations

Two kinds of test live here.

- **The self-test** (`tests/`) runs every situation with two scripted stand-ins for the agent:
  one does the right thing, one makes the mistake the situation is about. The right one must
  pass and the wrong one must fail. It checks that each setup builds the state it claims and that
  each check catches the mistake, without running a model.
- **The live suite** (`run.py`) gives each situation to a real Claude Code or Codex agent and
  checks the repository afterwards.

## Running the live suite

```sh
python3 evals/run.py --agent claude --model claude-opus-5 --reps 2
python3 evals/run.py --agent codex --effort high --reps 2
```

| Option | Meaning |
| --- | --- |
| `--condition skill` | install the skill (default) |
| `--condition none` | no git guidance at all, to see what the agent does on its own |
| `--scenario NAME` | run only this situation; repeat for several |
| `--reps N` | runs per situation |
| `--parallel N` | runs at the same time (default 4) |
| `--remote file` | a `file://` remote (default) |
| `--remote https` | a local remote that shows as `https://github.com/...` in every git command |
| `--claude-bin PATH` | a specific Claude Code binary, for example an older release |
| `--codex-auth PATH` | the Codex login file to link in (default `~/.codex/auth.json`) |
| `--out DIR` | where results and sandboxes go (default `results/<timestamp>`) |

Each run writes a line to `results.jsonl` with the verdict, the reasons for a failure, whether the
agent loaded the skill, and the path of its sandbox, which keeps the repositories and the raw
transcript for inspection. `summary.md` has the counts. With `--condition skill` the command exits
non-zero if any run fails or errors, so it can gate a change to the skill.

A verdict is `pass`, `fail` or `error`. An error means the agent did not finish (a timeout, a
missing binary, a login problem) and says nothing about the skill.

## What the agent sees

Each run gets a fresh directory with a bare origin, the agent's clone, sometimes a teammate's
clone, and a `gh` stub on `PATH`. The stub answers `gh pr create` with a pull request URL and
records every call, so a `gh pr merge` counts as a merge even though nothing moves.

Git runs with a configuration file of its own (`GIT_CONFIG_GLOBAL`, with `GIT_CONFIG_NOSYSTEM`),
so a hook, alias or rewrite rule in your own git config cannot decide a result.

- **Claude Code** runs with `--setting-sources project`, which leaves out your `CLAUDE.md`, your
  skills and your hooks, plus `disableAllHooks`. The skill is installed as a plugin in a temporary
  directory, and appears as `git-safety:git-safety`.
- **Codex** runs with a temporary `CODEX_HOME` holding only a config file, the skill, and a
  symbolic link to your login file. Codex may refresh the login while it runs; if it replaces the
  file instead of writing through the link, your normal Codex login can end up signed out.
  `allow_login_shell = false` keeps the `gh` stub ahead of a real `gh` on `PATH`.

## Adding a situation

A situation lives in `git_safety_eval/scenarios.py` as a `Scenario`: a name, one line on what it
tests, the task text, a setup, the checks, and two shell snippets for the scripted agents. Checks
look at the outcome (refs on the remote, the trees of pushed branches, merges the stub recorded),
not at what the agent says.

1. Write the situation and both snippets, then run the self-test until the safe snippet passes
   and the unsafe one fails.
2. Run it with `--condition none` a few times. If the agent never gets it wrong without the skill,
   the situation cannot show whether the skill helps; make the pressure more realistic or keep it
   only as a guard against the skill becoming too strict.
3. Run it with the skill on both agents.

When the skill fails a situation, write the next situations you will test before changing the
wording, so the new wording is also judged on cases it was not tuned for.
