"""(mu+lambda) search over the grove agent's schedule knobs on the fair environment.

Sparring set: pass (absolute economy), the tier-9 meta line (the target), v16 (our
previous ranch) and grove itself (mirror). Fitness = mean coin margin.
Log: experiments/evolve_grove_log.jsonl; best: experiments/evolve_grove_best.json.
"""
import sys, os, json, random, time, statistics as st, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor

V16 = dict(target={'COW': 8, 'SHEEP': 4}, feed_float_days=10, hands=6, land=1, buy_feed=True,
           grow_surplus=True, deny_ranchers=True, deny_mode='buyers', zone_mode='bands',
           max_wheat=15, n_melon=17, melon_rate=3, animal_batch=1, animal_buffer=104,
           hands_mode='flat', day0={'COW': 2, 'SHEEP': 1})
OPPS = ["pass", ROOT + "refagents/closer_cleo.py", "v16", "grove"]
SPACE = {
    "straw_rate": ("int", 3, 10), "straw_cash": ("int", 100, 800), "straw_start": ("int", 3, 9),
    "straw_peak": ("int", 20, 52), "straw_peak_day": ("int", 11, 16), "straw_until": ("int", 15, 20),
    "cows_final": ("int", 4, 12), "sheep_final": ("int", 2, 9), "sheep_fast": ("int", 0, 1),
    "melon0": ("int", 4, 10), "melon_mid": ("int", 6, 14), "melon_until": ("int", 13, 20),
    "wheat": ("int", 5, 14), "feed_days": ("int", 1, 4), "cash_floor": ("int", 40, 700),
    "land1": ("int", 5, 8), "land2": ("int", 8, 12), "land_reserve": ("int", 0, 1500),
    "work_per_unit": ("int", 4, 13), "hands_max": ("int", 8, 16), "hands_day0": ("int", 3, 6),
    "sell_chunk": ("int", 4, 14), "melon_chunk": ("int", 3, 10), "fert_reserve": ("int", 0, 4),
    "day0_wheat": ("int", 4, 14), "animals_per_day": ("int", 1, 4),
    "harvest_min_animal": ("int", 1, 3), "hands_min": ("int", 2, 5), "herd_first": ("int", 0, 1), "harvest_full": ("int", 0, 1), "cows_fast": ("int", 0, 1),
}
BASE = dict(straw_rate=6, straw_cash=350, straw_start=4, straw_peak=40, straw_peak_day=14, straw_until=18,
            cows_final=8, sheep_final=6, sheep_fast=0, melon0=7, melon_mid=12, melon_until=19,
            wheat=10, feed_days=2, cash_floor=80, land1=6, land2=9, land_reserve=200,
            work_per_unit=9, hands_max=12, hands_day0=4, sell_chunk=8, melon_chunk=6, fert_reserve=2, day0_wheat=10, animals_per_day=1, harvest_min_animal=2, hands_min=2, herd_first=0, harvest_full=0, cows_fast=0)

def to_kwargs(g):
    d0, dpk = g["straw_start"], max(g["straw_start"] + 1, g["straw_peak_day"])
    straw = [(d0, 2)] + [(d, int(round(2 + (g["straw_peak"] - 2) * (d - d0) / (dpk - d0)))) for d in range(d0 + 1, dpk + 1)]
    cf = g["cows_final"]
    cows = ([(0, 3), (4, 4), (6, max(4, cf - 3)), (8, max(4, cf - 1)), (10, cf)] if g.get("cows_fast", 0)
            else [(0, 3), (5, 4), (7, 5), (9, 6), (11, cf)])
    sheep = ([(0, 1), (4, 2), (6, 4), (8, g["sheep_final"])] if g["sheep_fast"]
             else [(0, 1), (5, 2), (8, 4), (10, g["sheep_final"])])
    melon = [(0, g["melon0"]), (5, max(g["melon0"], g["melon_mid"] - 2)), (7, g["melon_mid"])]
    return dict(straw=straw, straw_rate=g["straw_rate"], straw_cash=g["straw_cash"], straw_until=g["straw_until"],
                cows=cows, sheep=sheep, melon=melon, melon_until=g["melon_until"],
                wheat=g["wheat"], feed_days=g["feed_days"], cash_floor=g["cash_floor"],
                land_days=(g["land1"], g["land2"]), land_reserve=g["land_reserve"],
                work_per_unit=float(g["work_per_unit"]), hands_max=g["hands_max"], hands_day0=g["hands_day0"],
                sell_chunk=g["sell_chunk"], melon_chunk=g["melon_chunk"], fert_reserve=g["fert_reserve"],
                day0_wheat=g["day0_wheat"], animals_per_day=g.get("animals_per_day", 1),
                harvest_min_animal=g.get("harvest_min_animal", 2), hands_min=g.get("hands_min", 2),
                herd_first=bool(g.get("herd_first", 0)), harvest_full=bool(g.get("harvest_full", 0)))

