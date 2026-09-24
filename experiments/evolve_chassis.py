"""(mu+lambda) search over the reflex constants of the public farm2945 v9/4 chassis (refagents/public/farm2945_v9_4.py).

The chassis reads its layer parameters from module globals at call time, so a genome is applied by importing the
file fresh and setattr-ing the constants (no edit of the Apache-2.0 file). Fitness = mean margin in FAIR-ENV games
against REACTIVE opponents only (the unmodified chassis as mirror, plus the other public agents in refagents/public/),
because frozen traces flatter a sale-racer. Log experiments/evolve_chassis_log.jsonl, best experiments/evolve_chassis_best.json.
Run: (. .venv/bin/activate && nohup python experiments/evolve_chassis.py <rngseed> > scratchpad/evolve_chassisN.log 2>&1 &)
"""
import sys, os, re, json, random, time, statistics as st, pathlib, importlib.util
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor

PUB_DIR = ROOT + "refagents/public/"
# which public file to tune: env CHASSIS=farm2945 (default) | demand | v56 | <path>
CHASSIS_FILES = {"farm2945": PUB_DIR + "farm2945_v9_4.py", "demand": PUB_DIR + "tetsutani_demand_preserving.py", "v56": PUB_DIR + "ahmed_v56.py"}
CHASSIS_NAME = os.environ.get("CHASSIS", "farm2945")
CHASSIS = CHASSIS_FILES.get(CHASSIS_NAME, CHASSIS_NAME)
# reactive opponents: name -> file. "mirror" = the unmodified chassis.
OPP_FILES = {"mirror": CHASSIS, "farm2945": PUB_DIR + "farm2945_v9_4.py",
             "demand": PUB_DIR + "tetsutani_demand_preserving.py", "firstline": PUB_DIR + "alperen_first_in_line.py",
             "rhythm": PUB_DIR + "alperen_market_rhythm.py", "v48": PUB_DIR + "ahmed_v48.py", "v47": PUB_DIR + "ahmed_v47.py",
             "v56": PUB_DIR + "ahmed_v56.py", "shopwork": PUB_DIR + "shopwork_tetsutani.py"}
OPP_FILES = {k: v for k, v in OPP_FILES.items() if os.path.exists(v) and (k == "mirror" or v != CHASSIS)}
if os.environ.get("SELF_GENOME"): OPP_FILES["self"] = CHASSIS        # our tuned best plays as a reactive opponent (see load_opp)
# per generation: mirror on 3 seeds + 4 other bots on 1 seed each (paired seeds across the population)
MIRROR_SEEDS, OTHER_PER_GEN = 3, 4
import trace_agent
def _pool(**kw):
    try: return trace_agent.pool(**kw)
    except FileNotFoundError: return []
TRACES = _pool(folder="mid") + _pool(folder="band2900") + _pool(folder="live26")   # diverse frozen farms, 1500-2960, incl. live clones
TRACES_PER_GEN = int(os.environ.get("TRACES_PER_GEN", 3))

SPACE = {  # module constant: (kind, lo, hi)   -- ranges bracket the shipped values
    "V9_COURIER_FROM_HOUR": ("int", 6, 20),
    "V9_CARROT_RATIO": ("float", 1.0, 3.0), "V9_CARROT_FIRST_DAY": ("int", 6, 16), "V9_CARROT_LAST_DAY": ("int", 18, 26),
    "V9_CARROT_WHEAT_RESERVE": ("int", 10, 80), "V9_CARROT_BOOM_RATIO": ("float", 2.0, 6.0), "V9_CARROT_BOOM_RESERVE": ("int", 0, 30),
    "V9_HERD_MIN_WOOL": ("int", 80, 250), "V9_HERD_MIN_MILK": ("int", 80, 250), "V9_HERD_MAX_EGG_SHOPS": ("int", 0, 3),
    "V9_HERD_MAX_EGG_SHOPS_COW": ("int", 0, 2), "V9_HERD_MIN_MILK_SHOPS": ("int", 1, 4), "V9_FERT_FIRST_DAY": ("int", 8, 24),
    "V9_RACE_DEFAULT": ("int", 4, 48), "V9_RACE_MAX": ("int", 24, 72), "V9_RACE_MARGIN": ("int", 0, 24), "V9_RACE_GAP": ("int", 1, 8),
    "V9_RACE_WINDOW": ("int", 10, 60), "V9_RACEPX_MARGIN": ("int", -30, 60), "V9_RACEGATE_MARGIN": ("int", -30, 60),
    "_CA_FROM": ("int", 4, 12), "_CA_TO": ("int", 20, 29), "_CA_MARGIN": ("float", -30.0, 20.0), "_CA_DROP": ("float", 0.0, 1.0),
    "_CA_BUFFER": ("int", 0, 20), "_CA_FEED_DAYS": ("int", 0, 4), "_CA_CASH": ("int", 0, 2000), "_CA_RESCUE": ("int", 0, 1),
    "_OR2_CAP": ("int", 5, 60), "_OR2_SN_K": ("int", 0, 3), "_OR2_SN_H": ("int", 6, 48), "_OR2_SLOT_H": ("int", 1, 12),
    "_OR2_SLOT_MARGIN": ("float", 0.0, 150.0), "_CH_SHED": ("int", 60, 100), "_CH_SELL": ("int", 0, 1), "_SR_MARGIN": ("int", 0, 12),
    "_HD2_FROM": ("int", 96, 288), "_HD2_TO": ("int", 240, 480), "_HD2_RATIO": ("float", 0.8, 2.0), "_HD2_MIN_GAIN": ("float", 0.0, 2000.0),
    "_HD2_LOOKBACK": ("int", 1, 6), "_HD2_CARE": ("float", 0.0, 1.0), "_HD2_FUTURE": ("float", 0.0, 1.0),
    "_CS_FROM": ("int", 96, 192), "_CS_TO": ("int", 144, 288), "_CS_RATIO": ("float", 0.8, 2.0), "_CS_MIN_GAIN": ("float", 0.0, 2000.0),
    "OPEN_BUY": ("int", 10, 40), "OPEN_SELL": ("int", 5, 30),     # V9_OPENING_STEP0 quantities (shipped 20 / 15)
}
BOOLS = {"_CA_RESCUE", "_CH_SELL"}

