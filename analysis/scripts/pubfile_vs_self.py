"""Paired both-seat head-to-head: a public file (last-callable entry) vs one of our genome builds.
Usage: CHASSIS=<cha22|demand> .venv/bin/python analysis/scripts/pubfile_vs_self.py <pubfile.py> <genome.json> [seeds=601-616] [jobs=8]"""
import sys, os, json, statistics as st, importlib.util
os.environ["PYTHONWARNINGS"] = "ignore"
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
PUB, GEN = sys.argv[1], sys.argv[2]; lo, hi = map(int, (sys.argv[3] if len(sys.argv) > 3 else "601-616").split("-")); JOBS = int(sys.argv[4]) if len(sys.argv) > 4 else 8
def load(path):
    sp = importlib.util.spec_from_file_location("pub_" + os.path.basename(path)[:-3], path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return [v for v in vars(m).values() if callable(v)][-1]
def play(job):
    seed, swap = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    g = json.load(open(GEN)); g = g.get("genome", g); a = C.make_agent({**C.base_genome(), **{k: v for k, v in g.items() if k in C.SPACE}}, tag="self"); b = load(PUB)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([b, a] if swap else [a, b]); f = env.steps[-1]
    ra, rb = (f[1]["reward"], f[0]["reward"]) if swap else (f[0]["reward"], f[1]["reward"]); return seed, swap, ra, rb, f[0]["status"], f[1]["status"]
if __name__ == "__main__":
    with ProcessPoolExecutor(JOBS) as ex: res = list(ex.map(play, [(s, sw) for s in range(lo, hi + 1) for sw in (0, 1)], chunksize=1))
    for lab, r in (("self first", [x for x in res if not x[1]]), ("self second", [x for x in res if x[1]]), ("ALL", res)):
        print(f"{os.path.basename(GEN)} vs {os.path.basename(PUB)} [{lab}]: {sum(a > b for _, _, a, b, _, _ in r)}-{sum(a < b for _, _, a, b, _, _ in r)} margin {st.mean(a - b for _, _, a, b, _, _ in r):+,.0f} ours {st.mean(a for _, _, a, _, _, _ in r):,.0f} statuses {set(s for *_, s, t in r) | set(t for *_, s, t in r)}", flush=True)
