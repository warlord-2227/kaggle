"""What did the opponent actually do? Read a downloaded replay."""
import json, sys, collections

def load(p):
    with open(p) as f: return json.load(f)

def summarize(path):
    r = load(path)
    steps = r["steps"]
    final = steps[-1]
    print(f"\n{'='*72}\n{path.split('/')[-1]}   steps={len(steps)}\n{'='*72}")
    rewards = [s.get("reward") for s in final]
    print(f"final rewards: {rewards}")
    # Which index are we? our agent is deterministic; identify by comparing.
    for idx in (0, 1):
        obs = final[0]["observation"]
        farm = obs["farms"][idx]
        tiles = farm["tiles"]
        kinds = collections.Counter()
        animals = collections.Counter()
        for row in tiles:
            for t in row:
                if t is None: kinds["empty"] += 1
                elif t == "LOCKED": kinds["LOCKED"] += 1
                elif isinstance(t, dict):
                    kinds[t.get("kind")] += 1
                    if t.get("animal"): animals[t["animal"]] += 1
                    if t.get("kind") == "PLANT": kinds["crop:"+t.get("crop","?")] += 1
        print(f"\n--- player {idx}  money={farm['money']:,.0f}  "
              f"quadrants={farm['unlocked_quadrants']}  hires_today={farm.get('hires_today')}")
        print(f"    tiles: {dict(kinds)}")
        print(f"    animals: {dict(animals)}")
    # Hand usage over the season
    for idx in (0, 1):
        hands = []
        for i, s in enumerate(steps):
            if i % 24 == 1:
                hands.append(len(s[0]["observation"]["farms"][idx].get("hands", [])))
        print(f"\n    player {idx} hands hired per day: {hands}")
    # Market: what moved
    m = final[0]["observation"]["market"]
    print(f"\n  market inventory vs 10000: "
          f"{ {k: v-10000 for k, v in m['inventory'].items() if v != 10000} }")
    print(f"  final prices: {m['prices']}")

for p in sys.argv[1:]:
    summarize(p)
