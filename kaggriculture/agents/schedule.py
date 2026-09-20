"""Build-order agent. The opening is a day-indexed SCHEDULE, not thresholds.

Reconstructed from a 129k opponent read at turn resolution (replays/,
analysis/data/reference_opening_129k.json). Every one of the 17 opponents that
beat v11/v12 surged hands to 9-16; 12 of 17 opened with sheep; the top ones
planted a melon block on day 0 and lifted it in one harvest on day 10.

  day 0   2 cows, 2 sheep, 12 melon, feed -- spend to ~0
  days 2-7   one or two cows a day, paid from fertilizer + wheat sales
  day 5+  strawberry, ramping onto the new land
  day 6   wool sells -> land -> hands 7
  day 10  melon harvest, hands 11, ~60 melons in one day
  day 11  second land, strawberry to 33, geese
  then    reactive, liquidate from day 26

The executor (zones, restock-first, feed/care/harvest/water) is the proven one
from ranch.py, plus FERTILIZE. All purchases fire once a day: the unguarded
per-turn purchase has bitten five times.
"""
import math

SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}
ANIMAL = {"COW": ("PASTURE", "BUILD_PASTURE", "MILK"),
          "SHEEP": ("PASTURE", "BUILD_PASTURE", "WOOL"),
          "GOOSE": ("COOP", "BUILD_COOP", "EGG")}
COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
RIPE = {"MELON": 10, "STRAWBERRY": 10, "WHEAT": 4, "CARROT": 3}
BONUS_START = {"MELON": 6, "STRAWBERRY": 5, "WHEAT": 2}   # fertilize from this age

# --- the schedule (day-indexed targets; last value holds) ------------------
def _at(seq, day):
    return seq[day] if day < len(seq) else seq[-1]

DEFAULT = dict(
    cows=[2, 2, 3, 3, 4, 4, 6, 8],
    sheep=[2, 2, 2, 2, 2, 2, 2, 2, 4, 6],
    geese=[0] * 10 + [2, 3],
    melon_d0=12,
    straw=[0, 0, 0, 0, 0, 4, 12, 16, 20, 20, 20, 33],
    wheat_tiles=[7, 7, 7, 7, 7, 3, 6, 9, 5, 5, 12, 21, 24],
    hands=[5, 3, 4, 5, 4, 4, 7, 7, 8, 8, 11, 10, 9, 9],
    hands_late=10, liquidate_from=26,
    land_days=(6, 11), land_reserve=100,
    fert_from=6, fert_per_day=2,
    feed_days=2, cash_floor=60, max_animals_per_day=2,
    day0_wheat=8, day0_wheat_seed=7,
)


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


