"""Adaptive dispatcher: pick a market the opponent is not in.

Markets are shared, so two agents selling the same goods destroy each other's
prices. Measured: our crop agent scores 30,000 against a non-melon opponent and
11,905 against Melon Mateo. Our livestock agent beats Rancher Rita 6-0 while
suppressing her from 46,900 to 12,956.

The opponent's build-out is visible, and readable by day 1:
    rancher_rita  12 pens / 13 crops     ledger_lena  4 pens / 17 crops
    melon_mateo    0 pens / 32 crops     rotation_rosa 0 pens / 25 crops

So: hold all investment on day 0, read their pen count on day 1, then commit to
the opposite market and never revisit the decision.
"""
from .ranch import make as _ranch
from .crop import make as _crop

_STATE = {"mode": None, "last_step": -1}

_RANCH = _ranch(target={"COW": 8, "SHEEP": 5}, feed_float_days=8, hands=8,
                land=2, buy_feed=True)
_CROP = _crop(hands=6, melon_share=0.40, wheat_share=0.30, sell_per_turn=6,
              adapt=True)

PEN_KINDS = ("PASTURE", "COOP")
ANIMALS = ("COW", "SHEEP", "GOOSE")


def _opponent_pens(obs):
    opp = obs["farms"][1 - obs["player"]]
    n = 0
    for row in opp["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("animal") in ANIMALS or t.get("kind") in PEN_KINDS:
                    n += 1
    return n


def _hold(obs):
    """Day-0 opening: hire and stock seed, commit nothing we might waste."""
    me = obs["farms"][obs["player"]]
    market = []
    if obs["hour"] == 0:
        for _ in range(6):
            market.append(["HIRE"])
    if me["money"] > 800 and obs["hour"] == 1:
        market.append(["BUY_PRODUCT", "WHEAT", 20])
    return {"farmer": ["PASS"],
            "hands": [["PASS"] for _ in me["hands"]],
            "market": market}


def agent(obs, config=None):
    try:
        step = int(obs.get("step", 0) or 0)
        # New episode: the module persists across games in one process.
        if step <= _STATE["last_step"]:
            _STATE["mode"] = None
        _STATE["last_step"] = step

        if _STATE["mode"] is None:
            if obs["day"] < 1:
                return _hold(obs)
            # Commit once, on the first look, and never revisit.
            _STATE["mode"] = "crop" if _opponent_pens(obs) >= 3 else "ranch"

        return _RANCH(obs) if _STATE["mode"] == "ranch" else _CROP(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
