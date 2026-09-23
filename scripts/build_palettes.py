"""Build the offline palette registry from pinned sources; never execute remote code.

Maintainer-only. First collection needs --fetch; later builds reuse --cache.
Runtime getters have no network or ggsci installation dependency.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GGSCI_COMMIT = "37b74f85e62680b9d4523b0b4c0d9bfa0403d299"
GGSCI_BASE = f"https://raw.githubusercontent.com/nanxstats/ggsci/{GGSCI_COMMIT}"

GGSCI_FAMILY_LABELS = {
    "npg": "NPG", "aaas": "AAAS", "nejm": "NEJM", "jama": "JAMA", "bmj": "BMJ", "jco": "JCO",
    "ucscgb": "UCSCGB", "d3": "D3", "igv": "IGV", "uchicago": "UChicago", "cosmic": "COSMIC",
    "gsea": "GSEA", "bs5": "BS5", "tw3": "TW3", "rickandmorty": "R&M", "startrek": "Star Trek",
    "flatui": "Flat UI", "locuszoom": "LocusZoom",
}
GGSCI_VARIANT_LABELS = {
    "nrc": "NRC", "lanonc": "Oncol.", "category10": "Cat 10", "category20": "Cat 20",
    "category20b": "Cat 20B", "category20c": "Cat 20C", "observable10": "10", "mark17": "Mark 17",
    "categorical8": "Cat 8", "alternating": "Alt", "signature_substitutions": "Sig. Subs.",
}


def title_words(value):
    aliases = {"aaas": "AAAS", "npg": "NPG", "nejm": "NEJM", "jama": "JAMA", "bmj": "BMJ",
               "jco": "JCO", "ucscgb": "UCSCGB", "d3": "D3", "igv": "IGV", "cosmic": "COSMIC",
               "gsea": "GSEA", "bs5": "BS5", "tw3": "TW3", "iterm2": "iTerm2", "hc": "HC", "cvd": "CVD"}
    words = re.split(r"[_\s-]+", value.strip())
    return " ".join(aliases.get(word.lower(), word[:1].upper() + word[1:]) for word in words if word)


def compact_palette_label(palette):
    """Keep catalogue titles short; retain the previous full label separately."""
    palette_id = palette["id"]
    family = palette["family"]
    full = palette.get("label_full", palette.get("label", ""))
    parts = palette_id.split(".")

    if family == "ggsci" and "extension" in palette.get("tags", []):
        raw = full.removeprefix("iTerm / ").split(" / ")
        if len(raw) >= 2:
            theme = raw[0].replace("Higher Contrast", "HC").replace("High Contrast", "HC")
            theme = theme.replace("Medium Contrast", "MC").replace("Dark Background", "Dark")
            theme = theme.replace("Light Background", "Light").replace("Deuteranopia", "Deut.")
            variant = {"normal": "N", "bright": "B"}.get(raw[-1].lower(), title_words(raw[-1]))
            return f"{theme} · {variant}"
        return full
    if family == "ggsci" and len(parts) >= 3:
        source, variant = parts[1], ".".join(parts[2:])
        name = GGSCI_FAMILY_LABELS.get(source, title_words(source))
        variant = GGSCI_VARIANT_LABELS.get(variant, "" if variant == "default" else title_words(variant))
        return f"{name} · {variant}" if variant else name
    if family == "brewer":
        return full
    if family == "viridis" and len(parts) > 1:
        return title_words(parts[-1])
    if family == "colorspace" and len(parts) > 1:
        names = {"green_brown": "Green–Brown", "blue_red3": "Blue–Red 3", "blues3": "Blues 3",
                 "ylgnbu": "YlGnBu", "set2": "Set 2", "dark3": "Dark 3"}
        return names.get(parts[-1], title_words(parts[-1]))
    if family == "cetcolor" and len(parts) > 1:
        return "KRYW Legacy" if parts[-1].startswith("linear_kryw_") else parts[-1].upper()
    if family == "matplotlib" and len(parts) > 1:
        name = parts[-1]
        return {"bwr": "BWR", "tab10": "Tab10", "tab20": "Tab20", "tab20b": "Tab20b",
                "tab20c": "Tab20c"}.get(name, title_words(name))
    if family == "tol":
        return title_words(parts[-1])
    if family == "cud":
        return "Okabe–Ito"
    if family == "china":
        return full.replace("·分级原色", " · 分级").replace("·原色", "")
    if family == "dongfang":
        return full.replace(" / classic-derived", " · 衍生")
    if family == "scico":
        name = full.removeprefix("Scientific colour maps / ")
        if name.endswith("_discrete"):
            name = name.removesuffix("_discrete") + " · 离散"
        return name[:1].upper() + name[1:]
    if family == "cmocean":
        name = full.removeprefix("cmocean / ")
        if name.endswith("_i"):
            name = name.removesuffix("_i") + " · 反转"
        return name[:1].upper() + name[1:]
    return full


def fetch(cache, name, url, enabled):
    path = cache / name
    if not path.exists():
        if not enabled:
            raise FileNotFoundError(f"Missing cached source {path}; use --fetch for explicit collection")
        with urlopen(Request(url, headers={"User-Agent": "EasyPlot-palette-builder/1.0"}), timeout=40) as response:
            data = response.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return path.read_text(encoding="utf-8-sig")


def parse_ggsci(text, iterm=False):
    # Restrict extraction to literal named colour-vector assignments.
    db = "ggsci_db_iterm" if iterm else "ggsci_db"
    pattern = rf'{db}\$"([^"\n]+)"\$"([^"\n]+)"\s*<-\s*c\((.*?)\n\)'
    records = []
    matches = list(re.finditer(pattern, text, re.S))
    expected = len(re.findall(rf'^{db}\$"[^"\n]+"\$"', text, re.M))
    non_tables = re.findall(rf'^{db}\$"([^"\n]+)"\s*<-', text, re.M)
    if set(non_tables) - {"gephi"}:
        raise ValueError(f"Unknown non-table palette assignments: {non_tables}")
    if not matches or len(matches) != expected:
        raise ValueError(f"Unparsed {db} assignments: {len(matches)} of {expected}")
    for match in matches:
        family, variant, body = match.groups()
        pairs = re.findall(r'"([^"\n]*)"\s*=\s*"(#[\da-fA-F]{6})"', body)
        if len(pairs) != len(re.findall(r'#[\da-fA-F]{6}', body)) or not pairs:
            raise ValueError(f"Unexpected colour literal grammar in {family}/{variant}")
        if iterm:
            # URL-style percent encoding is deterministic and collision-free for theme names.
            from urllib.parse import quote
            pid = f"ggsci.iterm.{quote(family, safe='-_')}.{variant}"
            label = f"iTerm / {family} / {variant}"
            kind, tags = "qualitative", ["extension", "terminal-theme"]
        else:
            pid, label = f"ggsci.{family}.{variant}", f"{family} ({variant})"
            kind = "diverging" if family == "gsea" else "sequential" if family in {"bs5", "material", "tw3"} else "qualitative"
            tags = ["original", "ggsci"]
            if family in {"bs5", "material", "tw3", "flatui"}:
                tags.append("design-system")
        records.append(dict(
            id=pid, label=label, family="ggsci", kind=kind,
            colours=[colour.upper() for _, colour in pairs], colour_names=[name for name, _ in pairs],
            selection="prefix" if kind == "qualitative" else "lut", tags=tags,
            cvd=dict(status="not_assessed", evidence="https://nanx.me/ggsci/articles/ggsci.html",
                     note="No blanket colour-vision guarantee from journal/theme names; inspect rendered marks."),
            source=dict(url=f"{GGSCI_BASE}/R/{'palettes-iterm.R' if iterm else 'palettes.R'}",
                        version=f"5.2.0 / {GGSCI_COMMIT}", license="GPL-3.0-or-later"),
            upstream_call=f'ggsci::pal_iterm("{family}", variant = "{variant}")' if iterm else f'ggsci::pal_{family}("{variant}")',
        ))
    return records


def write_new_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--rscript", required=True)
    parser.add_argument("--extra", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "assets/palettes.json")
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing overwrite: {args.output}")
    args.cache.mkdir(parents=True, exist_ok=True)
    source_text = fetch(args.cache, "ggsci-palettes.R", f"{GGSCI_BASE}/R/palettes.R", args.fetch)
    iterm_text = fetch(args.cache, "ggsci-palettes-iterm.R", f"{GGSCI_BASE}/R/palettes-iterm.R", args.fetch)
    license_text = fetch(args.cache, "ggsci-LICENSE.md", f"{GGSCI_BASE}/LICENSE.md", args.fetch)
    fetch(args.cache, "ggsci-DESCRIPTION", f"{GGSCI_BASE}/DESCRIPTION", args.fetch)
    for family in ("gsea", "material", "bs5", "tw3"):
        fetch(args.cache, f"ggsci-continuous-{family}.R", f"{GGSCI_BASE}/R/continuous-{family}.R", args.fetch)
    core = parse_ggsci(source_text)
    extensions = parse_ggsci(iterm_text, iterm=True)
    # Cached R output may be reused only when its parsed input is identical.
    input_path, r_output = args.cache / "ggsci-core-input.json", args.cache / "r-palettes.json"
    if input_path.exists():
        if json.loads(input_path.read_text(encoding="utf-8")) != core:
            raise ValueError("Cached R input changed; use a fresh cache directory")
    else:
        write_new_json(input_path, core)
    if not r_output.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts/easyplot_run_r.py"),
                        "--rscript", args.rscript, str(ROOT / "scripts/build_palette_sources.R"),
                        str(input_path), str(r_output)], check=True)
    palettes = json.loads(r_output.read_text(encoding="utf-8")) + extensions

    # Freeze CET tables and source-level class-count metadata separately; this
    # keeps the ordinary rebuild reproducible without installing cetcolor.
    cvd_source = json.loads((ROOT / "assets/cvd-source-data.json").read_text(encoding="utf-8"))
    brewer_cvd = cvd_source["brewer"]
    for palette in palettes:
        if palette["id"].startswith("brewer."):
            entry = brewer_cvd.get(palette["id"])
            if entry is None or set(entry["by_n"]) != set(palette.get("native_sizes", {})):
                raise ValueError(f"ColorBrewer CVD n-class metadata mismatch: {palette['id']}")
            palette["cvd"] = dict(status=entry["status"], by_n=entry["by_n"],
                evidence=entry["evidence"], note="ColorBrewer browser metadata is specific to native class count. See cvd.by_n; unlisted sizes remain unassessed.")
            palette["tags"].append("cvd-n-dependent")
            if any(status in {"reported", "conditional"} for status in entry["by_n"].values()):
                palette["tags"].append("cvd-shortlist")
        elif palette["family"] == "viridis" and palette["cvd"]["status"] == "reported":
            palette["tags"].append("cvd-shortlist")
    palettes.extend(cvd_source["palettes"])

    import matplotlib
    from matplotlib import colormaps
    from matplotlib.colors import to_hex
    for name in ("tab10", "tab20", "tab20b", "tab20c"):
        values = [to_hex(c).upper() for c in colormaps[name].colors]
        palettes.append(dict(id=f"matplotlib.{name}", label=name, family="matplotlib", kind="qualitative",
            colours=values, selection="prefix", tags=["classic"],
            cvd=dict(status="not_assessed", evidence="https://matplotlib.org/stable/users/explain/colors/colormaps.html", note="No blanket CVD guarantee."),
            source=dict(url="https://matplotlib.org/stable/users/explain/colors/colormaps.html", version=matplotlib.__version__, license="Matplotlib license")))
    for name, kind in (("coolwarm", "diverging"), ("bwr", "diverging"), ("seismic", "diverging"),
                       ("twilight", "cyclic"), ("twilight_shifted", "cyclic"), ("terrain", "multisequential")):
        cmap = colormaps[name]
        values = [to_hex(cmap(i / 256)).upper() for i in range(257)]
        palettes.append(dict(id=f"matplotlib.{name}", label=name, family="matplotlib", kind=kind,
            colours=values, selection="lut", tags=["classic"],
            cvd=dict(status="not_assessed", evidence="https://matplotlib.org/stable/users/explain/colors/colormaps.html", note="Cyclic/topographic/diverging semantics need task-specific limits; no CVD claim."),
            source=dict(url="https://matplotlib.org/stable/users/explain/colors/colormaps.html", version=matplotlib.__version__, license="Matplotlib license")))

    dongfang = json.loads((ROOT / "assets/dongfang.json").read_text(encoding="utf-8"))
    # Verify that every stored original swatch still matches the current public cards.
    page = fetch(args.cache, "2kil.html", "https://www.2kil.com/", args.fetch)
    from build_dongfang import extract_source
    current = {row["name"]: row["hex"] for row in extract_source(page)}
    originals = {row["name"]: row["hex"] for row in dongfang["source_colours"]}
    if current != originals:
        raise ValueError("2kil originals differ from the existing snapshot; review instead of silently changing colours")
    for name, spec in dongfang["palettes"].items():
        palettes.append(dict(id=f"dongfang.{name}", label=f'{spec["label"]} / classic-derived', family="dongfang", kind=spec["type"],
            colours=spec["fill"], selection="prefix" if spec["type"] == "qualitative" else "lut", tags=["derived", "candidate"],
            cvd=dict(status="not_assessed", evidence="", note="EasyPlot classic-based edits; not original 2kil swatches or CVD certification."),
            source=dict(url="https://www.2kil.com/", version=dongfang["version"], license="Local trial; source dataset redistribution terms not located"),
            notes="Legacy classic-derived candidate retained unchanged; use china.* for unmodified source-colour combinations."))
    recipes = json.loads((ROOT / "assets/china-palette-recipes.json").read_text(encoding="utf-8"))
    for recipe in recipes["palettes"]:
        values = [originals[name] for name in recipe["names"]]
        if len(values) != len(set(values)):
            raise ValueError(f"Repeated colour within {recipe['id']}")
        palettes.append(dict(id=recipe["id"], label=recipe["label"], family="china", kind=recipe["kind"],
            colours=values, colour_names=recipe["names"], selection="prefix" if recipe["kind"] == "qualitative" else "lut",
            tags=["2kil-original-colours", "easyplot-curated", "candidate", "stepped" if recipe["kind"] != "qualitative" else "categorical"],
            cvd=dict(status="not_assessed", evidence="https://www.2kil.com/", note="Source-faithful curation; no CVD claim. Use group labels/markers/linetypes."),
            source=dict(url="https://www.2kil.com/", version=recipes["version"], license="Local trial; source dataset redistribution terms not located"),
            notes=recipe["reference"] + "; names/combinations curated by EasyPlot, all HEX unchanged from 2kil."))

    sources = [dict(name="ggsci", version=f"5.2.0 / {GGSCI_COMMIT}", url="https://nanx.me/ggsci/",
                    attribution="Nan Xiao and ggsci contributors; iTerm2-Color-Schemes contributors", license="GPL-3.0-or-later"),
               dict(name="2kil / 东方色", url="https://www.2kil.com/", attribution="Frank Lin, site footer copyright 2020",
                    license="No explicit dataset redistribution terms found; local use preview only"),
               dict(name="ColorBrewer", url="https://colorbrewer2.org/", attribution="This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/).", license="See assets/colorbrewer-LICENSE.txt"),
               dict(name="viridisLite", url="https://sjmgarnier.github.io/viridisLite/", license="MIT"),
               dict(name="Matplotlib", url="https://matplotlib.org/", version=matplotlib.__version__, license="Matplotlib license")]
    sources += cvd_source["sources"]
    if args.extra:
        extra = json.loads(args.extra.read_text(encoding="utf-8"))
        palettes += extra["palettes"]
        sources += extra["sources"]
    for palette in palettes:
        if palette.get("cvd", {}).get("status") in {"reported", "conditional"}:
            tags = palette.setdefault("tags", [])
            if "cvd-shortlist" not in tags:
                tags.append("cvd-shortlist")
        previous_label = palette.get("label_full", palette.get("label", ""))
        display_label = compact_palette_label(palette)
        if display_label != previous_label:
            palette["label_full"] = previous_label
        else:
            palette.pop("label_full", None)
        palette["label"] = display_label
    ids = [p["id"] for p in palettes]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate palette IDs")
    for p in palettes:
        if not p["colours"] or any(not re.fullmatch(r"#[0-9A-F]{6}", c) for c in p["colours"]):
            raise ValueError(f"Invalid colour table: {p['id']}")
    result = dict(schema_version=1, version="1.2.0", built_utc=datetime.now(timezone.utc).isoformat(),
        palettes=palettes, sources=sources,
        omissions=["ggsci Gephi is a generative algorithm with RNG/number-of-colours parameters, not a fixed colour table; no frozen arbitrary-seed set is presented as the original palette.",
                   "No claim to include every palette from every scientific package. See source/version and family counts for the actual snapshot."],
        coverage=dict(total=len(palettes), families=dict(Counter(p["family"] for p in palettes)),
                      ggsci_fixed_core=len(core), ggsci_iterm_extensions=len(extensions), china_original_schemes=len(recipes["palettes"])))
    write_new_json(args.output, result)
    # Keep attribution/license locally with the frozen imported data.
    license_dir = ROOT / "assets/palette-licenses"
    license_dir.mkdir(parents=True, exist_ok=True)
    license_path = license_dir / "ggsci-GPL-3.0.md"
    if not license_path.exists():
        with license_path.open("x", encoding="utf-8") as stream:
            stream.write(license_text)
    print(json.dumps(result["coverage"], ensure_ascii=False))


if __name__ == "__main__":
    main()
