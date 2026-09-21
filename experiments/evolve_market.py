"""(mu+lambda) search over the market agent's knobs (kaggriculture/agents/market.py).

Genome = a subset of market.DEFAULT (ints/floats/bools) mutated within ranges; the agent is
market.make(**genome). Sparring: pass, the meta line (Cleo), v20 (our best grove), and the
market defaults as mirror. Seeds mix normal and no-strawberry-shop ("glut") draws.
Log: experiments/evolve_market_log.jsonl; best: experiments/evolve_market_best.json.
"""
import sys, os, json, random, time, statistics as st, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor

OPPS = ["pass", ROOT + "refagents/closer_cleo.py", "v20", "market"]
GLUT = [9002, 9006, 9007, 9028, 9034, 9038, 9048, 9050]
SPACE = {  # name: (kind, lo, hi)
    "cows_d0": ("int", 1, 3), "sheep_d0": ("int", 1, 4), "herd_ramp_day": ("int", 3, 8), "herd_until": ("int", 12, 20),
    "milk_prior": ("float", 0, 10), "milk_prior_early": ("float", 2, 14), "prior_until": ("int", 6, 16),
    "wool_prior": ("float", 0, 8), "cows_min": ("int", 2, 6), "cows_max": ("int", 6, 14), "sheep_min": ("int", 1, 5),
    "sheep_max": ("int", 4, 12), "geese_max": ("int", 0, 12),
    "melon_tiles": ("int", 4, 16), "melon_until": ("int", 1, 4),
    "straw_prior": ("float", 0, 20), "straw_mult": ("float", 0.6, 1.8), "straw_min": ("int", 8, 24), "straw_max": ("int", 24, 48),
    "straw_until": ("int", 14, 20), "straw_rate": ("int", 4, 16), "straw_cash": ("int", 50, 600), "straw_priority_day": ("int", 2, 10),
    "wheat_mult": ("float", 0.3, 1.5), "wheat_feed_mult": ("float", 0.0, 1.0), "wheat_min": ("int", 4, 16), "wheat_max": ("int", 12, 44),
    "carrot_from": ("int", 4, 16), "carrot_max": ("int", 0, 24), "tomato_from": ("int", 4, 16), "tomato_max": ("int", 0, 12),
    "sprint_from": ("int", 18, 25), "sprint_until": ("int", 24, 27), "herd_reserve": ("int", 0, 900),
    "hands_day0": ("int", 3, 6), "hands_min": ("int", 3, 8), "hands_max": ("int", 8, 14), "work_per_unit": ("float", 4.0, 10.0),
    "feed_days": ("int", 1, 3), "cash_floor": ("int", 20, 300), "animals_per_day": ("int", 1, 10), "day0_wheat": ("int", 4, 14),
    "sell_chunk": ("int", 4, 14), "melon_chunk": ("int", 4, 12), "fert_reserve": ("int", 0, 4), "harvest_min_animal": ("int", 1, 3),
    "deliver_min": ("int", 300, 3000), "deliver_k": ("float", 0.1, 0.8), "deliver_min_early": ("int", 100, 1000), "deliver_early_until": ("int", 4, 14),
    "land_reserve": ("int", 0, 1500),
}
from kaggriculture.agents import market as M
BASE = {k: M.DEFAULT[k] for k in SPACE}

def play(job):
    g, opp, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    from kaggriculture.agents import market
    import importlib.util
    a = market.make(**g)
    if opp == "v20":
        sp = importlib.util.spec_from_file_location("m20", ROOT + "submissions/v20_grove_tuned2.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); b = m.agent
    elif opp == "market":
        b = market.make()
    else:
        b = opp
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]

def mutate(g, rng, k=4):
    c = dict(g)
    for key in rng.sample(list(SPACE), k):
        kind, lo, hi = SPACE[key]
        if kind == "int":
            span = max(1, (hi - lo) // 4); c[key] = min(hi, max(lo, c[key] + rng.randint(-span, span)))
        else:
            span = (hi - lo) / 4; c[key] = round(min(hi, max(lo, c[key] + rng.uniform(-span, span))), 2)
    return c

def evaluate(pop, seeds, ex):
    jobs = [(g, o, s) for g in pop for o in OPPS for s in seeds]
    res = list(ex.map(play, jobs, chunksize=1))
    out = []; k = len(OPPS) * len(seeds)
    for i, g in enumerate(pop):
        r = res[i * k:(i + 1) * k]; by = {}
        for j, o in enumerate(OPPS):
            rr = r[j * len(seeds):(j + 1) * len(seeds)]; by[os.path.basename(o)[:6]] = round(st.mean(a - b for a, b in rr))
        out.append(dict(genome=g, margin=st.mean(a - b for a, b in r), wins=sum(a > b for a, b in r) / k, ours=st.mean(a for a, _ in r), by_opp=by))
    return out

if __name__ == "__main__":
    MU, LAM, SEEDS = 4, 12, 3
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    log = open(ROOT + "experiments/evolve_market_log.jsonl", "a")
    elites = [dict(genome=dict(BASE))]; gen = 0
    try:
        prev = json.load(open(ROOT + "experiments/evolve_market_best.json"))["genome"]; elites.append(dict(genome={**BASE, **prev}))
    except Exception:
        pass
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 16))) as ex:
        while True:
            seeds = [rng.randrange(10**6) for _ in range(SEEDS - 1)] + [rng.choice(GLUT)]   # one glut seed per generation
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]; q = rng.choice(elites)["genome"]
                base = {k: (p[k] if rng.random() < 0.5 else q[k]) for k in p} if rng.random() < 0.3 else p
                children.append(mutate(base, rng))
            t0 = time.time(); scored = evaluate([e["genome"] for e in elites] + children, seeds, ex)
            for s in scored: log.write(json.dumps(dict(gen=gen, seeds=seeds, **s)) + "\n")
            log.flush(); scored.sort(key=lambda s: -s["margin"]); elites = scored[:MU]; b = elites[0]
            json.dump(b, open(ROOT + "experiments/evolve_market_best.json", "w"), indent=1)
            base_s = next((s for s in scored if s["genome"] == BASE), None)
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s best margin {b['margin']:>8,.0f} wins {b['wins']:.2f} ours {b['ours']:>8,.0f} {b['by_opp']} | base {round(base_s['margin']) if base_s else 'n/a'}", flush=True)
            print("     ", {k: v for k, v in b["genome"].items() if v != BASE[k]}, flush=True)
            gen += 1
