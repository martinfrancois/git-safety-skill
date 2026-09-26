"""Run one task with a real agent CLI, or with a scripted stand-in, and read what it did.

Both real adapters start the agent with none of the user's own instructions,
skills or hooks, so the only git guidance it has is the skill under test (or
nothing, for the baseline):

- Claude Code loads only project settings (`--setting-sources project`), hooks
  are disabled, and the skill arrives as a plugin in a temporary directory.
- Codex runs with a temporary `CODEX_HOME` holding only a config file, the skill
  and a link to the login file.
"""

from __future__ import annotations

import json
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


@dataclass
class Transcript:
    commands: list[str] = field(default_factory=list)
    skill_loaded: bool = False
    final: str = ""
    error: str | None = None


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
    try:
        with open(log, "w") as out, open(sb.root / "agent-stderr.txt", "w") as err:
            subprocess.run(cmd, cwd=sb.work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout)
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
    error = _run(cmd, sb, env, opts.timeout)
    return parse_claude(_events(sb), error)


def parse_claude(events: list[dict[str, object]], error: str | None = None) -> Transcript:
    t = Transcript(error=error)
    for event in events:
        if event.get("type") == "result":
            t.final = str(event.get("result") or "")
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
    (home / "auth.json").symlink_to(opts.codex_auth)
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