def play(job):
    g, opp, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    from kaggriculture.agents import grove, ranch
    a = grove.make(**to_kwargs(g))
    if opp == "grove":                       # self opponent = the latest submitted genome
        try:
            g20 = json.load(open(ROOT + "experiments/v20_genome.json")); b = grove.make(**to_kwargs(g20))
        except Exception:
            b = grove.make()
    else:
        b = ranch.make(**V16) if opp == "v16" else opp
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]

def mutate(g, rng, k=3):
    c = dict(g)
    for key in rng.sample(list(SPACE), k):
        _, lo, hi = SPACE[key]; span = max(1, (hi - lo) // 4)
        c[key] = min(hi, max(lo, c[key] + rng.randint(-span, span)))
    return c

def evaluate(pop, seeds, ex):
    jobs = [(g, o, s) for g in pop for o in OPPS for s in seeds]
    res = list(ex.map(play, jobs, chunksize=1))
    out = []; k = len(OPPS) * len(seeds)
    for i, g in enumerate(pop):
        r = res[i * k:(i + 1) * k]
        by = {}
        for j, o in enumerate(OPPS):
            rr = r[j * len(seeds):(j + 1) * len(seeds)]
            by[os.path.basename(o)[:6]] = round(st.mean(a - b for a, b in rr))
        out.append(dict(genome=g, margin=st.mean(a - b for a, b in r), wins=sum(a > b for a, b in r) / k,
                        ours=st.mean(a for a, _ in r), by_opp=by))
    return out

if __name__ == "__main__":
    MU, LAM, SEEDS = 4, 12, 3
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    log = open(ROOT + "experiments/evolve_grove_log.jsonl", "a")
    elites = [dict(genome=dict(BASE))]; gen = 0
    try:
        prev = json.load(open(ROOT + "experiments/evolve_grove_best.json"))["genome"]
        elites.append(dict(genome={**BASE, **prev}))
    except Exception:
        pass
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 16))) as ex:
        while True:
            seeds = [rng.randrange(10**6) for _ in range(SEEDS)]
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]; q = rng.choice(elites)["genome"]
                base = {k: (p[k] if rng.random() < 0.5 else q[k]) for k in p} if rng.random() < 0.3 else p
                children.append(mutate(base, rng))
            t0 = time.time(); scored = evaluate([e["genome"] for e in elites] + children, seeds, ex)
            for s in scored: log.write(json.dumps(dict(gen=gen, seeds=seeds, **s)) + "\n")
            log.flush(); scored.sort(key=lambda s: -s["margin"]); elites = scored[:MU]; b = elites[0]
            json.dump(b, open(ROOT + "experiments/evolve_grove_best.json", "w"), indent=1)
            base_s = next((s for s in scored if s["genome"] == BASE), None)
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s best margin {b['margin']:>8,.0f} wins {b['wins']:.2f} ours {b['ours']:>8,.0f} {b['by_opp']} | base {round(base_s['margin']) if base_s else 'n/a'}", flush=True)
            print("     ", {k: v for k, v in b["genome"].items() if v != BASE[k]}, flush=True)
            gen += 1
