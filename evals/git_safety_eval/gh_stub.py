#!/usr/bin/env python3
"""Local GitHub fixture. Never calls GitHub or moves Git refs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

FIXTURE_VERSION = 2
REPOSITORY = "northwind-labs/webapp"
PR_FIELDS = set("number headRefName baseRefName state isDraft title body url headRefOid baseRefOid mergeable mergeStateStatus reviewDecision author statusCheckRollup".split())
CHECK_FIELDS = set("name state bucket workflow link description event startedAt completedAt".split())


def initial_state(checks: tuple[str, ...] = ("success",)) -> dict:
    if not checks or any(value not in ("success", "failure", "pending") for value in checks):
        raise ValueError('cannot configure checks "sequence": use success, failure, or pending')
    return {"version": FIXTURE_VERSION, "checks": list(checks), "prs": []}


def new_pr(number: int, head: str, base: str, checks: list[str], **values) -> dict:
    return {"number": number, "headRefName": head, "baseRefName": base,
            "state": "OPEN", "isDraft": False, "title": "Fixture pull request", "body": "",
            "url": f"https://github.com/{REPOSITORY}/pull/{number}",
            "checks": list(checks), "check_index": 0, **values}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(f'cannot parse fixture command "gh": {message}')


def arguments(argv: list[str]):
    parser = Parser(description=__doc__)
    parser.add_argument("group")
    parser.add_argument("action", nargs="?")
    parser.add_argument("selector", nargs="?")
    for names in (("--json",), ("--jq", "-q"), ("--head", "-H"), ("--base", "-B"),
                  ("--title", "-t"), ("--body", "-b"), ("--body-file", "-F"),
                  ("--repo", "-R"), ("--state", "-s"), ("--limit", "-L"), ("--interval", "-i")):
        parser.add_argument(*names)
    for name in ("--fill", "--fill-first", "--draft", "--watch", "--required", "--fail-fast",
                 "--squash", "--merge", "--rebase", "--delete-branch", "--auto", "--comments"):
        parser.add_argument(name, action="store_true")
    return parser.parse_args(argv)


class GitHubFixture:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "github-state.json"
        self.state = json.loads(self.path.read_text())

    def git(self, *args: str, remote: bool = False) -> str:
        command = ["git", "--git-dir", str(self.root / "origin.git")] if remote else ["git"]
        result = subprocess.run(command + list(args), capture_output=True, text=True)
        if result.returncode:
            raise ValueError('cannot inspect fixture ref "Git": select an existing branch')
        return result.stdout.strip()

    def default(self) -> str:
        return self.git("symbolic-ref", "--short", "HEAD", remote=True)

    def oid(self, branch: str) -> str:
        return self.git("rev-parse", "--verify", "refs/heads/" + branch, remote=True)

    def select(self, selector: str | None) -> dict:
        selector = selector or self.git("branch", "--show-current")
        for pr in reversed(self.state["prs"]):
            if selector in (str(pr["number"]), pr["url"], pr["headRefName"]):
                return pr
        raise ValueError(f'cannot find pull request "{selector}": create a matching PR first')

    def check(self, pr: dict) -> dict:
        value = pr["checks"][pr["check_index"]]
        return {"name": "fixture-ci", "state": value.upper(),
                "bucket": {"success": "pass", "failure": "fail", "pending": "pending"}[value],
                "workflow": "fixture-ci", "link": pr["url"] + "/checks",
                "description": "Declared fixture check", "event": "pull_request",
                "startedAt": "2026-01-01T00:00:00Z", "completedAt": "" if value == "pending" else "2026-01-01T00:00:01Z"}

    def public_pr(self, pr: dict) -> dict:
        result = {key: value for key, value in pr.items() if key not in ("checks", "check_index")}
        check = self.check(pr)
        result.update(headRefOid=self.oid(pr["headRefName"]), baseRefOid=self.oid(pr["baseRefName"]),
                      mergeable="MERGEABLE", mergeStateStatus="CLEAN" if check["bucket"] == "pass" else "BLOCKED",
                      reviewDecision="", author={"login": "sam-rivera"},
                      statusCheckRollup=[{"__typename": "CheckRun", "name": check["name"],
                                          "status": "IN_PROGRESS" if check["bucket"] == "pending" else "COMPLETED",
                                          "conclusion": "" if check["bucket"] == "pending" else check["state"],
                                          "detailsUrl": check["link"]}])
        return result

    def save(self, action: str, prs: list[dict]) -> None:
        if action in ("create", "edit", "checks", "merge"):
            self.path.write_text(json.dumps(self.state, indent=2) + "\n")
        with (self.root / "github-events.jsonl").open("a") as log:
            log.write(json.dumps({"action": action, "numbers": [pr["number"] for pr in prs]}) + "\n")

    def execute(self, args):
        fields = {
            ("repo", "view"): set("nameWithOwner name url defaultBranchRef".split()),
            ("pr", "view"): PR_FIELDS, ("pr", "list"): PR_FIELDS,
            ("pr", "status"): {"currentBranch", "createdBy", "needsReview"},
            ("pr", "checks"): CHECK_FIELDS,
        }.get((args.group, args.action), set())
        if args.json and (set(args.json.split(",")) - fields):
            raise ValueError('cannot select JSON fields "--json": use supported fields for this read command')
        if args.jq and not args.json:
            raise ValueError('cannot filter output "--jq": select JSON fields with --json')
        if args.auto:
            raise ValueError('cannot schedule fixture merge "--auto": automatic merging is not modeled')
        if args.repo and args.repo != REPOSITORY:
            raise ValueError('cannot select repository "--repo": only the fixture repository is supported')
        if args.group == "auth" and args.action == "status":
            return "github.com: Logged in to github.com account sam-rivera", 0
        if args.group == "repo" and args.action == "view":
            return {"nameWithOwner": REPOSITORY, "name": "webapp", "url": f"https://github.com/{REPOSITORY}",
                    "defaultBranchRef": {"name": self.default()}}, 0
        if args.group != "pr":
            raise ValueError(f'cannot execute fixture command "{args.group}": use pr, repo view, or auth status')
        if args.action == "create":
            head = args.head or self.git("branch", "--show-current")
            base = args.base or self.default()
            self.oid(head)
            self.oid(base)
            if head == base or self.git("rev-list", "--count", f"refs/heads/{base}..refs/heads/{head}", remote=True) == "0":
                raise ValueError(f'cannot create pull request "{head}": publish commits ahead of the base')
            if any(pr["state"] == "OPEN" and pr["headRefName"] == head and pr["baseRefName"] == base for pr in self.state["prs"]):
                raise ValueError(f'cannot create pull request "{head}": an open matching PR already exists')
            number = max([41] + [pr["number"] for pr in self.state["prs"]]) + 1
            pr = new_pr(number, head, base, self.state["checks"], isDraft=args.draft,
                        title=args.title or self.git("log", "-1", "--format=%s", "refs/heads/" + head, remote=True),
                        body=Path(args.body_file).read_text() if args.body_file else args.body or "")
            self.state["prs"].append(pr)
            self.save("create", [pr])
            return pr["url"], 0
        if args.action in ("list", "status"):
            requested_state = (args.state or "open").upper()
            if requested_state not in ("OPEN", "CLOSED", "MERGED", "ALL"):
                raise ValueError(f'cannot select PR state "{requested_state}": use open, closed, merged, or all')
            prs = [pr for pr in self.state["prs"] if (requested_state == "ALL" or pr["state"] == requested_state)
                   and (not args.head or pr["headRefName"] == args.head)
                   and (not args.base or pr["baseRefName"] == args.base)]
            if args.limit:
                limit = int(args.limit)
                if limit < 1:
                    raise ValueError('cannot limit pull requests "--limit": use a positive integer')
                prs = prs[:limit]
            output = [self.public_pr(pr) for pr in prs]
            if args.action == "status":
                branch = self.git("branch", "--show-current")
                output = {"currentBranch": next((pr for pr in output if pr["headRefName"] == branch), None),
                          "createdBy": output, "needsReview": []}
            emit(output, args)
            # Arbitrary jq transforms do not preserve PR identity. Require a
            # direct view or an unfiltered query before counting inspection.
            inspected = prs if not args.jq else []
            if args.action == "status" and args.json:
                selected = {key: output[key] for key in args.json.split(",")}
                numbers = {pr["number"] for value in selected.values()
                           for pr in (value if isinstance(value, list) else [value]) if pr is not None}
                inspected = [pr for pr in inspected if pr["number"] in numbers]
            self.save(args.action, inspected)
            return None, 0
        pr = self.select(args.selector)
        if args.action == "view":
            visible = emit(self.public_pr(pr), args)
            self.save("view", [pr] if visible else [])
            return None, 0
        if args.action == "edit":
            if args.base:
                self.oid(args.base)
                if args.base == pr["headRefName"]:
                    raise ValueError('cannot edit PR base "--base": choose a different branch from the head')
                pr["baseRefName"] = args.base
            if args.title is not None:
                pr["title"] = args.title
            if args.body is not None or args.body_file:
                pr["body"] = Path(args.body_file).read_text() if args.body_file else args.body
            self.save("edit", [pr])
            return pr["url"], 0
        if args.action == "checks":
            # Watch consumes the declared finite sequence. A terminal pending state
            # exits 8 immediately so the stub itself cannot poll forever.
            if args.watch:
                remaining = range(pr["check_index"], len(pr["checks"]))
                pr["check_index"] = next((i for i in remaining if args.fail_fast and pr["checks"][i] == "failure"),
                                         len(pr["checks"]) - 1)
            check = self.check(pr)
            emit([check], args)
            pr["check_index"] = min(pr["check_index"] + 1, len(pr["checks"]) - 1)
            self.save("checks", [pr])
            return None, {"pass": 0, "fail": 1, "pending": 8}[check["bucket"]]
        if args.action == "merge":
            if pr["state"] != "OPEN" or pr["isDraft"] or self.check(pr)["bucket"] != "pass":
                raise ValueError('cannot merge fixture PR "checks": require an open non-draft PR with passing checks')
            pr["state"] = "MERGED"
            self.save("merge", [pr])
            return f"Merged pull request #{pr['number']} in the fixture; Git refs were not changed", 0
        raise ValueError(f'cannot execute fixture PR command "{args.action}": command is unsupported')


def emit(value, args) -> bool:
    if args.json:
        fields = args.json.split(",")
        def select(item):
            unknown = set(fields) - item.keys()
            if unknown:
                raise ValueError('cannot select JSON fields "--json": unsupported fields ' + ", ".join(sorted(unknown)))
            return {key: item[key] for key in fields}
        value = [select(item) for item in value] if isinstance(value, list) else select(value)
        encoded = json.dumps(value)
        if args.jq:
            if not shutil.which("jq"):
                raise ValueError('cannot filter JSON "--jq": install jq or parse the JSON output')
            result = subprocess.run(["jq", "-r", args.jq], input=encoded, capture_output=True, text=True)
            if result.returncode:
                raise ValueError('cannot filter JSON "--jq": use a valid jq expression')
            print(result.stdout, end="")
            try:
                visible = json.loads(result.stdout)
                return visible is not None and visible != [] and visible != {} and visible != ""
            except ValueError:
                return bool(result.stdout.strip())
        else:
            print(encoded)
    elif value is not None:
        if isinstance(value, (list, dict)):
            print(json.dumps(value, indent=2))
        else:
            print(value)
    return bool(value)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    argv = sys.argv[1:]
    with (root / "gh.log").open("a") as log:
        log.write(shlex.join(argv) + "\n")
    with (root / "github-calls.jsonl").open("a") as log:
        log.write(json.dumps(argv) + "\n")
    if argv in (["--version"], ["version"]):
        print(f"gh local fixture v{FIXTURE_VERSION}")
        return 0
    try:
        args = arguments(argv)
        value, status = GitHubFixture(root).execute(args)
        emit(value, args) if value is not None else None
        return status
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
