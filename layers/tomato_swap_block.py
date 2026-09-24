

# ---------------------------------------------------------------------------
# IWA_setu TOMATO-SWAP layer (2026-09-24). The tape plants its last strawberry batch (13 tiles) on day 11; those berries
# produce on days 21-27 into a book both farms have already crashed (measured: $28 on day 20, $18 at the end, even vs a
# passive rival), while tomato trades at base ($60+) with nobody selling. This layer turns the first TS_K strawberry
# plantings on/after day TS_FROM_DAY into tomato on the same tiles (seed 50 instead of 100), swapping the tape's JIT
# BUY_SEED STRAWBERRY orders too. The tape keeps visiting those tiles daily (water, fertilize, harvest), which is all a
# tomato needs; its 4 productions land on the tape's own harvest visits.
# ---------------------------------------------------------------------------
TS_K = 13
TS_FROM_DAY = 11
TS_TO_DAY = 12
_TS_HOST = [v for v in list(globals().values()) if callable(v)][-1]
_TS_STATE = {}
_TS_REPORT = dict(ts_seed_swaps=0, ts_plant_swaps=0, ts_errors=0)


def tomato_swap_agent(observation, configuration=None):
    action = _TS_HOST(observation, configuration)
    try:
        step = int(observation["step"]); day = step // 24; player = int(observation["player"])
        st = _TS_STATE.setdefault(player, {"seeds": 0, "plants": 0})
        if not (TS_FROM_DAY <= day <= TS_TO_DAY) or not isinstance(action, dict) or TS_K <= 0:
            return action
        market = list(action.get("market") or [])
        for i, o in enumerate(market):
            if isinstance(o, list) and len(o) >= 3 and o[0] == "BUY_SEED" and o[1] == "STRAWBERRY" and st["seeds"] < TS_K:
                q = int(o[2]); k = min(q, TS_K - st["seeds"])
                market[i] = ["BUY_SEED", "TOMATO", k]; st["seeds"] += k; _TS_REPORT["ts_seed_swaps"] += k
                if q > k: market.insert(i + 1, ["BUY_SEED", "STRAWBERRY", q - k])
        action = dict(action); action["market"] = market[:10]
        units = [action.get("farmer")] + list(action.get("hands") or [])
        out = []
        for u in units:
            if isinstance(u, list) and len(u) >= 2 and u[0] == "PLANT" and u[1] == "STRAWBERRY" and st["plants"] < TS_K:
                u = ["PLANT", "TOMATO"]; st["plants"] += 1; _TS_REPORT["ts_plant_swaps"] += 1
            out.append(u)
        action["farmer"] = out[0]; action["hands"] = out[1:]
        return action
    except Exception:
        _TS_REPORT["ts_errors"] += 1
        return action


tomato_swap_agent.telemetry = _TS_REPORT
agent = tomato_swap_agent
