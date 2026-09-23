"""Maintainer-only build of the opt-in Dongfang registry; network requires --fetch.

Uses the installed scikit-image only at build time. Runtime R/Python consume
the same frozen LUTs without a colour-science or network dependency.
"""
from __future__ import annotations

import argparse
import colorsys
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

import numpy as np
import matplotlib
from matplotlib import colormaps
from matplotlib.colors import to_hex, to_rgb
from skimage.color import rgb2lab, lab2rgb, deltaE_ciede2000
from easyplot_palette_audit import contrast_ratio, parse_hex
from easyplot_py import write_manifest

DEST = Path(__file__).resolve().parents[1] / "assets" / "dongfang.json"
URL = "https://www.2kil.com/"
# Explicit character aliases; source spellings and source pinyin remain untouched.
ALIASES = str.maketrans(dict(zip(
    "緑紅藍鳳硃銀龍鴨銅煙蓮駝棗絳紺紡絲麥鵝鶏艶獣鉄蔵徳羅牽蘇綿長淺黃楓葉琲瑪瑙樹織選庫獸雞烏寶棕",
    "绿红蓝凤朱银龙鸭铜烟莲驼枣绛绀纺丝麦鹅鸡艳兽铁藏德罗牵苏绵长浅黄枫叶琲玛瑙树织选库兽鸡乌宝棕",
)))


def extract_source(page):
    pattern = (r'<div class="card" style="border-color:\s*rgb\((?P<rgb>[^)]+)\);">'
               r'.*?<h4 class="card-title">(?P<name>[^<]+)</h4>(?P<cmyk>.*?)'
               r'<p class="card-text hex-value">(?P<hex>#[0-9A-Fa-f]{6})</p>'
               r'.*?<p class="card-text en-name">(?P<pinyin>[^<]+)</p>')
    rows = []
    for index, match in enumerate(re.finditer(pattern, page, re.S), 1):
        name = html.unescape(match['name']).strip()
        colour = match['hex'].upper()
        rgb = [int(value.strip()) for value in match['rgb'].split(',')]
        if rgb != [int(colour[pos:pos + 2], 16) for pos in (1, 3, 5)]:
            raise ValueError(f"Source card HEX/RGB disagreement: {name}")
        alias = name.translate(ALIASES)
        rows.append({"id": f"df{index:03d}", "name": name,
                     "aliases": [alias] if alias != name else [], "hex": colour,
                     "pinyin": html.unescape(match['pinyin']).strip(), "rgb": rgb,
                     "cmyk_display": [int(x) for x in re.findall(r'>(\d+)/100</span>', match['cmyk'])]})
    if len(rows) != 320 or len({row['name'] for row in rows}) != 320:
        raise ValueError(f"Source layout/count changed: {len(rows)} records; review before replacing snapshot")
    if any(len(row['cmyk_display']) != 4 for row in rows):
        raise ValueError("Source CMYK display parsing changed")
    return rows


def dark_stroke(colour):
    h, lightness, saturation = colorsys.rgb_to_hls(*to_rgb(colour))
    factor = 1.0
    candidate = colour
    while contrast_ratio(parse_hex(candidate), (1, 1, 1)) < 4.5:
        factor *= 0.97
        candidate = to_hex(colorsys.hls_to_rgb(h, lightness * factor, saturation)).upper()
    return candidate, {"source_hex": colour, "method": "HLS lightness scaling; white-background contrast >=4.5",
                       "lightness_factor": round(factor, 9), "derived": candidate != colour}


