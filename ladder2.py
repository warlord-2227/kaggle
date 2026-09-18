import statistics as st
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
from crop import make
REF="refagents/"
OPPS=["melon_mateo","rancher_rita","homestead_hana"]
def job(a):
    cfg,opp,seed,side=a
    env=mk("kaggriculture",configuration={"episodeSteps":720,"seed":seed})
    me=make(**cfg); them=REF+opp+".py"
    env.run([me,them] if side==0 else [them,me])
    r=env.steps[-1]
    m,t=(r[0]["reward"],r[1]["reward"]) if side==0 else (r[1]["reward"],r[0]["reward"])
    return (cfg["floor_frac"],cfg["adapt"]),opp,m,t
if __name__=="__main__":
    SEEDS=[7,11,23]
    cfgs=[dict(hands=6,melon_share=0.40,wheat_share=0.30,sell_per_turn=6,
               floor_frac=f,adapt=a) for f in (0.0,0.45,0.60) for a in (False,True)]
    jobs=[(c,o,s,side) for c in cfgs for o in OPPS for s in SEEDS for side in (0,1)]
    with ProcessPoolExecutor() as ex: res=list(ex.map(job,jobs))
    agg={}
    for k,o,m,t in res: agg.setdefault((k,o),[]).append((m,t))
    print(f"{'floor':>6}{'adapt':>7}{'opponent':>16}{'W':>3}{'L':>3}{'ours':>10}{'theirs':>10}")
    for (k,o),v in sorted(agg.items()):
        w=sum(1 for m,t in v if m>t); l=len(v)-w
        print(f"{k[0]:>6.0%}{str(k[1]):>7}{o:>16}{w:>3}{l:>3}"
              f"{st.median([m for m,_ in v]):>10,.0f}{st.median([t for _,t in v]):>10,.0f}")
