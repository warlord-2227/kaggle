"""Probe experiments: isolate one mechanic at a time and measure it."""
from kaggle_environments import make

def run(agent, steps=720, label=""):
    env = make("kaggriculture", configuration={"episodeSteps": steps})
    env.run([agent, "pass"])
    fin = env.steps[-1]
    print(f"{label:<34} final={fin[0]['reward']:>10,.0f}  status={fin[0]['status']}")
    return env

# ---- Probe 1: one goose, FEED+CARE daily, HARVEST when full -------------
def goose_agent(obs):
    me = obs["farms"][obs["player"]]
    priv, mkt = obs["private"], []
    fx, fy = me["farmer"]
    tile = me["tiles"][fy][fx]
    inv = priv["inventories"][0]
    shed = priv["shed"]

    # Keep wheat stocked for feed.
    if shed.get("WHEAT", 0) + inv.get("WHEAT", 0) < 5 and me["money"] > 200:
        mkt.append(["BUY_PRODUCT", "WHEAT", 5])
    if shed.get("EGG", 0) > 0:
        mkt.append(["SELL", "EGG", shed["EGG"]])

    # Build the coop and place the goose on the starting tile.
    if tile is None:
        if shed.get("GOOSE", 0) == 0 and me["money"] >= 300:
            mkt.append(["BUY_ANIMAL", "GOOSE", 1])
        return {"farmer": ["BUILD_COOP"], "hands": [], "market": mkt}
    if isinstance(tile, dict) and tile.get("kind") == "COOP":
        if tile.get("animal") is None:
            if inv.get("GOOSE", 0) > 0:
                return {"farmer": ["PLACE", "GOOSE"], "hands": [], "market": mkt}
            if shed.get("GOOSE", 0) > 0:   # must stand adjacent to shed to pick up
                return {"farmer": ["PICKUP", "GOOSE", 1], "hands": [], "market": mkt}
            return {"farmer": ["PASS"], "hands": [], "market": mkt}
        # Animal present: harvest when near cap, else feed, care, restock wheat.
        if tile.get("yield_units", 0) >= 4:
            return {"farmer": ["HARVEST"], "hands": [], "market": mkt}
        if not tile.get("fed_today"):
            if inv.get("WHEAT", 0) > 0:
                return {"farmer": ["FEED"], "hands": [], "market": mkt}
            return {"farmer": ["PICKUP", "WHEAT", 10], "hands": [], "market": mkt}
        if not tile.get("cared_today"):
            return {"farmer": ["CARE"], "hands": [], "market": mkt}
        if tile.get("yield_units", 0) > 0:
            return {"farmer": ["HARVEST"], "hands": [], "market": mkt}
        return {"farmer": ["DROP"], "hands": [], "market": mkt}
    return {"farmer": ["PASS"], "hands": [], "market": mkt}

# ---- Probe 2: pure wheat loop on the one starting tile ------------------
def wheat_agent(obs):
    me = obs["farms"][obs["player"]]
    priv, mkt = obs["private"], []
    fx, fy = me["farmer"]
    tile = me["tiles"][fy][fx]
    if priv["seeds"].get("WHEAT", 0) < 2 and me["money"] >= 20:
        mkt.append(["BUY_SEED", "WHEAT", 2])
    if priv["shed"].get("WHEAT", 0) > 0:
        mkt.append(["SELL", "WHEAT", priv["shed"]["WHEAT"]])
    if tile is None:
        return {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": mkt}
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        age = obs["day"] - tile["planted_day"]
        if age >= 4 and tile["yield_units"] > 0:
            return {"farmer": ["HARVEST"], "hands": [], "market": mkt}
        if not tile["watered_today"]:
            return {"farmer": ["WATER"], "hands": [], "market": mkt}
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return {"farmer": ["DIG"], "hands": [], "market": mkt}
    return {"farmer": ["DROP"], "hands": [], "market": mkt}

print("Single-tile probes (opponent = pass, start = 3000):")
e1 = run(goose_agent, label="  1 goose, feed+care+harvest")
e2 = run(wheat_agent,  label="  1 tile wheat loop")
run("starter",         label="  starter (reference)")

# Inspect the goose tile at the end.
f = e1.steps[-1][0]["observation"]["farms"][0]
for row in f["tiles"]:
    for t in row:
        if isinstance(t, dict) and "animal" in t:
            print("\n  goose tile at end:", {k: t[k] for k in
                  ("animal", "yield_units", "consecutive_unfed", "pending_care_bonus")})