def tune_classic(colours, hue_shift, chroma_scale=.96):
    """Small LCh edits; preserve the classic lightness trajectory before quantization."""
    original = rgb2lab(np.array([to_rgb(value) for value in colours]))
    hue = np.arctan2(original[:, 2], original[:, 1]) + np.deg2rad(hue_shift)
    chroma = np.hypot(original[:, 1], original[:, 2]) * chroma_scale
    lab = original.copy()
    lab[:, 1], lab[:, 2] = chroma * np.cos(hue), chroma * np.sin(hue)
    # Back off toward the classic colour if the edit leaves sRGB. Saturated
    # yellows keep their classic character instead of becoming dull by clipping.
    for _ in range(160):
        rgb = lab2rgb(lab)
        clipped = np.linalg.norm(rgb2lab(rgb) - lab, axis=1) > .01
        if not clipped.any():
            break
        lab[clipped, 1:] = .9 * lab[clipped, 1:] + .1 * original[clipped, 1:]
    else:
        raise ValueError('Unable to place tuned colours in sRGB gamut')
    result = [to_hex(value).upper() for value in rgb]
    rounded = rgb2lab(np.array([to_rgb(value) for value in result]))
    delta = deltaE_ciede2000(original, rounded)
    metrics = {'max_delta_Lstar': float(np.max(abs(rounded[:, 0] - original[:, 0]))),
               'mean_delta_E00': float(delta.mean()), 'max_delta_E00': float(delta.max())}
    if metrics['max_delta_Lstar'] > .3 or metrics['max_delta_E00'] > 5:
        raise ValueError(f'Classic palette edit exceeded the small-adjustment budget: {metrics}')
    return result, metrics


