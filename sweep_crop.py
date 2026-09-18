import statistics as st
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
from crop import make
SEEDS=[7,11,23,42,99]
def job(a):
    h,ms,ws,sp,seed=a
    env=mk("kaggriculture",configuration={"episodeSteps":720,"seed":seed})
    env.run([make(hands=h,melon_share=ms,wheat_share=ws,sell_per_turn=sp),"pass"])
    return (h,ms,ws,sp),env.steps[-1][0]["reward"]
if __name__=="__main__":
    grid=[(h,ms,ws,sp,s)
          for h in (2,3,4,5,6)
          for ms in (0.20,0.30,0.40)
          for ws in (0.30,0.45)
          for sp in (6,)
          for s in SEEDS]
    with ProcessPoolExecutor() as ex: res=list(ex.map(job,grid))
    agg={}
    for k,v in res: agg.setdefault(k,[]).append(v)
    rank=sorted(((st.median(v),min(v),k) for k,v in agg.items()),reverse=True)
    print(f"{'hands':>6}{'melon':>7}{'wheat':>7}{'median':>10}{'worst':>10}")
    for med,mn,k in rank[:12]:
        print(f"{k[0]:>6}{k[1]:>7.0%}{k[2]:>7.0%}{med:>10,.0f}{mn:>10,.0f}")
