"""Paired head-to-head of two chassis genomes (same chassis), same shops both sides, both seat orders.
Usage: CHASSIS=cha22 .venv/bin/python analysis/scripts/genome_h2h.py <A.json> <B.json> [seeds=601-664] [jobs=8]"""
import sys, os, json, statistics as st
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ.setdefault("CHASSIS", "cha22")
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
A, B = sys.argv[1], sys.argv[2]; lo, hi = map(int, (sys.argv[3] if len(sys.argv) > 3 else "601-664").split("-")); JOBS = int(sys.argv[4]) if len(sys.argv) > 4 else 8
def gen(p):
    g = json.load(open(p)); g = g.get("genome", g); return {**C.base_genome(), **{k: v for k, v in g.items() if k in C.SPACE}}
def play(job):
    seed, swap = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    a, b = C.make_agent(gen(A), tag="A"), C.make_agent(gen(B), tag="B")
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([b, a] if swap else [a, b]); f = env.steps[-1]
    ra, rb = (f[1]["reward"], f[0]["reward"]) if swap else (f[0]["reward"], f[1]["reward"]); return seed, swap, ra, rb
if __name__ == "__main__":
    with ProcessPoolExecutor(JOBS) as ex: res = list(ex.map(play, [(s, sw) for s in range(lo, hi + 1) for sw in (0, 1)], chunksize=1))
    for lab, r in (("A first", [x for x in res if not x[1]]), ("A second", [x for x in res if x[1]]), ("ALL", res)):
        print(f"{os.path.basename(A)} vs {os.path.basename(B)} [{lab}]: {sum(a > b for _, _, a, b in r)}-{sum(a < b for _, _, a, b in r)} ties {sum(a == b for _, _, a, b in r)} margin {st.mean(a - b for _, _, a, b in r):+,.0f}", flush=True)
