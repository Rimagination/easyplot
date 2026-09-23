"""Contracts: python -B test_easyplot_palettes.py [output-dir] [--real | --registry PATH].

Fixtures live in an isolated temporary installation; installed assets are never
modified. --real additionally checks ../assets/palettes.json; --registry checks a
staged JSON file in a temporary installation. An output directory requests
python_palette_parity.csv for the selected registry, or the fixture by default.
"""
from __future__ import annotations

import argparse
import builtins
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent


def fixture_registry():
    def record(id, colours, selection="prefix", kind="qualitative", **extra):
        return dict(
            id=id, label=id, family=id.split(".")[0], kind=kind,
            colours=colours, selection=selection,
            cvd=dict(status="not_assessed", evidence="https://example.invalid/fixture",
                     note="Synthetic test fixture; no accessibility claim."),
            source=dict(url="https://example.invalid/fixture", version="test-1", license="fixture"),
            tags=["fixture"], **extra,
        )

    set2 = ["#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3"]
    blues3 = ["#DEEBF7", "#9ECAE1", "#3182BD"]
    blues5 = ["#EFF3FF", "#BDD7E7", "#6BAED6", "#3182BD", "#08519C"]
    records = [
        record("ggsci.npg.nrc", ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
                                 "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"]),
        record("brewer.Set2", set2, "native", native_sizes={"3": set2[:3], "4": set2[:4], "8": set2}),
        record("brewer.Blues", blues5, "native", "sequential", native_sizes={"3": blues3, "5": blues5}),
        record("viridis.viridis", ["#440154", "#31688E", "#35B779", "#FDE725"], "lut", "sequential"),
        record("test.odd", ["#111111", "#333333", "#777777", "#BBBBBB", "#EEEEEE"], "lut", "diverging"),
        record("test.single", ["#112233"], "lut", "cyclic"),
        record("test.multi", ["#111122", "#222244", "#333366"], "lut", "multisequential"),
        record("cud.okabe_ito", ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]),
        record("china.jiangnan", ["#123456", "#789ABC"], colour_names=["青", "绿"], notes="Synthetic colours."),
        record("dongfang.qingya", ["#654321", "#CBA987"]),
        record("ggsci.iterm.Ocean%20%28Night%29.dark", ["#123123", "#456456"]),
        record("china.stepped", ["#123456", "#234567", "#345678", "#456789", "#56789A", "#6789AB", "#789ABC"], "lut", "sequential"),
    ]
    records[3]["cvd"]["status"] = "conditional"
    records[4]["cvd"]["status"] = "not_recommended"
    records[7]["cvd"]["status"] = "reported"
    records[8]["label"] = "江南（测试）"
    records[10]["tags"].append("extension")
    return dict(schema_version=1, version="1.0.0", palettes=records, sources=[], omissions=[])


def load_api(path):
    spec = importlib.util.spec_from_file_location("palette_api_under_test", path)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api


def expect_error(call, pattern):
    try:
        call()
    except ValueError as error:
        assert pattern.lower() in str(error).lower(), (pattern, str(error))
    else:
        raise AssertionError(f"Expected ValueError containing {pattern!r}")


def sample_sizes(record):
    if record["selection"] == "prefix":
        return list(range(1, len(record["colours"]) + 1))
    if record["selection"] == "native":
        return sorted({1, 2, *(int(n) for n in record["native_sizes"])})
    size = len(record["colours"])
    return sorted({1, 2, 3, 4, 5, 7, 17, size, min(size + 1, 65536), min(2 * size - 1, 65536)})


