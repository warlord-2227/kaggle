"""Mathematical model of Kaggriculture, computed against the real simulator constants."""
import math, sys
sys.path.insert(0, ".venv/lib/python3.12/site-packages")
from kaggle_environments.envs.kaggriculture.kaggriculture import (
    CROPS, ANIMALS, MARKET_PARAMS, MARKET_I0, market_price, _fib, _hire_cost,
)

TURNS_PER_DAY, DAYS = 24, 30


def crop_plan(crop, harvest_age=None):
    """Optimal action plan for one tile-cycle of a one-time crop.

    Returns (harvest_age, n_waters, units, actions). Rules from the source:
      - yield starts at 1; watering at age in [ (myd+1)//2 , myd ] adds +1 (cap max_yield)
      - plant day counts as unwatered, so age 0 MUST be watered
      - dies if unwatered 2 consecutive days -> water at least every other day
      - harvest legal once age >= first_yield_day
    """
    c = CROPS[crop]
    if c["ongoing"]:
        return None
    myd, fyd, cap = c["max_yield_day"], c["first_yield_day"], c["max_yield"]
    w0 = (myd + 1) // 2
    best = None
    for h in range(fyd, myd + 1):
        # Water every bonus day in [w0,h]; plus survival waters before w0.
        bonus_days = set(range(w0, h + 1))
        survival = set()
        last = 0
        survival.add(0)                      # age 0 mandatory
        while last + 2 <= h:                 # never 2 consecutive dry days
            nxt = last + 2
            if nxt not in bonus_days:
                survival.add(nxt)
            last = nxt if nxt not in bonus_days else last
            if nxt in bonus_days:
                last = nxt
        waters = sorted(bonus_days | survival)
        units = min(cap, 1 + len(bonus_days))
        actions = 1 + len(waters) + 1        # plant + waters + harvest
        occ = h + 1
        cand = (h, len(waters), units, actions, occ)
        if best is None or units / actions > best[2] / best[3]:
            best = cand
    return best


def revenue_curve(item, n):
    """Total coins from selling n units into a fresh market, one at a time."""
    inv, total = MARKET_I0, 0
    for _ in range(n):
        total += market_price(item, inv)
        inv += 1
    return total


def optimal_sale(item, cap=4000):
    """n maximizing total revenue, and that revenue."""
    inv, total, best_n, best_tot = MARKET_I0, 0, 0, 0
    for n in range(1, cap + 1):
        total += market_price(item, inv)
        inv += 1
        if total > best_tot:
            best_tot, best_n = total, n
    return best_n, best_tot


print("=" * 78)
print("ONE-TIME CROPS -- optimal single tile-cycle (actions incl. plant+waters+harvest)")
print("=" * 78)
print(f"{'crop':<11}{'harv age':>9}{'waters':>8}{'units':>7}{'actions':>9}"
      f"{'u/action':>10}{'u/tile-day':>12}{'seed':>6}")
for c in CROPS:
    p = crop_plan(c)
    if not p:
        continue
    h, w, u, a, occ = p
    print(f"{c:<11}{h:>9}{w:>8}{u:>7}{a:>9}{u/a:>10.2f}{u/occ:>12.2f}{CROPS[c]['seed']:>6}")

print()
print("=" * 78)
print("MARKET CEILING -- how much each product can ever be sold for (fresh market)")
print("=" * 78)
print(f"{'item':<12}{'base':>6}{'T':>6}{'max units':>11}{'max revenue':>13}"
      f"{'avg $/unit':>12}{'price@100':>11}{'price@300':>11}")
for it in MARKET_PARAMS:
    n, tot = optimal_sale(it)
    p100 = market_price(it, MARKET_I0 + 100)
    p300 = market_price(it, MARKET_I0 + 300)
    print(f"{it:<12}{MARKET_PARAMS[it]['base']:>6}{MARKET_PARAMS[it]['T']:>6}"
          f"{n:>11}{tot:>13,.0f}{tot/max(n,1):>12.1f}{p100:>11}{p300:>11}")


print()
print("=" * 78)
print("LABOR -- cumulative cost of hiring H hands for ONE day (fib), and action budget")
print("=" * 78)
print(f"{'hands H':>8}{'cost/day':>10}{'cost/season':>13}{'actions/day':>13}{'$/action':>10}")
cum = 0
for H in range(0, 21):
    if H:
        cum += _hire_cost(H - 1)
    acts = (1 + H) * TURNS_PER_DAY
    if H in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20):
        print(f"{H:>8}{cum:>10,}{cum * DAYS:>13,}{acts:>13}{cum / acts:>10.2f}")

print()
print("=" * 78)
print("EGG CEILING -- price after selling N eggs (log curve barely decays)")
print("=" * 78)
print(f"{'N sold':>8}{'price':>8}{'cum revenue':>14}{'avg $/egg':>11}")
inv, tot = MARKET_I0, 0
for n in range(1, 6001):
    tot += market_price("EGG", inv); inv += 1
    if n in (100, 500, 1000, 2000, 3000, 4000, 6000):
        print(f"{n:>8}{market_price('EGG', inv):>8}{tot:>14,.0f}{tot/n:>11.1f}")

print()
print("=" * 78)
print("GOOSE UNIT ECONOMICS (steady state, FEED+CARE daily, HARVEST every 2 days)")
print("=" * 78)
EGG_P = 40      # conservative sustained price
WHEAT_BUY = 26  # market buy price
acts_feed, acts_care, acts_harv, acts_move = 1, 1, 0.5, 1.0
acts = acts_feed + acts_care + acts_harv + acts_move
print(f"  eggs/day (care doubles base 1)      : 2")
print(f"  actions/goose/day                  : {acts} (feed {acts_feed}, care {acts_care}, "
      f"harvest {acts_harv}, move ~{acts_move})")
print(f"  gross/day                          : ${2*EGG_P}")
print(f"  wheat feed cost/day (buy @ ~{WHEAT_BUY})    : ${WHEAT_BUY}")
print(f"  net/day                            : ${2*EGG_P - WHEAT_BUY}")
print(f"  net per action                     : ${(2*EGG_P - WHEAT_BUY)/acts:.1f}")
print(f"  payback on $300 goose              : {300/(2*EGG_P-WHEAT_BUY):.1f} days")

print()
print("=" * 78)
print("SCALING -- how many geese the action budget supports")
print("=" * 78)
print(f"{'hands':>6}{'actions/day':>13}{'max geese':>11}{'labor/season':>14}"
      f"{'gross/day':>11}{'net/day':>10}")
for H in (0, 4, 8, 10, 12, 14):
    cumH = sum(_hire_cost(i) for i in range(H))
    acts_avail = (1 + H) * TURNS_PER_DAY
    geese = int(acts_avail / acts)
    gross = geese * 2 * EGG_P
    net = gross - geese * WHEAT_BUY - cumH
    print(f"{H:>6}{acts_avail:>13}{geese:>11}{cumH*DAYS:>14,}{gross:>11,}{net:>10,}")
print()
print("  Tile cap: 25 (NW only) / 50 / 75 / 100 quadrants at 0 / 1k / 3k / 7k cumulative.")
print("  So geese are capped by TILES long before actions once H >= 8.")
