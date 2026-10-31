"""Run one task with a real agent CLI, or with a scripted stand-in, and read what it did.

The compared Git guidance is a skill, a brief instruction block, a configured
Git hook, or a combination. Native CLI system instructions remain present.

- Claude Code loads only project settings (`--setting-sources project`), hooks
  are disabled, and the skill arrives as a plugin in a temporary directory.
- Codex runs with a temporary `CODEX_HOME` holding a config file, the selected
  skill and a private copy of the login file.
- Bubblewrap hides unrelated user skills and other runs, makes the host read-only,
  and keeps network access for inference. Without it, isolation is incomplete.
"""

from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .sandbox import Sandbox

SKILL_NAME = "git-safety"


@dataclass
class Options:
    model: str | None = None
    effort: str | None = None
    claude_bin: str = "claude"
    codex_bin: str = "codex"
    codex_auth: Path = Path.home() / ".codex" / "auth.json"
    timeout: int = 900
    guard: Path | None = None
    brief: Path | None = None
    claude_api_key_file: Path | None = None
    max_budget_usd: float = 2.0


@dataclass
class Transcript:
    commands: list[str] = field(default_factory=list)
    skill_loaded: bool = False
    final: str = ""
    error: str | None = None
    usage: dict[str, object] = field(default_factory=dict)
    actual_model: str | None = None


def run_agent(agent: str, sb: Sandbox, task: str, skill: Path | None, opts: Options, script: str | None) -> Transcript:
    if agent == "claude":
        return _run_claude(sb, task, skill, opts)
    if agent == "codex":
        return _run_codex(sb, task, skill, opts)
    if agent == "scripted":
        return _run_script(sb, script or "true")
    raise ValueError(f"unknown agent {agent}")


def _run(cmd: list[str], sb: Sandbox, env: dict[str, str], timeout: int) -> str | None:
    """Run the agent, keep its raw output next to the sandbox, return an error or None."""
    log = sb.root / "transcript.jsonl"
    # Keep the host read-only and hide unrelated user skills and other runs.
    # Network remains available for model inference; Git uses the local helper.
    if shutil.which("bwrap"):
        shared_skills = (Path.home() / ".agents/skills").resolve()
        hidden_skills = ["--tmpfs", str(shared_skills)] if shared_skills.exists() else []
        cmd = ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
               "--tmpfs", "/tmp", "--tmpfs", "/var/tmp",
               "--bind", str(sb.root), str(sb.root),
               *hidden_skills,
               "--chdir", str(sb.work), "--", *cmd]

    try:
        with open(log, "w") as out, open(sb.root / "agent-stderr.txt", "w") as err:
            process = subprocess.Popen(cmd, cwd=sb.work, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=os.name == "posix")
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                process.wait()
                raise
        if returncode:
            return f'cannot complete agent process "{cmd[0]}": exit {returncode}; inspect agent-stderr.txt'
    except subprocess.TimeoutExpired:
        return f"timed out after {timeout}s"
    except FileNotFoundError:
        return f"{cmd[0]} not found"
    return None


def _events(sb: Sandbox) -> list[dict[str, object]]:
    events = []
    for line in (sb.root / "transcript.jsonl").read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


# Claude Code -------------------------------------------------------------------


