---
name: git-safety
description: Preserve work while committing, rewriting PR history, pushing, merging, reverting, or deleting Git refs, including scripts that perform those actions. Read before the first Git write and when a push is rejected.
---

# Git safety

Complete the authorized work while preserving changes other people or systems
rely on. Keep one cohesive commit per logical change. A clean history does not
require preserving every intermediate commit ID.

## Actions that still need approval

Updating `main`, `master`, the actual default branch, or a protected/shared
integration branch requires approval for that specific action or an explicit
standing rule. This includes merges through `gh`, direct pushes, and scripts.
Resolve the actual destination before acting, including configured push refspecs
and the base branch of an API merge.

Deleting or moving somebody else's remote branch or a published tag also needs
specific approval. A request to clean up merged branches covers branches proven
merged; it does not cover unmerged work or release refs.

A go-ahead names the action, such as "push directly to main" or "merge PR #42",
or is an explicit standing rule for that action. Asking for an outcome or a
destination, including "get main green" or "get that onto main", grants no push
or merge approval. Prepare a branch and PR, then wait for the user's decision.
Urgency, "full authority", "ship it", an unavailable user, missing PR tooling,
and absent branch protection do not change that boundary. Approval to rewrite a
PR branch does not authorize updating its base branch.

Immediately before any protected-branch update, state the operation and target,
then quote the existing user instruction or standing rule that authorizes that
specific operation. Apply the distinction above to that quote. Do not substitute
your interpretation of the desired outcome or invent an approval. If no matching
authorization exists, publish the verified fix on a task branch and prepare the
PR; leave the protected update pending. Continue other authorized work.

Keep authorization separate from technical safety. A valid fix, a fast-forward,
an identical tree, passing tests, or repairing damage you caused does not grant
permission to update a protected branch. Check authorization again at execution
time even if you considered it earlier. This check requires no fresh permission
for a task-branch rewrite already covered by standing approval.

## Routine branch work

Branch, commit, push task branches, and open pull requests. When the user grants
standing approval for routine PR rewrites, amend, squash, rebase, and force-push
those branches without requesting approval for each update. This includes
integrating remote work and retrying after a rejected push. Without that standing
approval or a task that requests the rewrite, ask before rewriting published work.

Before each commit, inspect `git diff --cached --stat` and the relevant diff.
Account for every file and exclude secrets. If a tool deletes tracked files that
the task did not intend to remove, stop before committing or pushing those
deletions and tell the user. A formatter's "generated" label, lack of imports,
passing tests, recoverability from Git, or a PR warning does not establish that
deletion is intended. "Commit whatever it changes" does not authorize unrelated
source removal. Preserve the original files and continue only with changes whose
intent is clear. Ask when restoring them or changing the tool needs a decision.

Before rewriting or reverting, require a full history. If
`git rev-parse --is-shallow-repository` returns `true`, fetch the missing history
or use a full clone before continuing.

## Safe rewrites

1. Identify the actual push repository and destination ref. Check the remote's
   default branch and repository protection rules. Save the local starting tip
   in a backup ref. Use a named local branch so its reflog records the rewrite.
2. Fetch the destination branch and record its full object ID. Before rewriting,
   ensure that tip is an ancestor of your starting branch. If the histories
   diverge, inspect and incorporate the remote changes first. Fetching alone does
   not incorporate them. If a rewrite already happened, recover the previous tip
   from the reflog or backup and compare both histories.
3. Preserve the remote changes and contributor attribution while folding fixes
   into their logical commits. Review the final tree and patch series. A
   history-only cleanup must leave the tree unchanged. For a rebase or integration,
   account for changes against both inputs and run the relevant checks.
4. Push one explicit branch refspec with a lease pinned to the incorporated
   remote tip, for example:

   ```sh
   git -c push.followTags=false push \
     --force-with-lease="refs/heads/$target:$expected_oid" \
     "$remote" "refs/heads/$source:refs/heads/$target"
   ```

   Verify the variables and destination first. Use a single push destination,
   without mirror settings. Keep the recorded lease fixed while preparing this
   candidate. Never substitute plain `--force`, `-f`, a `+` refspec, or an
   unpinned lease. `--force-if-includes` adds no check to an explicit-ID lease.
5. If the remote advanced, fetch and inspect the new changes, integrate them,
   redo the cleanup and validation, and retry with the newly incorporated tip as
   the lease. Preserve both inputs in backup refs. Do not merely refresh the lease
   and resend the old candidate. Ask only for unclear conflict intent or repeated
   concurrent updates that prevent convergence. Verify the published result.

## Failed checks and damage

A rejection stops that attempt. Identify and satisfy the failed check before
retrying. Standing approval for rewrites never authorizes disabling hooks,
clearing agent markers, `--no-verify`, or `AGENT_GUARD_APPROVE`. Those overrides
require the user's specific permission. A hook passing does not prove that the
result preserves the intended behavior.

If a push already damaged shared work, report it before repairing it, and repair
with an additional commit. If a tool reports success but the repository disagrees,
report the mismatch instead of forcing the result through another route.
