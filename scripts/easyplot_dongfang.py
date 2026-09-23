"""Opt-in, source-attributed Dongfang colour schemes. No network at runtime."""
from __future__ import annotations

import json
from numbers import Integral
from pathlib import Path

import numpy as np
from matplotlib.colors import ListedColormap

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "dongfang.json"


def registry():
    """Return a fresh registry including source identities and curation rationale."""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def dongfang_color(name: str) -> str:
    for colour in registry()["source_colours"]:
        if name == colour["name"] or name in colour["aliases"]:
            return colour["hex"]
    raise ValueError(f"Unknown Dongfang source colour: {name!r}")


def dongfang_palettes():
    return {name: {key: value for key, value in entry.items() if key in
                  ("label", "type", "max_n", "rationale", "uses")}
            for name, entry in registry()["palettes"].items()}


def dongfang_palette(name="danqing", n=None, role="fill", reverse=False):
    """Stable category prefixes or samples of a frozen continuous LUT.

    Map the returned values to explicit group names once per figure. For
    diverging data, declare a meaningful centre in the plotting normalization.
    """
    palettes = registry()["palettes"]
    if not isinstance(reverse, (bool, np.bool_)):
        raise ValueError("reverse must be a boolean")
    if name not in palettes:
        raise ValueError(f"Unknown palette {name!r}; choose from {', '.join(palettes)}")
    spec = palettes[name]
    if role not in ("fill", "line") or role not in spec:
        raise ValueError(f"Role {role!r} is unavailable for {name}")
    colours = spec[role]
    if n is None:
        n = len(colours)
    if isinstance(n, bool) or not isinstance(n, Integral) or n < 1:
        raise ValueError("n must be a positive integer")
    if spec["type"] == "qualitative":
        if n > spec["max_n"]:
            raise ValueError(f"{name} supports at most {spec['max_n']} categories; use facets or another scheme")
        result = colours[:n]
    else:
        indices = [len(colours) // 2] if n == 1 else np.floor(np.linspace(0, len(colours) - 1, n) + 0.5).astype(int)
        result = [colours[index] for index in indices]
    return result[::-1] if reverse else result


def dongfang_cmap(name="qingci", reverse=False):
    spec = registry()["palettes"].get(name)
    if spec is None or spec["type"] == "qualitative":
        raise ValueError("A continuous cmap requires qingci, qinglan, qingzhu or moyun")
    cmap = ListedColormap(dongfang_palette(name, reverse=reverse), name=f"dongfang_{name}")
    cmap.set_bad(registry()["neutrals"]["missing"])
    return cmap