def make(**over):
    S = {**DEFAULT, **over}

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
        endgame = day >= S["liquidate_from"]
        cells = tiles_by_distance(owned)

        live = {}
        for (x, y) in cells:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("animal"):
                live[t["animal"]] = live.get(t["animal"], 0) + 1
        n_animals = sum(live.values())
        n_herd = n_animals + sum(shed.get(a, 0) + sum(i.get(a, 0) for i in invs) for a in ("COW", "SHEEP", "GOOSE"))

        def held(sp):
            return shed.get(sp, 0) + sum(i.get(sp, 0) for i in invs)

        # --- hands: the schedule's ramp -------------------------------------
        if hour == 0:
            n = S["hands_late"] if endgame else _at(S["hands"], day)
            for _ in range(n):
                market.append(["HIRE"])

        # --- selling: everything, premium first, every turn -----------------
        reserve = 0 if endgame else n_herd * S["feed_days"] + 4
        for item in ("MILK", "WOOL", "MELON", "STRAWBERRY", "EGG", "FERTILIZER", "WHEAT"):
            have = shed.get(item, 0)
            if item == "WHEAT":
                have -= reserve
            if item == "FERTILIZER" and S["fert_from"] <= day <= 10 and not endgame:
                have -= 2          # keep a little for the melon bonus window; sell the rest (100 each)
            if have <= 0 or prices.get(item, 0) <= 1:
                continue
            market.append(["SELL", item, min(have, 60 if endgame else 30)])
            if len(market) >= 8:
                break

        # --- buying: once a day, in schedule order --------------------------
        if not endgame:
            wheat_have = shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in invs)
            if day == 0 and hour == 1:
                # Feed FIRST (orders stop when cash runs out), then herd, then seeds.
                # Orders resolve in list order and stop at zero cash. v1 put 27
                # wheat first and the melon block last: melon got cut to 4 tiles.
                market.append(["BUY_SEED", "MELON", S["melon_d0"]])
                market.append(["BUY_ANIMAL", "COW", _at(S["cows"], 0)])
                market.append(["BUY_ANIMAL", "SHEEP", _at(S["sheep"], 0)])
                market.append(["BUY_PRODUCT", "WHEAT", S["day0_wheat"]])
                market.append(["BUY_SEED", "WHEAT", S["day0_wheat_seed"]])
            elif hour in (1, 13):
                # Feed shortfall for the herd we have, twice a day, plus land on its day.
                need = n_herd * S["feed_days"] + 2
                if wheat_have < need and money > S["cash_floor"]:
                    market.append(["BUY_PRODUCT", "WHEAT", min(need - wheat_have,
                                                               int(money // max(prices.get("WHEAT", 30), 1)))])
                nq = len(owned)
                land_cost = [1000, 2000, 4000]
                if hour == 1 and nq - 1 < len(S["land_days"]) and day >= S["land_days"][nq - 1] and nq < 4 \
                        and money > land_cost[nq - 1] + S["land_reserve"]:
                    market.append(["BUY_LAND"])
            elif hour == 2:
                # Herd toward today's target, at most max_animals_per_day, and only if
                # tomorrow's feed for the enlarged herd is still affordable afterwards.
                # v1 bought 4 cows + 6 sheep + 3 geese on day 11 and starved them all.
                wp = max(prices.get("WHEAT", 30), 1)
                bought = 0
                n_plant = sum(1 for (x, y) in cells if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PLANT")
                space = len(cells) - n_plant - n_herd
                for sp in ("COW", "SHEEP", "GOOSE"):
                    tgt = _at(S[{"COW": "cows", "SHEEP": "sheep", "GOOSE": "geese"}[sp]], day)
                    short = tgt - live.get(sp, 0) - held(sp)
                    while short > 0 and bought < S["max_animals_per_day"] and space - bought > 0:
                        feed_reserve = (n_animals + bought + 1) * S["feed_days"] * wp
                        if money < COST[sp] + feed_reserve + S["cash_floor"]:
                            break
                        market.append(["BUY_ANIMAL", sp, 1])
                        money -= COST[sp]; short -= 1; bought += 1
            elif hour == 3:
                # Seeds for today's planting targets; fertilizer for the bonus window.
                planted = {}
                for (x, y) in cells:
                    t = tiles[y][x]
                    if isinstance(t, dict) and t.get("kind") == "PLANT":
                        planted[t["crop"]] = planted.get(t["crop"], 0) + 1
                st_short = _at(S["straw"], day) - planted.get("STRAWBERRY", 0) - seeds.get("STRAWBERRY", 0)
                q = min(st_short, 4)
                if st_short > 0 and money > 100 * q + 120:
                    market.append(["BUY_SEED", "STRAWBERRY", q])
                if seeds.get("WHEAT", 0) < 4 and money > 100:
                    market.append(["BUY_SEED", "WHEAT", 6])

        # --- field plan -------------------------------------------------------
        # Pens nearest, then the melon block, then strawberry, then wheat.
        plan = {}
        want = (["COW"] * _at(S["cows"], day) + ["SHEEP"] * _at(S["sheep"], day)
                + ["GOOSE"] * _at(S["geese"], day))
        built = [(x, y) for (x, y) in cells
                 if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") in ("PASTURE", "COOP")]
        pen_cells = built[:]
        for c in cells:
            if len(pen_cells) >= len(want): break
            if c not in pen_cells: pen_cells.append(c)
        for i, c in enumerate(pen_cells):
            plan[c] = want[min(i, len(want) - 1)] if want else None
        rest = [c for c in cells if c not in plan]
        n_mel = S["melon_d0"] if day <= 10 else 0
        for c in rest[:n_mel]: plan[c] = "MELON"
        n_st = _at(S["straw"], day)
        for c in rest[n_mel:n_mel + n_st]: plan[c] = "STRAWBERRY"
        n_wh = _at(S["wheat_tiles"], day)
        # The reference cuts wheat as strawberry replaces it. Without strawberry
        # on the ground, cutting wheat just starves the herd.
        n_wh = max(n_wh, 6 - n_st) if n_st == 0 else n_wh
        for c in rest[n_mel + n_st:n_mel + n_st + n_wh]: plan[c] = "WHEAT"
        # A growing crop keeps its role until harvested (the v12 fix).
        for (x, y) in cells:
            t = tiles[y][x]
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                plan[(x, y)] = t["crop"]

        # --- zones: row bands balanced by work, idle fallback ------------------
        units = [me["farmer"]] + list(me["hands"])
        n = len(units)
        planned = [c for c in cells if plan.get(c) is not None]
        def weight(c):
            return 3.0 if plan.get(c) in ANIMAL else 1.2
        rows = {}
        for c in planned:
            rows.setdefault(c[1], []).append(c)
        serp = []
        for y in sorted(rows):
            serp.extend(sorted(rows[y], key=lambda c: c[0], reverse=(y % 2 == 1)))
        total = sum(weight(c) for c in serp)
        assign = [[] for _ in units]
        k, acc = 0, 0.0
        for c in serp:
            if k < n - 1 and acc >= total * (k + 1) / n:
                k += 1
            assign[k].append(c)
            acc += weight(c)

        def job_for(t, want_, fx, fy, x, y, carrying, fert):
            if want_ in ANIMAL:
                struct, build, _ = ANIMAL[want_]
                if t is None: return [build]
                if not isinstance(t, dict): return None
                if t.get("kind") == "WEED": return ["DIG"] if not endgame else None
                if t.get("animal"):
                    if t["yield_units"] >= 2: return ["HARVEST"]
                    if not t["fed_today"] and carrying > 0: return ["FEED"]
                    if not t["cared_today"]: return ["CARE"]
                    if t.get("fertilizer_available"): return ["COLLECT_FERTILIZER"]
                return None
            if want_ is None: return None
            if t is None:
                late = want_ in ("MELON", "STRAWBERRY") and day > 19
                return ["PLANT", want_] if seeds.get(want_, 0) > 0 and not late else None
            if not isinstance(t, dict): return None
            if t.get("kind") == "WEED": return ["DIG"] if not endgame else None
            if t.get("kind") == "PLANT":
                c = t["crop"]; age = day - t["planted_day"]
                if age >= RIPE.get(c, 4) and t["yield_units"] > 0: return ["HARVEST"]
                if endgame and t["yield_units"] > 0: return ["HARVEST"]
                if not t["watered_today"]: return ["WATER"]
                if (fert > 0 and c in BONUS_START and age >= BONUS_START[c]
                        and t.get("fertilized_until_day", -1) < day): return ["FERTILIZE"]
            return None

        def unit_op(u, pos):
            fx, fy = pos
            inv = invs[u] if u < len(invs) else {}
            mine = assign[u] if u < len(assign) else []
            carrying = inv.get("WHEAT", 0); fert = inv.get("FERTILIZER", 0)
            hungry = [c for c in mine if isinstance(tiles[c[1]][c[0]], dict)
                      and tiles[c[1]][c[0]].get("animal") and not tiles[c[1]][c[0]]["fed_today"]]
            if hungry and carrying == 0 and shed.get("WHEAT", 0) > 0:
                return step(fx, fy, *SHED) or ["PICKUP", "WHEAT", min(len(hungry) + 1, shed["WHEAT"])]
            if carrying > 0:
                best, bd = None, 99
                for (x, y) in planned:
                    t = tiles[y][x]
                    if isinstance(t, dict) and t.get("animal") and not t["fed_today"]:
                        d = abs(x - fx) + abs(y - fy)
                        if d < bd: best, bd = (x, y), d
                if best:
                    return step(fx, fy, *best) or ["FEED"]
            # fetch fertilizer when our crops are in window and we carry none
            if fert == 0 and shed.get("FERTILIZER", 0) > 0 and not hungry:
                needs = any(isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PLANT"
                            and tiles[y][x]["crop"] in BONUS_START
                            and day - tiles[y][x]["planted_day"] >= BONUS_START[tiles[y][x]["crop"]]
                            and tiles[y][x].get("fertilized_until_day", -1) < day for (x, y) in mine)
                if needs:
                    return step(fx, fy, *SHED) or ["PICKUP", "FERTILIZER", min(4, shed["FERTILIZER"])]
            for (x, y) in mine:
                w = plan.get((x, y))
                if w in ANIMAL:
                    t = tiles[y][x]
                    if isinstance(t, dict) and t.get("kind") == ANIMAL[w][0] and not t.get("animal"):
                        if inv.get(w, 0) > 0: return step(fx, fy, x, y) or ["PLACE", w]
                        if shed.get(w, 0) > 0: return step(fx, fy, *SHED) or ["PICKUP", w, 1]
            best, bd, bj = None, 99, None
            for (x, y) in mine:
                j = job_for(tiles[y][x], plan.get((x, y)), fx, fy, x, y, carrying, fert)
                if j:
                    d = abs(x - fx) + abs(y - fy)
                    if d < bd: best, bd, bj = (x, y), d, j
            if best:
                return step(fx, fy, *best) or bj
            for (x, y) in planned:          # idle fallback: help anywhere
                j = job_for(tiles[y][x], plan.get((x, y)), fx, fy, x, y, carrying, fert)
                if j and j[0] in ("FEED", "CARE", "HARVEST", "WATER"):
                    return step(fx, fy, x, y) or j
            return step(fx, fy, *SHED) or ["DROP"]

        return {"farmer": unit_op(0, units[0]),
                "hands": [unit_op(i + 1, h) for i, h in enumerate(me["hands"])],
                "market": market[:10]}
    return agent
