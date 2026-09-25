"""Tour executor: fixed daily tours instead of an hourly job auction.

At the start of each day the planned tiles (role per cell, from market.py's planner) are split into contiguous
serpentine zones balanced by workload, one per worker. Each worker first picks up the wheat / fertilizer its zone
needs at the shed, then walks its zone in order doing every pending action on each tile (dig, plant, water,
fertilize, harvest, feed, care, collect, place), commits to that tour for the day, and walks premium produce back
to the shed before midnight (DROP puts the whole inventory in the shed; the night drop discards overflow).
Zones are recomputed only while the day's hands are still arriving (hours 0-3).

Entry point: execute(ctx) -> (farmer_op, [hand_ops]).  ctx keys: S, state, day, hour, tiles, units (positions),
invs, shed, seeds, plan (cell -> role), planned (cells), endgame, P (price fn), n_st, held (fn), owned (quadrants).
"""
from .market import ANIMAL, RIPE, ONESHOT, SHED, step

SHED_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
PREMIUM = ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "TOMATO", "CARROT")


def _weight(cell, plan, tiles):
    role = plan.get(cell)
    if role in ANIMAL: return 3.0
    return 1.0


def make_zones(planned, plan, tiles, n):
    """Serpentine over the planned cells (row-major, alternating direction), cut into n contiguous chunks by weight."""
    if n <= 0: return []
    rows = {}
    for c in planned: rows.setdefault(c[1], []).append(c)
    serp = []
    for y in sorted(rows):
        serp.extend(sorted(rows[y], key=lambda c: c[0], reverse=(y % 2 == 1)))
    total = sum(_weight(c, plan, tiles) for c in serp)
    zones = [[] for _ in range(n)]; k = 0; acc = 0.0
    for c in serp:
        if k < n - 1 and acc >= total * (k + 1) / n: k += 1
        zones[k].append(c); acc += _weight(c, plan, tiles)
    return zones


def tile_jobs(cell, ctx, inv):
    """Ordered list of ops still needed on this cell for the unit carrying `inv` (empty if nothing to do)."""
    S, tiles, plan, day, hour, seeds, endgame = ctx["S"], ctx["tiles"], ctx["plan"], ctx["day"], ctx["hour"], ctx["seeds"], ctx["endgame"]
    x, y = cell; t = tiles[y][x]; w = plan.get(cell); jobs = []
    held = ctx["held"]
    if w in ANIMAL:
        struct, build, prod = ANIMAL[w]
        if t is None:
            if inv.get(w, 0) > 0: jobs.append([build])
            return jobs
        if not isinstance(t, dict): return jobs
        if t.get("kind") == "WEED": return [["DIG"]]
        if t.get("animal"):
            if not t["fed_today"] and inv.get("WHEAT", 0) > 0: jobs.append(["FEED"])
            if not t["cared_today"]: jobs.append(["CARE"])
            if t["yield_units"] >= S["harvest_min_animal"] or (endgame and t["yield_units"] > 0): jobs.append(["HARVEST"])
            if t.get("fertilizer_available"): jobs.append(["COLLECT_FERTILIZER"])
        elif inv.get(w, 0) > 0:
            jobs.append(["PLACE", w])
        return jobs
    # crops
    if t is None:
        late = (w == "MELON" and day > S["melon_until"]) or (w == "STRAWBERRY" and day > S["straw_until"]) or (w == "TOMATO" and day > S["tomato_until"])
        if w and seeds.get(w, 0) > 0 and not late and not endgame: jobs.append(["PLANT", w])
        return jobs
    if not isinstance(t, dict): return jobs
    if t.get("kind") == "WEED":
        return [] if endgame else [["DIG"]]
    if t.get("kind") != "PLANT": return jobs
    c = t["crop"]; age = day - t["planted_day"]
    # harvest (decay-aware, same rules as the auction executor)
    if t["yield_units"] > 0 and age >= RIPE.get(c, 4):
        if c in ONESHOT:
            w0, w1, ymax = ONESHOT[c]
            if age > w1 or (age == w1 and (t["watered_today"] or hour >= S["harvest_late_hour"] or endgame)) or (age >= w0 and t["yield_units"] >= ymax) or (endgame and day >= 29):
                jobs.append(["HARVEST"])
        elif c in ("STRAWBERRY", "TOMATO"):
            if t["yield_units"] >= 2 or day >= 26 or t.get("max_lifespan_step", -1) >= 0: jobs.append(["HARVEST"])
    if not t["watered_today"] and not (endgame and day >= 29):
        jobs.append(["WATER"])
    fert_on = t.get("fertilized_until_day", -1) >= day
    if not fert_on and not endgame and inv.get("FERTILIZER", 0) > 0:
        if (c == "STRAWBERRY" and 9 <= age <= 15 and age % 2 == 1) or (c == "MELON" and 6 <= age <= 10 and t["yield_units"] < 5) \
                or (c in ("WHEAT", "CARROT") and 1 <= age <= ONESHOT[c][1] - 1 and S.get("tour_fert_crops", 1)):
            jobs.append(["FERTILIZE"])
    # water before harvest on the last growth day so the unit gets the extra unit first
    if ["WATER"] in jobs and ["HARVEST"] in jobs and c in ONESHOT and age == ONESHOT[c][1] and not t["watered_today"]:
        jobs.remove(["HARVEST"]); jobs.append(["HARVEST"])
    return jobs


