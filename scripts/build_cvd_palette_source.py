"""Freeze upstream CET tables and ColorBrewer's per-class colour-vision flags."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
CET_COMMIT = "c7e95748040f75f4aef364ad68413c439d590844"
CET_ROOT = f"cetcolor-{CET_COMMIT}/data-raw/CETperceptual_csv_0_1/"
CET_URL = f"https://github.com/coatless-rpkg/cetcolor/tree/{CET_COMMIT}/data-raw/CETperceptual_csv_0_1"
BREWER_URL = "https://colorbrewer2.org/colorbrewer_schemes.js"

CET_SPECS = (
    ("cbl1", "CET-CBL1.csv", "linear-protanopic-deuteranopic_kbjyw_5-95_c25_n256", "线性 · protan/deutan", ["protan", "deutan"], "sequential"),
    ("cbl2", "CET-CBL2.csv", "linear-protanopic-deuteranopic_kbw_5-98_c40_n256", "线性 · protan/deutan（高色度）", ["protan", "deutan"], "sequential"),
    ("cbd1", "CET-CBD1.csv", "diverging-protanopic-deuteranopic_bwy_60-95_c32_n256", "发散 · protan/deutan", ["protan", "deutan"], "diverging"),
    ("cbc1", "CET-CBC1.csv", "cyclic-protanopic-deuteranopic_bwyk_16-96_c31_n256", "循环 · protan/deutan（四相）", ["protan", "deutan"], "cyclic"),
    ("cbc2", "CET-CBC2.csv", "cyclic-protanopic-deuteranopic_wywb_55-96_c33_n256", "循环 · protan/deutan（两相）", ["protan", "deutan"], "cyclic"),
    ("cbtl1", "CET-CBTL1.csv", "linear-tritanopic_krjcw_5-98_c46_n256", "线性 · tritan", ["tritan"], "sequential"),
    ("cbtl2", "CET-CBTL2.csv", "linear-tritanopic_krjcw_5-95_c24_n256", "线性 · tritan（低色度）", ["tritan"], "sequential"),
    ("cbtd1", "CET-CBTD1.csv", "diverging-tritanopic_cwr_75-98_c20_n256", "发散 · tritan", ["tritan"], "diverging"),
    ("cbtc1", "CET-CBTC1.csv", "cyclic-tritanopic_cwrk_40-100_c20_n256", "循环 · tritan（四相）", ["tritan"], "cyclic"),
    ("cbtc2", "CET-CBTC2.csv", "cyclic-tritanopic_wrwc_70-100_c20_n256", "循环 · tritan（两相）", ["tritan"], "cyclic"),
    ("l3", "CET-L3.csv", "linear_kryw_0-100_c71_n256", "线性 · KRYW（现行短名）", [], "sequential"),
    ("linear_kryw_5_100_c67", "linear_kryw_5-100_c67_n256.csv", "linear_kryw_5-100_c67_n256", "用户示例（旧名）", [], "sequential"),
)


def find_object(text: str, name: str) -> str:
    start = re.search(rf"(?m)^\s*{re.escape(name)}\s*:\s*\{{", text)
    if not start:
        raise ValueError(f"ColorBrewer palette not found: {name}")
    opening = text.index("{", start.start())
    depth = 0
    quote = None
    escaped = False
    for pos in range(opening, len(text)):
        char = text[pos]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "\"'`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening:pos + 1]
    raise ValueError(f"Unclosed ColorBrewer record: {name}")


def brewer_class_flags(text: str, name: str, native_sizes: dict) -> dict:
    block = find_object(text, name)
    match = re.search(r"\bproperties\b['\"]?\s*:\s*\{[^}]*?\bblind\b['\"]?\s*:\s*\[([^]]*)\]", block, re.S)
    if not match:
        return {str(n): "not_assessed" for n in map(int, native_sizes)}
    raw = [int(value) for value in re.findall(r"\d+", match.group(1))]
    if not raw or any(value not in {0, 1, 2} for value in raw):
        raise ValueError(f"Unexpected ColorBrewer blind flags: {name}")
    by_n = {}
    for n in map(int, native_sizes):
        index = n - 3
        if len(raw) == 1:
            flag = raw[0]
        elif index < len(raw):
            flag = raw[index]
        else:
            by_n[str(n)] = "not_assessed"
            continue
        by_n[str(n)] = {0: "not_recommended", 1: "reported", 2: "conditional"}[flag]
    return by_n


def rgb_hex(csv_bytes: bytes) -> list[str]:
    colours = []
    for line_no, line in enumerate(csv_bytes.decode("ascii").splitlines(), 1):
        fields = line.split(",")
        if len(fields) != 3:
            raise ValueError(f"Malformed CET RGB at line {line_no}")
        channels = []
        for field in fields:
            value = float(field)
            if not 0 <= value <= 1:
                raise ValueError(f"CET channel outside [0, 1] at line {line_no}")
            channels.append(max(0, min(255, int(value * 255 + 0.5))))
        colours.append("#" + "".join(f"{channel:02X}" for channel in channels))
    if len(colours) != 256:
        raise ValueError(f"CET table must contain 256 colours; found {len(colours)}")
    return colours


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cet-archive", type=Path, required=True)
    parser.add_argument("--brewer-js", type=Path, required=True)
    parser.add_argument("--r-palettes", type=Path, required=True,
                        help="JSON exported by build_palette_sources.R, including its colorspace records")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing overwrite: {args.output}")
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    r_records = json.loads(args.r_palettes.read_text(encoding="utf-8"))
    r_by_id = {p["id"]: p for p in r_records}
    hcl = {f"colorspace.{name}" for name in ("blues3", "ylgnbu", "green_brown", "blue_red3", "set2", "dark3")}
    if not hcl <= r_by_id.keys():
        raise ValueError(f"R export lacks HCL records: {sorted(hcl - r_by_id.keys())}")
    existing = {p["id"] for p in registry["palettes"]}
    with ZipFile(args.cet_archive) as archive:
        broken = archive.testzip()
        if broken:
            raise ValueError(f"Corrupt CET archive member: {broken}")
        names = set(archive.namelist())
        cet_records = []
        for short, filename, official_name, description, targets, map_type in CET_SPECS:
            source_path = CET_ROOT + filename
            if source_path not in names or not source_path.startswith(CET_ROOT):
                raise ValueError(f"CET source table missing: {filename}")
            if short == "linear_kryw_5_100_c67":
                pid = "cetcolor.linear_kryw_5_100_c67"
                status = "not_assessed"
                tagset = ["legacy-deprecated"]
                cvd_note = "Legacy example requested by the user; cetcolor marks this long name deprecated. It has no CVD-specific claim. The current CET L3 shortname is available separately."
            elif targets:
                pid = f"cetcolor.{short}"
                status = "reported"
                tagset = ["cvd-shortlist", "cet-color-vision-map"]
                cvd_note = f"CET explicitly designs this map in the {', '.join(targets)} projected colour-vision space. This source design claim is not a guarantee for every observer or mark size."
            else:
                pid = f"cetcolor.{short}"
                status = "not_assessed"
                tagset = ["cet-legacy"]
                cvd_note = "General CET sequential map; the source does not label it as a dedicated colour-vision-deficiency map."
            if pid in existing:
                raise ValueError(f"CET palette ID already exists: {pid}")
            cet_records.append(dict(
                id=pid, label=f"{short} · {description}", family="cetcolor", kind=map_type,
                colours=rgb_hex(archive.read(source_path)), selection="lut",
                tags=tagset + [f"cvd-{target}" for target in targets], source_map_name=official_name,
                cvd=dict(status=status, targets=targets, evidence="https://colorcet.com/gallery.html",
                         note=cvd_note),
                source=dict(url=CET_URL, version=f"cetcolor 0.2.2 / commit {CET_COMMIT}; CET CSV tables 0.1",
                            license="Underlying table CC-BY-4.0; cetcolor data compilation CC-BY-SA-4.0"),
                notes=f"Source table: {filename}; 256 fixed entries. {description}."))

    # Keep the named legacy request searchable with and without upstream punctuation.
    cet_records[-1]["tags"].append("linear_kryw_5_100_c67_n256")
    brewer_text = args.brewer_js.read_text(encoding="utf-8-sig")
    brewer_records = [p for p in registry["palettes"] if p["id"].startswith("brewer.")]
    if len(brewer_records) != 35:
        raise ValueError(f"Expected all 35 installed ColorBrewer families; found {len(brewer_records)}")
    brewer = {}
    for record in brewer_records:
        name = record["id"].removeprefix("brewer.")
        by_n = brewer_class_flags(brewer_text, name, record.get("native_sizes", {}))
        observed = set(by_n.values())
        status = "reported" if observed == {"reported"} else \
                 "conditional" if observed & {"reported", "conditional"} else \
                 "not_assessed" if observed <= {"not_assessed"} else "not_recommended"
        brewer[record["id"]] = dict(by_n=by_n, status=status, evidence=BREWER_URL)

    source_data = dict(schema_version=1, upstream=dict(
        cetcolor=dict(version="0.2.2", commit=CET_COMMIT, csv_release="CETperceptual_csv_0_1", accessed="2026-09-23"),
        colorbrewer=dict(name="ColorBrewer 2", resource=BREWER_URL, accessed="2026-09-23")),
        palettes=cet_records, brewer=brewer,
        sources=[
            dict(name="colorspace HCL palettes", url="https://colorspace.r-forge.r-project.org/articles/hcl_palettes.html",
                 attribution="colorspace package authors", version="installed package version recorded per palette",
                 license="BSD-3-Clause; source package implementation is not copied"),
            dict(name="CET / cetcolor", url="https://colorcet.com/gallery.html",
                 attribution="Peter Kovesi; cetcolor R package by James Balamuta",
                 version=f"cetcolor 0.2.2 / {CET_COMMIT}",
                 license="Underlying colour-map tables CC-BY-4.0; cetcolor's compilation CC-BY-SA-4.0. See assets/palette-licenses/cetcolor-COPYRIGHTS.txt."),
            dict(name="ColorBrewer 2 CVD class metadata", url=BREWER_URL,
                 attribution="Cynthia Brewer, Mark Harrower and The Pennsylvania State University",
                 version="ColorBrewer 2; accessed 2026-09-23", license="Apache-style ColorBrewer license; see assets/colorbrewer-LICENSE.txt")
        ])
    payload = json.dumps(source_data, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    with args.output.open(mode, encoding="utf-8") as stream:
        stream.write(payload)
    print(json.dumps({"status": "source data frozen", "new_palettes": len(cet_records),
                      "CET_maps": len(CET_SPECS), "ColorBrewer_families": len(brewer)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
