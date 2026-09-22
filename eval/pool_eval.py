"""Standard verification of a candidate genome (the recipe that gated v23).

Usage: .venv/bin/python eval/pool_eval.py <genome.json> [--ref experiments/v23_genome.json] [--jobs 16]
(1) full replay pools on native seeds (ladder / mid / top buckets);
(2) fair-env: vs the reference genome (8 seeds), vs pass (4 seeds), glut seeds 9002/9006 vs pass.
Prints one summary line per part and writes <genome>.pool_eval.json next to the genome.
"""
import sys, os, json, statistics as st, pathlib, argparse
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "experiments"); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor
import evolve_market as E

def play_pair(job):
    g, ref, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    from kaggriculture.agents import market
    a = market.make(**g); b = "pass" if ref is None else market.make(**ref)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("genome"); ap.add_argument("--ref", default=ROOT + "experiments/v23_genome.json")
    ap.add_argument("--jobs", type=int, default=16); ap.add_argument("--no-fair", action="store_true"); a = ap.parse_args()
    g = json.load(open(a.genome)); g = g.get("genome", g); g = {**E.BASE, **{k: v for k, v in g.items() if k in E.SPACE}}
    ref = json.load(open(a.ref)); ref = ref.get("genome", ref); ref = {**E.BASE, **{k: v for k, v in ref.items() if k in E.SPACE}}
    out = {"genome": g}
    with ProcessPoolExecutor(a.jobs) as ex:
        res = E.fullpool(g, ex); out["pools"] = {k: v for k, v in res.items() if k != "by_opp"}; out["by_opp"] = res["by_opp"]
        print("POOLS ", E.fmt(res), flush=True)
        if not a.no_fair:
            jobs = [(g, ref, s) for s in range(101, 109)] + [(g, None, s) for s in range(201, 205)] + [(g, None, s) for s in (9002, 9006)]
            r = list(ex.map(play_pair, jobs))
            vr, vp, gl = r[:8], r[8:12], r[12:]
            out["fair"] = dict(vs_ref=vr, vs_pass=vp, glut=gl)
            print(f"FAIR   vs ref {sum(x > y for x, y in vr)}/8 margin {st.mean(x - y for x, y in vr):+,.0f} | vs pass {st.mean(x for x, _ in vp):,.0f} | glut {st.mean(x for x, _ in gl):,.0f}", flush=True)
    json.dump(out, open(a.genome + ".pool_eval.json", "w"), indent=1)
