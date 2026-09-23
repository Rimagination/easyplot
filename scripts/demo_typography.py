"""Reproducible bilingual R/Python export benchmark, using the same CSV files.

Synthetic observations only. Run into a NEW disposable directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import warnings

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from pypdf import PdfReader

from easyplot_py import (EASYPLOT_LINE_PALETTE, EASYPLOT_PALETTE, add_panel_tag,
                         export_figure, format_axes, make_scientific_plate,
                         plot_heatmap, plot_timecourse, publication_context)
from easyplot_metadata import inspect_file


WIDTH, HEIGHT, DPI = 177.8, 127, 300  # 7 x 5 inches; exact integer Cairo points.
GROUPS = ["CK", "Rh", "Ps", "RP"]
LABELS = {"x": "处理 Treatment", "y": "生物量 Biomass (mg)", "time": "时间 Time (h)",
          "signal": "信号 Signal (μmol/L)", "feature": "特征 Feature"}


def make_tables(root):
    directory = root / "数据"
    directory.mkdir(parents=True)
    rng = np.random.default_rng(723)
    raw = pd.DataFrame({"处理": np.repeat(GROUPS, 8), "重复": np.tile(np.arange(1, 9), 4),
                        "生物量": np.concatenate([rng.normal(mean, sd, 8) for mean, sd in
                                                   [(1.3, .24), (2.8, .32), (3.7, .36), (3.2, .3)]]),
                        "位置": np.repeat(np.arange(1, 5), 8) + np.tile(np.linspace(-.16, .16, 8), 4)})
    summary = raw.groupby("处理", sort=False)["生物量"].agg(均值="mean", 标准差="std").reset_index()
    summary["下限"] = summary["均值"] - summary["标准差"]
    summary["上限"] = summary["均值"] + summary["标准差"]
    times = np.array([0, 12, 24, 48, 72])
    curve = pd.DataFrame({"处理": np.repeat(GROUPS, len(times)), "时间": np.tile(times, 4),
                          "信号": np.concatenate([1 + strength*(1-np.exp(-times/24)) for strength in (1, 6, 8, 4)])})
    matrix = pd.DataFrame({"处理": np.tile(GROUPS, 5), "特征": np.repeat([f"M{i}" for i in range(1, 6)], 4),
                           "数值": rng.uniform(.08, .96, 20)})
    matrix.loc[9, "数值"] = np.nan
    for name, frame in [("原始观测.csv", raw), ("均值和标准差.csv", summary), ("时间序列.csv", curve), ("热图.csv", matrix)]:
        frame.to_csv(directory / name, index=False, encoding="utf-8", float_format="%.15g")
    # Both renderers read the actual UTF-8 files, not in-memory substitutes.
    return [pd.read_csv(directory / name, encoding="utf-8") for name in
            ["原始观测.csv", "均值和标准差.csv", "时间序列.csv", "热图.csv"]]


def draw_python(root, tables):
    raw, summary, curve, heat = tables
    output = root / "Python"
    output.mkdir()
    with publication_context(font_family="Arial", cjk_family="Microsoft YaHei", glyphs=" ".join(LABELS.values())) as fonts:
        fig, axes = make_scientific_plate(width_mm=WIDTH, height_mm=HEIGHT, dpi=DPI)
        a, b, c, d = axes.flat
        for ax in axes.flat:
            format_axes(ax)
        x = np.arange(1, 5)
        colors = [EASYPLOT_PALETTE[g] for g in GROUPS]
        a.bar(x, summary["均值"], width=.62, color=colors, edgecolor="#333333", linewidth=.7)
        a.errorbar(x, summary["均值"], yerr=summary["标准差"], fmt="none", ecolor="#333333",
                   elinewidth=.9, capsize=2)
        samples = [raw.loc[raw["处理"] == g, "生物量"].to_numpy() for g in GROUPS]
        boxes = b.boxplot(samples, positions=x, widths=.6, patch_artist=True, showfliers=False,
                           medianprops={"color": "#333333", "linewidth": .8},
                           boxprops={"linewidth": .7}, whiskerprops={"linewidth": .7}, capprops={"linewidth": .7})
        for box, color in zip(boxes["boxes"], colors):
            box.set_facecolor(color)
        for ax in (a, b):
            ax.scatter(raw["位置"], raw["生物量"], s=8, c="#333333", linewidths=0, zorder=4)
            ax.set(xticks=x, xticklabels=GROUPS, xlim=(.4, 4.6), ylim=(0, 5), xlabel=LABELS["x"], ylabel=LABELS["y"])
        plot_timecourse(c, curve.rename(columns={"处理": "series", "时间": "time", "信号": "estimate"}),
                        palette=EASYPLOT_LINE_PALETTE, markers={"CK": "s", "Rh": "o", "Ps": "^", "RP": "D"},
                        linestyles={"CK": "--", "Rh": "-", "Ps": "-.", "RP": ":"})
        if c.get_legend():
            c.get_legend().remove()
        for group in GROUPS:
            last = curve.loc[curve["处理"] == group].iloc[-1]
            c.text(76, last["信号"], group, color=EASYPLOT_LINE_PALETTE[group], va="center", fontsize=7)
        c.set(xlabel=LABELS["time"], ylabel=LABELS["signal"], xlim=(0, 87), ylim=(0, 10), xticks=[0, 24, 48, 72])
        cmap = LinearSegmentedColormap.from_list("benchmark_blues", ["#EFF3FF", "#6BAED6", "#08519C"])
        cmap.set_bad("#DDDDDD")
        heat_matrix = heat.pivot(index="特征", columns="处理", values="数值").reindex(columns=GROUPS)
        plot_heatmap(d, heat_matrix.to_numpy(), list(heat_matrix.index), GROUPS, cmap=cmap,
                     vmin=0, vmax=1, colorbar_label="Scaled\nvalue")
        d.set(xlabel=LABELS["x"], ylabel=LABELS["feature"])
        for tag, ax in zip("abcd", axes.flat):
            add_panel_tag(ax, tag, fontsize=8)
        fig.canvas.draw()
        # Freeze the measured panel grid across formats after final-size layout.
        fig.set_layout_engine("none")
        positions = []
        for number, ax in enumerate(axes.flat, 1):
            box = ax.get_position()
            positions.append({"panel": str(number), "left": box.x0*WIDTH, "right": box.x1*WIDTH,
                              "bottom": box.y0*HEIGHT, "top": box.y1*HEIGHT})
        provenance = {"synthetic": True, "font": fonts, "input_directory": str(root / "数据"),
                      "uncertainty": "sample SD; n=8 independent synthetic units per group",
                      "journal_profile": "none", "caption": "../图注.md"}
        export_figure(fig, output / "双语四联图", formats=("png", "pdf", "svg"), dpi=DPI, provenance=provenance,
                      svg_text="editable")
        export_figure(fig, output / "双语四联图-outline", formats=("svg",), dpi=DPI, provenance=provenance,
                      svg_text="outline")
        plt.close(fig)
    (output / "layout.json").write_text(json.dumps({"panels_mm": positions, "font": fonts, "svg_text": "editable"},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")


def audit(root):
    reports = []
    alignments = {}
    for backend in ("R", "Python"):
        output = root / backend
        layout = json.loads((output / "layout.json").read_text(encoding="utf-8"))
        boxes = {p["panel"]: p for p in layout["panels_mm"]}
        assert set(boxes) == set("1234"), f"Missing measured panel regions: {backend}"
        deltas = [abs(boxes[a][edge] - boxes[b][edge]) for a, b, edges in
                  [("1", "3", ("left", "right")), ("2", "4", ("left", "right")),
                   ("1", "2", ("top", "bottom")), ("3", "4", ("top", "bottom"))] for edge in edges]
        alignments[backend] = {"max_edge_difference_mm": max(deltas), "scope": "final-size PNG device plotting regions"}
        assert max(deltas) < .2, f"Panel regions misaligned in {backend}: {max(deltas)} mm"
        for path in sorted(output.glob("双语四联图*")):
            if path.suffix not in {".png", ".pdf", ".svg"}:
                continue
            mode = "outline" if path.stem.endswith("-outline") else layout["svg_text"]
            report = inspect_file(path, min_dpi=DPI, target_width_mm=WIDTH, target_height_mm=HEIGHT,
                                  size_tolerance_mm=.05, require_embedded_fonts=True,
                                  expected_svg_text=mode if path.suffix == ".svg" else None)
            reports.append(report)
            assert not report["errors"], report
            assert not report["warnings"], report
            if path.suffix == ".pdf":
                reader = PdfReader(path)
                assert len(reader.pages) == 1, "One figure must export as exactly one PDF page"
                text = reader.pages[0].extract_text()
                assert "生物量" in text and "时间" in text and "μ" in text, text
    data = {"profile": "none", "synthetic": True, "width_mm": WIDTH, "height_mm": HEIGHT,
            "files": reports, "alignment": alignments,
            "limits": ["Cmap and font resources do not prove every shaping/glyph operation.",
                       "Editable SVG depends on fonts in the receiving viewer.",
                       "This benchmark uses integer-point dimensions; Cairo can round other sizes."]}
    (root / "audit.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rscript", required=True)
    parser.add_argument("--r-library")
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        tables = make_tables(root)
        draw_python(root, tables)
    if captured:
        raise RuntimeError("Python render warnings: " + "; ".join(str(w.message) for w in captured))
    scripts = Path(__file__).resolve().parent
    command = [sys.executable, "-B", "-X", "utf8", str(scripts / "easyplot_run_r.py"), "--rscript", args.rscript]
    if args.r_library:
        command += ["--library", args.r_library]
    subprocess.run(command + [str(scripts / "demo_typography.R"), str(root)], check=True)
    caption = """# 图注 / Caption

