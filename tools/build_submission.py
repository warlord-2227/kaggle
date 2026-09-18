#!/usr/bin/env python3
"""Build a self-contained main.py from an agent module.

Kaggle submits a single file, so the agent source lives in kaggriculture/agents/
for readability and gets inlined here. Run from the repo root:

    python tools/build_submission.py ranch --config "target={'COW':8,'SHEEP':5}, \
        feed_float_days=8, hands=8, land=2, buy_feed=True"
"""
import argparse
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / "kaggriculture" / "agents"

FOOTER = '''

# --- generated entry point -------------------------------------------------
_impl = make({config})


def agent(obs, config=None):
    try:
        return _impl(obs)
    except Exception:
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module", help="agent module name under kaggriculture/agents")
    ap.add_argument("--config", default="", help="kwargs passed to make()")
    ap.add_argument("--header", default="", help="path to a docstring header file")
    ap.add_argument("-o", "--out", default=str(ROOT / "main.py"))
    args = ap.parse_args()

    src = (AGENTS / f"{args.module}.py").read_text()
    if src.lstrip().startswith(('"""', "'''")):
        # Drop the module docstring; the submission header replaces it.
        src = re.sub(r'^\s*(""".*?"""|\'\'\'.*?\'\'\')\s*\n', "", src, count=1, flags=re.S)

    header = pathlib.Path(args.header).read_text() if args.header else ""
    out = header + src + FOOTER.format(config=args.config)
    pathlib.Path(args.out).write_text(out)

    compile(out, args.out, "exec")          # fail loudly rather than at submit time
    print(f"wrote {args.out} ({len(out.splitlines())} lines) from {args.module}")


if __name__ == "__main__":
    main()
