"""Multi-unit goose farm. Tests whether capacity-per-unit survives coordination.

Deadlock fix: each unit is in exactly one MODE, and the mode flips only on a
monotone condition (wheat in hand hits zero / becomes positive). It can never
oscillate between "go to shed" and "go to goose", which is what killed v1.

Each unit owns a disjoint set of tiles, assigned nearest-shed-first, so units
never compete for the same job.
"""
SHED = (4, 4)
QUAD_ORIGIN = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}


def _tiles_for(quadrants):
    """All tiles in owned quadrants, nearest to the shed first."""
    out = []
    for q in quadrants:
        ox, oy = QUAD_ORIGIN[q]
        for x in range(ox, ox + 5):
            for y in range(oy, oy + 5):
                out.append((abs(x - SHED[0]) + abs(y - SHED[1]), x, y))
    out.sort()
    return [(x, y) for _, x, y in out]


def _step(fx, fy, tx, ty):
    if fx < tx: return ["EAST"]
    if fx > tx: return ["WEST"]
    if fy < ty: return ["SOUTH"]
    if fy > ty: return ["NORTH"]
    return None


def make_agent(hands=8, geese_per_unit=4, quad_plan=(("NE", 3), ("SW", 6))):
    """quad_plan: list of (quadrant, day_to_buy)."""

    def agent(obs, config=None):
        try:
            return _decide(obs)
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}

    def _decide(obs):
        p = obs["player"]
        me = obs["farms"][p]
        priv = obs["private"]
        day, hour = obs["day"], obs["hour"]
        tiles = me["tiles"]
        money = me["money"]
        owned = me["unlocked_quadrants"]
        invs = priv["inventories"]
        shed = priv["shed"]
        market = []

        # --- market: hire at dawn, buy land on schedule, sell eggs always ----
        live0 = sum(1 for row in tiles for t in row
                    if isinstance(t, dict) and t.get("animal"))
        if hour == 0:
            # Each unit services ~4 geese; hiring ahead of the flock burns cash
            # every day for nothing. Ramp hands with the flock, not with the plan.
            want_hands = min(hands, max(0, live0 // 4))
            for _ in range(want_hands):
                market.append(["HIRE"])
        # Land is for proximity, but only once income covers it with room spare.
        for q, d in quad_plan:
            if day >= d and q not in owned and money > 3500:
                market.append(["BUY_LAND"])
                break
        if shed.get("EGG", 0) > 0:
            market.append(["SELL", "EGG", shed["EGG"]])

        # Feed buffer. Grown wheat takes ~4 days to arrive, so bootstrap by
        # buying -- but only ever top up to a small reserve, never in bulk:
        # buying 1,350 units costs 66,828, buying 100 costs 3,170.
        live_now = sum(1 for row in tiles for t in row
                       if isinstance(t, dict) and t.get("animal"))
        carried = sum(i.get("WHEAT", 0) for i in invs)
        reserve = shed.get("WHEAT", 0) + carried
        want = max(6, live_now * 3)
        # ONCE a day only. This fires every turn otherwise, which buys ~288
        # units/day up a rising price curve and drains the whole bank.
        if hour == 1 and reserve < want and money > 600:
            market.append(["BUY_PRODUCT", "WHEAT", min(20, want - reserve)])

        cells = _tiles_for(owned)
        n_units = 1 + len(me["hands"])
        target_geese = min(len(cells), n_units * geese_per_unit)

        # Buy a goose whenever we have spare capital and an empty pen to fill.
        live = sum(1 for (x, y) in cells
                   if isinstance(tiles[y][x], dict) and tiles[y][x].get("animal"))
        held = shed.get("GOOSE", 0) + sum(i.get("GOOSE", 0) for i in invs)
        feed_ok = (shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)) >= (live + 1) * 2
        if day <= 22 and live + held < target_geese and money >= 300 + 400 and feed_ok:
            market.append(["BUY_ANIMAL", "GOOSE", 1])

        # --- partition tiles across units, disjointly ------------------------
        goose_cells = cells[:target_geese]
        n_wheat = int(target_geese * 1.35) + 2
        wheat_cells = cells[target_geese:target_geese + n_wheat]
        assign = [[] for _ in range(n_units)]
        for i, c in enumerate(goose_cells):
            assign[i % n_units].append(("G", c))
        for i, c in enumerate(wheat_cells):
            assign[i % n_units].append(("W", c))

        def unit_op(u, pos):
            inv = invs[u] if u < len(invs) else {}
            fx, fy = pos
            mine = assign[u] if u < len(assign) else []
            wheat = inv.get("WHEAT", 0)

            unfed = [c for k, c in mine if k == "G"
                     and isinstance(tiles[c[1]][c[0]], dict)
                     and tiles[c[1]][c[0]].get("animal")
                     and not tiles[c[1]][c[0]]["fed_today"]]

            # MODE RESTOCK: monotone -- only entered with zero wheat in hand.
            if unfed and wheat == 0:
                if shed.get("WHEAT", 0) > 0:
                    mv = _step(fx, fy, *SHED)
                    return mv or ["PICKUP", "WHEAT", 12]
                # No wheat anywhere: go tend our wheat plot instead.

            # Place a goose we are carrying, or fetch one for an empty pen.
            for k, (x, y) in mine:
                if k != "G":
                    continue
                t = tiles[y][x]
                if isinstance(t, dict) and t.get("kind") == "COOP" and not t.get("animal"):
                    if inv.get("GOOSE", 0) > 0:
                        return _step(fx, fy, x, y) or ["PLACE", "GOOSE"]
                    if shed.get("GOOSE", 0) > 0:
                        return _step(fx, fy, *SHED) or ["PICKUP", "GOOSE", 1]

            # MODE SERVICE: nearest job among our own tiles.
            best, bd, bk = None, 99, None
            for k, (x, y) in mine:
                t = tiles[y][x]
                d = abs(x - fx) + abs(y - fy)
                if k == "G":
                    if t is None:
                        job = "BUILD"
                    elif isinstance(t, dict) and t.get("kind") == "WEED":
                        job = "DIG"
                    elif isinstance(t, dict) and t.get("animal"):
                        if t["yield_units"] >= 4: job = "HARVEST"
                        elif not t["fed_today"] and wheat > 0: job = "FEED"
                        elif not t["cared_today"]: job = "CARE"
                        elif t["yield_units"] > 0: job = "HARVEST"
                        else: continue
                    else:
                        continue
                else:  # wheat plot
                    if t is None:
                        job = "PLANT"
                    elif isinstance(t, dict) and t.get("kind") == "WEED":
                        job = "DIG"
                    elif isinstance(t, dict) and t.get("kind") == "PLANT":
                        age = day - t["planted_day"]
                        if age >= 4 and t["yield_units"] > 0: job = "HARVESTW"
                        elif not t["watered_today"]: job = "WATER"
                        else: continue
                    else:
                        continue
                if d < bd:
                    best, bd, bk = (x, y), d, job
            if best:
                mv = _step(fx, fy, *best)
                if mv:
                    return mv
                return {"BUILD": ["BUILD_COOP"], "DIG": ["DIG"], "HARVEST": ["HARVEST"],
                        "FEED": ["FEED"], "CARE": ["CARE"], "PLANT": ["PLANT", "WHEAT"],
                        "WATER": ["WATER"], "HARVESTW": ["HARVEST"]}[bk]

            # Idle: dump inventory at the shed so wheat is poolable.
            mv = _step(fx, fy, *SHED)
            return mv or ["DROP"]

        farmer_op = unit_op(0, me["farmer"])
        hand_ops = [unit_op(i + 1, h) for i, h in enumerate(me["hands"])]
        # Seeds for the wheat plots.
        if priv["seeds"].get("WHEAT", 0) < n_units * 2 and money > 400:
            market.append(["BUY_SEED", "WHEAT", n_units * 2])
        return {"farmer": farmer_op, "hands": hand_ops, "market": market[:10]}

    return agent
