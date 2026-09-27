"""Per hand-day in v33's live games: tail-idle length (PASS run to the end of the day), whether the hand resumes work after an idle
run of >=2 steps (unsafe to borrow), and where tail-idle hands stand relative to free tiles. Usage: .venv/bin/python analysis/scripts/idle_structure.py"""
import json, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from income_gap import jobs, ROOT
def analyse(job):
    path, idx, label = job
    if label != "v33": return None
    R = json.load(open(path)); steps = R["steps"]
    if len(steps) < 720: return None
    tail = collections.defaultdict(list); resume = collections.Counter(); handdays = collections.Counter(); tailpos = collections.defaultdict(list)
    for day in range(30):
        # verbs per hand per hour; hands list can grow during the day (hires) -> key by index
        seq = collections.defaultdict(dict)
        for h in range(24):
            t = day * 24 + h
            if t + 1 >= 720: break
            a = steps[t + 1][idx].get("action") or {}
            for i, c in enumerate(a.get("hands") or []):
                v = c[0] if isinstance(c, (list, tuple)) and c else (c or "PASS"); seq[i][h] = v
        for i, s in seq.items():
            hours = sorted(s); verbs = [s[h] for h in hours]
            if not verbs: continue
            handdays[day] += 1
            # tail idle
            k = 0
            for v in reversed(verbs):
                if v == "PASS": k += 1
                else: break
            tail[day].append(k)
            # resume after idle run >= 2
            run = 0; res = False
            for v in verbs[:len(verbs) - k]:
                if v == "PASS": run += 1
                else:
                    if run >= 2: res = True
                    run = 0
            if res: resume[day] += 1
            if k >= 3:
                t = (day * 24 + hours[-k]); farm = steps[t][0]["observation"]["farms"][idx]
                pos = farm["hands"][i] if i < len(farm["hands"]) else None
                free = [(x, y) for y in range(10) for x in range(10) if farm["tiles"][y][x] is None]
                if pos and free: tailpos[day].append(min(abs(pos[0] - x) + abs(pos[1] - y) for x, y in free))
    return dict(tail={d: v for d, v in tail.items()}, resume=dict(resume), handdays=dict(handdays), tailpos={d: st.mean(v) for d, v in tailpos.items() if v})
if __name__ == "__main__":
    J = [j for j in jobs() if j[2] == "v33"]
    with ProcessPoolExecutor(8) as ex: res = [r for r in ex.map(analyse, J) if r]
    print("day | hand-days | mean tail-idle steps/hand | hands with tail>=3 | total tail steps/day | hands resuming after idle>=2 | dist tail-hand->free")
    for d in range(30):
        tails = [x for r in res for x in r["tail"].get(d, [])]; hd = st.mean(r["handdays"].get(d, 0) for r in res)
        rs = st.mean(r["resume"].get(d, 0) for r in res); tp = [r["tailpos"][d] for r in res if d in r["tailpos"]]
        print(f"{d:3d} | {hd:5.1f} | {st.mean(tails) if tails else 0:5.1f} | {sum(x >= 3 for x in tails) / len(res):5.1f} | {sum(tails) / len(res):6.1f} | {rs:5.1f} | {st.mean(tp) if tp else 0:4.1f}")
