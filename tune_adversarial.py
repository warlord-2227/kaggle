"""Tune against a real opponent, scoring WIN RATE -- not coins against `pass`."""
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
from farm import make

REF = dict(geese_per_unit=3, hands=3, ambition=8)   # current champion

def duel(args):
    cfg, seed, side = args
    a = make(**cfg); b = make(**REF)
    env = mk("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([a, b] if side == 0 else [b, a])
    r = env.steps[-1]
    mine, theirs = (r[0]["reward"], r[1]["reward"]) if side == 0 else (r[1]["reward"], r[0]["reward"])
    return mine, theirs

if __name__ == "__main__":
    SEEDS = [7, 11, 23, 42, 99, 123, 256, 512]
    cands = [dict(geese_per_unit=3, hands=3, ambition=a) for a in (4,5,6,7,8,9,10,12)]
    jobs, meta = [], []
    for c in cands:
        for s in SEEDS:
            for side in (0, 1):
                jobs.append((c, s, side)); meta.append(c["ambition"])
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(duel, jobs))
    agg = {}
    for amb, (m, t) in zip(meta, res):
        agg.setdefault(amb, []).append((m, t))
    print("CANDIDATE vs REFERENCE (ambition 8), 8 seeds x 2 sides = 16 games each")
    print(f"{'ambition':>9}{'W':>4}{'L':>4}{'T':>4}{'winrate':>9}{'our coins':>11}{'their coins':>13}")
    for amb in sorted(agg):
        v = agg[amb]
        w = sum(1 for m, t in v if m > t); l = sum(1 for m, t in v if m < t)
        ti = len(v) - w - l
        print(f"{amb:>9}{w:>4}{l:>4}{ti:>4}{w/len(v):>9.1%}"
              f"{st.median([m for m,_ in v]):>11,.0f}{st.median([t for _,t in v]):>13,.0f}")