本图仅使用固定种子的模拟数据，用于 EasyPlot 的字体、尺寸和双后端导出验证，不代表科研结论。
a：4 组各 8 个独立模拟观测；柱为均值，误差线为样本标准差，黑点为原始值。
b：同一批观测的箱线图（中位数、四分位数、1.5×IQR 须）和相同位置的原始点。
c：确定性的模拟时间轨迹，无推断、平滑或置信区间；颜色、形状、线型和末端标签共同标识组别。
d：0–1 模拟数值矩阵，灰格表示一个缺失值；各组共用同一颜色范围。未进行聚类。

尺寸：177.8 × 127 mm；PNG 为 300 dpi；未指定期刊，未作期刊合规认证。
字体：Arial 用于拉丁字符/数字，Microsoft YaHei 用于中文。R 的整段混排轴标题使用 Microsoft YaHei；Python 逐字形使用字体回退链。
图题、图注和方法仅在本文件中；画布只包含坐标、单位、分组、panel 标记和局部色标。
可编辑 SVG 需要接收方安装相同字体；转曲 SVG 保留形状但文字不可编辑。缺少 svglite 时 R 仅输出转曲 SVG。

Alt text: Four aligned panels show synthetic group means with SD and observations, the same distributions,
four labelled time trajectories, and a blue magnitude matrix with one explicitly grey missing cell.
All source tables are in 数据/. No significance tests or scientific findings are claimed.
"""
    (root / "图注.md").write_text(caption, encoding="utf-8")
    data = audit(root)
    print(json.dumps({"output": str(root), "files": len(data["files"]), "alignment": data["alignment"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