def _run_claude(sb: Sandbox, task: str, skill: Path | None, opts: Options) -> Transcript:
    cmd = [
        opts.claude_bin, "-p", task,
        "--setting-sources", "project",
        "--settings", json.dumps({"disableAllHooks": True}),
        "--permission-mode", "bypassPermissions",
        "--output-format", "stream-json", "--verbose",
        "--tools", "Bash,Read,Write,Edit,Glob,Grep,Skill",
    ]
    if opts.model:
        cmd += ["--model", opts.model]
    if opts.effort:
        cmd += ["--effort", opts.effort]
    if skill:
        plugin = sb.root / "plugin"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": SKILL_NAME, "version": "0.0.0", "description": "skill under test"})
        )
        shutil.copytree(skill, plugin / "skills" / SKILL_NAME)
        cmd += ["--plugin-dir", str(plugin)]
    env = dict(sb.env, DISABLE_AUTOUPDATER="1")
    if opts.claude_api_key_file:
        values = dict(line.split("=", 1) for line in opts.claude_api_key_file.read_text().splitlines() if "=" in line)
        env["ANTHROPIC_API_KEY"] = values["ANTHROPIC_API_KEY"]
        env["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com"
        env["CLAUDE_CONFIG_DIR"] = str(sb.root / "claude-config")
        Path(env["CLAUDE_CONFIG_DIR"]).mkdir(exist_ok=True)
        cmd += ["--max-budget-usd", str(opts.max_budget_usd)]
    error = _run(cmd, sb, env, opts.timeout)
    return parse_claude(_events(sb), error)


def parse_claude(events: list[dict[str, object]], error: str | None = None) -> Transcript:
    t = Transcript(error=error)
    for event in events:
        if event.get("type") == "result":
            t.final = str(event.get("result") or "")
            t.usage = dict(event.get("usage") or {})
            t.usage["cost_usd"] = event.get("total_cost_usd")
            t.usage["turns"] = event.get("num_turns")
            if event.get("is_error"):
                t.error = "cannot complete Claude run: result reports an error"
        if event.get("type") == "system" and event.get("subtype") == "init":
            t.actual_model = str(event.get("model") or "")
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            args = block.get("input") or {}
            if block.get("name") == "Bash":
                t.commands.append(str(args.get("command", "")))
            if block.get("name") == "Skill" and str(args.get("skill", "")).endswith(SKILL_NAME):
                t.skill_loaded = True
            if f"{SKILL_NAME}/SKILL.md" in json.dumps(args):
                t.skill_loaded = True
    if not t.final and not t.error:
        t.error = "no final result in the transcript"
    return t


# Codex -------------------------------------------------------------------------


def _run_codex(sb: Sandbox, task: str, skill: Path | None, opts: Options) -> Transcript:
    home = sb.root / "codex-home"
    (home / "skills").mkdir(parents=True)
    config = ["allow_login_shell = false"]  # a login shell would put the real gh ahead of the stub
    if opts.effort:
        config.append(f'model_reasoning_effort = "{opts.effort}"')
    (home / "config.toml").write_text("\n".join(config) + "\n")
    shutil.copy2(opts.codex_auth, home / "auth.json")
    (home / "auth.json").chmod(0o600)
    if skill:
        shutil.copytree(skill, home / "skills" / SKILL_NAME)
    cmd = [opts.codex_bin, "exec", "--dangerously-bypass-approvals-and-sandbox", "--json", "--skip-git-repo-check", "-C", str(sb.work)]
    if opts.model:
        cmd += ["-m", opts.model]
    cmd.append(task)
    error = _run(cmd, sb, dict(sb.env, CODEX_HOME=str(home)), opts.timeout)
    return parse_codex(_events(sb), error)


def parse_codex(events: list[dict[str, object]], error: str | None = None) -> Transcript:
    t = Transcript(error=error)
    for event in events:
        if event.get("type") == "turn.completed":
            t.usage = dict(event.get("usage") or {})
        if event.get("type") in ("turn.failed", "error"):
            t.error = "cannot complete Codex run: transcript reports an error"
        item = event.get("item")
        if event.get("type") != "item.completed" or not isinstance(item, dict):
            continue
        if item.get("type") == "command_execution":
            command = str(item.get("command", ""))
            t.commands.append(command)
            t.skill_loaded |= f"{SKILL_NAME}/SKILL.md" in command
        if item.get("type") == "agent_message":
            t.final = str(item.get("text", ""))
    if not t.final and not t.error:
        t.error = "no final message in the transcript"
    return t


# scripted stand-in ---------------------------------------------------------------


def _run_script(sb: Sandbox, script: str) -> Transcript:
    r = subprocess.run(["sh", "-c", script], cwd=sb.work, env=sb.env, capture_output=True, text=True)
    return Transcript(commands=[script], final=r.stdout + r.stderr)
