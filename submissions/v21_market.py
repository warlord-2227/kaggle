"""Kaggriculture submission v21: "market" -- demand-driven farm (grove v3).

Our own implementation (kaggriculture/agents/market.py). No third-party code
or recorded action sequence is used.

Design from the engine's market rules and the rank-1 team's replays: each
unlocked town shop buys 6 units a day of every product it lists (12 if it
lists one), the town centre buys 1 of everything, nothing buys melon or
fertilizer. Selling up to that drain holds the price; selling past it slides
down the glut curve. So the farm is re-sized every day to the shops that
actually exist: cows, sheep, geese, strawberry, wheat, carrot and tomato each
to their demand. Opening like the top teams (cows + 3 sheep cared daily, 10
wheat, melon as the day-10 cash lump), herd bought whenever cash lands,
harvested produce carried to the shed instead of waiting for the nightly dump,
carrot/wheat sprint from day 22. Labour: grove's coin-priced auction.

Knobs = best genome of experiments/evolve_market.py (50 knobs; sparring pass,
meta line, v20, itself; one no-strawberry-shop seed per generation).

Fresh seeds: 10-0 vs v20 (88,971 vs 78,460); 126,092 vs pass; 100-103k on
seeds with no strawberry buyer (v20: 80-87k); 1-3 vs the meta line.
"""
import math

SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}
ANIMAL = {"COW": ("PASTURE", "BUILD_PASTURE", "MILK"),
          "SHEEP": ("PASTURE", "BUILD_PASTURE", "WOOL"),
          "GOOSE": ("COOP", "BUILD_COOP", "EGG")}
COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
RIPE = {"MELON": 10, "STRAWBERRY": 10, "WHEAT": 4, "CARROT": 3, "TOMATO": 8}
ONGOING = {"STRAWBERRY", "TOMATO"}
SEED = {"MELON": 80, "STRAWBERRY": 100, "WHEAT": 10, "CARROT": 20, "TOMATO": 50}
SHOPS = {"BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
         "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
         "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
         "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]}


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


def _ramp(points, day):
    """Piecewise-constant schedule: points = [(day, value), ...] ascending."""
    v = 0
    for d, val in points:
        if day >= d: v = val
    return v


DEFAULT = dict(
    # opening (rank-1 pattern): 2 cows + 3 sheep cared daily -> 18 wool on day 6 buys the herd
    cows_d0=2, sheep_d0=3, herd_ramp_day=5, herd_until=16,
    milk_prior=4.0, milk_prior_early=10.0, prior_until=12, wool_prior=3.0, deliver_min=1000, deliver_k=0.3, deliver_min_early=150, deliver_early_until=10, cows_min=3, cows_max=12, sheep_min=3, sheep_max=10, geese_max=10,
    melon_tiles=8, melon_until=2,
    straw_prior=10.0, straw_mult=1.2, straw_min=16, straw_max=40, straw_until=18, straw_rate=12, straw_cash=250,
    wheat_mult=1.0, wheat_feed_mult=0.5, wheat_min=10, wheat_max=40,
    carrot_from=8, carrot_max=16, tomato_from=8, tomato_max=8,
    sprint_from=21, sprint_until=26, straw_priority_day=6, herd_reserve=450,
    land_days=(6, 9), land_reserve=0,
    hands_day0=4, hands_min=6, hands_max=11, work_per_unit=6.0,
    feed_days=1, cash_floor=40, animals_per_day=8, day0_wheat=9,
    sell_chunk=8, melon_chunk=8, fert_reserve=1, liquidate_from=28, harvest_min_animal=1,
    dist_pow=1.0, adaptive=True, match="unit", zone_bias=0.0, commit=False, stay=True, bundle=True,
    collect_value=0, harvest_full=False,
)


def make(debug=False, **over):
    S = dict(DEFAULT); S.update(over)
    state = {"day": -1, "commit": {}}      # unit index -> (cell, op[0]) kept across hours

    def agent(obs, config=None):
        if debug:
            return decide(obs)
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
        endgame = day >= S["liquidate_from"]
        market = []
        cells = tiles_by_distance(owned)

        def P(item, default=50):
            return max(prices.get(item, default), 1)

        # ---- census ---------------------------------------------------------
        live, n_plant, ripe_now, pens_free = {}, 0, 0, 0
        for (x, y) in cells:
            t = tiles[y][x]
            if not isinstance(t, dict):
                continue
            if t.get("animal"):
                live[t["animal"]] = live.get(t["animal"], 0) + 1
            elif t.get("kind") in ("PASTURE", "COOP"):
                pens_free += 1
            if t.get("kind") == "PLANT":
                n_plant += 1
                if t["yield_units"] > 0 and day - t["planted_day"] >= RIPE.get(t["crop"], 4):
                    ripe_now += 1
        n_animals = sum(live.values())
        held = lambda it: shed.get(it, 0) + sum(i.get(it, 0) for i in invs)
        n_herd = n_animals + sum(held(a) for a in ANIMAL)

        # ---- demand from the town ---------------------------------------------
        # Each unlocked shop buys 6 units a day of every product it lists (12 if it lists one);
        # the town centre buys 1 of everything; nothing buys melon or fertilizer. Selling up to
        # that drain keeps a price at or above base, selling past it slides down the glut curve,
        # so every product line is sized to the shops that actually exist today.
        shops = (obs.get("town") or {}).get("unlocked_shops", [])
        drain = {p: 1.0 for p in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")}
        for sh in shops:
            prods = SHOPS.get(sh, []); mult = 2 if len(prods) == 1 else 1
            for p in prods: drain[p] = drain.get(p, 0) + 6 * mult
        def clamp(v, lo, hi): return max(lo, min(hi, int(v)))
        # early on, milk buyers (3 of the 8 shop types) are likely and a cow pays back fastest:
        # build the herd on a high prior, then let the real shops decide from mid-game
        milk_prior = S["milk_prior_early"] if day <= S["prior_until"] else S["milk_prior"]
        cows_t = clamp(round((drain["MILK"] + milk_prior) / 1.5), S["cows_min"], S["cows_max"])
        sheep_t = clamp(round((drain["WOOL"] + S["wool_prior"]) / 1.33), S["sheep_min"], S["sheep_max"])
        geese_t = clamp(round(drain["EGG"] / 2.0), 0, S["geese_max"]) if drain["EGG"] >= 7 else 0
        if day < S["herd_ramp_day"]:                       # opening: the day-0 basket, then wait for the wool cash
            cows_t, sheep_t, geese_t = min(cows_t, S["cows_d0"]), min(sheep_t, S["sheep_d0"]), 0
        if day > S["herd_until"]:                          # no new animals late: they would not pay back
            cows_t, sheep_t, geese_t = live.get("COW", 0), live.get("SHEEP", 0), live.get("GOOSE", 0)
        straw_t = clamp(round((drain["STRAWBERRY"] + S["straw_prior"]) * S["straw_mult"]), S["straw_min"], S["straw_max"]) if day <= S["straw_until"] else 0
        wheat_t = clamp(round(drain["WHEAT"] * S["wheat_mult"] + n_herd * S["wheat_feed_mult"]), S["wheat_min"], S["wheat_max"])
        carrot_t = clamp(round((drain["CARROT"] - 1) / 1.33), 0, S["carrot_max"]) if day >= S["carrot_from"] else 0
        tomato_t = clamp(round(drain["TOMATO"] - 1), 0, S["tomato_max"]) if S["tomato_from"] <= day <= 20 else 0
        melon_t = S["melon_tiles"] if day <= S["melon_until"] else 0
        sprint = S["sprint_from"] <= day <= S["sprint_until"]
        sprint_crop = "CARROT" if drain["CARROT"] >= 7 else "WHEAT"
        want_cows, want_sheep, want_geese = cows_t, sheep_t, geese_t

        # ---- field plan -----------------------------------------------------------
        plan = {}
        pen_roles = ["COW"] * want_cows + ["SHEEP"] * want_sheep + ["GOOSE"] * want_geese
        built = [c for c in cells if isinstance(tiles[c[1]][c[0]], dict)
                 and tiles[c[1]][c[0]].get("kind") in ("PASTURE", "COOP")]
        for c in built:                                    # existing pens keep their kind
            t = tiles[c[1]][c[0]]
            if t.get("animal"): plan[c] = t["animal"]
            else: plan[c] = "GOOSE" if t.get("kind") == "COOP" else ("COW" if want_cows > sum(1 for v in plan.values() if v == "COW") else "SHEEP")
        have = {}
        for v in plan.values(): have[v] = have.get(v, 0) + 1
        for sp in ("COW", "SHEEP", "GOOSE"):
            k = max(0, {"COW": want_cows, "SHEEP": want_sheep, "GOOSE": want_geese}[sp] - have.get(sp, 0))
            for c in cells:
                if k == 0: break
                if c not in plan and tiles[c[1]][c[0]] is None: plan[c] = sp; k -= 1
        for (x, y) in cells:                               # growing crops keep their role
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("kind") == "PLANT" and (x, y) not in plan:
                plan[(x, y)] = t["crop"]
        have = {}
        for v in plan.values(): have[v] = have.get(v, 0) + 1
        rest = [c for c in cells if c not in plan]
        if day < S["straw_priority_day"]:      # opening: cheap wheat (feed + cash) before the strawberry ramp
            order = [("WHEAT", min(wheat_t, S["wheat_min"])), ("MELON", melon_t), ("WHEAT", wheat_t), ("STRAWBERRY", straw_t), ("CARROT", carrot_t), ("TOMATO", tomato_t)]
        else:
            order = [("MELON", melon_t), ("STRAWBERRY", straw_t), ("WHEAT", wheat_t), ("CARROT", carrot_t), ("TOMATO", tomato_t)]
        if sprint: order = [(sprint_crop, 99)] + order
        for crop, target in order:
            k = max(0, target - have.get(crop, 0))
            for c in rest[:k]: plan[c] = crop
            rest = rest[k:]
        planned = [c for c in cells if plan.get(c) is not None]
        n_st = have.get("STRAWBERRY", 0)

        # ---- hiring: to the work on the board (<= 10 orders a turn, so spill into hours 1-2) ----
        if hour <= 2:
            if day == 0:
                n_hire = S["hands_day0"]
            else:
                work = n_plant + 2.5 * n_animals + ripe_now + 0.5 * len(rest) \
                       + sum(1 for c in planned if tiles[c[1]][c[0]] is None)
                n_hire = int(math.ceil(work / S["work_per_unit"])) - 1
                n_hire = max(S["hands_min"], min(S["hands_max"], n_hire))
                if endgame: n_hire = max(n_hire, 6)
                FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
                while n_hire > S["hands_min"] and sum(FIB[:n_hire]) > money * 0.3:
                    n_hire -= 1
            n_hire = max(0, n_hire - len(me["hands"]))
            market += [["HIRE"]] * min(10, n_hire)

        # ---- selling: continuous small lots, premium first ------------------------
        reserve_w = 0 if endgame else n_herd * S["feed_days"] + 2
        fert_demand = 0
        for (x, y) in planned:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                age = day - t["planted_day"]
                if (t["crop"] == "STRAWBERRY" and 7 <= age <= 15) or (t["crop"] == "MELON" and 4 <= age <= 10):
                    fert_demand += 1
        reserve_f = 0 if endgame else min(30, S["fert_reserve"] + fert_demand // 2)
        for item in ("STRAWBERRY", "MILK", "WOOL", "MELON", "EGG", "TOMATO", "CARROT", "FERTILIZER", "WHEAT"):
            if len(market) >= 10: break
            q = shed.get(item, 0)
            if item == "WHEAT": q -= reserve_w
            if item == "FERTILIZER": q -= reserve_f
            if q <= 0 or prices.get(item, 0) <= 1:
                continue
            chunk = 40 if endgame else (S["melon_chunk"] if item == "MELON" else S["sell_chunk"])
            market.append(["SELL", item, min(q, chunk)])

        # ---- buying ---------------------------------------------------------------
        if not endgame:
            wheat_have = held("WHEAT")
            if day == 0 and hour == 1:
                # orders fill in list order until cash runs out: herd, its feed, then seeds
                market.append(["BUY_ANIMAL", "COW", S["cows_d0"]])
                market.append(["BUY_PRODUCT", "WHEAT", S["day0_wheat"]])
                market.append(["BUY_ANIMAL", "SHEEP", S["sheep_d0"]])
                market.append(["BUY_SEED", "WHEAT", S["wheat_min"]])
                market.append(["BUY_SEED", "MELON", min(8, S["melon_tiles"])])
            elif hour in (1, 13) or (day <= 4 and hour in (5, 9, 17, 21)):
                need = n_herd * S["feed_days"] + 2
                if wheat_have < need and money > S["cash_floor"] and hour != 12:
                    market.append(["BUY_PRODUCT", "WHEAT", min(need - wheat_have, int(money // P("WHEAT", 30)))])
                nq = len(owned)
                if hour == 1 and nq - 1 < len(S["land_days"]) and day >= S["land_days"][nq - 1] \
                        and money > [1000, 2000, 4000][nq - 1] + S["land_reserve"]:
                    market.append(["BUY_LAND"])
            elif hour in (2, 5, 8, 11, 14, 17, 20):
                # herd toward the demand-sized targets, best value-per-coin first, whenever cash allows
                # (wool/milk cash lands mid-morning; cows are the best return in the game, seeds wait)
                space = sum(1 for c in cells if tiles[c[1]][c[0]] is None) + pens_free - sum(held(a) for a in ANIMAL)
                bought = 0
                rate = {"COW": 1.5 * P("MILK", 160) / COST["COW"], "SHEEP": 1.33 * P("WOOL", 200) / COST["SHEEP"],
                        "GOOSE": 2.0 * P("EGG", 50) / COST["GOOSE"]}
                for sp in sorted(("COW", "SHEEP", "GOOSE"), key=lambda s: -rate[s]):
                    want = {"COW": want_cows, "SHEEP": want_sheep, "GOOSE": want_geese}[sp]
                    short = want - live.get(sp, 0) - held(sp)
                    while (short > 0 and space > 0 and bought < S["animals_per_day"]
                           and money >= COST[sp] + (n_herd + bought + 1) * S["feed_days"] * P("WHEAT", 30) + S["cash_floor"]):
                        market.append(["BUY_ANIMAL", sp, 1]); money -= COST[sp]; space -= 1; short -= 1; bought += 1
            elif hour in (3, 12):
                empty = {}
                for c in planned:
                    if tiles[c[1]][c[0]] is None and plan[c] not in ANIMAL:
                        empty[plan[c]] = empty.get(plan[c], 0) + 1
                herd_short = (want_cows > live.get("COW", 0) + held("COW")) or (want_sheep > live.get("SHEEP", 0) + held("SHEEP")) \
                             or (want_geese > live.get("GOOSE", 0) + held("GOOSE"))
                for crop in ("WHEAT", "MELON", "CARROT", "STRAWBERRY", "TOMATO"):
                    short = empty.get(crop, 0) - seeds.get(crop, 0)
                    if short <= 0: continue
                    q = min(short, S["straw_rate"] if crop == "STRAWBERRY" else 10)
                    floor = S["straw_cash"] if crop == "STRAWBERRY" else S["cash_floor"]
                    if herd_short and crop in ("STRAWBERRY", "TOMATO", "CARROT"):
                        floor += S["herd_reserve"]            # animals first: a cow returns more than seeds
                    afford = int((money - floor) // SEED[crop])
                    q = min(q, afford)
                    if q > 0:
                        market.append(["BUY_SEED", crop, q]); money -= q * SEED[crop]
            elif hour == 4:
                due = sum(1 for (x, y) in planned if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PLANT"
                          and tiles[y][x]["crop"] in ("STRAWBERRY", "MELON") and tiles[y][x].get("fertilized_until_day", -1) < day
                          and ((tiles[y][x]["crop"] == "STRAWBERRY" and 9 <= day - tiles[y][x]["planted_day"] <= 15)
                               or (tiles[y][x]["crop"] == "MELON" and 6 <= day - tiles[y][x]["planted_day"] <= 10)))
                short = due - held("FERTILIZER")
                if short > 0 and P("FERTILIZER", 100) < 0.8 * P("STRAWBERRY", 120) and money > S["cash_floor"] + 100:
                    q = min(short, 10, int((money - S["cash_floor"]) // P("FERTILIZER", 100)))
                    if q > 0: market.append(["BUY_PRODUCT", "FERTILIZER", q])

        # ---- labour auction ---------------------------------------------------
        units = [tuple(me["farmer"])] + [tuple(h) for h in me["hands"]]
        n = len(units)
        p_st, p_mel, p_wh = P("STRAWBERRY", 120), P("MELON", 250), P("WHEAT", 25)
        p_milk, p_wool, p_egg = P("MILK", 150), P("WOOL", 200), P("EGG", 50)
        p_car, p_tom = P("CARROT", 35), P("TOMATO", 60)
        ANIMAL_PRICE = {"COW": p_milk, "SHEEP": p_wool, "GOOSE": p_egg}
        jobs = []   # (value, (x, y), op, need)  need in {None, "WHEAT", "FERT", animal}
        for (x, y) in planned:
            w = plan[(x, y)]; t = tiles[y][x]
            if w in ANIMAL:
                struct, build, prod = ANIMAL[w]
                if t is None:
                    if held(w) > 0: jobs.append((380, (x, y), [build], w))
                elif not isinstance(t, dict):
                    continue
                elif t.get("kind") == "WEED":
                    jobs.append((80, (x, y), ["DIG"], None))
                elif t.get("animal"):
                    pp = ANIMAL_PRICE.get(t["animal"], p_milk)
                    if t["yield_units"] >= S["harvest_min_animal"] or (endgame and t["yield_units"] > 0):
                        jobs.append((t["yield_units"] * pp, (x, y), ["HARVEST"], None))
                    if not t["fed_today"]:
                        # an unfed animal produces nothing that day (~1.5 milk or 0.5 wool + its care bonus);
                        # two unfed days kill it. Price it above any single crop action.
                        jobs.append((900 if t.get("consecutive_unfed", 0) else max(600, 3.0 * pp), (x, y), ["FEED"], "WHEAT"))
                    if not t["cared_today"]:
                        jobs.append((0.8 * pp, (x, y), ["CARE"], None))
                    if t.get("fertilizer_available"):
                        jobs.append((max(P("FERTILIZER", 90), p_st if n_st else 0, S["collect_value"]), (x, y), ["COLLECT_FERTILIZER"], None))
                elif not t.get("animal") and held(w) > 0:
                    jobs.append((380, (x, y), ["PLACE", w], w))
                continue
            # crops
            if t is None:
                late = (w == "MELON" and day > S["melon_until"]) or (w == "STRAWBERRY" and day > S["straw_until"]) or (w == "TOMATO" and day > 20)
                if seeds.get(w, 0) > 0 and not late and not endgame:
                    v = {"STRAWBERRY": 220, "MELON": 180, "WHEAT": 35, "CARROT": 60, "TOMATO": 80}.get(w, 30)
                    jobs.append((v, (x, y), ["PLANT", w], None))
            elif not isinstance(t, dict):
                continue
            elif t.get("kind") == "WEED":
                if not endgame: jobs.append((40, (x, y), ["DIG"], None))
            elif t.get("kind") == "PLANT":
                c = t["crop"]; age = day - t["planted_day"]
                ripe = age >= RIPE.get(c, 4) and t["yield_units"] > 0
                if ripe:
                    if c == "STRAWBERRY":
                        if t["yield_units"] >= 2 or day >= 26:
                            jobs.append((t["yield_units"] * p_st, (x, y), ["HARVEST"], None))
                    elif c == "TOMATO":
                        if t["yield_units"] >= 2 or day >= 26:
                            jobs.append((t["yield_units"] * p_tom, (x, y), ["HARVEST"], None))
                    elif c == "CARROT":
                        if t["yield_units"] >= 4 or age >= 4 or endgame:
                            jobs.append((t["yield_units"] * p_car, (x, y), ["HARVEST"], None))
                    elif c == "MELON":
                        if t["yield_units"] >= 6 or age >= (13 if S["harvest_full"] else 12) or endgame:
                            jobs.append((t["yield_units"] * p_mel, (x, y), ["HARVEST"], None))
                    elif c == "WHEAT" and S["harvest_full"] and age <= 4 and t["yield_units"] < 6 and not endgame:
                        pass                                    # one more watered day = one more unit
                    else:
                        jobs.append((t["yield_units"] * P(c, 30), (x, y), ["HARVEST"], None))
                fert_on = t.get("fertilized_until_day", -1) >= day
                unw = t.get("consecutive_unwatered", 0)
                if not t["watered_today"] and not (endgame and day >= 29):
                    v = 25.0                                   # routine: keeps the streak at 0
                    if unw >= 1: v = 600.0                     # skip today and the plant is a weed tomorrow
                    if c == "STRAWBERRY" and age >= 9 and age % 2 == 1:
                        v = max(v, (1.0 if fert_on else 0.15) * p_st)   # production tonight; bonus needs water
                    elif c == "MELON" and 6 <= age <= 12 and t["yield_units"] < 6:
                        v = max(v, (1.6 if fert_on else 0.8) * p_mel)   # +1 (+2) yield per watered day
                    elif c == "WHEAT" and 2 <= age <= 4 and t["yield_units"] < 6:
                        v = max(v, (2.0 if fert_on else 1.0) * p_wh)
                    elif c == "CARROT" and 2 <= age <= 3 and t["yield_units"] < 4:
                        v = max(v, (2.0 if fert_on else 1.0) * p_car)
                    elif c == "TOMATO" and age >= 7:
                        v = max(v, (1.0 if fert_on else 0.2) * p_tom)
                    jobs.append((v, (x, y), ["WATER"], None))
                if not fert_on and not endgame:
                    if c == "STRAWBERRY" and 9 <= age <= 15 and age % 2 == 1:
                        jobs.append((2.0 * p_st, (x, y), ["FERTILIZE"], "FERT"))      # covers two production nights
                    elif c == "MELON" and 6 <= age <= 10 and t["yield_units"] < 5:
                        jobs.append((1.5 * p_mel, (x, y), ["FERTILIZE"], "FERT"))

        # deliver: a unit holding valuable produce brings it to the shed (sales happen from the shed only)
        SELLABLE = ("MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "CARROT", "TOMATO", "FERTILIZER")
        dmin = S["deliver_min_early"] if day < S["deliver_early_until"] else S["deliver_min"]
        for u in range(len(units)):
            inv = invs[u] if u < len(invs) else {}
            val = sum(inv.get(it, 0) * P(it, 50) for it in SELLABLE)
            if val >= dmin:
                jobs.append((S["deliver_k"] * val, SHED, ["DROP"], "DELIVER:%d" % u))

        # supply runs: wheat for feeding, fertilizer for the bonus window
        hungry = sum(1 for v, _, op, nd in jobs if op[0] == "FEED")
        fert_jobs = sum(1 for v, _, op, nd in jobs if op[0] == "FERTILIZE")
        carriers_w = sum(1 for i in invs if i.get("WHEAT", 0) > 0)
        carriers_f = sum(1 for i in invs if i.get("FERTILIZER", 0) > 0)
        if hungry and shed.get("WHEAT", 0) > 0 and carriers_w < max(1, hungry // 4):
            jobs.append((240, SHED, ["PICKUP", "WHEAT", min(shed["WHEAT"], max(2, hungry))], "SHEDW"))
        if fert_jobs >= 1 and shed.get("FERTILIZER", 0) >= 1 and carriers_f < max(1, fert_jobs // 5) and not endgame:
            jobs.append((1.5 * p_st, SHED, ["PICKUP", "FERTILIZER", min(shed["FERTILIZER"], 6)], "SHEDF"))

        # animals waiting in the shed: one pickup job per species (value competes in the auction)
        for w in ANIMAL:
            if shed.get(w, 0) > 0 and any(plan.get(c) == w and (tiles[c[1]][c[0]] is None or (
                    isinstance(tiles[c[1]][c[0]], dict) and tiles[c[1]][c[0]].get("kind") == ANIMAL[w][0]
                    and not tiles[c[1]][c[0]].get("animal"))) for c in planned):
                jobs.append((400, SHED, ["PICKUP", w, 1], "SHEDA"))

        # optional soft territories: planned cells split into serpentine bands, one per unit;
        # a job outside a unit's band is discounted by zone_bias (0 = no territories)
        band_of = {}
        if S["zone_bias"] > 0 and n > 1 and planned:
            rows_ = {}
            for c in planned: rows_.setdefault(c[1], []).append(c)
            serp = []
            for yy in sorted(rows_): serp.extend(sorted(rows_[yy], key=lambda c: c[0], reverse=(yy % 2 == 1)))
            w = lambda c: 3.0 if plan.get(c) in ANIMAL else 1.0
            total = sum(w(c) for c in serp); k, acc = 0, 0.0
            for c in serp:
                if k < n - 1 and acc >= total * (k + 1) / n: k += 1
                band_of[c] = k; acc += w(c)
        # greedy global matching by value / (1 + distance)
        pairs = []
        for u, (ux, uy) in enumerate(units):
            inv = invs[u] if u < len(invs) else {}
            for j, (v, (x, y), op, need) in enumerate(jobs):
                if need == "WHEAT" and inv.get("WHEAT", 0) <= 0: continue
                if need == "FERT" and inv.get("FERTILIZER", 0) <= 0: continue
                if need in ANIMAL and inv.get(need, 0) <= 0: continue
                if need == "SHEDW" and inv.get("WHEAT", 0) > 0: continue
                if need == "SHEDF" and inv.get("FERTILIZER", 0) > 0: continue
                if need == "SHEDA" and any(inv.get(a, 0) > 0 for a in ANIMAL): continue
                if isinstance(need, str) and need.startswith("DELIVER:") and int(need.split(":")[1]) != u: continue
                d = abs(x - ux) + abs(y - uy)
                sc = v / (1.0 + d) ** S["dist_pow"]
                if band_of and (x, y) in band_of and band_of[(x, y)] != u: sc *= (1.0 - S["zone_bias"])
                pairs.append((sc, u, j))
        if S["match"] == "job":
            # job-centric: the most valuable job takes the nearest eligible free unit, and so on;
            # ties in value broken by distance. Cuts travel versus ranking unit-job pairs by value/(1+d).
            eligible = {}
            for score, u, j in pairs:
                eligible.setdefault(j, []).append((abs(jobs[j][1][0] - units[u][0]) + abs(jobs[j][1][1] - units[u][1]), u))
            order = sorted(eligible, key=lambda j: -jobs[j][0])
            pairs = []
            for rank, j in enumerate(order):
                for d, u in sorted(eligible[j]):
                    pairs.append((-(rank * 1000 + d), u, j))
        if S["match"] == "optimal" and pairs:
            # global assignment: maximise the summed score over units (Hungarian), then fall through
            # to the greedy loop with the optimal pairs first so cell-uniqueness rules still apply.
            try:
                import numpy as np
                from scipy.optimize import linear_sum_assignment
                us = sorted(set(u for _, u, _ in pairs)); js = sorted(set(j for _, _, j in pairs))
                ui = {u: i for i, u in enumerate(us)}; ji = {j: i for i, j in enumerate(js)}
                M = np.zeros((len(us), len(js)))
                for sc, u, j in pairs: M[ui[u], ji[j]] = sc
                rows, cols = linear_sum_assignment(-M)
                opt = {(us[r], js[c]) for r, c in zip(rows, cols) if M[r, c] > 0}
                pairs = [(sc + (1e6 if (u, j) in opt else 0), u, j) for sc, u, j in pairs]
            except Exception:
                pass
        if S["bundle"]:
            # a tile's jobs are done in one visit: score each job by the value of everything pending there
            cell_sum = {}
            for v, c, op, need in jobs:
                if op[0] != "PICKUP": cell_sum[c] = cell_sum.get(c, 0.0) + v
            pairs = [(sc * (cell_sum.get(jobs[j][1], jobs[j][0]) / max(jobs[j][0], 1e-6)) ** 0.5, u, j) for sc, u, j in pairs]
        pairs.sort(reverse=True)
        chosen, taken_units, taken_cells = {}, set(), set()
        if S["stay"]:
            # finish the tile you stand on before walking anywhere (FEED -> CARE -> COLLECT, WATER -> FERTILIZE)
            for u, (ux, uy) in enumerate(units):
                inv = invs[u] if u < len(invs) else {}
                best = None
                for j, (v, (x, y), op, need) in enumerate(jobs):
                    if (x, y) != (ux, uy) or op[0] == "PICKUP": continue
                    if need == "WHEAT" and inv.get("WHEAT", 0) <= 0: continue
                    if need == "FERT" and inv.get("FERTILIZER", 0) <= 0: continue
                    if need in ANIMAL and inv.get(need, 0) <= 0: continue
                    key = ((x, y), op[0])
                    if key in taken_cells: continue
                    if best is None or v > best[0]: best = (v, j, key)
                if best:
                    v, j, key = best
                    chosen[u] = (jobs[j][1], jobs[j][2]); taken_units.add(u); taken_cells.add(key)
        if S["commit"]:
            # honour yesterday's-hour commitments first: a unit already walking to a job keeps it
            # while the job still exists and it can still do it (hands reset nightly).
            if state["day"] != day:
                state["day"] = day; state["commit"] = {}
            still = {}
            for u, (cell, opname) in state["commit"].items():
                if u >= n: continue
                inv = invs[u] if u < len(invs) else {}
                for j, (v, c, op, need) in enumerate(jobs):
                    if c != cell or op[0] != opname: continue
                    if need == "WHEAT" and inv.get("WHEAT", 0) <= 0: break
                    if need == "FERT" and inv.get("FERTILIZER", 0) <= 0: break
                    if need in ANIMAL and inv.get(need, 0) <= 0: break
                    if need == "SHEDW" and inv.get("WHEAT", 0) > 0: break
                    if need == "SHEDF" and inv.get("FERTILIZER", 0) > 0: break
                    if need == "SHEDA" and any(inv.get(a, 0) > 0 for a in ANIMAL): break
                    key = (cell, opname) if opname not in ("PICKUP",) else (cell, opname, u)
                    if key in taken_cells: break
                    chosen[u] = (cell, op); taken_units.add(u); taken_cells.add(key); still[u] = (cell, opname)
                    break
            state["commit"] = still
        for score, u, j in pairs:
            if u in taken_units: continue
            v, cell, op, need = jobs[j]
            key = (cell, op[0]) if op[0] in ("FEED", "CARE", "WATER", "HARVEST", "PLANT", "DIG", "FERTILIZE", "COLLECT_FERTILIZER", "PLACE", "BUILD_PASTURE", "BUILD_COOP") else (cell, op[0], u)
            if key in taken_cells: continue
            if op[0] == "PLACE" or op[0].startswith("BUILD"):
                # one animal per pen: don't send two units to place on the same cell
                pass
            chosen[u] = (cell, op); taken_units.add(u); taken_cells.add(key)
            if S["commit"]: state["commit"][u] = (cell, op[0])
        def op_for(u):
            if u not in chosen:
                return ["PASS"]
            (x, y), op = chosen[u]
            ux, uy = units[u]
            return step(ux, uy, x, y) or op

        return {"farmer": op_for(0),
                "hands": [op_for(i + 1) for i in range(len(me["hands"]))],
                "market": market[:10]}
    return agent


# --- generated entry point -------------------------------------------------
_impl = make(cows_d0=1, sheep_d0=3, herd_ramp_day=5, herd_until=14, milk_prior=4.64, milk_prior_early=5.2, prior_until=10, wool_prior=3.0, cows_min=3, cows_max=10, sheep_min=3, sheep_max=9, geese_max=8, melon_tiles=11, melon_until=4, straw_prior=10.0, straw_mult=1.5, straw_min=18, straw_max=43, straw_until=17, straw_rate=9, straw_cash=318, straw_priority_day=5, wheat_mult=1.14, wheat_feed_mult=0.71, wheat_min=9, wheat_max=34, carrot_from=10, carrot_max=16, tomato_from=8, tomato_max=10, sprint_from=21, sprint_until=26, herd_reserve=256, hands_day0=5, hands_min=6, hands_max=11, work_per_unit=8.12, feed_days=1, cash_floor=71, animals_per_day=8, day0_wheat=8, sell_chunk=7, melon_chunk=6, fert_reserve=1, harvest_min_animal=2, deliver_min=1000, deliver_k=0.46, deliver_min_early=150, deliver_early_until=10, land_reserve=222)


def agent(obs, config=None):
    try:
        return _impl(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