def auto_space(path):
    """Knobs derived from a file's top-level numeric/bool constants (ALLCAPS names, literal values)."""
    sp, bools = {}, set()
    for m in re.finditer(r"^(_?[A-Z][A-Z_0-9]*) = (True|False|-?\d+(?:\.\d+)?)\s*(?:#.*)?$", open(path).read(), re.M):
        k, v = m.group(1), m.group(2)
        if any(t in k for t in ("REPORT", "STATE", "CACHE", "STEP", "TURNS", "BOARD", "MAX_ORDERS", "CAPACITY", "FLOOR", "PRICE", "COST", "SIZE")): continue
        if v in ("True", "False"): sp[k] = ("int", 0, 1); bools.add(k); continue
        if "." in v:
            x = float(v); span = max(0.5, abs(x)); sp[k] = ("float", (x - span) if x < 0 else max(0.0, x - span), x + span)
        else:
            x = int(v); span = max(2, abs(x)); sp[k] = ("int", (x - span) if x < 0 else max(0, x - span), x + span)
    return sp, bools

if CHASSIS_NAME != "farm2945":
    SPACE, BOOLS = auto_space(CHASSIS)
    SPACE = {k: v for k, v in SPACE.items() if k not in ("OPEN_BUY", "OPEN_SELL")}


def _fresh(path, name):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def base_genome():
    m = _fresh(CHASSIS, "chassis_base"); g = {}
    for k in SPACE:
        if k == "OPEN_BUY": g[k] = m.V9_OPENING_STEP0[0][2]
        elif k == "OPEN_SELL": g[k] = m.V9_OPENING_STEP0[1][2]
        else:
            v = getattr(m, k); g[k] = int(v) if k in BOOLS else v
    return g


def make_agent(genome, tag="cand"):
    m = _fresh(CHASSIS, "chassis_" + tag)
    for k, v in genome.items():
        if k == "OPEN_BUY": continue
        if k == "OPEN_SELL":
            m.V9_OPENING_STEP0 = (("BUY_PRODUCT", "WHEAT", int(genome["OPEN_BUY"])), ("SELL", "WHEAT", int(v))); continue
        setattr(m, k, bool(v) if k in BOOLS else v)
    return m.agent


SELF_GENOME = os.environ.get("SELF_GENOME")        # e.g. experiments/v30_demand_genome.json: our own best as a reactive opponent
def load_opp(name):
    if name == "self" and SELF_GENOME:
        g = json.load(open(SELF_GENOME if os.path.isabs(SELF_GENOME) else ROOT + SELF_GENOME)); g = g.get("genome", g)
        return make_agent({**base_genome(), **{k: v for k, v in g.items() if k in SPACE}}, tag="self")
    m = _fresh(OPP_FILES[name], "opp_" + name)
    return [v for v in vars(m).values() if callable(v)][-1]   # Kaggle's last-callable rule


def play(job):
    g, opp, seed = job
    import fair_env
    from kaggle_environments import make as mk
    a = make_agent(g)
    if opp.startswith("trace:"):
        fair_env.restore()                     # a recorded opponent is faithful only under the shipped shop draw
        name, path, idx, rating = TRACES[int(opp.split(":")[1])]; b = trace_agent.make(path, idx); seed = trace_agent.seed_of(path)
    else:
        fair_env.apply(); b = load_opp(opp)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}); env.run([a, b])
    f = env.steps[-1]; return f[0]["reward"], f[1]["reward"]


