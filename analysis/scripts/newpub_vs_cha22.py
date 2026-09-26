"""Paired head-to-head of cha22 (our base) vs newly pulled public files, same shops both sides (fair_env), seeds 601-612.
Usage: .venv/bin/python analysis/scripts/newpub_vs_cha22.py [jobs]"""
import sys, os, statistics as st, importlib.util
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ["CHASSIS"] = "cha22"
ROOT = "/home/iwa/working/kaggle"; sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/eval"); sys.path.insert(0, ROOT + "/experiments")
from concurrent.futures import ProcessPoolExecutor
NEW = {n: f"{ROOT}/refagents/public/{f}" for n, f in (("v34", "ahmed_v34.py"), ("v41", "ahmed_v41.py"), ("me53e", "masterengine_v53e_guru.py"),
       ("marketshock", "marketshock_m1_leoprovorov.py"), ("v43", "arsgorynich_v43.py"), ("herdsafe3", "arsgorynich_herdsafe_v3.py"))}
CHA = ROOT + "/refagents/public/cha22.py"
ENTRY = {"marketshock": "agent"}   # override of the last-callable rule (its last callable is a patch factory -> 3,000 coins)
def load(path, entry=None):
    sp = importlib.util.spec_from_file_location("opp_" + os.path.basename(path)[:-3], path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return getattr(m, entry) if entry else [v for v in vars(m).values() if callable(v)][-1]
def play(job):
    name, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    a = load(CHA); b = load(NEW[name], ENTRY.get(name))
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b]); f = env.steps[-1]
    return name, seed, f[0]["reward"], f[1]["reward"], f[1]["status"]
if __name__ == "__main__":
    jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    if len(sys.argv) > 2: NEW = {k: v for k, v in NEW.items() if k in sys.argv[2].split(",")}
    for n, p in NEW.items():
        try: a = load(p, ENTRY.get(n)); print(n, "loads:", getattr(a, "__name__", "?"), flush=True)
        except Exception as e: print(n, "LOAD ERROR", repr(e)[:120], flush=True)
    with ProcessPoolExecutor(jobs) as ex: res = list(ex.map(play, [(n, s) for n in NEW for s in range(601, 613)]))
    for n in NEW:
        r = [(a, b, s) for nn, sd, a, b, s in res if nn == n]
        print(f"cha22 vs {n:12s}: {sum(a > b for a, b, _ in r)}-{sum(a < b for a, b, _ in r)} margin {st.mean(a - b for a, b, _ in r):+,.0f} ours {st.mean(a for a, _, _ in r):,.0f} theirs {st.mean(b for _, b, _ in r):,.0f} statuses {set(s for _, _, s in r)}", flush=True)
