"""Measure real movement/logistics overhead: N geese serviced by one farmer.

Restock-first state machine: never walk to a goose without the wheat to feed it.
"""
from kaggle_environments import make

SHED = (4, 4)


def make_agent(n_geese, cells=None):
    def agent(obs):
        me = obs["farms"][obs["player"]]
        priv, mkt = obs["private"], []
        fx, fy = me["farmer"]
        tiles, inv, shed = me["tiles"], priv["inventories"][0], priv["shed"]

        if shed.get("EGG", 0) > 0:
            mkt.append(["SELL", "EGG", shed["EGG"]])
        if shed.get("WHEAT", 0) < n_geese * 4 and me["money"] > 500:
            mkt.append(["BUY_PRODUCT", "WHEAT", n_geese * 2])

        _c = cells if cells is not None else [(x, y) for y in range(5) for x in range(5)]
        _cells = _c[:n_geese]

        def step_to(tx, ty):
            if fx < tx: return ["EAST"]
            if fx > tx: return ["WEST"]
            if fy < ty: return ["SOUTH"]
            if fy > ty: return ["NORTH"]
            return None

        have_goose = inv.get("GOOSE", 0) > 0
        need_feed = [(x, y) for (x, y) in _cells
                     if isinstance(tiles[y][x], dict) and tiles[y][x].get("animal")
                     and not tiles[y][x]["fed_today"]]

        # 1. Restock FIRST -- never approach a goose without wheat in hand.
        if len(need_feed) > inv.get("WHEAT", 0):
            if shed.get("WHEAT", 0) > 0:
                mv = step_to(*SHED)
                if mv:
                    return {"farmer": mv, "hands": [], "market": mkt}
                return {"farmer": ["PICKUP", "WHEAT", n_geese * 3], "hands": [], "market": mkt}

        # 2. Service the nearest goose that needs something we can give.
        best, bestd = None, 99
        for (x, y) in _cells:
            t = tiles[y][x]
            if not (isinstance(t, dict) and t.get("animal")):
                continue
            needs = ((not t["fed_today"] and inv.get("WHEAT", 0) > 0)
                     or not t["cared_today"] or t["yield_units"] >= 4)
            if needs:
                d = abs(x - fx) + abs(y - fy)
                if d < bestd:
                    best, bestd = (x, y), d
        if best:
            x, y = best
            mv = step_to(x, y)
            if mv:
                return {"farmer": mv, "hands": [], "market": mkt}
            t = tiles[y][x]
            if t["yield_units"] >= 4:
                return {"farmer": ["HARVEST"], "hands": [], "market": mkt}
            if not t["fed_today"] and inv.get("WHEAT", 0) > 0:
                return {"farmer": ["FEED"], "hands": [], "market": mkt}
            return {"farmer": ["CARE"], "hands": [], "market": mkt}

        # 3. Expand: build a coop, or fetch and place a goose.
        for (x, y) in _cells:
            t = tiles[y][x]
            if t is None:
                mv = step_to(x, y)
                return {"farmer": mv or ["BUILD_COOP"], "hands": [], "market": mkt}
            if isinstance(t, dict) and t.get("kind") == "COOP" and not t.get("animal"):
                if have_goose:
                    mv = step_to(x, y)
                    return {"farmer": mv or ["PLACE", "GOOSE"], "hands": [], "market": mkt}
                if shed.get("GOOSE", 0) > 0:
                    mv = step_to(*SHED)
                    return {"farmer": mv or ["PICKUP", "GOOSE", 1], "hands": [], "market": mkt}
                if me["money"] >= 300:
                    mkt.append(["BUY_ANIMAL", "GOOSE", 1])
                break

        # 4. Idle: harvest anything pending, else top up wheat at the shed.
        for (x, y) in _cells:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("yield_units", 0) > 0:
                mv = step_to(x, y)
                return {"farmer": mv or ["HARVEST"], "hands": [], "market": mkt}
        mv = step_to(*SHED)
        return {"farmer": mv or ["DROP"], "hands": [], "market": mkt}
    return agent


if __name__ == "__main__":
    print(f"{'geese':>6}{'final':>10}{'profit':>9}{'$/goose':>9}{'alive':>7}{'eggs sold':>11}")
    for n in (1, 2, 3, 4, 6, 8, 12, 16):
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 7})
        env.run([make_agent(n), "pass"])
        fin = env.steps[-1][0]
        money = fin["reward"]
        farm = fin["observation"]["farms"][0]
        alive = sum(1 for row in farm["tiles"] for t in row
                    if isinstance(t, dict) and t.get("animal"))
        eggs = fin["observation"]["market"]["inventory"]["EGG"] - 10000
        print(f"{n:>6}{money:>10,.0f}{money-3000:>9,.0f}{(money-3000)/n:>9,.0f}"
              f"{alive:>7}{eggs:>11}")
