---
name: git-safety
description: Rules for git and GitHub actions that change what other people see. Read before the first commit, push, merge, force-push, revert, reset, rebase, tag, or branch deletion, and before running a script or test that could push. Applies with extra force when the task is urgent or the user is unavailable.
---

# Git safety

**Shared state** is anything outside your own working copy that other people or systems rely on: the default branch, pull request merges, branches others push to, tags, releases, and remote history. You work freely up to the edge of shared state. Crossing it is the user's decision.

## Yours to do

- Branch, commit, push branches you created, and open pull requests.
- Before every commit, read `git diff --cached --stat` and account for every file it lists. A file or a deletion you did not intend, or anything that looks like a secret: stop and tell the user.

## The user's to decide

Each of these needs the user's go-ahead for that specific action:

- Updating the default branch in any way: a push, a merge, `gh pr merge`, or a script that does either.
- Force-pushing or rewriting anything already pushed, and deleting or moving remote branches or tags that you did not create in this task.
- Bypassing a check: `--no-verify`, `AGENT_GUARD_APPROVE`, clearing the environment marker a guard uses to tell an agent from a human (`CLAUDECODE`, `CODEX_THREAD_ID`).

A go-ahead names the action, like "merge #42", "push this straight to main" or "delete the merged branches", or it is a standing rule in the user's own instructions. Asking for an outcome or a destination, like "get main green", "get this onto main" or "ship it", names no action: the route there is a pull request. Nothing else is a go-ahead either: not urgency, not "full authority" or "do whatever it takes", not "don't wait for me" or "I can't be reached", not missing pull request tooling, and not the absence of a hook or branch protection. These rules exist for exactly those moments, because that is when a mistake costs most and nobody is checking.

When a named action clearly covers some targets and not others, do the clear ones and ask about the rest. A target is never clear if acting on it would lose work that exists nowhere else, or would change something already published.

## At the edge

Stop at the last safe step and make the rest a one-step decision: the fix on a branch, pushed, verified, and a pull request open whenever the tooling works. Give a raw command only when it does not. Then write a short report of what is ready and the one step the user takes. Then carry on with any work that does not cross the edge.

## When something goes wrong

- A rejected push is a stop signal: fetch, look at the remote, tell the user. Force-push only with approval, and only with `--force-with-lease --force-if-includes`.
- If a push already did damage, tell the user before you repair it, and repair by adding commits.
- If a tool reports success but the repository says otherwise, report the mismatch. Do not reach the same result by another route.
