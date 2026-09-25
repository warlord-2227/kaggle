"""Make the town shop draw seed-deterministic for LOCAL evaluation.

In the shipped env, _end_of_day builds one Random((seed*1_000_003) ^ day),
spends it on weed rolls -- one per EMPTY tile on both farms -- and then draws
the day's shop from what is left. Different agents leave different numbers
of empty tiles, so two variants "on the same seed" face different shops.
Milk is worth 66 or 216 depending on that draw, which swamps most A/Bs.

apply() replaces the weed pass with one that always consumes exactly one
roll per tile (100 per farm), keeping each empty tile's weed probability
identical while making the shop draw a pure function of the seed.

Local evaluation only. The competition env is unchanged; on the ladder the
noise is symmetric between the two players.
"""
from kaggle_environments.envs.kaggriculture import kaggriculture as K

_ORIGINAL_SPAWN_WEEDS = K._spawn_weeds   # captured at import, before any apply()


def _spawn_weeds_fixed_consumption(farm, board_size, weed_chance, rng):
    for y in range(board_size):
        for x in range(board_size):
            r = rng.random()                       # always consume
            if farm["tiles"][y][x] is None and r < weed_chance:
                farm["tiles"][y][x] = {"kind": "WEED"}


def apply():
    K._spawn_weeds = _spawn_weeds_fixed_consumption


def restore():
    """Undo apply(). REQUIRED before any replayed-trace game in a worker process that ran a fair-env game:
    the patch is process-wide and a recorded opponent is only faithful under the shipped shop draw."""
    K._spawn_weeds = _ORIGINAL_SPAWN_WEEDS


def is_applied():
    return K._spawn_weeds is _spawn_weeds_fixed_consumption
