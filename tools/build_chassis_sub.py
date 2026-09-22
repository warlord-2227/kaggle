"""Build a submission = a public chassis file (byte-exact) + an appended block that overrides its module constants.
Usage: .venv/bin/python tools/build_chassis_sub.py <chassis name|path> <genome.json> <out.py> [--tag "v26 ..."]
The layers read module globals at call time, so the block changes play without editing the layers. Only constants that
differ from the file's own values are written. The file's last callable stays the entry point (Kaggle's loader rule)."""
import sys, os, json, argparse, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT + "experiments")
ap = argparse.ArgumentParser(); ap.add_argument("chassis"); ap.add_argument("genome"); ap.add_argument("out"); ap.add_argument("--tag", default="")
a = ap.parse_args()
os.environ["CHASSIS"] = a.chassis
import evolve_chassis as C
g = json.load(open(a.genome)); g = g.get("genome", g); B = C.base_genome()
src = open(C.CHASSIS).read()
lines = ["", "", "# " + "-" * 75, f"# IWA_setu {a.tag} constants re-tuned by search (experiments/evolve_chassis.py, CHASSIS={a.chassis}) against the reactive",
         "# public pool in refagents/public/. Everything above this block is the byte-exact public file (Apache-2.0, notices kept);",
         "# the layers read these module constants at call time, so overriding them here changes play without editing the layers.",
         "# " + "-" * 75]
n = 0
for k, v in g.items():
    if k not in C.SPACE or v == B.get(k): continue
    if k in ("OPEN_BUY", "OPEN_SELL"): continue
    lines.append(f"{k} = {repr(bool(v) if k in C.BOOLS else v)}"); n += 1
if "OPEN_BUY" in g and (g["OPEN_BUY"] != B.get("OPEN_BUY") or g["OPEN_SELL"] != B.get("OPEN_SELL")):
    lines.append(f'V9_OPENING_STEP0 = (("BUY_PRODUCT", "WHEAT", {int(g["OPEN_BUY"])}), ("SELL", "WHEAT", {int(g["OPEN_SELL"])}))'); n += 1
if src.rstrip().endswith("agent = globals().pop('agent')") or "\nagent = globals().pop(" in src[-400:]:
    lines.append("agent = globals().pop('agent')   # keep Kaggle's last-callable rule pointing at the full stack")
open(a.out, "w").write(src.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
print(f"wrote {a.out}: {n} constants overridden; last callable must be checked by the caller")
