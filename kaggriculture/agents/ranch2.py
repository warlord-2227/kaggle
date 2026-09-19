"""Livestock + wheat-for-sale farm. Built from the ladder research (Objective
model, "Why we are at 500"):

  * v6 collapsed to 2,285 and 9,010 against other ranches because it BOUGHT
    ~3,000 wheat while the opponent SOLD 3,000 -- we funded them. Wheat is now
    grown on every spare tile, eaten first, surplus sold. Buying is a day-0-to-5
    bridge only, before the first harvest lands.
  * v6 left 60% of unit-actions idle on 8 hands. Hands are staged: few early,
    scaled with tiles, 10 for liquidation.
  * Spend to near-zero on day 0 (cows, a sheep, melon seeds, starter feed) --
    cash sitting idle earns nothing and the herd needs 8 days to first yield.
  * Melon as a bridge loan: seeds on day 0, sold ~day 10 at ~250, funding land.
  * Land bought from income, not starting capital.
  * Fertilizer collected daily and sold.
  * Liquidate from day 26: inventory is worth zero at turn 720.
"""
import math

SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}
ANIMAL = {"COW": ("PASTURE", "BUILD_PASTURE", "MILK"),
          "SHEEP": ("PASTURE", "BUILD_PASTURE", "WOOL")}
COST = {"COW": 400, "SHEEP": 500}
# (first_yield_day, harvest_age)
CROP = {"WHEAT": (2, 4), "MELON": (10, 10), "STRAWBERRY": (10, 10)}


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


