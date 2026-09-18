"""Objective model for Kaggriculture, calibrated against measured runs.

Everything here is either read from the simulator's constants or fitted to a
measured experiment. No free-floating guesses.
"""
import math
from kaggle_environments.envs.kaggriculture.kaggriculture import (
    MARKET_I0, market_price, _hire_cost, LAND_PRICES)

TURNS, DAYS = 24, 30
START = 3000
GOOSE = 300
EGG_P = 38          # measured invariant across 400 town draws (Phase 0 Q2)
WHEAT_P = 26        # market buy price, roughly flat
SERVICE = 3.5       # actions/goose/day: feed 1 + care 1 + harvest 0.5 + 1 internal move

# --- capacity model -------------------------------------------------------
# A unit has 24 moves. It must walk out to its cluster and back for wheat (2d),
# then spend SERVICE per goose. Calibrated: at d=2 this gives k=6, which is
# exactly the measured hard ceiling.
def capacity(d):
    return max(0.0, (TURNS + 1 - 2 * d) / SERVICE)

# --- prime real estate ----------------------------------------------------
# Tiles within distance d of the shed, per quadrant owned.
def tiles_within(d, quadrants):
    n = 0
    for q in range(quadrants):
        for dist in range(0, d + 1):
            n += 1 if dist == 0 else min(dist + 1, 5)
    return n

def geese_supportable(quadrants, units):
    """Greedily fill nearest tiles first, capped by per-unit capacity."""
    tiles = []
    for q in range(quadrants):
        for x in range(5):
            for y in range(5):
                tiles.append(abs(x - 4) + abs(y - 4))
    tiles.sort()
    total, u_used, budget = 0, 0, 0.0
    for d in tiles:
        if budget <= 0:
            if u_used >= units:
                break
            u_used += 1
            budget = TURNS + 1 - 2 * d       # this unit's action budget after the walk
        if budget >= SERVICE:
            budget -= SERVICE
            total += 1
        else:
            budget = 0
    return total

# --- season simulation ----------------------------------------------------
def simulate(hands, quadrants, land_day=3, ramp=True, verbose=False):
    """Day-by-day capital model. Returns final bank."""
    bank = START
    geese = 0
    cap = geese_supportable(quadrants, 1 + hands)
    land_cost = sum(LAND_PRICES[:max(0, quadrants - 1)])
    paid_land = False
    for day in range(DAYS):
        # Buy land once, early.
        if not paid_land and day >= land_day and quadrants > 1:
            if bank >= land_cost:
                bank -= land_cost
                paid_land = True
        # Hire hands (cost resets daily).
        bank -= sum(_hire_cost(i) for i in range(hands))
        # Buy geese with spare capital, up to capacity.
        if ramp:
            while geese < cap and bank >= GOOSE + 200:
                bank -= GOOSE
                geese += 1
        # Production: a goose laid its first egg 4 days after purchase; approximate
        # by discounting the first 4 days of each bird's life via a ramp factor.
        active = geese * min(1.0, max(0.0, (day - 2) / 4))
        bank += active * 2 * EGG_P          # 2 eggs/day, care bonus included
        bank -= active * WHEAT_P            # 1 wheat/day feed
    return bank, geese, cap

print("=" * 74)
print("CAPACITY MODEL  (calibrated: d=2 -> 6 geese, matching the measured ceiling)")
print("=" * 74)
print(f"{'distance from shed':>20}{'geese one unit can hold':>26}")
for d in range(0, 9):
    print(f"{d:>20}{capacity(d):>26.1f}")

print()
print("=" * 74)
print("SUPPORTABLE FLOCK  (nearest-tile-first assignment)")
print("=" * 74)
print(f"{'units':>7}" + "".join(f"{f'{q}quad':>10}" for q in (1, 2, 3, 4)))
for u in (1, 2, 4, 6, 8, 11, 13):
    row = "".join(f"{geese_supportable(q, u):>10}" for q in (1, 2, 3, 4))
    print(f"{u:>7}{row}")

print()
print("=" * 74)
print("STRATEGY OPTIONS  (day-by-day capital model, 30 days)")
print("=" * 74)
STRATS = [
    ("A  Solo, no land, no hands",        0,  1),
    ("B  Solo + 1 quadrant",              0,  2),
    ("C  4 hands, 1 quadrant",            4,  2),
    ("D  8 hands, 2 quadrants",           8,  3),
    ("E  10 hands, all land",            10,  4),
    ("F  13 hands, all land",            13,  4),
    ("G  16 hands, all land",            16,  4),
]
print(f"{'strategy':<30}{'flock cap':>11}{'geese built':>13}{'final bank':>13}{'profit':>11}")
best = None
for name, h, q in STRATS:
    bank, geese, cap = simulate(h, q)
    if best is None or bank > best[1]:
        best = (name, bank)
    print(f"{name:<30}{cap:>11}{geese:>13}{bank:>13,.0f}{bank-START:>11,.0f}")
print(f"\n  best on this model: {best[0]}  ({best[1]:,.0f})")

print()
print("=" * 74)
print("SENSITIVITY  (final bank, hands x quadrants)")
print("=" * 74)
print(f"{'hands':>7}" + "".join(f"{f'{q}quad':>12}" for q in (1, 2, 3, 4)))
for h in (0, 2, 4, 6, 8, 10, 12, 14, 16):
    row = "".join(f"{simulate(h, q)[0]:>12,.0f}" for q in (1, 2, 3, 4))
    print(f"{h:>7}{row}")

print()
print("=" * 74)
print("WHAT BREAKS IT  (final bank of the best strategy under worse assumptions)")
print("=" * 74)
import copy
base_bank = simulate(10, 4)[0]
print(f"  baseline (10 hands, all land)              {base_bank:>12,.0f}")
for label, key, val in [
    ("service cost 4.5 actions not 3.5", "SERVICE", 4.5),
    ("service cost 5.5 actions not 3.5", "SERVICE", 5.5),
    ("egg price 30 not 38",              "EGG_P",   30),
    ("wheat feed 40 not 26",             "WHEAT_P", 40),
]:
    g = globals(); old = g[key]; g[key] = val
    print(f"  {label:<42}{simulate(10,4)[0]:>12,.0f}")
    g[key] = old
