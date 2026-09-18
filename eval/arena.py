"""Local arena: play agents head-to-head and report win rate.

Rating on Kaggle depends only on win/loss/tie, not coin margin, so win rate
is the metric that matters -- coin stats are diagnostic only.
"""
import argparse, os, random, statistics as st
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("PYTHONWARNINGS", "ignore")


def play(args):
    """Run one episode. Returns (a_coins, b_coins, a_status, b_status)."""
    a, b, seed, steps = args
    from kaggle_environments import make
    cfg = {"episodeSteps": steps, "seed": seed}
    env = make("kaggriculture", configuration=cfg)
    env.run([a, b])
    fin = env.steps[-1]
    return (fin[0]["reward"], fin[1]["reward"],
            fin[0]["status"], fin[1]["status"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("agent_a")
    p.add_argument("agent_b")
    p.add_argument("-n", "--games", type=int, default=20)
    p.add_argument("-s", "--steps", type=int, default=720)
    p.add_argument("-j", "--jobs", type=int, default=os.cpu_count())
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    rng = random.Random(args.seed)
    seeds = [rng.randrange(1 << 30) for _ in range(args.games)]

    # Play each seed twice with sides swapped to cancel any first-player edge.
    jobs = [(args.agent_a, args.agent_b, s, args.steps) for s in seeds]
    jobs += [(args.agent_b, args.agent_a, s, args.steps) for s in seeds]

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(play, jobs))

    n = args.games
    a_coins, b_coins, wins, losses, ties, errs = [], [], 0, 0, 0, 0
    for i, (r0, r1, s0, s1) in enumerate(res):
        # First n jobs: A is player 0. Second n: A is player 1.
        ac, bc = (r0, r1) if i < n else (r1, r0)
        as_, bs_ = (s0, s1) if i < n else (s1, s0)
        if as_ != "DONE" or bs_ != "DONE":
            errs += 1
        a_coins.append(ac); b_coins.append(bc)
        if ac > bc: wins += 1
        elif ac < bc: losses += 1
        else: ties += 1

    tot = len(res)
    print(f"{args.agent_a}  vs  {args.agent_b}   ({tot} games, {n} seeds x2 sides)")
    print(f"  record : {wins}W {losses}L {ties}T")
    print(f"  winrate: {wins / tot:.1%}  (+ties {(wins + 0.5 * ties) / tot:.1%})")
    print(f"  coins A: median {st.median(a_coins):>10,.0f}   mean {st.mean(a_coins):>10,.0f}   max {max(a_coins):>10,.0f}")
    print(f"  coins B: median {st.median(b_coins):>10,.0f}   mean {st.mean(b_coins):>10,.0f}   max {max(b_coins):>10,.0f}")
    if errs:
        print(f"  !! {errs} games had a non-DONE status")


if __name__ == "__main__":
    main()
