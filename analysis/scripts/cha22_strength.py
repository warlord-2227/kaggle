import sys, os, statistics as st, importlib.util
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ["CHASSIS"] = "demand"
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C, evolve_market as E, trace_agent, fair_env
def load(p):
    sp = importlib.util.spec_from_file_location("opp", p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return [v for v in vars(m).values() if callable(v)][-1]
CHA = ROOT + "/refagents/public/cha22.py"
def h2h(job):
    opp, seed = job; fair_env.apply()
    from kaggle_environments import make as mk
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([load(CHA), C.load_opp(opp)]); f = env.steps[-1]; return "h2h", opp, f[0]["reward"], f[1]["reward"]
def tr(job):
    pool, i = job; fair_env.restore()
    from kaggle_environments import make as mk
    name, path, idx, rating = pool[i]
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": trace_agent.seed_of(path)}); env.run([load(CHA), trace_agent.make(path, idx)]); f = env.steps[-1]; return "trace", name[:1], f[0]["reward"], f[1]["reward"]
if __name__ == "__main__":
    top = [t for t in E.TRACE_POOL if E.bucket(t[3]) == "top"]; band = trace_agent.pool(folder="band2900")
    with ProcessPoolExecutor(10) as ex:
        r1 = list(ex.map(h2h, [(o, s) for o in ("mirror", "v56", "farm2945") for s in range(601, 609)]))
        r2 = list(ex.map(tr, [(top, i) for i in range(len(top))])); r3 = list(ex.map(tr, [(band, i) for i in range(len(band))]))
    for o in ("mirror", "v56", "farm2945"):
        r = [(a, b) for k, oo, a, b in r1 if oo == o]; print(f"cha22 vs {o:9s}: {sum(a > b for a, b in r)}-{sum(a < b for a, b in r)} {st.mean(a - b for a, b in r):+,.0f}", flush=True)
    for lab, r in (("top traces", r2), ("band2900 traces", r3)):
        print(f"cha22 vs {lab}: {sum(a > b for _, _, a, b in r)}-{sum(a < b for _, _, a, b in r)} {st.mean(a - b for _, _, a, b in r):+,.0f} ours {st.mean(a for _, _, a, _ in r):,.0f}", flush=True)
