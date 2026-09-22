"""Head-to-head check of chassis genomes: every reactive public opponent x fixed seeds, per-opponent W-L and mean margin.
Usage: .venv/bin/python eval/chassis_check.py <genome.json|base> [<genome.json|base> ...] [--seeds 601-608] [--jobs 8]
A genome file may be an evolve_chassis best/full json (uses its "genome" field)."""
import sys, os, json, statistics as st, pathlib, argparse
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "experiments"); sys.path.insert(0, ROOT + "eval")
os.environ["PYTHONWARNINGS"] = "ignore"
from concurrent.futures import ProcessPoolExecutor
import evolve_chassis as C
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("genomes", nargs="+"); ap.add_argument("--seeds", default="601-608"); ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(); lo, hi = map(int, a.seeds.split("-")); seeds = list(range(lo, hi + 1))
    B = C.base_genome(); gens = []
    for g in a.genomes:
        if g == "base": gens.append(("base", dict(B)))
        else:
            d = json.load(open(g)); d = d.get("genome", d); gens.append((os.path.basename(g), {**B, **{k: v for k, v in d.items() if k in C.SPACE}}))
    opps = list(C.OPP_FILES); jobs = [(g, o, s) for _, g in gens for o in opps for s in seeds]
    with ProcessPoolExecutor(a.jobs) as ex: res = list(ex.map(C.play, jobs, chunksize=1))
    k = len(opps) * len(seeds); out = {}
    for i, (name, g) in enumerate(gens):
        r = res[i * k:(i + 1) * k]; line = []; tot = []
        for j, o in enumerate(opps):
            rr = r[j * len(seeds):(j + 1) * len(seeds)]; tot += rr
            line.append(f"{o} {sum(x > y for x, y in rr)}-{sum(x < y for x, y in rr)} {st.mean(x - y for x, y in rr):+,.0f}")
        out[name] = dict(genome=g, results={o: r[j * len(seeds):(j + 1) * len(seeds)] for j, o in enumerate(opps)})
        print(f"{name:32s} ALL {sum(x > y for x, y in tot)}-{sum(x < y for x, y in tot)} {st.mean(x - y for x, y in tot):+,.0f} ours {st.mean(x for x, _ in tot):,.0f} | " + " | ".join(line), flush=True)
    json.dump(out, open(ROOT + "experiments/chassis_check_last.json", "w"), indent=1)
