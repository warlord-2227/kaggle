"""Verify a built submission file plays identically to the tuner's make_agent(genome): same rewards on fixed seeds vs a fixed opponent.
Usage: CHASSIS=cha22 .venv/bin/python analysis/scripts/verify_build.py <built.py> <genome.json> [seeds=601,602] [opp=demand]"""
import sys, os, json, importlib.util
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ.setdefault("CHASSIS", "cha22")
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
BUILT, GEN = sys.argv[1], sys.argv[2]
SEEDS = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "601,602").split(",")]; OPP = sys.argv[4] if len(sys.argv) > 4 else "demand"
def load_file(path):
    sp = importlib.util.spec_from_file_location("built_sub", path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    c = [v for v in vars(m).values() if callable(v)][-1]; return c
def play(job):
    kind, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    if kind == "file": a = load_file(BUILT)
    else:
        g = json.load(open(GEN)); g = g.get("genome", g); a = C.make_agent({**C.base_genome(), **{k: v for k, v in g.items() if k in C.SPACE}}, tag="verify")
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, C.load_opp(OPP)]); f = env.steps[-1]
    return kind, seed, f[0]["reward"], f[1]["reward"], f[0]["status"]
if __name__ == "__main__":
    print("built file last callable:", getattr(load_file(BUILT), "__name__", "?"), flush=True)
    with ProcessPoolExecutor(4) as ex: res = list(ex.map(play, [(k, s) for s in SEEDS for k in ("file", "genome")]))
    ok = True
    for s in SEEDS:
        f = [r for r in res if r[0] == "file" and r[1] == s][0]; g = [r for r in res if r[0] == "genome" and r[1] == s][0]
        same = f[2:] == g[2:]; ok &= same
        print(f"seed {s}: file {f[2]:,} vs {OPP} {f[3]:,} [{f[4]}] | genome {g[2]:,} vs {g[3]:,} [{g[4]}] -> {'IDENTICAL' if same else 'DIFFER'}", flush=True)
    print("VERIFY", "PASS" if ok else "FAIL")