def mutate(g, rng, k=3):
    c = dict(g)
    for key in rng.sample(list(SPACE), k):
        kind, lo, hi = SPACE[key]
        if kind == "int":
            span = max(1, (hi - lo) // 4); c[key] = min(hi, max(lo, c[key] + rng.randint(-span, span)))
        else:
            span = (hi - lo) / 4; c[key] = round(min(hi, max(lo, c[key] + rng.uniform(-span, span))), 3)
    return c


def evaluate(pop, jobs_of, ex):
    """jobs_of(genome) -> [(opp, seed), ...]; returns per-genome dict(margin, wins, ours, by_opp)."""
    jobs = [(g, o, s) for g in pop for o, s in jobs_of(g)]
    res = list(ex.map(play, jobs, chunksize=1)); out = []; i = 0
    for g in pop:
        js = jobs_of(g); r = res[i:i + len(js)]; i += len(js); by = {}
        for (o, s), (a, b) in zip(js, r): by.setdefault(o, []).append(a - b)
        out.append(dict(genome=g, margin=st.mean(a - b for a, b in r), wins=sum(a > b for a, b in r) / len(r),
                        ours=st.mean(a for a, _ in r), by_opp={o: round(st.mean(v)) for o, v in by.items()}))
    return out


def fullcheck(genome, ex, seeds=range(601, 609)):
    """Every reactive opponent on 8 fixed seeds (mirror included) + every diverse trace (no-regression term)."""
    plan = [(o, s) for o in OPP_FILES for s in seeds] + [("trace:%d" % i, 0) for i in range(len(TRACES))]
    v = evaluate([genome], lambda g: plan, ex)[0]
    tr = [m for o, m in v["by_opp"].items() if o.startswith("trace:")]
    if tr: v["traces"] = (sum(m > 0 for m in tr), len(tr), st.mean(tr)); v["by_opp"] = {o: m for o, m in v["by_opp"].items() if not o.startswith("trace:")}
    return v


def fmt(v):
    tr = f" | traces {v['traces'][0]}/{v['traces'][1]} {v['traces'][2]:+,.0f}" if "traces" in v else ""
    return f"margin {v['margin']:+,.0f} wins {v['wins']:.2f} ours {v['ours']:,.0f} " + " ".join(f"{o}:{m:+,}" for o, m in v["by_opp"].items()) + tr


if __name__ == "__main__":
    MU, LAM = 4, 12
    RUN = sys.argv[1] if len(sys.argv) > 1 else "0"; rng = random.Random(int(RUN))
    TAG = "" if CHASSIS_NAME == "farm2945" else "_" + CHASSIS_NAME
    log = open(ROOT + f"experiments/evolve_chassis{TAG}_log.jsonl", "a")
    BASE = base_genome(); elites = [dict(genome=dict(BASE))]
    try:
        prev = json.load(open(ROOT + f"experiments/evolve_chassis{TAG}_best.json")); prev = prev.get("genome", prev)
        elites.append(dict(genome={**BASE, **{k: v for k, v in prev.items() if k in SPACE}}))
    except Exception:
        pass
    others = [o for o in OPP_FILES if o != "mirror"]
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 16))) as ex:
        gen = 0
        while True:
            seeds = [rng.randrange(10**6) for _ in range(MIRROR_SEEDS)]
            # the frontier bots (they beat the unmodified chassis 8-0) are in every generation; two others rotate
            frontier = [o for o in ("demand", "v56", "self") if o in OPP_FILES]
            picks = frontier + rng.sample([o for o in others if o not in frontier], min(OTHER_PER_GEN - len(frontier), len(others)))
            oseed = rng.randrange(10**6)
            fseeds = [rng.randrange(10**6) for _ in range(int(os.environ.get("FRONT_SEEDS", 1)))]   # extra seeds vs the frontier bots
            plan = [("mirror", s) for s in seeds] + [(o, oseed) for o in picks] + [(o, s) for o in frontier for s in fseeds]
            if TRACES: plan += [("trace:%d" % i, 0) for i in rng.sample(range(len(TRACES)), min(TRACES_PER_GEN, len(TRACES)))]
            children = []
            for _ in range(LAM):
                p = rng.choice(elites)["genome"]; q = rng.choice(elites)["genome"]
                base = {k: (p[k] if rng.random() < 0.5 else q[k]) for k in p} if rng.random() < 0.3 else p
                children.append(mutate(base, rng))
            t0 = time.time(); scored = evaluate([e["genome"] for e in elites] + children, lambda g: plan, ex)
            for s in scored: log.write(json.dumps(dict(gen=gen, run=RUN, plan=plan, **s)) + "\n")
            log.flush(); scored.sort(key=lambda s: -s["margin"]); elites = scored[:MU]; b = elites[0]
            json.dump(b, open(ROOT + f"experiments/evolve_chassis{TAG}_best.json", "w"), indent=1)
            base_s = next((s for s in scored if s["genome"] == BASE), None)
            print(f"gen {gen:>3} {time.time()-t0:5.0f}s best {fmt(b)} | base {round(base_s['margin']) if base_s else 'n/a'}", flush=True)
            print("     ", {k: v for k, v in b["genome"].items() if v != BASE[k]}, flush=True)
            if gen % 6 == 5:
                v = fullcheck(b["genome"], ex)
                print(f"      FULL-CHECK gen {gen}: {fmt(v)}", flush=True)
                json.dump(dict(gen=gen, run=RUN, **v), open(ROOT + "experiments/evolve_chassis%s_full_%s_%03d.json" % (TAG, RUN, gen), "w"), indent=1)
            gen += 1
