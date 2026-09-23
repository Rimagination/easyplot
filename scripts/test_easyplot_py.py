"""Executable smoke test for EasyPlot's Python/Matplotlib runtime."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from easyplot_py import (  # noqa: E402
    EASYPLOT_TEMPLATE_VERSION,
    add_panel_tag,
    check_font_glyphs,
    export_figure,
    make_scientific_plate,
    plot_bar_pastel,
    plot_box_jitter,
    plot_heatmap,
    plot_timecourse,
    publication_context,
    save_figure,
    write_manifest,
)
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
from pypdf import PdfReader
from PIL import Image
import xml.etree.ElementTree as ET
from easyplot_run_r import r_environment


def check_typography_export(output_dir):
    parent = os.environ.copy()
    child = r_environment(windows=True)
    assert child["LC_ALL"].endswith(".UTF-8") and child["LC_ALL"] != "C.UTF-8"
    assert os.environ == parent
    for families, text in [(["EasyPlot-absent-font"], "A"), (["DejaVu Sans"], "中文")]:
        try:
            check_font_glyphs(text, families)
        except ValueError:
            pass
        else:
            raise AssertionError("missing family or missing glyph must fail preflight")
    available = {entry.name for entry in font_manager.fontManager.ttflist}
    cjk = "Microsoft YaHei" if "Microsoft YaHei" in available else None
    label = "中文 α μ −" if cjk else "alpha α μ −"
    prior = dict(matplotlib.rcParams)
    with publication_context(cjk_family=cjk, glyphs=label) as info:
        assert info["glyph_coverage"]["checked_codepoints"] > 0
        fig, ax = plt.subplots(figsize=(180/25.4, 86/25.4))
        ax.set_xlabel(label)
        ax.plot([0, 1], [0, 1])
    # Save outside the context, with conflicting user rcParams.
    with matplotlib.rc_context({"svg.fonttype": "path", "pdf.fonttype": 3, "savefig.bbox": "tight"}):
        bundle = export_figure(fig, output_dir / "中文路径" / "验证", formats=("png", "pdf", "svg"), dpi=150,
                               provenance={"font": info})
        outlined = save_figure(fig, output_dir / "outlined.svg", svg_text="outline")
        assert matplotlib.rcParams["savefig.bbox"] == "tight"
    assert dict(matplotlib.rcParams) == prior
    png, pdf, svg = bundle["outputs"]
    with Image.open(png) as im:
        assert abs(im.width - 180/25.4*150) <= 1 and abs(im.height - 86/25.4*150) <= 1
    page = PdfReader(pdf).pages[0]
    assert abs(float(page.mediabox.width)*25.4/72 - 180) < 0.01
    assert abs(float(page.mediabox.height)*25.4/72 - 86) < 0.01
    assert "α" in page.extract_text()
    ns = {"s": "http://www.w3.org/2000/svg"}
    texts = ET.parse(svg).findall(".//s:text", ns)
    assert texts and label in "".join("".join(node.itertext()) for node in texts)
    assert not ET.parse(outlined).findall(".//s:text", ns)
    assert ET.parse(outlined).findall(".//s:path", ns)
    manifest = json.loads(bundle["manifest"].read_text(encoding="utf-8"))
    assert manifest["svg_text"] == "editable" and manifest["pdf_fonttype"] == 42
    try:
        save_figure(fig, output_dir / "invalid.svg", svg_text="unknown")
    except ValueError:
        assert not (output_dir / "invalid.svg").exists()
    else:
        raise AssertionError("invalid SVG text mode must fail")
    plt.close(fig)


def main() -> None:
    conditions = ["CK", "Rh", "Ps", "RP"]
    summary = pd.DataFrame(
        {
            "condition": conditions,
            "estimate": [1.0, 2.2, 3.5, 2.9],
            "lower": [0.8, 1.9, 3.1, 2.5],
            "upper": [1.2, 2.5, 3.9, 3.3],
            "sig_label": ["c", "b", "a", "ab"],
        }
    )
    raw = pd.DataFrame(
        {
            "condition": np.repeat(conditions, 6),
            "value": np.array(
                [
                    0.8, 0.9, 1.0, 1.1, 1.1, 1.2,
                    1.8, 2.0, 2.1, 2.3, 2.4, 2.6,
                    3.1, 3.2, 3.4, 3.5, 3.7, 3.9,
                    2.5, 2.7, 2.8, 3.0, 3.1, 3.3,
                ]
            ),
        }
    )
    time_summary = pd.DataFrame(
        {
            "series": ["CK", "CK", "CK", "Rh", "Rh", "Rh"],
            "time": [0, 24, 48, 0, 24, 48],
            "estimate": [1.0, 1.2, 1.3, 1.0, 2.2, 3.1],
            "lower": [0.9, 1.1, 1.2, 0.9, 2.0, 2.8],
            "upper": [1.1, 1.3, 1.4, 1.1, 2.4, 3.4],
        }
    )

    with tempfile.TemporaryDirectory(prefix="easyplot-py-smoke-") as temp_dir:
        output_dir = Path(temp_dir)
        check_typography_export(output_dir)
        with publication_context(font_family="Arial") as font_info:
            fig, axes = make_scientific_plate(width_mm=180, height_mm=120, dpi=160)
            plot_bar_pastel(
                axes[0, 0],
                summary,
                lower="lower",
                upper="upper",
                raw=raw,
                sig_label="sig_label",
                order=conditions,
            )
            plot_box_jitter(axes[0, 1], raw, order=conditions)
            markers = {"CK": "s", "Rh": "^"}
            linestyles = {"CK": "--", "Rh": ":"}
            plot_timecourse(axes[1, 0], time_summary, markers=markers, linestyles=linestyles)
            for line in axes[1, 0].lines:
                assert line.get_marker() == markers[line.get_label()]
                assert line.get_linestyle() == linestyles[line.get_label()]
            before = len(axes[1, 0].lines)
            try:
                plot_timecourse(axes[1, 0], time_summary, markers={"CK": "s"})
            except ValueError:
                pass
            else:
                raise AssertionError("partial marker maps must fail before drawing any data")
            assert len(axes[1, 0].lines) == before
            # Reordered data retains group identity; omitted styling keeps old defaults.
            probe_fig, probe_ax = plt.subplots()
            plot_timecourse(probe_ax, time_summary.iloc[::-1], markers=markers, linestyles=linestyles)
            assert {line.get_label(): line.get_marker() for line in probe_ax.lines} == markers
            probe_ax.clear()
            plot_timecourse(probe_ax, time_summary)
            assert all(line.get_marker() == "o" and line.get_linestyle() == "-" for line in probe_ax.lines)
            probe_ax.clear()
            categorical = time_summary.copy()
            categorical["series"] = pd.Categorical(categorical["series"], categories=["CK", "Rh", "unused"])
            original_groupby = pd.DataFrame.groupby

            def old_groupby_default(frame, *args, **kwargs):
                kwargs.setdefault("observed", False)  # pandas <3 default, regardless of installed version
                return original_groupby(frame, *args, **kwargs)

            with patch.object(pd.DataFrame, "groupby", old_groupby_default):
                plot_timecourse(probe_ax, categorical, markers=markers, linestyles=linestyles,
                                lower="lower", upper="upper", fill_palette={"CK": "#DDDDDD", "Rh": "#EFB9BA"})
            assert {line.get_label(): line.get_marker() for line in probe_ax.lines} == markers
            plt.close(probe_fig)
            image = plot_heatmap(
                axes[1, 1],
                np.arange(12, dtype=float).reshape(3, 4),
                ["M1", "M2", "M3"],
                conditions,
                vmin=0,
                vmax=11,
            )
            assert image.get_array().shape == (3, 4)
            for tag, ax in zip("abcd", axes.flat):
                add_panel_tag(ax, tag)
            png_path = save_figure(fig, output_dir / "smoke.png", dpi=160)
            pdf_path = save_figure(fig, output_dir / "smoke.pdf", dpi=160)
            manifest_path = write_manifest(
                output_dir / "smoke.manifest.json",
                template_version=EASYPLOT_TEMPLATE_VERSION,
                font=font_info,
                output_width_mm=180,
                output_height_mm=120,
                synthetic=True,
            )
            bundle = export_figure(
                fig,
                output_dir / "bundle",
                formats=("png", "pdf"),
                dpi=160,
                provenance={"synthetic": True, "seed": 42},
            )
        plt.close(fig)
        assert png_path.exists() and png_path.stat().st_size > 1000
        assert pdf_path.exists() and pdf_path.stat().st_size > 1000
        assert manifest_path.exists() and manifest_path.stat().st_size > 100
        assert all(path.exists() and path.stat().st_size > 1000 for path in bundle["outputs"])
        assert bundle["manifest"].exists() and bundle["manifest"].stat().st_size > 100
        try:
            save_figure(fig, png_path, dpi=160)
        except FileExistsError:
            pass
        else:
            raise AssertionError("save_figure must refuse implicit overwrite")
        try:
            export_figure(fig, output_dir / "bundle", formats=("png", "pdf"), dpi=160)
        except FileExistsError:
            pass
        else:
            raise AssertionError("export_figure must refuse implicit overwrite")

    print(f"EasyPlot Python runtime checks passed ({EASYPLOT_TEMPLATE_VERSION})")


if __name__ == "__main__":
    main()
