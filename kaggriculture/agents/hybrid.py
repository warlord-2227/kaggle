"""Hybrid: a public route-tape chassis plays the opening (days 0..takeover-1), our demand-driven market agent takes the
farm over from `takeover_step` and runs the second half (tomato/wheat/carrot lines sized to the town, labour auction).

make(takeover_step=288, chassis="demand", **market_knobs) -> agent(obs, config).
Chassis files live in refagents/public/ (Apache-2.0); loaded with Kaggle's last-callable rule.
"""
import os, importlib.util
from kaggriculture.agents import market

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHASSIS = {"demand": "tetsutani_demand_preserving.py", "v56": "ahmed_v56.py", "farm2945": "farm2945_v9_4.py"}


def load_chassis(name):
    path = name if os.path.sep in name else os.path.join(ROOT, "refagents", "public", CHASSIS.get(name, name))
    sp = importlib.util.spec_from_file_location("chassis_" + os.path.basename(path).replace(".", "_"), path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return [v for v in vars(m).values() if callable(v)][-1]


def make(takeover_step=288, chassis="demand", debug=False, **over):
    tape = load_chassis(chassis)
    ours = market.make(debug=debug, **over)

    def agent(obs, config=None):
        if int(obs["step"]) < takeover_step:
            return tape(obs, config)
        return ours(obs, config)
    return agent
