import json, sys, statistics as st, urllib.request, time
API = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
def games(S):
    req = urllib.request.Request(API, data=json.dumps({"submissionId": S}).encode(), headers={"content-type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60)); rows = []
    for e in sorted((e for e in d.get("episodes", []) if e["state"] == "COMPLETED" and len({a.get("submissionId") for a in e["agents"]}) == 2), key=lambda e: e["createTime"]):
        me = next(a for a in e["agents"] if a.get("submissionId") == S); op = next(a for a in e["agents"] if a.get("submissionId") != S)
        rows.append((me["reward"], op["reward"], op.get("initialScore", 0), me.get("updatedScore", 0)))
    return rows
def band(r): return "<2200" if r < 2200 else ("2200-2400" if r < 2400 else ("2400-2500" if r < 2500 else "2500+"))
out = {}
for S, name in ((56559582, "v34 cha22 g4-17"), (56553451, "v33 cha22 g3-17"), (56515072, "v32 tuned (run 6)")):
    rows = games(S); out[name] = rows; time.sleep(8)
    if not rows: print(f"{name}: no games yet"); continue
    print(f"== {name}: {len(rows)} games, rating {rows[-1][3]:.0f}, path@20/40/60/80/100: {[round(rows[i][3]) for i in (19,39,59,79,99) if i < len(rows)]}")
    for b in ("<2200", "2200-2400", "2400-2500", "2500+"):
        r = [x for x in rows if band(x[2]) == b]
        if r: print(f"   {b:9s}: {sum(x[0]>x[1] for x in r)}-{sum(x[0]<x[1] for x in r)} margin {st.mean(x[0]-x[1] for x in r):+,.0f}")