def check_registry(api, registry):
    records = registry["palettes"]
    palette, info, catalogue = api.easyplot_palette, api.easyplot_palette_info, api.easyplot_palettes
    metadata = catalogue()
    assert isinstance(metadata, list)
    assert [row["id"] for row in metadata] == [record["id"] for record in records]
    assert len({record["id"] for record in records}) == len(records)
    assert palette("ggsci.npg.nrc", 1) == ["#E64B35"]
    assert palette("brewer.Set2", 3) == ["#66C2A5", "#FC8D62", "#8DA0CB"]
    assert catalogue(family="no-such-family") == []
    assert catalogue(kind="no-such-kind") == []
    assert catalogue(cvd="no-such-status") == []
    for field in ("family", "kind", "cvd"):
        for bad in (True, 1, [], ["brewer"], {}, "", "  "):
            expect_error(lambda: catalogue(**{field: bad}), field)
        key = "cvd_status" if field == "cvd" else field
        for value in {row[key] for row in metadata}:
            assert catalogue(**{field: value}) == [row for row in metadata if row[key] == value]
    for family, kind, cvd in {(row["family"], row["kind"], row["cvd_status"]) for row in metadata}:
        assert catalogue(family=family, kind=kind, cvd=cvd) == [
            row for row in metadata if (row["family"], row["kind"], row["cvd_status"]) == (family, kind, cvd)
        ]

    for record, meta in zip(records, metadata):
        id, full = record["id"], record["colours"]
        assert info(id) == record, id
        assert palette(id) == full, id
        assert palette(id, reverse=True) == full[::-1], id
        assert meta["n_colours"] == len(full)
        assert meta["selection"] == record["selection"]
        assert meta["cvd_status"] == record["cvd"]["status"]
        assert meta["cvd_note"] == record["cvd"]["note"]
        for n in sample_sizes(record):
            colours = palette(id, n)
            assert len(colours) == n
            assert palette(id, n, reverse=True) == colours[::-1]
            if record["selection"] == "prefix":
                assert colours == full[:n]
            elif record["selection"] == "native":
                schemes = record["native_sizes"]
                expected = schemes[str(min(map(int, schemes)))][:n] if n < 3 else schemes[str(n)]
                assert colours == expected, (id, n)
            else:
                # Integer arithmetic is an independent oracle for half-up rounding.
                indices = [len(full) // 2] if n == 1 else [
                    (2 * i * (len(full) - 1) + n - 1) // (2 * (n - 1)) for i in range(n)
                ]
                assert colours == [full[i] for i in indices], (id, n)
                if n >= 2:
                    assert colours[0] == full[0] and colours[-1] == full[-1]
        if record["selection"] == "lut":
            assert meta["max_n"] == 65536
            expect_error(lambda: palette(id, 65537), "65536")
        else:
            capacity = max(map(int, record["native_sizes"])) if record["selection"] == "native" else len(full)
            assert meta["max_n"] == capacity
            expect_error(lambda: palette(id, capacity + 1), "at most")
            if record["selection"] == "native":
                for missing in set(range(3, capacity)) - set(map(int, record["native_sizes"])):
                    expect_error(lambda: palette(id, missing), "stored")
        # Validate every policy, including defaults for reverse and exact ID case.
        for bad in (0, -1, 1.5, 2.0, True, False, float("nan"), float("inf"), -float("inf"), "2", [], [2], 1j):
            expect_error(lambda: palette(id, bad), "positive integer")
        for bad in (None, 0, 1, "true", [], [True], float("nan")):
            expect_error(lambda: palette(id, reverse=bad), "reverse")
        assert full and all(isinstance(c, str) and len(c) == 7 and c.startswith("#") for c in full)

    for bad in (None, "", " ", "npg", "ggsci.NPG.nrc", "brewer.set2", "brewer.Set2 ", "unknown", 1, True, [], {}):
        expect_error(lambda: info(bad), "id")
        expect_error(lambda: palette(bad), "id")
    changed = info("brewer.Set2")
    changed["colours"][0] = "#FFFFFF"
    changed["native_sizes"]["3"][0] = "#FFFFFF"
    changed["cvd"]["status"] = "not_recommended"
    changed["source"]["url"] = "changed"
    changed["tags"].append("changed")
    metadata[0]["label"] = "changed"
    returned = palette("ggsci.npg.nrc")
    returned[0] = "#FFFFFF"
    assert info("brewer.Set2") == next(r for r in records if r["id"] == "brewer.Set2")
    assert catalogue()[0]["label"] == records[0]["label"]
    assert palette("ggsci.npg.nrc", 1) == ["#E64B35"]


def check_fixture_edges(api):
    palette = api.easyplot_palette
    assert palette("brewer.Blues", 3) == ["#DEEBF7", "#9ECAE1", "#3182BD"]
    assert palette("brewer.Blues", 3) != palette("brewer.Blues")[:3]
    assert palette("brewer.Blues", 2) == ["#DEEBF7", "#9ECAE1"]
    assert palette("brewer.Blues", 2, reverse=True) == ["#9ECAE1", "#DEEBF7"]
    assert palette("viridis.viridis", 1) == ["#35B779"]
    assert palette("viridis.viridis", 3) == ["#440154", "#35B779", "#FDE725"]
    assert palette("test.odd", 1) == ["#777777"]
    assert palette("test.odd", 9) == ["#111111", "#333333", "#333333", "#777777", "#777777",
                                      "#BBBBBB", "#BBBBBB", "#EEEEEE", "#EEEEEE"]
    assert palette("test.single", 3) == ["#112233"] * 3
    assert palette("ggsci.iterm.Ocean%20%28Night%29.dark", 1) == ["#123123"]
    expect_error(lambda: palette("ggsci.iterm.Ocean (Night).dark"), "id")
    assert "extension" in api.easyplot_palette_info("ggsci.iterm.Ocean%20%28Night%29.dark")["tags"]
    assert set(palette("china.stepped", 17)) <= set(palette("china.stepped"))
    maximum = palette("viridis.viridis", 65536)
    assert len(maximum) == 65536 and maximum[0] == "#440154" and maximum[-1] == "#FDE725"
    assert set(maximum) == set(palette("viridis.viridis"))
    changed = api.easyplot_palette_info("china.jiangnan")
    changed["colour_names"][0] = "changed"
    assert api.easyplot_palette_info("china.jiangnan")["colour_names"] == ["青", "绿"]


