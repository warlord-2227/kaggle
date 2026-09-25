

# ---------------------------------------------------------------------------
# IWA_setu UNREADABLE layer (2026-09-24). Relatives forecast our premium sales from recorded public streams and, in clone
# mode, assume our order list equals theirs. This layer makes both fail: (1) the sale-race horizon becomes per-item and
# jittered each day by a private RNG (seeded from our private shed, which the rival cannot see), so our lots land at times
# no recorded stream has; (2) optionally the order of our SELL slots is shuffled per turn, so the lockstep assumption breaks.
# The tape and every other layer are untouched: _V9_ITEM_HZ is replaced by a dict whose .get() returns jittered horizons.
# ---------------------------------------------------------------------------
_UR_HOST = [v for v in list(globals().values()) if callable(v)][-1]   # capture the agent BEFORE defining anything callable here
import random as _ur_random
UR_JITTER = 12          # max +/- turns added to each item's race horizon per day (0 = off)
UR_SHUFFLE = 0          # 1 = shuffle the order of SELL orders each turn
UR_HZ_MIN, UR_HZ_MAX = 4, 72
_UR_SALT = "iwa-unreadable-2026"
_UR_REPORT = dict(ur_turns=0, ur_shuffles=0, ur_errors=0)
_UR_CTX = {}


class _URHorizons(dict):
    def get(self, key, default=None):
        v = super().get(key, default)
        if not isinstance(v, dict) or UR_JITTER <= 0: return v
        ctx = _UR_CTX.get(key)
        if not ctx: return v
        rng = _ur_random.Random(f"{_UR_SALT}:{ctx}")
        return {item: max(UR_HZ_MIN, min(UR_HZ_MAX, h + rng.randint(-UR_JITTER, UR_JITTER))) for item, h in v.items()}


_ur_old = _V9_ITEM_HZ
_V9_ITEM_HZ = _URHorizons(_ur_old)


def unreadable_agent(observation, configuration=None):
    _UR_REPORT["ur_turns"] += 1
    try:
        player = int(observation["player"]); step = int(observation["step"]); day = step // 24
        shed = observation.get("private", {}).get("shed", {}) or {}
        _UR_CTX[player] = f"{player}:{day}:{sum(shed.values())}:{sorted(shed.items())[:3]}"
    except Exception:
        _UR_REPORT["ur_errors"] += 1
    action = _UR_HOST(observation, configuration)
    if UR_SHUFFLE and isinstance(action, dict):
        try:
            market = list(action.get("market") or [])
            sells = [i for i, o in enumerate(market) if isinstance(o, list) and o and o[0] == "SELL"]
            if len(sells) > 1:
                rng = _ur_random.Random(f"{_UR_SALT}:shuffle:{_UR_CTX.get(int(observation['player']))}:{observation['step']}")
                perm = sells[:]; rng.shuffle(perm)
                new = list(market)
                for src, dst in zip(sells, perm): new[dst] = market[src]
                action = dict(action); action["market"] = new; _UR_REPORT["ur_shuffles"] += 1
        except Exception:
            _UR_REPORT["ur_errors"] += 1
    return action


unreadable_agent.telemetry = _UR_REPORT
agent = unreadable_agent
