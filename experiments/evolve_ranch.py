"""(mu+lambda) evolutionary search over ranch.make knobs on the fair environment.

Fitness = mean coin margin (ours - theirs) over a sparring set: v12 itself, Rancher Rita,
Melon Mateo and Closer Cleo (tier-9 meta line, local sparring only - never embedded).
Every candidate is logged to experiments/evolve_log.jsonl; the running best to evolve_best.json.
"""
import sys, os, json, random, time, statistics as st, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor

V12 = dict(target={'COW': 8, 'SHEEP': 5}, feed_float_days=8, hands=5, land=2, buy_feed=True,
           grow_surplus=True, deny_ranchers=True, deny_mode='buyers', zone_mode='bands',
           max_wheat=12, n_melon=24, hands_mode='event', day0={'COW': 2, 'SHEEP': 2})
V14 = dict(V12, feed_float_days=10, max_wheat=10, hands_mode='flat', day0={'COW': 2, 'SHEEP': 1})
V15 = dict(V14, max_wheat=6, n_melon=26, animal_batch=1)
# Round 4: drop the older selves (optimising margin against our own family drifted toward
# weaker absolute farms), add "pass" so absolute economy counts directly.
V16 = dict(V15, hands=6, target={'COW': 8, 'SHEEP': 4}, n_melon=17, melon_rate=3, max_wheat=15, land=1, animal_buffer=104)
OPPS = ["v16", "pass", ROOT + "refagents/rancher_rita.py", ROOT + "refagents/melon_mateo.py",
        ROOT + "refagents/closer_cleo.py"]
# knob: (kind, low, high) or (kind, choices)
SPACE = {
    "hands": ("int", 3, 9), "cow": ("int", 3, 12), "sheep": ("int", 0, 8),
    "feed_float_days": ("int", 2, 16), "n_melon": ("int", 0, 32), "max_wheat": ("int", 4, 24),
    "n_straw": ("int", 0, 24), "land": ("int", 1, 3), "liquidate_from": ("int", 24, 29),
    "invest_until": ("int", 12, 26), "animal_batch": ("int", 1, 4), "animal_buffer": ("int", 0, 800),
    "sell_chunk": ("int", 5, 30), "hands_mode": ("cat", ["flat", "event", "formula"]),
    "d0cow": ("int", 0, 3), "d0sheep": ("int", 0, 3), "deny_mode": ("cat", ["all", "buyers"]),
    "melon_rate": ("int", 2, 8),
}

def to_kwargs(g):
    k = dict(V12)
    k.update(target={"COW": g["cow"], "SHEEP": g["sheep"]}, day0={"COW": g["d0cow"], "SHEEP": g["d0sheep"]})
    for key in ("hands", "feed_float_days", "n_melon", "max_wheat", "n_straw", "land", "liquidate_from",
                "invest_until", "animal_batch", "animal_buffer", "sell_chunk", "hands_mode", "deny_mode", "melon_rate"):
        k[key] = g[key]
    return k

def play(job):
    g, opp, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    from kaggriculture.agents.ranch import make
    a = make(**to_kwargs(g)); b = make(**V12) if opp == "v12" else make(**V14) if opp == "v14" else make(**V15) if opp == "v15" else make(**V16) if opp == "v16" else opp
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]

def base_genome():
    return dict(hands=5, cow=8, sheep=5, feed_float_days=8, n_melon=24, max_wheat=12, n_straw=0, land=2,
                liquidate_from=28, invest_until=22, animal_batch=2, animal_buffer=400, sell_chunk=20,
                hands_mode="event", d0cow=2, d0sheep=2, deny_mode="buyers", melon_rate=4)

def mutate(g, rng, k=3):
    c = dict(g)
    for key in rng.sample(list(SPACE), k):
        sp = SPACE[key]
        if sp[0] == "int":
            lo, hi = sp[1], sp[2]; span = max(1, (hi - lo) // 4)
            c[key] = min(hi, max(lo, c[key] + rng.randint(-span, span)))
        else:
            c[key] = rng.choice(sp[1])
    return c

def crossover(a, b, rng):
    return {k: (a[k] if rng.random() < 0.5 else b[k]) for k in a}

def evaluate(pop, seeds, ex):
    jobs = [(g, o, s) for g in pop for o in OPPS for s in seeds]
    res = list(ex.map(play, jobs, chunksize=1))
    out = []
    for i, g in enumerate(pop):
        r = res[i * len(OPPS) * len(seeds):(i + 1) * len(OPPS) * len(seeds)]
        margin = st.mean(a - b for a, b in r); wins = sum(a > b for a, b in r) / len(r)
        by_opp = {os.path.basename(o)[:8]: round(st.mean(a - b for (a, b), (_, oo, _s) in zip(r, [(g, o2, s) for o2 in OPPS for s in seeds]) if oo == o)) for o in OPPS}
        out.append(dict(genome=g, margin=margin, wins=wins, ours=st.mean(a for a, _ in r), by_opp=by_opp))
    return out

if __name__ == "__main__":
    MU, LAM, SEEDS_PER_GEN = 4, 12, 3
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    log = open(ROOT + "experiments/evolve_log.jsonl", "a")
    elites = [dict(genome=base_genome(), margin=None),
              dict(genome=dict(base_genome(), d0sheep=1, feed_float_days=10, hands_mode='flat', max_wheat=10), margin=None)]
    for line in open(ROOT + "experiments/evolve_log.jsonl"):   # resume from the best logged genomes
        r = json.loads(line)
        if r["margin"] and r["margin"] > 12000 and r["genome"] not in [e["genome"] for e in elites]:
            elites.append(dict(genome=r["genome"], margin=r["margin"]))
    elites.insert(0, dict(genome=dict(base_genome(), d0sheep=1, feed_float_days=10, hands_mode='flat', max_wheat=6, n_melon=26, animal_batch=1), margin=None))
    elites.insert(0, dict(genome=dict(base_genome(), d0sheep=1, feed_float_days=10, hands_mode='flat', hands=6, sheep=4, n_melon=17, melon_rate=3, max_wheat=15, land=1, animal_batch=1, animal_buffer=104), margin=None))
    elites = elites[:6]
    gen = 0
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 16))) as ex:
        while True:
            seeds = [rng.randrange(10**6) for _ in range(SEEDS_PER_GEN)]
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]
                q = rng.choice(elites)["genome"]
                children.append(mutate(crossover(p, q, rng) if rng.random() < 0.3 else p, rng))
            pop = [e["genome"] for e in elites] + children      # elites re-scored on this gen's seeds
            t0 = time.time(); scored = evaluate(pop, seeds, ex)
            for s in scored:
                log.write(json.dumps(dict(gen=gen, seeds=seeds, **s)) + "\n")
            log.flush()
            scored.sort(key=lambda s: -s["margin"])
            elites = scored[:MU]
            b = elites[0]
            json.dump(b, open(ROOT + "experiments/evolve_best.json", "w"), indent=1)
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s  best margin {b['margin']:>8,.0f} wins {b['wins']:.2f} "
                  f"ours {b['ours']:>8,.0f} {b['by_opp']}  base(v12) margin {next(s['margin'] for s in scored if s['genome']==base_genome()) if any(s['genome']==base_genome() for s in scored) else 'n/a'}", flush=True)
            print("     ", {k: v for k, v in b["genome"].items()}, flush=True)
            gen += 1
