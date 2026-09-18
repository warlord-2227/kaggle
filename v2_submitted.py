"""Kaggriculture submission v2.

Five geese on the five tiles nearest the shed, one farmer, fed and cared daily.

Chosen because it is the best configuration we have MEASURED (6,519 median vs
starter's ~3,550), not the best we have modelled. A larger multi-unit design
modelled at ~31,000 but tested at 5,612 -- worse than this -- so it is not here.

Key structure: the unit is in exactly one mode at a time, and the mode flips
only on a monotone condition (wheat in hand hits zero / becomes positive).
An earlier version that re-decided every turn oscillated between "walk to the
goose" and "walk to the shed" for 14 consecutive turns and starved the flock.
"""

SHED = (4, 4)
# The five tiles closest to the shed inside the starting quadrant.
CELLS = [(4, 4), (3, 4), (4, 3), (2, 4), (3, 3)]
SAFE = {"farmer": ["PASS"], "hands": [], "market": []}


def _step(fx, fy, tx, ty):
    if fx < tx: return ["EAST"]
    if fx > tx: return ["WEST"]
    if fy < ty: return ["SOUTH"]
    if fy > ty: return ["NORTH"]
    return None


def _decide(obs):
    me = obs["farms"][obs["player"]]
    priv = obs["private"]
    fx, fy = me["farmer"]
    tiles = me["tiles"]
    inv = priv["inventories"][0] if priv.get("inventories") else {}
    shed = priv.get("shed", {})
    money = me["money"]
    market = []

    # Sell eggs every turn: keeps the 100-item shed clear and eggs barely move
    # the price (log glut curve -- still ~36 after 4,000 sold).
    if shed.get("EGG", 0) > 0:
        market.append(["SELL", "EGG", shed["EGG"]])
    # Small, capped feed top-ups. Bulk buying is ruinous: 1,350 units costs
    # 66,828 because buying drains inventory and drives the price up.
    if shed.get("WHEAT", 0) < 20 and money > 500:
        market.append(["BUY_PRODUCT", "WHEAT", 10])

    def act(op):
        return {"farmer": op, "hands": [], "market": market}

    live = [c for c in CELLS
            if isinstance(tiles[c[1]][c[0]], dict) and tiles[c[1]][c[0]].get("animal")]
    unfed = [c for c in live if not tiles[c[1]][c[0]]["fed_today"]]

    # MODE RESTOCK -- only entered with zero wheat in hand, so it cannot oscillate.
    if unfed and inv.get("WHEAT", 0) == 0 and shed.get("WHEAT", 0) > 0:
        mv = _step(fx, fy, *SHED)
        return act(mv or ["PICKUP", "WHEAT", 15])

    # MODE SERVICE -- nearest tile that has a job we can actually do.
    best, bd, bk = None, 99, None
    for (x, y) in CELLS:
        t = tiles[y][x]
        d = abs(x - fx) + abs(y - fy)
        if t is None:
            job = "BUILD"
        elif not isinstance(t, dict):
            continue
        elif t.get("kind") == "WEED":
            job = "DIG"
        elif t.get("kind") == "COOP" and not t.get("animal"):
            job = "PLACE" if inv.get("GOOSE", 0) > 0 else (
                  "FETCH" if shed.get("GOOSE", 0) > 0 else None)
            if job is None:
                if money >= 300:
                    market.append(["BUY_ANIMAL", "GOOSE", 1])
                continue
        elif t.get("animal"):
            if t.get("yield_units", 0) >= 4: job = "HARVEST"
            elif not t.get("fed_today") and inv.get("WHEAT", 0) > 0: job = "FEED"
            elif not t.get("cared_today"): job = "CARE"
            elif t.get("yield_units", 0) > 0: job = "HARVEST"
            else: continue
        else:
            continue
        if d < bd:
            best, bd, bk = (x, y), d, job

    if best:
        x, y = best
        if bk == "FETCH":
            mv = _step(fx, fy, *SHED)
            return act(mv or ["PICKUP", "GOOSE", 1])
        mv = _step(fx, fy, x, y)
        if mv:
            return act(mv)
        return act({"BUILD": ["BUILD_COOP"], "DIG": ["DIG"], "PLACE": ["PLACE", "GOOSE"],
                    "HARVEST": ["HARVEST"], "FEED": ["FEED"], "CARE": ["CARE"]}[bk])

    mv = _step(fx, fy, *SHED)
    return act(mv or ["DROP"])


def agent(obs, config=None):
    try:
        return _decide(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
