"""Run scenarios against an agent, record every result, and summarise."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .agents import Options, run_agent
from .sandbox import Sandbox
from .scenarios import BY_NAME, SCENARIOS, Run, Scenario, no_hook_bypass

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SKILL = REPO / "skills" / "git-safety"


def run_one(agent: str, condition: str, scenario: Scenario, rep: int, out: Path, remote: str,
            skill: Path, opts: Options, script: str | None = None) -> dict[str, object]:
    sb = Sandbox(out / "runs" / f"{agent}-{condition}-{scenario.name}-{rep}", remote=remote)
    scenario.setup(sb)
    before = sb.refs()
    if "guard" in condition:
        if opts.guard is None:
            raise ValueError('cannot install guard "--guard": provide a hook path')
        probe = sb.git(sb.work, "-c", "hook.eval-capability.event=pre-push",
                       "-c", "hook.eval-capability.command=:", "hook", "list", "pre-push")
        if "eval-capability" not in probe.splitlines():
            raise ValueError('cannot install guard "configured hooks": Git did not report the capability probe')
        guard = sb.root / "guard"
        shutil.copy2(opts.guard, guard)
        guard.chmod(0o755)
        # Config hooks coexist with fixture and repository hooks. Install after setup.
        sb.git(sb.work, "config", "--global", "hook.eval-guard.event", "pre-push")
        sb.git(sb.work, "config", "--global", "hook.eval-guard.command", f"'{guard}'" + (" --config-hook" if "--config-hook" in guard.read_text() else "" ))
        sb.env["AGENT_GUARD"] = "1"
    if "brief" in condition:
        if opts.brief is None:
            raise ValueError('cannot install instructions "--brief": provide a file path')
        (sb.root / ("CLAUDE.md" if agent == "claude" else "AGENTS.md")).write_text(opts.brief.read_text())
    started = time.monotonic()
    transcript = run_agent(agent, sb, scenario.task.replace("{url}", sb.url),
                           skill if "skill" in condition else None, opts, script)
    run = Run(before=before, after=sb.refs(), commands=transcript.commands)
    (sb.root / "refs.json").write_text(json.dumps({"before": run.before, "after": run.after}, indent=2))
    failures = scenario.failures(sb, run)
    if "guard" in condition:
        failures = list(dict.fromkeys(failures + no_hook_bypass(sb, run)))
    completion_failures = [reason for check in scenario.completion_checks for reason in check(sb, run)]
    verdict = "error" if transcript.error else ("fail" if failures or completion_failures else "pass")
    return {
        "agent": agent, "model": opts.model, "condition": condition, "scenario": scenario.name,
        "rep": rep, "verdict": verdict, "failures": failures, "error": transcript.error,
        "completion_failures": completion_failures, "safe": not failures,
        "completed": not completion_failures if scenario.completion_checks else None,
        "commands": len(transcript.commands), "usage": transcript.usage, "actual_model": transcript.actual_model,
        "skill_loaded": transcript.skill_loaded, "seconds": round(time.monotonic() - started),
        "sandbox": str(sb.root), "final": transcript.final[-600:],
    }


def summarise(results: list[dict[str, object]]) -> str:
    counts: dict[tuple[str, str], Counter[str]] = {}
    for r in results:
        counts.setdefault((str(r["condition"]), str(r["scenario"])), Counter())[str(r["verdict"])] += 1
    lines = ["| condition | scenario | pass | fail | error |", "| --- | --- | --- | --- | --- |"]
    for (condition, scenario), c in sorted(counts.items()):
        lines.append(f"| {condition} | {scenario} | {c['pass']} | {c['fail']} | {c['error']} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", choices=["claude", "codex"], required=True)
    p.add_argument("--condition", choices=["skill", "none", "brief", "guard", "brief-guard", "skill-guard"], default="skill",
                   help="skill: install the skill; none: the baseline with no git guidance")
    p.add_argument("--scenario", action="append", choices=sorted(BY_NAME), help="repeat to pick several; default all")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--guard", type=Path)
    p.add_argument("--brief", type=Path)
    p.add_argument("--model")
    p.add_argument("--effort", help="reasoning effort passed to the agent")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--remote", choices=["file", "https"], default="file",
                   help="file: a file:// remote; https: a local remote that reads as a GitHub URL")
    p.add_argument("--skill", type=Path, default=DEFAULT_SKILL)
    p.add_argument("--claude-api-key-file", type=Path)
    p.add_argument("--max-budget-usd", type=float, default=2.0)
    p.add_argument("--claude-bin", default="claude")
    p.add_argument("--codex-bin", default="codex")
    p.add_argument("--codex-auth", type=Path, default=Options.codex_auth,
                   help="login file copied into the temporary CODEX_HOME")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--out", type=Path, default=Path("/var/tmp/git-safety-evals") / time.strftime("%Y%m%d-%H%M%S"))
    args = p.parse_args(argv)

    opts = Options(model=args.model, effort=args.effort, claude_bin=args.claude_bin, codex_bin=args.codex_bin,
                   codex_auth=args.codex_auth, timeout=args.timeout, guard=args.guard, brief=args.brief, claude_api_key_file=args.claude_api_key_file, max_budget_usd=args.max_budget_usd)
    scenarios = [BY_NAME[n] for n in args.scenario] if args.scenario else SCENARIOS
    jobs = [(s, rep) for rep in range(1, args.reps + 1) for s in scenarios]
    args.out.mkdir(parents=True, exist_ok=True)
    results_file = args.out / "results.jsonl"
    results: list[dict[str, object]] = []

    def job(item: tuple[Scenario, int]) -> dict[str, object]:
        scenario, rep = item
        return run_one(args.agent, args.condition, scenario, rep, args.out, args.remote, args.skill, opts)

    with ThreadPoolExecutor(max_workers=args.parallel) as pool, open(results_file, "a") as f:
        for r in pool.map(job, jobs):
            results.append(r)
            f.write(json.dumps(r) + "\n")
            f.flush()
            failures = r["failures"] + r["completion_failures"]
            detail = "; ".join(failures) if isinstance(failures, list) and failures else str(r["error"] or "")
            print(f"{r['verdict']:5} {r['scenario']:14} rep {r['rep']}  skill loaded: {r['skill_loaded']}  {detail}",
                  flush=True)

    summary = summarise(results)
    (args.out / "summary.md").write_text(summary + "\n")
    print("\n" + summary + f"\n\nresults: {results_file}")
    bad = [r for r in results if r["verdict"] != "pass"]
    if args.condition != "none" and bad:
        print(f"\n{len(bad)} of {len(results)} runs did not pass", file=sys.stderr)
        return 1
    return 0
