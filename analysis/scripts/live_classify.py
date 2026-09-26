"""Classify a live submission's opponents (clone of us vs other, by day-12 farm census) and tabulate record by kind x rating band.
Usage: .venv/bin/python analysis/scripts/live_classify.py <submission_id> [min_opp_rating=2200]; reads analysis/data/live/<id>.json, replays -> replays/live_<id>/"""
import json, os, time, urllib.request, collections, statistics as st
from concurrent.futures import ThreadPoolExecutor
import sys
SP = os.path.dirname(os.path.abspath(__file__)); ROOT = "/home/iwa/working/kaggle"; S = int(sys.argv[1]); MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 2200
D = ROOT + "/replays/live_" + str(S); os.makedirs(D, exist_ok=True)
d = json.load(open(f"{ROOT}/analysis/data/live/{S}.json"))
eps = [e for e in d["episodes"] if e["state"] == "COMPLETED" and len({a.get("submissionId") for a in e["agents"]}) == 2]
games = []
for e in eps:
    me = next(a for a in e["agents"] if a.get("submissionId") == S); op = next(a for a in e["agents"] if a.get("submissionId") != S)
    if (op.get("initialScore") or 0) >= MIN:
        games.append(dict(ep=e["id"], me_idx=e["agents"].index(me), mr=me["reward"], orew=op["reward"], osub=op["submissionId"], orating=op.get("initialScore", 0), win=me["reward"] > op["reward"]))
print(f"games vs >={MIN}:", len(games), flush=True)
def fetch(g):
    p = f"{D}/episode-{g['ep']}-replay.json"
    if os.path.exists(p) and os.path.getsize(p) > 1_000_000: return p
    for _ in range(3):
        try:
            b = urllib.request.urlopen(f"https://www.kaggleusercontent.com/episodes/{g['ep']}.json", timeout=300).read()
            if len(b) > 1_000_000: open(p, "wb").write(b); return p
        except Exception: time.sleep(5)
with ThreadPoolExecutor(4) as ex: paths = list(ex.map(fetch, games))
def census(farm):
    cr = collections.Counter(); an = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("animal"): an[t["animal"]] += 1
                elif t.get("kind") == "PLANT": cr[t["crop"]] += 1
    return cr, an
rows = []
for g, p in zip(games, paths):
    if not p: continue
    R = json.load(open(p)); steps = R["steps"]; mi = g["me_idx"]; oi = 1 - mi
    obs12 = steps[12 * 24 + 23][0]["observation"]; obs20 = steps[20 * 24 + 23][0]["observation"]
    mc, ma = census(obs12["farms"][mi]); oc, oa = census(obs12["farms"][oi]); oc20, oa20 = census(obs20["farms"][oi]); mc20, _ = census(obs20["farms"][mi])
    diff = abs(mc["STRAWBERRY"] - oc["STRAWBERRY"]) + abs(mc["WHEAT"] - oc["WHEAT"]) + abs(ma["COW"] - oa["COW"]) + abs(ma["SHEEP"] - oa["SHEEP"]) + abs(ma["GOOSE"] - oa["GOOSE"])
    a1 = steps[1][oi].get("action"); step0 = a1.get("market") if isinstance(a1, dict) else None
    kind = "clone" if diff <= 4 else "other"
    rows.append(dict(**g, diff=diff, kind=kind, step0=step0, otom20=oc20["TOMATO"], ostr20=oc20["STRAWBERRY"], owh20=oc20["WHEAT"], mtom20=mc20["TOMATO"]))
json.dump(rows, open(f"{ROOT}/analysis/data/live/{S}_classified.json", "w"))
def band(r): return "<2000" if r < 2000 else ("2000-2200" if r < 2200 else ("2200-2400" if r < 2400 else ("2400-2500" if r < 2500 else "2500+")))
print("\nkind × band: record (win rate), mean margin")
for kind in ("clone", "other"):
    for b in ("<2000", "2000-2200", "2200-2400", "2400-2500", "2500+"):
        rr = [r for r in rows if r["kind"] == kind and band(r["orating"]) == b]
        if rr: print(f"  {kind:5s} {b:9s}: {sum(r['win'] for r in rr)}-{sum(not r['win'] for r in rr)} ({st.mean(r['win'] for r in rr):.0%})  margin {st.mean(r['mr'] - r['orew'] for r in rr):+,.0f}  ours {st.mean(r['mr'] for r in rr):,.0f}")
oth = [r for r in rows if r["kind"] == "other"]
print(f"\n'other' opponents: {len(oth)}; their day-20 tomato/straw/wheat mean: {st.mean(r['otom20'] for r in oth) if oth else 0:.1f}/{st.mean(r['ostr20'] for r in oth) if oth else 0:.1f}/{st.mean(r['owh20'] for r in oth) if oth else 0:.1f}")
for r in sorted(oth, key=lambda r: -r["orating"])[:15]: print(f"   r{r['orating']:.0f} {'W' if r['win'] else 'L'} {r['mr']:>8,.0f} vs {r['orew']:>8,.0f} diff {r['diff']:>2} tom20 {r['otom20']:>2} str20 {r['ostr20']:>2} wh20 {r['owh20']:>2} step0 {str(r['step0'])[:70]}")
cl = [r for r in rows if r["kind"] == "clone"]
sig = collections.Counter(str(r["step0"])[:60] for r in cl); print("\nclone step-0 signatures:", sig.most_common(6))