def check_cmap(api):
    expect_error(lambda: api.easyplot_cmap("ggsci.npg.nrc"), "qualitative")
    expect_error(lambda: api.easyplot_cmap("viridis.viridis", reverse=1), "reverse")
    if importlib.util.find_spec("matplotlib") is None:
        print("Matplotlib unavailable: optional cmap rendering contract skipped.")
        return
    from matplotlib.colors import ListedColormap, to_hex
    for id in ("viridis.viridis", "test.odd", "test.single", "test.multi", "brewer.Blues"):
        cmap = api.easyplot_cmap(id)
        assert isinstance(cmap, ListedColormap)
        assert list(cmap.colors) == api.easyplot_palette(id)
        assert list(api.easyplot_cmap(id, reverse=True).colors) == api.easyplot_palette(id)[::-1]
        assert to_hex(cmap.get_bad()).upper() == "#E2E2E2"
        cmap.set_bad("#FFFFFF")
        assert to_hex(api.easyplot_cmap(id).get_bad()).upper() == "#E2E2E2"


def write_parity(api, registry, path):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "n", "reverse", "index", "colour"])
        for record in sorted(registry["palettes"], key=lambda r: r["id"]):
            for n in [None, *sample_sizes(record)]:
                for reverse in (False, True):
                    for index, colour in enumerate(api.easyplot_palette(record["id"], n, reverse), 1):
                        writer.writerow([record["id"], "default" if n is None else n, int(reverse), index, colour])


def main(output_dir=None, real=False, registry_path=None):
    runtime = SCRIPT_DIR / "easyplot_palettes.py"
    assert runtime.is_file(), f"Public API runtime is missing: {runtime}"
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="python-palette-", dir=output_dir) as temporary:
        root = Path(temporary)
        (root / "scripts").mkdir()
        (root / "assets").mkdir()
        fixture = fixture_registry()
        (root / "assets" / "palettes.json").write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        shutil.copyfile(runtime, root / "scripts" / runtime.name)
        original_import = builtins.__import__

        def stdlib_only(name, *args, **kwargs):
            if name.split(".")[0] in {"matplotlib", "numpy", "pandas", "seaborn"}:
                raise ImportError(f"Base palette getters must be stdlib-only: {name}")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = stdlib_only
        try:
            api = load_api(root / "scripts" / runtime.name)
            check_registry(api, fixture)
            check_fixture_edges(api)
        finally:
            builtins.__import__ = original_import
        check_cmap(api)
        print(f"Python fixture contracts passed: {len(fixture['palettes'])} palettes; stdlib-only getters and optional cmap.")
        if real:
            registry = json.loads((SCRIPT_DIR.parent / "assets" / "palettes.json").read_text(encoding="utf-8"))
            api = load_api(runtime)
            check_registry(api, registry)
            print(f"Python real-registry contracts passed: {len(registry['palettes'])} palettes.")
        elif registry_path is not None:
            shutil.copyfile(registry_path, root / "assets" / "palettes.json")
            registry = json.loads((root / "assets" / "palettes.json").read_text(encoding="utf-8"))
            api = load_api(root / "scripts" / runtime.name)
            check_registry(api, registry)
            print(f"Python staged-registry contracts passed: {len(registry['palettes'])} palettes.")
        else:
            registry = fixture
        if output_dir is not None:
            path = output_dir / "python_palette_parity.csv"
            write_parity(api, registry, path)
            print(path.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", nargs="?", type=Path)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--real", action="store_true")
    selection.add_argument("--registry", type=Path, help="Read a staged registry without editing installed assets")
    options = parser.parse_args()
    main(options.output_dir, options.real, options.registry)
