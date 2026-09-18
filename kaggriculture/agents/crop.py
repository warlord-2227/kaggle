"""Crop-first farm, rebuilt after reading three opponent replays.

Melons return ~$126/action against a goose's $11, because the achievable
volume (20 plants -> 120 melons -> 26,763) sits right at the revenue peak,
while eggs only beat it at volumes needing ~100 geese.

Selling is price-responsive rather than fixed: each turn we sell whichever
product currently pays best relative to its base. If an opponent floods
melons, we shift to wheat and carrot without being told to.
"""
import math

SHED = (4, 4)
QO = {"NW": (0, 0), "NE": (5, 0), "SW": (0, 5), "SE": (5, 5)}
BASE = {"MELON": 250, "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
        "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
# (first_yield_day, max_yield_day, bonus_window_start)
CROP = {"MELON": (10, 12, 6), "WHEAT": (2, 4, 2), "CARROT": (2, 3, 2)}


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


def make(hands=7, melon_share=0.55, wheat_share=0.30, land_days=(4, 9, 16),
         sell_per_turn=6, floor_frac=0.0, adapt=False):
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
        shed, seeds = priv["shed"], priv["seeds"]
        prices = obs["market"]["prices"]
        market = []

        if hour == 0:
            for _ in range(hands):
                market.append(["HIRE"])
        # Land early: more tiles is more plants, and plants are the engine.
        for i, d in enumerate(land_days):
            if len(owned) < i + 2 and day >= d and money > 1200 + 800 * i:
                market.append(["BUY_LAND"]); break

        # Sell whatever currently pays best relative to base. Trickle, never dump.
        # Hold a price floor. Dumping into a crowded market is how we lost 0-8
        # to Melon Mateo: both of us flooding melon cost us 60% of our bank.
        # Late in the season the floor is released -- unsold stock scores zero.
        endgame = day >= 27
        ranked = sorted((k for k in shed if shed[k] > 0 and k != "GOOSE"),
                        key=lambda k: -(prices.get(k, 0) / BASE.get(k, 100)))
        for k in ranked[:2]:
            p = prices.get(k, 0)
            if p <= 1:
                continue
            if not endgame and p < floor_frac * BASE.get(k, 100):
                continue
            n = min(shed[k], sell_per_turn if not endgame else 30)
            if n > 0:
                market.append(["SELL", k, n])

        cells = tiles_by_distance(owned)
        n_cells = len(cells)
        n_melon = int(n_cells * melon_share)
        n_wheat = int(n_cells * wheat_share)
        ms = melon_share
        if adapt:
            # Look at the opponent's field. If they are melon-heavy, back off --
            # the melon revenue curve peaks near 158 units and declines after,
            # so two melon farmers make each other poorer.
            opp = obs["farms"][1 - obs["player"]]
            theirs = 0
            for row in opp["tiles"]:
                for t in row:
                    if isinstance(t, dict) and t.get("crop") == "MELON":
                        theirs += 1
            if theirs >= 6:
                ms = max(0.10, melon_share - 0.25)
        n_melon = int(len(cells) * ms)
        plan = {}
        for i, c in enumerate(cells):
            plan[c] = "MELON" if i < n_melon else ("WHEAT" if i < n_melon + n_wheat
                                                   else "CARROT")
        for crop, cost in (("MELON", 80), ("WHEAT", 10), ("CARROT", 20)):
            if seeds.get(crop, 0) < 4 and money > cost * 8:
                market.append(["BUY_SEED", crop, 4])

        units = [me["farmer"]] + list(me["hands"])
        n_units = len(units)
        assign = [[] for _ in range(n_units)]
        for i, c in enumerate(cells):
            assign[i % n_units].append(c)

        def unit_op(u, pos):
            fx, fy = pos
            best, bd, bj = None, 99, None
            for (x, y) in assign[u] if u < len(assign) else []:
                t = tiles[y][x]
                d = abs(x - fx) + abs(y - fy)
                want = plan[(x, y)]
                if t is None:
                    job = ("PLANT", want) if seeds.get(want, 0) > 0 else None
                elif not isinstance(t, dict):
                    job = None
                elif t.get("kind") == "WEED":
                    job = ("DIG",)
                elif t.get("kind") == "PLANT":
                    c = t["crop"]; fy_, my_, ws = CROP.get(c, (2, 4, 2))
                    age = day - t["planted_day"]
                    if age >= my_ and t["yield_units"] > 0:
                        job = ("HARVEST",)
                    elif age >= fy_ and t["yield_units"] >= 4:
                        job = ("HARVEST",)
                    elif not t["watered_today"]:
                        job = ("WATER",)
                    else:
                        job = None
                else:
                    job = None
                if job and d < bd:
                    best, bd, bj = (x, y), d, job
            if best:
                mv = step(fx, fy, *best)
                if mv: return mv
                return list(bj) if bj[0] != "PLANT" else ["PLANT", bj[1]]
            mv = step(fx, fy, *SHED)
            return mv or ["DROP"]

        return {"farmer": unit_op(0, units[0]),
                "hands": [unit_op(i + 1, h) for i, h in enumerate(me["hands"])],
                "market": market[:10]}
    return agent