def make(target=None, day0=None, melon_bridge=4, n_straw=0,
         hands_early=3, hands_mid=5, hands_late=10, late_from=26,
         land_from=6, land_reserve=600,
         feed_reserve_days=3, bridge_buy_until=6,
         sell_chunk=20, invest_until=22, cash_floor=120, max_wheat=24):
    """target: final herd. day0: herd bought on day 0 (default 3 cows, 1 sheep)."""
    target = target or {"COW": 8, "SHEEP": 5}
    day0 = day0 or {"COW": 3, "SHEEP": 1}

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
        endgame = day >= late_from

        cells = tiles_by_distance(owned)
        live = {}
        for (x, y) in cells:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("animal"):
                live[t["animal"]] = live.get(t["animal"], 0) + 1
        n_animals = sum(live.values())
        wheat_have = shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)

        # --- hands: staged ------------------------------------------------
        if hour == 0:
            n = hands_late if endgame else (hands_mid if len(owned) >= 2 else hands_early)
            for _ in range(n):
                market.append(["HIRE"])

        # --- land: from income --------------------------------------------
        land_cost = [1000, 2000, 4000]
        nq = len(owned)
        herd_frac = n_animals / max(1, sum(target.values()))
        land_ready = herd_frac >= (0.5 if nq == 1 else 0.85)
        if nq < 2 and day >= land_from and land_ready and money > land_cost[nq - 1] + land_reserve:
            market.append(["BUY_LAND"])

        # --- selling: premium first, wheat surplus, everything at the end -
        reserve = 0 if endgame else n_animals * feed_reserve_days
        for item in ("MILK", "WOOL", "MELON", "STRAWBERRY", "FERTILIZER", "WHEAT"):
            have = shed.get(item, 0)
            if item == "WHEAT":
                have -= reserve
            if have <= 0 or prices.get(item, 0) <= 1:
                continue
            market.append(["SELL", item, min(have, 60 if endgame else sell_chunk)])
            if len(market) >= 7:
                break

        def held(sp):
            return shed.get(sp, 0) + sum(i.get(sp, 0) for i in invs)

        # --- buying -------------------------------------------------------
        if not endgame:

            if day == 0 and hour == 1:
                # Spend to near-zero -- but feed FIRST. Orders resolve in list
                # order and stop when cash runs out; with feed last, the 45
                # wheat never bought and the sheep starved on day 2.
                market.append(["BUY_PRODUCT", "WHEAT", 40])
                for sp, n in day0.items():
                    market.append(["BUY_ANIMAL", sp, n])
                market.append(["BUY_SEED", "WHEAT", 10])
                if melon_bridge:
                    market.append(["BUY_SEED", "MELON", melon_bridge])
            else:
                # Bridge feed only until our own wheat lands.
                short = wheat_have < n_animals * 2
                if short and hour in (1, 9, 17) and money > 30:
                    # Feed first, always. An unfed animal is gone for good.
                    n = max(4, n_animals * 2 - wheat_have)
                    market.append(["BUY_PRODUCT", "WHEAT", min(n, int(money // max(prices.get("WHEAT", 30), 1)))])
                # Seed stock.
                if seeds.get("WHEAT", 0) < 6 and money > cash_floor + 100:
                    market.append(["BUY_SEED", "WHEAT", 8])
                if n_straw and seeds.get("STRAWBERRY", 0) < 4 and nq >= 2 and money > 800:
                    market.append(["BUY_SEED", "STRAWBERRY", 4])
                # Grow the herd as cash arrives; feed is grown, so no cash float,
                # but never below a small floor and never a bird we cannot feed
                # for two days from stock.
                if day <= invest_until and hour == 2:
                    for sp in ("COW", "SHEEP"):
                        if live.get(sp, 0) + held(sp) < target.get(sp, 0):
                            growing = sum(1 for (x, y) in cells
                                          if isinstance(tiles[y][x], dict)
                                          and tiles[y][x].get("crop") == "WHEAT")
                            feed_ok = growing >= (n_animals + 1) * 1.3 or wheat_have >= (n_animals + 1) * 3
                            if money >= COST[sp] + cash_floor + 150 and feed_ok:
                                market.append(["BUY_ANIMAL", sp, 1])
                            break

        # --- field plan ----------------------------------------------------
        # Pens for the herd we have (plus what we hold and one ahead), in the
        # target ratio; the rest of the near tiles go to wheat now and are
        # converted to pens as the herd grows.
        n_pen = min(sum(target.values()),
                    n_animals + sum(held(sp) for sp in ANIMAL) + 2)
        plan = {}
        want_list = ["COW"] * target["COW"] + ["SHEEP"] * target["SHEEP"]
        # keep already-built pens where they are
        built = [(x, y) for (x, y) in cells
                 if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PASTURE"]
        pen_cells = built[:]
        for c in cells:
            if len(pen_cells) >= n_pen: break
            if c not in pen_cells: pen_cells.append(c)
        for i, c in enumerate(pen_cells):
            plan[c] = want_list[min(i, len(want_list) - 1)]
        rest = [c for c in cells if c not in plan]
        for c in rest[:melon_bridge]:
            plan[c] = "MELON"
        for c in rest[melon_bridge:melon_bridge + n_straw]:
            plan[c] = "STRAWBERRY"
        for c in rest[melon_bridge + n_straw:melon_bridge + n_straw + max_wheat]:
            plan[c] = "WHEAT"
        # Tiles beyond the labour cap stay unplanned: an unwatered plant is a weed.

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
            if hungry and carrying == 0 and shed.get("WHEAT", 0) > 0:
                return step(fx, fy, *SHED) or ["PICKUP", "WHEAT", min(12, shed["WHEAT"])]
            for (x, y) in mine:
                want = plan.get((x, y))
                if want in ANIMAL:
                    t = tiles[y][x]
                    if isinstance(t, dict) and t.get("kind") == ANIMAL[want][0] and not t.get("animal"):
                        if inv.get(want, 0) > 0:
                            return step(fx, fy, x, y) or ["PLACE", want]
                        if shed.get(want, 0) > 0:
                            return step(fx, fy, *SHED) or ["PICKUP", want, 1]
            best, bd, bj = None, 99, None
            for (x, y) in mine:
                t = tiles[y][x]
                want = plan.get((x, y))
                if want is None:
                    continue
                d = abs(x - fx) + abs(y - fy)
                job = None
                if want in ANIMAL:
                    struct, build, _ = ANIMAL[want]
                    if t is None: job = [build]
                    elif not isinstance(t, dict): pass
                    elif t.get("kind") == "WEED": job = ["DIG"] if not endgame else None
                    elif t.get("animal"):
                        if t["yield_units"] >= 2: job = ["HARVEST"]
                        elif not t["fed_today"] and carrying > 0: job = ["FEED"]
                        elif not t["cared_today"]: job = ["CARE"]
                        elif t.get("fertilizer_available"): job = ["COLLECT_FERTILIZER"]
                else:
                    if t is None:
                        # Do not plant what cannot mature before the end.
                        first, _ = CROP[want]
                        if day + first <= 29 and seeds.get(want, 0) > 0:
                            job = ["PLANT", want]
                    elif not isinstance(t, dict): pass
                    elif t.get("kind") == "WEED": job = ["DIG"] if not endgame else None
                    elif t.get("kind") == "PLANT":
                        c = t["crop"]; age = day - t["planted_day"]
                        _, ready = CROP.get(c, (2, 4))
                        if age >= ready and t["yield_units"] > 0: job = ["HARVEST"]
                        elif endgame and t["yield_units"] > 0: job = ["HARVEST"]
                        elif not t["watered_today"]: job = ["WATER"]
                if job and d < bd:
                    best, bd, bj = (x, y), d, job
            if best:
                return step(fx, fy, *best) or bj
            return step(fx, fy, *SHED) or ["DROP"]

        return {"farmer": unit_op(0, units[0]),
                "hands": [unit_op(i + 1, h) for i, h in enumerate(me["hands"])],
                "market": market[:10]}
    return agent
