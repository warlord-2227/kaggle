"""Phase 0 Q1: how much does distance from the shed cost?

One goose on a tile at Manhattan distance d from the shed (4,4).
Farmer does nothing else. Measure season profit vs d.
"""
from kaggle_environments import make

SHED = (4, 4)


def make_agent(tx, ty):
    def agent(obs):
        me = obs["farms"][obs["player"]]
        priv, mkt = obs["private"], []
        fx, fy = me["farmer"]
        tiles, inv, shed = me["tiles"], priv["inventories"][0], priv["shed"]
        tile = tiles[ty][tx]

        if shed.get("EGG", 0) > 0:
            mkt.append(["SELL", "EGG", shed["EGG"]])
        if shed.get("WHEAT", 0) < 8 and me["money"] > 300:
            mkt.append(["BUY_PRODUCT", "WHEAT", 5])

        def step_to(gx, gy):
            if fx < gx: return ["EAST"]
            if fx > gx: return ["WEST"]
            if fy < gy: return ["SOUTH"]
            if fy > gy: return ["NORTH"]
            return None

        def act(op): return {"farmer": op, "hands": [], "market": mkt}

        # Need wheat in hand before walking out (one trip carries plenty).
        if tile is not None and isinstance(tile, dict) and tile.get("animal"):
            if not tile["fed_today"] and inv.get("WHEAT", 0) == 0:
                mv = step_to(*SHED)
                return act(mv or ["PICKUP", "WHEAT", 5])

        if tile is None:
            if shed.get("GOOSE", 0) == 0 and inv.get("GOOSE", 0) == 0 and me["money"] >= 300:
                mkt.append(["BUY_ANIMAL", "GOOSE", 1])
            mv = step_to(tx, ty)
            return act(mv or ["BUILD_COOP"])

        if isinstance(tile, dict) and tile.get("kind") == "COOP" and not tile.get("animal"):
            if inv.get("GOOSE", 0) > 0:
                mv = step_to(tx, ty)
                return act(mv or ["PLACE", "GOOSE"])
            if shed.get("GOOSE", 0) > 0:
                mv = step_to(*SHED)
                return act(mv or ["PICKUP", "GOOSE", 1])
            if me["money"] >= 300:
                mkt.append(["BUY_ANIMAL", "GOOSE", 1])
            return act(["PASS"])

        if isinstance(tile, dict) and tile.get("animal"):
            mv = step_to(tx, ty)
            if mv: return act(mv)
            if tile["yield_units"] >= 4: return act(["HARVEST"])
            if not tile["fed_today"] and inv.get("WHEAT", 0) > 0: return act(["FEED"])
            if not tile["cared_today"]: return act(["CARE"])
            if tile["yield_units"] > 0: return act(["HARVEST"])
            return act(["PASS"])
        return act(["PASS"])
    return agent


print(f"{'tile':>8}{'dist':>6}{'profit':>9}{'vs d=0':>9}   (one goose, 30 days)")
base = None
for (tx, ty) in [(4,4),(3,4),(2,4),(1,4),(0,4),(0,3),(0,2),(0,1),(0,0)]:
    d = abs(tx-4) + abs(ty-4)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 7})
    env.run([make_agent(tx, ty), "pass"])
    profit = env.steps[-1][0]["reward"] - 3000
    if base is None: base = profit
    print(f"{str((tx,ty)):>8}{d:>6}{profit:>9,.0f}{profit-base:>9,.0f}")
