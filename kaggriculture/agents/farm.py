"""Parameterised goose+wheat farm. One clean core, used for both 1-unit and N-unit tests."""
import math
SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}


def tiles_by_distance(quadrants):
    out = []
    for q in quadrants:
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


ANIMAL_SPEC = {"GOOSE": ("COOP", "BUILD_COOP"),
               "COW": ("PASTURE", "BUILD_PASTURE"),
               "SHEEP": ("PASTURE", "BUILD_PASTURE")}


def make(geese_per_unit=3, hands=0, quad_plan=(), wheat_ratio=1.25,
         stop_buy_day=22, ambition=99, n_cows=0, n_sheep=0, premium_day=12):
    def agent(obs, config=None):
        try:
            return decide(obs)
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}

    def decide(obs):
        p = obs["player"]; me = obs["farms"][p]; priv = obs["private"]
        day, hour = obs["day"], obs["hour"]
        tiles, money, owned = me["tiles"], me["money"], me["unlocked_quadrants"]
        invs, shed = priv["inventories"], priv["shed"]
        market = []

        cells = tiles_by_distance(owned)
        n_units = 1 + len(me["hands"])
        # Tile budget: each goose needs itself + wheat_ratio plots.
        cap_tiles = int(len(cells) / (1 + wheat_ratio))
        target_g = min(cap_tiles, ambition)
        n_wheat = math.ceil((target_g + n_cows + n_sheep) * wheat_ratio)

        live = sum(1 for (x, y) in cells
                   if isinstance(tiles[y][x], dict) and tiles[y][x].get("animal"))

        # Hire only what the flock justifies.
        if hour == 0 and hands:
            reach = min(target_g, live + geese_per_unit)   # a little ahead of the flock
            want = min(hands, max(0, math.ceil(reach / geese_per_unit) - 1))
            for _ in range(want):
                market.append(["HIRE"])

        for q, d in quad_plan:
            if day >= d and q not in owned and money > 3500:
                market.append(["BUY_LAND"]); break

        if shed.get("EGG", 0) > 0:
            market.append(["SELL", "EGG", shed["EGG"]])
        # Bootstrap feed only: grown wheat arrives ~day 5, geese starve in 2.
        wheat_total = shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)
        if hour == 1 and wheat_total < max(10, live * 4) and money > 250 and day < 12:
            market.append(["BUY_PRODUCT", "WHEAT", 10])
        if priv["seeds"].get("WHEAT", 0) < n_wheat and money > 300:
            market.append(["BUY_SEED", "WHEAT", n_wheat])

        def _held(sp):
            return shed.get(sp, 0) + sum(i.get(sp, 0) for i in invs)
        need = None
        rich = money >= 3000
        order = ("GOOSE", "COW", "SHEEP") if not (rich and day >= premium_day) \
                else ("COW", "SHEEP", "GOOSE")
        for sp in order:
            want = {"COW": n_cows, "SHEEP": n_sheep, "GOOSE": target_g}[sp]
            have = sum(1 for (x, y) in cells
                       if isinstance(tiles[y][x], dict)
                       and tiles[y][x].get("animal") == sp) + _held(sp)
            if have < want:
                need = sp; break
        held = _held(need) if need else 1
        feed_ok = wheat_total >= (live + 1) * 4
        COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
        if (hour == 2 and day <= stop_buy_day and need and held == 0
                and money >= COST[need] + 900 and feed_ok):
            market.append(["BUY_ANIMAL", need, 1])

        # Premium animals first (closest tiles), then geese, then wheat.
        mix = ["COW"] * n_cows + ["SHEEP"] * n_sheep + ["GOOSE"] * target_g
        n_animals = len(mix)
        g_cells = cells[:n_animals]
        w_cells = cells[n_animals:n_animals + n_wheat]
        # Each unit gets a contiguous slice of both, so units never share a tile.
        assign = [[] for _ in range(n_units)]
        for i, c in enumerate(g_cells): assign[i % n_units].append((mix[i], c))
        for i, c in enumerate(w_cells): assign[i % n_units].append(("W", c))

        def unit(u, pos):
            inv = invs[u] if u < len(invs) else {}
            fx, fy = pos
            mine = assign[u] if u < len(assign) else []
            wheat = inv.get("WHEAT", 0)
            unfed = [c for k, c in mine if k in ANIMAL_SPEC
                     and isinstance(tiles[c[1]][c[0]], dict)
                     and tiles[c[1]][c[0]].get("animal")
                     and not tiles[c[1]][c[0]]["fed_today"]]
            # RESTOCK: monotone, only with zero wheat in hand.
            if unfed and wheat == 0 and shed.get("WHEAT", 0) > 0:
                return step(fx, fy, *SHED) or ["PICKUP", "WHEAT", 12]
            for k, (x, y) in mine:
                if k in ANIMAL_SPEC:
                    struct, _ = ANIMAL_SPEC[k]
                    t = tiles[y][x]
                    if isinstance(t, dict) and t.get("kind") == struct and not t.get("animal"):
                        if inv.get(k, 0) > 0:
                            return step(fx, fy, x, y) or ["PLACE", k]
                        if shed.get(k, 0) > 0:
                            return step(fx, fy, *SHED) or ["PICKUP", k, 1]
            best, bd, bk = None, 99, None
            for k, (x, y) in mine:
                t = tiles[y][x]; d = abs(x - fx) + abs(y - fy)
                if k in ANIMAL_SPEC:
                    if t is None: job = ANIMAL_SPEC[k][1]
                    elif not isinstance(t, dict): continue
                    elif t.get("kind") == "WEED": job = "DIG"
                    elif t.get("animal"):
                        if t["yield_units"] >= 4: job = "HARVEST"
                        elif not t["fed_today"] and wheat > 0: job = "FEED"
                        elif not t["cared_today"]: job = "CARE"
                        elif t["yield_units"] > 0: job = "HARVEST"
                        else: continue
                    else: continue
                else:
                    if t is None: job = "PLANT"
                    elif not isinstance(t, dict): continue
                    elif t.get("kind") == "WEED": job = "DIG"
                    elif t.get("kind") == "PLANT":
                        age = day - t["planted_day"]
                        if age >= 4 and t["yield_units"] > 0: job = "HARVW"
                        elif not t["watered_today"]: job = "WATER"
                        else: continue
                    else: continue
                if d < bd: best, bd, bk = (x, y), d, job
            if best:
                mv = step(fx, fy, *best)
                if mv: return mv
                return {"BUILD_COOP": ["BUILD_COOP"], "BUILD_PASTURE": ["BUILD_PASTURE"],
                        "DIG": ["DIG"], "HARVEST": ["HARVEST"],
                        "FEED": ["FEED"], "CARE": ["CARE"], "PLANT": ["PLANT", "WHEAT"],
                        "WATER": ["WATER"], "HARVW": ["HARVEST"]}[bk]
            return step(fx, fy, *SHED) or ["DROP"]

        return {"farmer": unit(0, me["farmer"]),
                "hands": [unit(i + 1, h) for i, h in enumerate(me["hands"])],
                "market": market[:10]}
    return agent
