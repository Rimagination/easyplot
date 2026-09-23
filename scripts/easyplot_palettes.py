"""Unified EasyPlot palettes from the frozen ../assets/palettes.json registry.

IDs and filters are exact and case-sensitive, including percent-encoded IDs.
The three base getters use only the standard library and never access a network.
The registry is a process-local snapshot, read on the first getter call.

Selection rules:
* n=None returns all stored colours, for every selection policy.
* prefix takes the first n colours and refuses requests beyond capacity.
* native uses the stored scheme of exactly n colours. For n=1 or 2, take the
  first n colours of the smallest stored scheme. Missing sizes are errors.
* lut samples stored entries, without interpolation: n=1 uses zero-based
  floor((length-1)/2 + 0.5); n>=2 uses floor(i*(length-1)/(n-1) + 0.5).
  Both endpoints are included. Up to 65536 samples are allowed; requesting more
  samples than stored entries repeats colours and adds no colour precision.
reverse reverses the selected subset in all cases.

Use explicit group-to-colour mappings for qualitative data. easyplot_cmap lazily
imports Matplotlib and sets missing values to #E2E2E2. Declare normalization and
limits explicitly for continuous data, including a meaningful diverging centre.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from math import floor
from numbers import Integral
from pathlib import Path
import re

__all__ = ["easyplot_palettes", "easyplot_palette_info", "easyplot_palette", "easyplot_cmap"]
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "assets" / "palettes.json"


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _check_colours(colours, context):
    if not isinstance(colours, list) or not colours or any(
        not isinstance(colour, str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", colour) is None
        for colour in colours
    ):
        raise ValueError(f"Invalid #RRGGBB colours in {context}")


@lru_cache(maxsize=1)
def _registry():
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported palette registry schema_version; expected 1")
    if not isinstance(data.get("palettes"), list):
        raise ValueError("Palette registry palettes must be an array")
    records = {}
    for record in data["palettes"]:
        if not isinstance(record, dict) or any(not _text(record.get(key)) for key in ("id", "label", "family")):
            raise ValueError("Each palette needs a nonempty id, label and family")
        id = record["id"]
        if id in records:
            raise ValueError(f"Duplicate palette id: {id!r}")
        if record.get("kind") not in ("qualitative", "sequential", "diverging", "cyclic", "multisequential"):
            raise ValueError(f"Invalid palette kind for {id!r}")
        if record.get("selection") not in ("prefix", "native", "lut"):
            raise ValueError(f"Invalid palette selection for {id!r}")
        _check_colours(record.get("colours"), id)
        cvd = record.get("cvd")
        if not isinstance(cvd, dict) or cvd.get("status") not in ("reported", "conditional", "not_assessed", "not_recommended"):
            raise ValueError(f"Invalid cvd status for {id!r}")
        if any(not isinstance(cvd.get(key), str) for key in ("evidence", "note")):
            raise ValueError(f"Missing cvd evidence or note for {id!r}")
        if record["selection"] == "native":
            schemes = record.get("native_sizes")
            if not isinstance(schemes, dict) or not schemes:
                raise ValueError(f"Missing stored native sizes for {id!r}")
            for size, colours in schemes.items():
                _check_colours(colours, f"{id} native size {size}")
                if re.fullmatch(r"[1-9][0-9]*", size) is None or len(colours) != int(size):
                    raise ValueError(f"Invalid stored native size {size!r} for {id!r}")
        records[id] = record
    return records


def _record(id):
    if not _text(id) or id not in _registry():
        raise ValueError(f"Unknown palette id: {id!r}; use easyplot_palettes() for exact IDs")
    return _registry()[id]


def _capacity(record):
    if record["selection"] == "lut":
        return 65536
    if record["selection"] == "native":
        return max(map(int, record["native_sizes"]))
    return len(record["colours"])


@lru_cache(maxsize=1)
def _metadata():
    return [dict(
        **{key: record[key] for key in ("id", "label", "family", "kind", "selection")},
        n_colours=len(record["colours"]), max_n=_capacity(record),
        cvd_status=record["cvd"]["status"], cvd_evidence=record["cvd"]["evidence"],
        cvd_note=record["cvd"]["note"],
    ) for record in _registry().values()]


def easyplot_palettes(family=None, kind=None, cvd=None):
    """Return metadata dictionaries in registry order, with exact scalar filters.

    cvd filters a status string, not a boolean safety claim. Unknown strings match
    no records. Columns match the R data.frame: id, label, family, kind, selection,
    n_colours, max_n, cvd_status, cvd_evidence, cvd_note. max_n is the largest
    explicit request; native sizes can have gaps. Full provenance, tags and
    optional fields are available through easyplot_palette_info().
    """
    for key, value in (("family", family), ("kind", kind), ("cvd", cvd)):
        if value is not None and not _text(value):
            raise ValueError(f"{key} must be a nonempty string or None")
    return [dict(row) for row in _metadata()
            if (family is None or row["family"] == family)
            and (kind is None or row["kind"] == kind)
            and (cvd is None or row["cvd_status"] == cvd)]


def easyplot_palette_info(id):
    """Return a full defensive copy of a record, including provenance and notes."""
    return deepcopy(_record(id))


def easyplot_palette(id, n=None, reverse=False):
    """Return fresh colours using the selection rules in this module's docstring.

    n must be a positive Integral (bool and floats are rejected); reverse must
    be a Python bool. No aliases, ID decoding, recycling or interpolation occurs.
    LUT resampling may repeat stored colours, with no added precision.
    """
    record = _record(id)
    if type(reverse) is not bool:
        raise ValueError("reverse must be a boolean")
    if n is not None and (isinstance(n, bool) or not isinstance(n, Integral) or n < 1):
        raise ValueError("n must be a positive integer")
    colours = record["colours"]
    if n is None:
        result = list(colours)
    else:
        n = int(n)
        capacity = _capacity(record)
        if n > capacity:
            raise ValueError(f"{id} supports at most {capacity} requested colours")
        if record["selection"] == "prefix":
            result = colours[:n]
        elif record["selection"] == "native":
            schemes = record["native_sizes"]
            size = str(min(map(int, schemes))) if n < 3 else str(n)
            if size not in schemes or len(schemes[size]) < n:
                raise ValueError(f"No stored native size {n} for {id}; available sizes: {', '.join(schemes)}")
            result = schemes[size][:n]
        else:
            indices = [len(colours) // 2] if n == 1 else [
                floor(i * (len(colours) - 1) / (n - 1) + 0.5) for i in range(n)
            ]
            result = [colours[index] for index in indices]
    return result[::-1] if reverse else result


def easyplot_cmap(id, reverse=False):
    """Return a lazy Matplotlib ListedColormap; qualitative palettes are refused."""
    if _record(id)["kind"] == "qualitative":
        raise ValueError("A continuous cmap cannot use a qualitative palette")
    colours = easyplot_palette(id, reverse=reverse)
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(colours, name=f"easyplot_{id}" + ("_r" if reverse else ""))
    cmap.set_bad("#E2E2E2")
    return cmap
