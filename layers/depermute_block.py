# MEASURED 2026-09-22 17:05: NEGATIVE. Appended to the demand-preserving file this layer collapses the farm (9.6k vs 172k, 0-8 vs every
# relative): the tape depends on physical hand identity beyond the hands/inventories lists. Upper bound was ~0 anyway (a rival with
# its clone gates disabled ties 7/8 games). Kept for the record only; do not append.


# ---------------------------------------------------------------------------
# IWA_setu DEPERMUTE layer (2026-09-22). The public route-tape relatives detect a clone rival by comparing the two
# farms' worker position lists in order (`_race_positions_equal`) and then best-respond (clone race horizon, lockstep
# SELL re-ordering). Hands spawn together at the shed, so which physical hand runs which tape route is arbitrary:
# this layer gives the tape a view in which hand indices are permuted (hands that spawned in the same turn are
# assigned in reverse order) and re-permutes the tape's hand commands back. Our position list is then a permutation
# of a relative's, never equal, so relatives never enter clone mode against us; our own detection is made
# order-insensitive so we still recognise them. The tape itself sees a consistent world all day.
# ---------------------------------------------------------------------------
import copy as _dp_copy
_DP_HOST = [v for v in list(globals().values()) if callable(v)][-1]
_DP_STATE = {}
_DP_REPORT = dict(dp_turns=0, dp_permuted_turns=0, dp_errors=0)


def _dp_perm(player, n, step):
    """perm[physical] = tape index; extended (reversed within a spawn batch) as hands appear; reset each day."""
    st = _DP_STATE.setdefault(player, {"day": -1, "perm": []})
    day = step // 24
    if st["day"] != day:
        st["day"] = day; st["perm"] = []
    perm = st["perm"]
    if n < len(perm):                       # hands vanished (should only happen at the day change)
        del perm[n:]
    if n > len(perm):
        k0 = len(perm); k = n - k0
        perm.extend(k0 + (k - 1 - j) for j in range(k))
    return list(perm)


def _dp_view(observation, perm):
    """Observation copy in which our hands / inventories are listed in tape order."""
    n = len(perm)
    if n <= 1 or all(perm[i] == i for i in range(n)):
        return observation
    view = _dp_copy.deepcopy(observation)
    player = int(view["player"])
    farm = view["farms"][player]
    inv = [None] * n
    for phys, tape in enumerate(perm):
        inv[tape] = phys
    farm["hands"] = [observation["farms"][player]["hands"][inv[t]] for t in range(n)]
    priv = view.get("private")
    if priv and isinstance(priv.get("inventories"), list) and len(priv["inventories"]) >= n + 1:
        real = observation["private"]["inventories"]
        priv["inventories"] = [real[0]] + [real[1 + inv[t]] for t in range(n)]
    return view


def _dp_positions_equal_sorted(farms, player):
    own, rival = farms[player], farms[1 - player]
    return (len(own["hands"]) > 0 and len(own["hands"]) == len(rival["hands"])
            and sorted(map(tuple, own["hands"])) == sorted(map(tuple, rival["hands"])) and list(own["farmer"]) == list(rival["farmer"]))


if "_race_positions_equal" in globals():
    _race_positions_equal = _dp_positions_equal_sorted     # our clone detection stays order-insensitive


def depermute_agent(observation, configuration=None):
    _DP_REPORT["dp_turns"] += 1
    try:
        player = int(observation["player"]); step = int(observation["step"])
        hands = observation["farms"][player]["hands"]; n = len(hands)
        perm = _dp_perm(player, n, step)
        view = _dp_view(observation, perm)
        action = _DP_HOST(view, configuration)
        if n > 1 and any(perm[i] != i for i in range(n)) and isinstance(action, dict):
            tape_hands = list(action.get("hands") or [])
            out = []
            for phys in range(n):
                t = perm[phys]
                out.append(tape_hands[t] if t < len(tape_hands) else ["PASS"])
            action = dict(action); action["hands"] = out
            _DP_REPORT["dp_permuted_turns"] += 1
        return action
    except Exception:
        _DP_REPORT["dp_errors"] += 1
        return _DP_HOST(observation, configuration)


depermute_agent.telemetry = _DP_REPORT
agent = depermute_agent
