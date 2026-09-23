"""(mu+lambda) search over the second half of the hybrid agent (public tape days 0..11, our market planner + executor
from step 288). Fitness = our final coins vs a PASSIVE opponent from the tape's own day-11 farm on fixed seeds
(deterministic; the tape scores ~137k there on seed 601), plus one fair-env game vs the unmodified tape (margin, weight w).
Only knobs that act after day 11 are searched. Log experiments/evolve_hybrid_log.jsonl, best experiments/evolve_hybrid_best.json.
Run: (. .venv/bin/activate && nohup python experiments/evolve_hybrid.py <rngseed> > scratchpad/evolve_hybridN.log 2>&1 &)
"""
import sys, os, json, random, time, statistics as st, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval"); sys.path.insert(0, ROOT + "experiments")
os.environ["PYTHONWARNINGS"] = "ignore"; os.environ.setdefault("CHASSIS", "demand")
from concurrent.futures import ProcessPoolExecutor
import evolve_market as E

TAKEOVER = int(os.environ.get("TAKEOVER", 288))
SEEDS = [601, 605, 611]
W_TAPE = float(os.environ.get("W_TAPE", 1.0))     # weight of the margin vs the unmodified tape (fair env, seed 601)
SPACE = {k: v for k, v in E.SPACE.items() if k in (
    "milk_prior", "wool_prior", "cows_min", "cows_max", "sheep_min", "sheep_max", "geese_max", "geese_min", "herd_until", "herd_until2", "herd_rich_drain",
    "straw_until", "straw_max", "straw_prior", "straw_mult", "wheat_mult", "wheat_feed_mult", "wheat_min", "wheat_max", "carrot_from", "carrot_max",
    "carrot_mult", "tomato_from", "tomato_max", "tomato_until", "tomato_mult", "egg_drain_min", "sprint_from", "sprint_until", "herd_reserve",
    "hands_min", "hands_max", "work_per_unit", "feed_days", "cash_floor", "animals_per_day", "sell_chunk", "fert_reserve", "harvest_min_animal",
    "deliver_min", "deliver_k", "land_reserve", "opp_weight", "harvest_late_hour", "water_growth_mult", "liquidate_from", "shed_guard", "harvest_decay")}
SPACE.update({"feed_per_carrier": ("int", 2, 8), "pickup_value": ("int", 100, 900), "fert_reserve_mult": ("float", 0.0, 1.5), "executor": ("int", 0, 1)})
from kaggriculture.agents import market as M
BASE = {k: M.DEFAULT[k] for k in SPACE if k != "executor"}; BASE["executor"] = 0
G23 = json.load(open(ROOT + "experiments/v23_genome.json"))
V23 = {**BASE, **{k: v for k, v in G23.items() if k in SPACE}}
FIXED = {k: v for k, v in {**E.BASE, **{k: v for k, v in G23.items() if k in E.SPACE}}.items() if k not in SPACE}   # early-game knobs stay at v23


def make_agent(g):
    from kaggriculture.agents import hybrid
    knobs = {**FIXED, **{k: v for k, v in g.items() if k != "executor"}, "executor": "tour" if g.get("executor") else "auction"}
    return hybrid.make(takeover_step=TAKEOVER, chassis=os.environ.get("CHASSIS", "demand"), **knobs)


def play(job):
    g, opp, seed = job
    import fair_env; fair_env.apply()
    from kaggle_environments import make as mk
    import evolve_chassis as C
    a = make_agent(g); b = "pass" if opp == "pass" else C.load_opp("mirror")
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]


def mutate(g, rng, k=3):
    c = dict(g)
    for key in rng.sample(list(SPACE), k):
        kind, lo, hi = SPACE[key]
        if kind == "int":
            span = max(1, (hi - lo) // 4); c[key] = min(hi, max(lo, int(c[key]) + rng.randint(-span, span)))
        else:
            span = (hi - lo) / 4; c[key] = round(min(hi, max(lo, c[key] + rng.uniform(-span, span))), 3)
    return c


def evaluate(pop, ex):
    jobs = [(g, "pass", s) for g in pop for s in SEEDS] + [(g, "tape", 601) for g in pop]
    res = list(ex.map(play, jobs, chunksize=1)); out = []
    npass = len(SEEDS)
    for i, g in enumerate(pop):
        r = res[i * npass:(i + 1) * npass]; t = res[len(pop) * npass + i]
        ours = st.mean(a for a, _ in r); tape_margin = t[0] - t[1]
        out.append(dict(genome=g, ours=ours, tape_margin=tape_margin, fitness=ours + W_TAPE * tape_margin, by_seed=[a for a, _ in r]))
    return out


if __name__ == "__main__":
    MU, LAM = 4, 12
    RUN = sys.argv[1] if len(sys.argv) > 1 else "0"; rng = random.Random(int(RUN))
    log = open(ROOT + "experiments/evolve_hybrid_log.jsonl", "a")
    elites = [dict(genome=dict(V23)), dict(genome={**V23, "executor": 1})]
    try:
        prev = json.load(open(ROOT + "experiments/evolve_hybrid_best.json"))["genome"]; elites.append(dict(genome={**V23, **{k: v for k, v in prev.items() if k in SPACE}}))
    except Exception:
        pass
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 12))) as ex:
        gen = 0
        while True:
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]; q = rng.choice(elites)["genome"]
                base = {k: (p[k] if rng.random() < 0.5 else q[k]) for k in p} if rng.random() < 0.3 else p
                children.append(mutate(base, rng))
            t0 = time.time(); scored = evaluate([e["genome"] for e in elites] + children, ex)
            for s in scored: log.write(json.dumps(dict(gen=gen, run=RUN, **s)) + "\n")
            log.flush(); scored.sort(key=lambda s: -s["fitness"]); elites = scored[:MU]; b = elites[0]
            json.dump(b, open(ROOT + "experiments/evolve_hybrid_best.json", "w"), indent=1)
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s best fitness {b['fitness']:>9,.0f} ours-vs-pass {b['ours']:>9,.0f} {[round(x) for x in b['by_seed']]} tape-margin {b['tape_margin']:+,.0f} exec {'tour' if b['genome']['executor'] else 'auction'}", flush=True)
            print("     ", {k: v for k, v in b["genome"].items() if v != V23.get(k)}, flush=True)
            gen += 1
