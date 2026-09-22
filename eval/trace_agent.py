"""Replay a recorded ladder opponent as a sparring agent.

A Kaggle replay holds both players' actions for all 720 steps. Returning the
recorded action for the current step reproduces that opponent open-loop: its
farm decisions are fixed, only the shared market reacts to us. This is exactly
how the "meta line" reference agents were built. Local sparring only.
"""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL = os.path.join(ROOT, "replays", "pool")


def load_trace(path, player_idx):
    d = json.load(open(path))
    steps = d["steps"]
    # steps[i]["action"] is the action that produced state i, i.e. chosen at step i-1
    acts = [None] * len(steps)
    for i in range(1, len(steps)):
        a = steps[i][player_idx].get("action")
        acts[i - 1] = a if isinstance(a, dict) else None
    return acts


def make(path, player_idx):
    acts = load_trace(path, player_idx)
    empty = {"farmer": ["PASS"], "hands": [], "market": []}

    def agent(obs, config=None):
        i = obs["step"]
        a = acts[i] if i < len(acts) else None
        return a or empty
    return agent


def episode_seed(path):
    """The recorded game's seed (replay info.seed). A trace is only faithful on its own seed
    and on the REAL environment (fair_env changes the shop draw for the same seed)."""
    d = json.load(open(path))
    s = (d.get("info") or {}).get("seed") or d["configuration"].get("seed")
    return int(s)


_SEEDS = {}


def pool(min_rating=0, limit=None, folder="pool"):
    """[(name, path, idx, rating), ...] from replays/<folder>/manifest.json, strongest first."""
    base = os.path.join(ROOT, "replays", folder)
    man = json.load(open(os.path.join(base, "manifest.json")))
    out = []
    for p in man:
        path = os.path.join(base, f"episode-{p['ep']}-replay.json")
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000 and p["opp_rating"] >= min_rating:
            out.append((f"r{p['opp_rating']}_{p['opp_sub']}", path, p["opp_idx"], p["opp_rating"]))
    return out[:limit] if limit else out


def seed_of(path):
    if path not in _SEEDS: _SEEDS[path] = episode_seed(path)
    return _SEEDS[path]
