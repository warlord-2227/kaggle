import sys, os, json, statistics as st, importlib.util, time, glob
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ["CHASSIS"] = "demand"; os.environ["SELF_GENOME"] = "experiments/v31_demand_genome.json"
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
NEW = {n: f"{ROOT}/refagents/public/{f}" for n, f in (("v53", "ahmed_v53.py"), ("v55", "ahmed_v55.py"), ("cha22", "cha22.py"), ("multiroute", "multiroute_flexonafft.py"), ("master3", "masterengine3_guru.py"))}
def load(path):
    sp = importlib.util.spec_from_file_location("opp", path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return [v for v in vars(m).values() if callable(v)][-1]
def play(job):
    name, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    a = C.load_opp("self"); b = load(NEW[name])
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b]); f = env.steps[-1]
    return name, seed, f[0]["reward"], f[1]["reward"], f[1]["status"]
if __name__ == "__main__":
    for n, p in NEW.items():
        try: a = load(p); print(n, "loads:", getattr(a, "__name__", "?"), flush=True)
        except Exception as e: print(n, "LOAD ERROR", repr(e)[:100], flush=True)
    with ProcessPoolExecutor(12) as ex: res = list(ex.map(play, [(n, s) for n in NEW for s in range(601, 613)]))
    for n in NEW:
        r = [(a, b, s) for nn, sd, a, b, s in res if nn == n]
        print(f"v31 vs {n:10s}: {sum(a > b for a, b, _ in r)}-{sum(a < b for a, b, _ in r)} margin {st.mean(a - b for a, b, _ in r):+,.0f} ours {st.mean(a for a, _, _ in r):,.0f} theirs {st.mean(b for _, b, _ in r):,.0f} statuses {set(s for _, _, s in r)}", flush=True)