def curate(rows):
    source = {row['name']: row['hex'] for row in rows}
    palettes = {}
    specs = [
        ("danqing", "丹青", "tab10", [0, 3, 1, 2, 4, 5],
         ["竹月色", "硃砂", "黄琉璃", "灰緑", "紫藤灰", "赭石色"],
         "保留 Tableau 10 的分类对比与亮度；向竹月、朱砂等方向微调色相，降低 4% 彩度。", "通用分类；曲线与散点配点形或线型"),
        ("qingya", "清雅", "Set2", [2, 3, 1, 0, 4, 5],
         ["銀藍", "粉鳳仙", "肉黄", "奶緑", "嫩草緑", "黄琉璃"],
         "以 Set2 的柔和多色关系为底，向银蓝、粉凤仙、肉黄、奶绿等方向小幅偏移。", "条形、箱线、小提琴；密集小点使用较深线色"),
        ("qiushan", "秋山", "Dark2", [1, 5, 0, 4, 2],
         ["赭石色", "黄琉璃", "玉石藍", "嫩草緑", "紫藤灰"],
         "沿用 Dark2 的深色分类结构，暖橙与琉璃黄作前两色，冷青与草绿保持对照。", "生态与环境分组；类别色，不表达连续数值"),
    ]
    for key, label, classic, indices, names, rationale, uses in specs:
        base = [to_hex(colormaps[classic](index)).upper() for index in indices]
        base_lab = rgb2lab(np.array([to_rgb(value) for value in base]))
        target_lab = rgb2lab(np.array([to_rgb(source[name]) for name in names]))
        base_hue = np.rad2deg(np.arctan2(base_lab[:, 2], base_lab[:, 1]))
        target_hue = np.rad2deg(np.arctan2(target_lab[:, 2], target_lab[:, 1]))
        shifts = np.clip((target_hue - base_hue + 180) % 360 - 180, -6, 6)
        fill, metrics = tune_classic(base, shifts)
        strokes = [dark_stroke(value) for value in fill]
        palettes[key] = {"label": label, "type": "qualitative", "max_n": len(fill),
                         "source_names": names, "fill": fill, "line": [item[0] for item in strokes],
                         "classic": {"name": classic, "indices_zero_based": indices, "fill": base},
                         "fill_derivation": {"hue_shift_degrees": shifts.tolist(), "chroma_scale": .96,
                                             "lightness": "classic L* retained before 8-bit quantization", **metrics},
                         "derived": True,
                         "line_derivation": [item[1] for item in strokes],
                         "rationale": rationale, "uses": uses, "curator": "EasyPlot candidate v0.2"}
    for key, label, kind, classic, shifts, names, rationale, uses in [
        ("qingci", "青瓷", "sequential", "GnBu", [-3, -6, -8], ["浅青瓷釉色", "灰緑", "花青"],
         "沿用 GnBu 的浅绿—青绿—深蓝结构，色相向青瓷与青花蓝小幅偏移，保留原有明暗跨度。", "非负强度、丰度、密度与热图"),
        ("qinglan", "青岚", "sequential", "YlGnBu", [-1, -3, -5], ["淡米色", "奶緑", "花青"],
         "以 YlGnBu 的浅黄—青绿—深蓝层次为底，黄色略偏米色、深蓝略减紫意。", "需要较丰富层次的强度、丰度与密度图"),
        ("qingzhu", "青朱", "diverging", "RdBu_r", [-7, 0, 7], ["花青", "銀白色", "硃砂"],
         "保留 RdBu 的对称明暗结构与浅中点，蓝侧向青花、红侧向朱砂微调。", "相对零值或明确基准的正负变化"),
        ("moyun", "墨韵", "sequential", "Greys", [0, 0, 0], ["雪灰", "青灰色", "百草霜"],
         "保留经典 Greys 原色，作为中性工具色，不作为主推中国风配色。", "中性对照与灰度用途；备用方案"),
    ]:
        base_rgb = colormaps[classic].resampled(257)(np.linspace(0, 1, 257))[:, :3]
        base = [to_hex(rgb).upper() for rgb in base_rgb]
        if key == 'moyun':
            fill, metrics = base.copy(), {'max_delta_Lstar': 0.0, 'mean_delta_E00': 0.0, 'max_delta_E00': 0.0}
        else:
            fill, metrics = tune_classic(base_rgb, np.interp(np.linspace(0, 1, 257), [0, .5, 1], shifts))
        palettes[key] = {"label": label, "type": kind, "max_n": None,
                         "source_names": names, "anchors": [fill[i] for i in (0, 128, 256)], "fill": fill,
                         "classic": {"name": classic, "fill": base},
                         "fill_derivation": {"hue_shift_stops_degrees": shifts, "chroma_scale": 1.0 if key == 'moyun' else .96,
                                             "lightness": "classic L* retained before 8-bit quantization", **metrics},
                         "ramp_derivation": "257 original classic samples, no edits" if key == 'moyun' else
                                            "257 classic samples; bounded CIELCh hue edit; out-of-gamut edits backed off toward classic; 8-bit sRGB",
                         "derived": key != 'moyun', "rationale": rationale, "uses": uses,
                         "curator": "EasyPlot candidate v0.2", "recommended": key != 'moyun'}
    return palettes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='explicitly refresh original public source cards')
    parser.add_argument('--output', type=Path, default=DEST)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing overwrite: {args.output}")
    if args.fetch:
        with urlopen(Request(URL, headers={'User-Agent': 'EasyPlot-local-colour-study/0.1'}), timeout=30) as response:
            rows = extract_source(response.read().decode('utf-8'))
        source = {"url": URL, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                  "copyright_notice": "2020 Frank Lin (site footer)",
                  "license_status": "Explicit dataset redistribution permission not located on homepage; local trial, review before publishing",
                  "selection": "320 original colour cards; initial detail-panel placeholder excluded",
                  "encoding": "HEX treated as sRGB; CMYK values retained only as source display metadata"}
    else:
        snapshot = json.loads(args.output.read_text(encoding='utf-8'))
        source, rows = snapshot['source'], snapshot['source_colours']
    aliases = {}
    for row in rows:
        for key in [row['name'], *row['aliases']]:
            if key in aliases and aliases[key] != row['hex']:
                raise ValueError(f"Ambiguous colour alias: {key}")
            aliases[key] = row['hex']
    result = {"schema_version": 1, "family": "dongfang", "version": "0.2.0-classic-candidate",
              "source": source, "source_colours": rows, "palettes": curate(rows),
              "classic_sources": {"library": "matplotlib", "version": matplotlib.__version__,
                                  "documentation": "https://matplotlib.org/stable/users/explain/colors/colormaps.html",
                                  "colorbrewer": "https://colorbrewer2.org/", "license": "https://colorbrewer2.org/export/LICENSE.txt",
                                  "acknowledgment": "This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/)."},
              "neutrals": {"ink": "#303030", "frame": "#575A5D", "background": "#FFFFFF", "missing": "#E2E2E2"}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(args.output, overwrite=args.overwrite, **result)
    print(f"Built {len(rows)} source colours and {len(result['palettes'])} curated palettes: {args.output}")


if __name__ == '__main__':
    main()
