"""Build a replay pool of ladder opponents for trace_agent.

Usage: tools/build_pool.py <folder> <candidates.json> [--min-score N]
candidates.json = [[rating, submissionId, teamId, rank], ...] (from the leaderboard capture).
For each submission: ListEpisodes, take the most recent COMPLETED 2-player game where that
submission won (falls back to its highest-scoring game), download the replay into
replays/<folder>/ and append to replays/<folder>/manifest.json with the fields pool() reads
(ep, opp_idx, opp_sub, opp_rating). Skips episodes already present.
"""
import sys, os, json, time, urllib.request, pathlib
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"

def post(sub):
    req = urllib.request.Request(API, data=json.dumps({"submissionId": sub}).encode(), headers={"content-type": "application/json"})
    for _ in range(6):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60)); time.sleep(8); return d
        except Exception as e:
            err = e; time.sleep(60 if "429" in str(e) else 5)   # the episode API rate-limits bursts
    print("ListEpisodes failed", sub, err); return None

def pick(sub, d):
    best = None
    for e in d.get("episodes", []):
        if e.get("state") != "COMPLETED" or len(e.get("agents", [])) != 2: continue
        ags = e["agents"]
        if any(a.get("reward") is None for a in ags): continue
        me = next((i for i, a in enumerate(ags) if a.get("submissionId") == sub), None)
        if me is None or ags[1 - me].get("submissionId") == sub: continue
        won = ags[me]["reward"] > ags[1 - me]["reward"]
        key = (won, e["createTime"])
        if best is None or key > best[0]:
            best = (key, dict(ep=e["id"], opp_idx=me, opp_sub=sub, opp_rating=round(ags[me].get("initialScore") or 0),
                              opp_reward=ags[me]["reward"], other_reward=ags[1 - me]["reward"], other_sub=ags[1 - me].get("submissionId"),
                              other_rating=round(ags[1 - me].get("initialScore") or 0), won=won, created=e["createTime"]))
    return best[1] if best else None

def fetch(entry, folder):
    path = folder / f"episode-{entry['ep']}-replay.json"
    if path.exists() and path.stat().st_size > 1_000_000: return entry, True
    url = f"https://www.kaggleusercontent.com/episodes/{entry['ep']}.json"
    for _ in range(3):
        try:
            data = urllib.request.urlopen(url, timeout=300).read()
            if len(data) > 1_000_000:
                path.write_bytes(data); return entry, True
        except Exception as e:
            time.sleep(5)
    return entry, False

if __name__ == "__main__":
    folder = ROOT / "replays" / sys.argv[1]; folder.mkdir(parents=True, exist_ok=True)
    cands = json.load(open(sys.argv[2]))
    mpath = folder / "manifest.json"
    man = json.load(open(mpath)) if mpath.exists() else []
    have = {m["opp_sub"] for m in man}
    entries = []
    for rating, sub, *_ in cands:
        if sub in have: continue
        d = post(sub)
        if not d: continue
        e = pick(sub, d)
        if e: entries.append(e); print("pick", sub, rating, "ep", e["ep"], "won" if e["won"] else "LOST", e["opp_reward"], "vs", e["other_reward"], flush=True)
        else: print("no game for", sub, flush=True)
    with ThreadPoolExecutor(4) as ex:
        for entry, ok in ex.map(lambda e: fetch(e, folder), entries):
            print("fetched" if ok else "FAILED", entry["ep"], flush=True)
            if ok:
                man.append(entry); json.dump(man, open(mpath, "w"), indent=1)
    man.sort(key=lambda m: -m["opp_rating"]); json.dump(man, open(mpath, "w"), indent=1)
    print("manifest", len(man), "entries")
