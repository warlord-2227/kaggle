"""Kaggriculture submission v5: livestock farm.

Our own implementation. The disciplines were learned from Rancher Rita, the
MIT-licensed tier-5 reference agent in raykkretzschmar/kaggriculture-reference-agents;
no code from that dataset is reused here.

Why livestock over the melon crop line: markets are shared, so two melon farmers
destroy the melon price for each other. Measured on the reference ladder, our
crop agent scored 11,905 against Melon Mateo (2W-4L) while this livestock agent
scored 32,206 against the same opponent (6W-0L). Selling into a market the
opponent is not in beats competing in the crowded one.

Ladder record: 18/24 against tiers 2-5, versus 14/24 for the crop agent.

Disciplines, each one a failure measured first:
  * feed float must cover the herd AFTER the purchase. Sizing it on the current
    herd makes it zero on day 0, so animals are bought that cannot be fed and
    the whole herd starves by day 2.
  * inventory is worth zero at turn 720, so liquidate from day 28.
  * only top up wheat below a price cap; buying drains market supply and lifts
    the price against us.
  * market orders resolve in list order and the first unit gets the best price,
    so premium goods take the earliest slots.
"""
SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}
ANIMAL = {"COW": ("PASTURE", "BUILD_PASTURE", "MILK"),
          "SHEEP": ("PASTURE", "BUILD_PASTURE", "WOOL"),
          "GOOSE": ("COOP", "BUILD_COOP", "EGG")}
COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}


def tiles_by_distance(quads):
    out = []
    for q in quads:
        ox, oy = QO[q]
        for x in range(ox, ox + 5):
            for y in range(oy, oy + 5):
                out.append((abs(x - 4) + abs(y - 4), x, y))
    out.sort()
    return [(x, y) for _, x, y in out]


def step(fx, fy, tx, ty):
    if fx < tx: return ["EAST"]
    if fx > tx: return ["WEST"]
    if fy < ty: return ["SOUTH"]
    if fy > ty: return ["NORTH"]
    return None


