"""Benchmark ONLY. The tier 6-9 agents embed an unlicensed meta trace; we use
them here as sparring partners to size the gap, and never submit them."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + "/"
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
from kaggriculture.agents.ranch import make as ranch
from kaggriculture.agents.crop import make as crop
REF = ROOT + "refagents/"
META=["broker_bea","ledger_lena","slotter_silas","closer_cleo"]
R=lambda: ranch(target={"COW":8,"SHEEP":5},feed_float_days=8)
C=lambda: crop(hands=6,melon_share=0.40,wheat_share=0.30,sell_per_turn=6,adapt=True)
def job(a):
    who,opp,seed,side=a
    me = R() if who=="ranch" else C()
    them=REF+opp+".py"
    env=mk("kaggriculture",configuration={"episodeSteps":720,"seed":seed})
    env.run([me,them] if side==0 else [them,me])
    r=env.steps[-1]
    m,t=(r[0]["reward"],r[1]["reward"]) if side==0 else (r[1]["reward"],r[0]["reward"])
    return who,opp,m,t
if __name__=="__main__":
    SEEDS=[7,11]
    jobs=[(w,o,s,sd) for w in ("ranch","crop") for o in META for s in SEEDS for sd in (0,1)]
    with ProcessPoolExecutor() as ex: res=list(ex.map(job,jobs))
    agg={}
    for w,o,m,t in res: agg.setdefault((w,o),[]).append((m,t))
    print(f"{'agent':>7}{'meta opponent':>16}{'W':>3}{'L':>3}{'ours':>10}{'theirs':>10}{'ratio':>8}")
    for (w,o),v in sorted(agg.items()):
        wins=sum(1 for m,t in v if m>t)
        om=st.median([m for m,_ in v]); tm=st.median([t for _,t in v])
        print(f"{w:>7}{o:>16}{wins:>3}{len(v)-wins:>3}{om:>10,.0f}{tm:>10,.0f}{tm/max(om,1):>8.1f}x")
