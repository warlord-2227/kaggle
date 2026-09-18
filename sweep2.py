import statistics as st
from concurrent.futures import ProcessPoolExecutor
from kaggle_environments import make as mk
from crop import make
SEEDS=[7,11,23,42,99,123,256]
def job(a):
    h,ms,sp,seed=a
    env=mk("kaggriculture",configuration={"episodeSteps":720,"seed":seed})
    env.run([make(hands=h,melon_share=ms,wheat_share=0.30,sell_per_turn=sp),"pass"])
    return (h,ms,sp),env.steps[-1][0]["reward"]
if __name__=="__main__":
    grid=[(h,ms,sp,s) for h in (6,7,8,10) for ms in (0.35,0.40,0.45)
          for sp in (4,6,10) for s in SEEDS]
    with ProcessPoolExecutor() as ex: res=list(ex.map(job,grid))
    agg={}
    for k,v in res: agg.setdefault(k,[]).append(v)
    rank=sorted(((st.median(v),min(v),k) for k,v in agg.items()),reverse=True)
    print(f"{'hands':>6}{'melon':>7}{'sell/turn':>10}{'median':>10}{'worst':>10}")
    for med,mn,k in rank[:10]:
        print(f"{k[0]:>6}{k[1]:>7.0%}{k[2]:>10}{med:>10,.0f}{mn:>10,.0f}")