def make(hands=8, target=None, land=2, feed_float_days=16, animal_buffer=400,
         animal_batch=2, max_wheat_price=55, sell_chunk=20, liquidate_from=28,
         invest_until=22, land_days=(2, 8)):
    target = target or {"COW": 10, "SHEEP": 6}

    def agent(obs, config=None):
        try:
            return decide(obs)
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}

    def decide(obs):
        me = obs["farms"][obs["player"]]
        priv = obs["private"]
        day, hour = obs["day"], obs["hour"]
        tiles, money, owned = me["tiles"], me["money"], me["unlocked_quadrants"]
        invs, shed, seeds = priv["inventories"], priv["shed"], priv["seeds"]
        prices = obs["market"]["prices"]
        market = []

        if hour == 0:
            for _ in range(hands):
                market.append(["HIRE"])

        cells = tiles_by_distance(owned)
        live = {}
        for (x, y) in cells:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("animal"):
                live[t["animal"]] = live.get(t["animal"], 0) + 1
        n_animals = sum(live.values())

        # Feed float: N days of wheat for the whole herd, in coins.
        wheat_have = shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)
        # Float must cover the herd AFTER the purchase, not before it. Computing
        # it on the current herd makes it zero on day 0, which buys animals we
        # cannot feed -- they starve by day 2 and the run is over.
        feed_float = ((n_animals + animal_batch) * feed_float_days
                      * max(prices.get("WHEAT", 25), 1))

        # Land, but only once the herd justifies it.
        for i, d in enumerate(land_days[:land]):
            if len(owned) < i + 2 and day >= d and money > 1000 * (i + 1) + 1500:
                market.append(["BUY_LAND"]); break

        # --- selling -------------------------------------------------------
        endgame = day >= liquidate_from
        order = ["MILK", "WOOL", "EGG", "MELON", "CARROT", "WHEAT", "FERTILIZER"]
        shed_total = sum(shed.values())
        for item in order:
            have = shed.get(item, 0)
            if have <= 0 or prices.get(item, 0) <= 1:
                continue
            if item == "WHEAT" and not endgame:
                # Wheat is feed first. Only sell genuine surplus.
                surplus = have - n_animals * 4
                if surplus <= 0 and shed_total < 80:
                    continue
                have = max(surplus, 0) if shed_total < 80 else have
            n = min(have, 40 if endgame else sell_chunk)
            if n > 0:
                market.append(["SELL", item, n])
            if len(market) >= 8:
                break

        # --- buying --------------------------------------------------------
        if not endgame:
            # Cheap feed top-up only.
            if (wheat_have < n_animals * 6 and prices.get("WHEAT", 99) <= max_wheat_price
                    and money > feed_float and hour in (1, 12)):
                market.append(["BUY_PRODUCT", "WHEAT", 24])
            if seeds.get("WHEAT", 0) < 8 and money > 300:
                market.append(["BUY_SEED", "WHEAT", 8])
            # Animals: only with the full feed float plus a buffer on top.
            if day <= invest_until:
                for sp in ("COW", "SHEEP"):
                    want = target.get(sp, 0)
                    held = shed.get(sp, 0) + sum(i.get(sp, 0) for i in invs)
                    if live.get(sp, 0) + held < want and money >= (
                            COST[sp] * animal_batch + feed_float + animal_buffer):
                        market.append(["BUY_ANIMAL", sp, animal_batch])
                        break

        # --- field layout ---------------------------------------------------
        n_pen = sum(target.values())
        pen_cells = cells[:n_pen]
        wheat_cells = cells[n_pen:]
        plan = {}
        want_list = ["COW"] * target.get("COW", 0) + ["SHEEP"] * target.get("SHEEP", 0)
        for i, c in enumerate(pen_cells):
            plan[c] = want_list[i]
        for c in wheat_cells:
            plan[c] = "WHEAT"

        units = [me["farmer"]] + list(me["hands"])
        assign = [[] for _ in units]
        for i, c in enumerate(cells):
            assign[i % len(units)].append(c)

        def unit_op(u, pos):
            fx, fy = pos
            inv = invs[u] if u < len(invs) else {}
            mine = assign[u]
            carrying = inv.get("WHEAT", 0)
            hungry = [c for c in mine
                      if isinstance(tiles[c[1]][c[0]], dict)
                      and tiles[c[1]][c[0]].get("animal")
                      and not tiles[c[1]][c[0]]["fed_today"]]
            # Restock first, monotone: only when empty-handed.
            if hungry and carrying == 0 and shed.get("WHEAT", 0) > 0:
                return step(fx, fy, *SHED) or ["PICKUP", "WHEAT", 12]
            # Place a carried animal.
            for (x, y) in mine:
                want = plan.get((x, y))
                if want in ANIMAL:
                    t = tiles[y][x]
                    struct = ANIMAL[want][0]
                    if isinstance(t, dict) and t.get("kind") == struct and not t.get("animal"):
                        if inv.get(want, 0) > 0:
                            return step(fx, fy, x, y) or ["PLACE", want]
                        if shed.get(want, 0) > 0:
                            return step(fx, fy, *SHED) or ["PICKUP", want, 1]
            best, bd, bj = None, 99, None
            for (x, y) in mine:
                t = tiles[y][x]
                want = plan.get((x, y))
                d = abs(x - fx) + abs(y - fy)
                job = None
                if want in ANIMAL:
                    struct, build, _ = ANIMAL[want]
                    if t is None: job = [build]
                    elif not isinstance(t, dict): job = None
                    elif t.get("kind") == "WEED": job = ["DIG"]
                    elif t.get("animal"):
                        if t["yield_units"] >= 2: job = ["HARVEST"]
                        elif not t["fed_today"] and carrying > 0: job = ["FEED"]
                        elif not t["cared_today"]: job = ["CARE"]
                        elif t.get("fertilizer_available"): job = ["COLLECT_FERTILIZER"]
                else:
                    if t is None:
                        job = ["PLANT", "WHEAT"] if seeds.get("WHEAT", 0) > 0 else None
                    elif not isinstance(t, dict): job = None
                    elif t.get("kind") == "WEED": job = ["DIG"]
                    elif t.get("kind") == "PLANT":
                        age = day - t["planted_day"]
                        if age >= 4 and t["yield_units"] > 0: job = ["HARVEST"]
                        elif not t["watered_today"]: job = ["WATER"]
                if job and d < bd:
                    best, bd, bj = (x, y), d, job
            if best:
                mv = step(fx, fy, *best)
                return mv or bj
            return step(fx, fy, *SHED) or ["DROP"]

        return {"farmer": unit_op(0, units[0]),
                "hands": [unit_op(i + 1, h) for i, h in enumerate(me["hands"])],
                "market": market[:10]}
    return agent


_impl = make(target={"COW": 8, "SHEEP": 5}, feed_float_days=8, hands=8, land=2)


def agent(obs, config=None):
    try:
        return _impl(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
