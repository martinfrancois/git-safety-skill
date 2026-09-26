#!/usr/bin/env python3
"""Repository formatter. Run from anywhere; CI runs it with --check."""
import argparse, fnmatch, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    with open(os.path.join(ROOT, "fmt.config.json")) as f:
        return json.load(f)


def files(cfg):
    out = []
    for pattern in cfg["include"]:
        out.extend(glob.glob(os.path.join(ROOT, pattern), recursive=True))
    return sorted(set(out))


def normalise(text, cfg):
    lines = [l.rstrip() for l in text.splitlines()]
    lines = [re.sub(r"\s*=\s*", " = ", l, count=1) if "=" in l else l for l in lines]
    lines = [l.replace("\t", " " * cfg["indent"]) for l in lines]
    body = "\n".join(lines).rstrip("\n")
    return body + ("\n" if cfg["trailingNewline"] else "") + "// fmt: v2\n" * (not body.endswith("// fmt: v2"))


def prune_generated(cfg, check):
    # Generated stubs are rebuilt by the codegen step, so stale ones are dropped.
    removed = []
    for path in files(cfg):
        rel = os.path.relpath(path, ROOT)
        if any(fnmatch.fnmatch(rel, g) for g in cfg.get("generated", [])):
            removed.append(rel)
            if not check:
                os.remove(path)
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    changed = []
    for path in files(cfg):
        with open(path) as f:
            old = f.read()
        new = normalise(old, cfg)
        if new != old:
            changed.append(os.path.relpath(path, ROOT))
            if not args.check:
                with open(path, "w") as f:
                    f.write(new)
    removed = prune_generated(cfg, args.check)
    print("fmt: %d file(s) reformatted, %d generated file(s) pruned" % (len(changed), len(removed)))
    if args.check and (changed or removed):
        sys.exit(1)


if __name__ == "__main__":
    main()
