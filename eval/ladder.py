import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
import statistics as st, sys
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
REF = ROOT + "refagents/"
TIERS=[("fallow_finn",0),("wheat_walter",1),("rotation_rosa",2),
       ("homestead_hana",3),("melon_mateo",4),("rancher_rita",5)]
def job(a):
    opp,seed,side=a
    env=mk("kaggriculture",configuration={"episodeSteps":720,"seed":seed})
    p=[ ROOT + "main.py", REF+opp+".py"]
    if side: p=p[::-1]
    env.run(p)
    r=env.steps[-1]
    mine,theirs=(r[0]["reward"],r[1]["reward"]) if side==0 else (r[1]["reward"],r[0]["reward"])
    return opp,mine,theirs
if __name__=="__main__":
    SEEDS=[7,11,23,42]
    jobs=[(o,s,side) for o,_ in TIERS for s in SEEDS for side in (0,1)]
    with ProcessPoolExecutor() as ex: res=list(ex.map(job,jobs))
    agg={}
    for o,m,t in res: agg.setdefault(o,[]).append((m,t))
    print(f"{'tier':>5}  {'opponent':<16}{'W':>3}{'L':>3}{'our median':>12}{'their median':>14}")
    for o,tier in TIERS:
        v=agg[o]; w=sum(1 for m,t in v if m>t); l=sum(1 for m,t in v if m<t)
        print(f"{tier:>5}  {o:<16}{w:>3}{l:>3}"
              f"{st.median([m for m,_ in v]):>12,.0f}{st.median([t for _,t in v]):>14,.0f}")
