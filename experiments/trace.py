"""Trace money day-by-day for a head-to-head game, to show what win/loss looks like."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import sys
from kaggle_environments import make
from experiments.probe import goose_agent, wheat_agent

def trace(a, b, label, seed=7):
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([a, b])
    rows = []
    for step_i, step in enumerate(env.steps):
        if step_i % 24 != 0:       # once per day
            continue
        obs = step[0]["observation"]
        f = obs["farms"]
        rows.append((step_i // 24, f[0]["money"], f[1]["money"]))
    fin = env.steps[-1]
    a_end, b_end = fin[0]["reward"], fin[1]["reward"]
    verdict = "WIN " if a_end > b_end else ("LOSS" if a_end < b_end else "TIE ")
    print(f"\n{'='*66}\n{label}   ->  {verdict}  {a_end:,.0f} vs {b_end:,.0f}\n{'='*66}")
    print(f"{'day':>4}{'A money':>12}{'B money':>12}{'A-B':>12}")
    for d, ma, mb in rows:
        if d % 3 == 0 or d >= 28:
            print(f"{d:>4}{ma:>12,.0f}{mb:>12,.0f}{ma-mb:>12,.0f}")
    return a_end, b_end

trace(goose_agent, "starter", "A = 1 goose (single tile)   B = starter")
trace(wheat_agent, "starter", "A = 1 wheat tile            B = starter")
trace("random",    "starter", "A = random                  B = starter")