def zone_needs(zone, ctx):
    """Wheat units (unfed animals) and fertilizer units (open fertilize windows) a zone needs today."""
    tiles, day = ctx["tiles"], ctx["day"]; wheat = fert = 0
    for (x, y) in zone:
        t = tiles[y][x]
        if not isinstance(t, dict): continue
        if t.get("animal"):
            if not t["fed_today"]: wheat += 1
        elif t.get("kind") == "PLANT":
            c = t["crop"]; age = day - t["planted_day"]
            if t.get("fertilized_until_day", -1) < day and ((c == "STRAWBERRY" and 9 <= age <= 15) or (c == "MELON" and 6 <= age <= 10)): fert += 1
    return wheat, fert


def execute(ctx):
    S, state, day, hour = ctx["S"], ctx["state"], ctx["day"], ctx["hour"]
    units, invs, shed, plan, planned, tiles = ctx["units"], ctx["invs"], ctx["shed"], ctx["plan"], ctx["planned"], ctx["tiles"]
    n = len(units)
    ts = state.setdefault("tour", {"day": -1, "zones": [], "n": 0, "pos": [], "supplied": [], "mode": []})
    if ts["day"] != day:
        ts.update(day=day, zones=[], n=0, pos=[], supplied=[], mode=[])
    if ts["n"] != n and (hour <= S.get("tour_freeze_hour", 3) or not ts["zones"]):
        ts["zones"] = make_zones(planned, plan, tiles, n); ts["n"] = n
        ts["pos"] = [0] * n; ts["supplied"] = [False] * n; ts["mode"] = ["tour"] * n
    while len(ts["zones"]) < n:            # late hires beyond the frozen partition: share the last zone
        ts["zones"].append(ts["zones"][-1] if ts["zones"] else []); ts["pos"].append(0); ts["supplied"].append(False); ts["mode"].append("tour")
    P = ctx["P"]; endgame = ctx["endgame"]
    ops = [["PASS"]] * n
    taken = set()                          # (cell, op) claimed this hour, so two units never do the same job
    for u in range(n):
        ux, uy = units[u]; inv = invs[u] if u < len(invs) else {}
        zone = ts["zones"][u] if u < len(ts["zones"]) else []
        # 1. supplies. Wheat is need-based every hour: a unit carrying none while its zone still has unfed animals goes
        #    to the shed for exactly that many (the tour position is kept, so it resumes where it left off). Fertilizer
        #    is fetched once a day after the day's hands have arrived (zones are final then).
        wheat, fert = zone_needs(zone, ctx)
        if wheat > 0 and inv.get("WHEAT", 0) <= 0 and shed.get("WHEAT", 0) > 0 and day <= 28:
            if (ux, uy) in SHED_ACCESS:
                q = min(wheat, shed["WHEAT"]); ops[u] = ["PICKUP", "WHEAT", q]; shed = dict(shed); shed["WHEAT"] -= q
            else:
                ops[u] = step(ux, uy, *SHED)
            continue
        if not ts["supplied"][u] and hour >= S.get("tour_freeze_hour", 3):
            fert_need = max(0, fert - inv.get("FERTILIZER", 0))
            if fert_need >= S.get("tour_fert_min", 2) and shed.get("FERTILIZER", 0) > 0 and not endgame:   # a trip for one tile is not worth it
                if (ux, uy) in SHED_ACCESS:
                    q = min(fert_need, shed["FERTILIZER"]); ops[u] = ["PICKUP", "FERTILIZER", q]; shed = dict(shed); shed["FERTILIZER"] -= q
                else:
                    ops[u] = step(ux, uy, *SHED)
                continue
            ts["supplied"][u] = True
        # 1b. animals bought during the day wait in the shed: fetch one for an empty planned pen in this zone
        if not any(inv.get(a, 0) > 0 for a in ANIMAL) and not endgame:
            for sp in ANIMAL:
                if shed.get(sp, 0) > 0 and any(plan.get(c) == sp and (tiles[c[1]][c[0]] is None or (isinstance(tiles[c[1]][c[0]], dict)
                        and tiles[c[1]][c[0]].get("kind") == ANIMAL[sp][0] and not tiles[c[1]][c[0]].get("animal"))) for c in zone):
                    if (ux, uy) in SHED_ACCESS: ops[u] = ["PICKUP", sp, 1]; shed = dict(shed); shed[sp] -= 1
                    else: ops[u] = step(ux, uy, *SHED)
                    break
            if ops[u] != ["PASS"]: continue
        # 2. delivery. The midnight drop moves all cargo into the shed for free (up to 100 units), so a walk to the
        #    shed is only worth it early (cash compounds into the herd), when the unit is already close, once late in
        #    the day for a big lot, or when tonight's drop would overflow the shed.
        cargo = sum(inv.get(it, 0) * P(it, 50) for it in PREMIUM)
        dist = abs(ux - SHED[0]) + abs(uy - SHED[1])
        shed_total = sum(shed.values()) + sum(sum(i.values()) for i in invs)
        early = day < S["deliver_early_until"]
        want = (early and cargo >= S["deliver_min_early"]) or (cargo >= S["deliver_min"] and dist <= S.get("tour_deliver_dist", 3)) \
            or (hour >= S.get("tour_deliver_hour", 20) and cargo >= S["deliver_min"]) or (shed_total > S["shed_cap"] - 8 and cargo > 0 and hour >= 16)
        if ts["mode"][u] == "deliver" or want:
            ts["mode"][u] = "deliver"
            if (ux, uy) in SHED_ACCESS:
                ops[u] = ["DROP"]; ts["mode"][u] = "tour"
            else:
                ops[u] = step(ux, uy, *SHED)
            continue
        # 3. the tour: finish the current tile, else walk to the next tile in the zone with pending work
        here = (ux, uy)
        if here in zone:
            jobs = [j for j in tile_jobs(here, ctx, inv) if (here, j[0]) not in taken]
            if jobs:
                ops[u] = jobs[0]; taken.add((here, jobs[0][0])); continue
        L = len(zone)
        if L:
            start = ts["pos"][u] % L; target = None
            for k in range(L):
                c = zone[(start + k) % L]
                if c == here: continue
                jobs = [j for j in tile_jobs(c, ctx, inv) if (c, j[0]) not in taken]
                if jobs:
                    target = c; ts["pos"][u] = (start + k) % L; break
            if target is not None:
                taken.add((target, tile_jobs(target, ctx, inv)[0][0]))
                ops[u] = step(ux, uy, *target) or ["PASS"]; continue
        # 4. nothing left in the zone: help elsewhere (nearest tile on the farm with pending work), then deliver, else idle
        best = None
        for c in planned:
            if c in zone: continue
            d = abs(c[0] - ux) + abs(c[1] - uy)
            if best is not None and d >= best[0]: continue
            jobs = [j for j in tile_jobs(c, ctx, inv) if (c, j[0]) not in taken]
            if jobs: best = (d, c, jobs[0][0])
        if best is not None:
            d, c, op = best; taken.add((c, op))
            ops[u] = step(ux, uy, *c) or tile_jobs(c, ctx, inv)[0]; continue
        if cargo > 0 and (ux, uy) not in SHED_ACCESS and hour >= 12:
            ops[u] = step(ux, uy, *SHED); continue
        if cargo > 0 and (ux, uy) in SHED_ACCESS:
            ops[u] = ["DROP"]; continue
        ops[u] = ["PASS"]
    return ops[0], ops[1:]
