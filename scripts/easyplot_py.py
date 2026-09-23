"""EasyPlot's lightweight Python/Matplotlib runtime.

The module keeps the same scientific contracts as the R backend while using
Matplotlib's object-oriented API and constrained layout for static figures.
Values, statistics, and significance annotations must be supplied by the
calling script; this module only provides plotting primitives and export
helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path
import tempfile
from typing import Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import Colormap
import numpy as np
import pandas as pd


EASYPLOT_TEMPLATE_VERSION = "0.4.0-py"
EASYPLOT_INK = "#252A2E"
EASYPLOT_FRAME = "#566169"
EASYPLOT_PALETTE = {
    "CK": "#D8DDE2",
    "Rh": "#D8898D",
    "Ps": "#D6A15A",
    "RP": "#6C9DC5",
    "mist": "#F4F9FC",
    "blush": "#FBDDD7",
    "coral": "#F59092",
    "sand": "#E5D8D4",
    "rose": "#BB9491",
    "powder_blue": "#C6D4EA",
    "steel_blue": "#568FC3",
}

# Optional darker strokes keep the condition colour families for thin marks.
# Pastel fills remain unchanged; callers explicitly select this palette.
EASYPLOT_LINE_PALETTE = {
    "CK": "#707983",
    "Rh": "#AB4B53",
    "Ps": "#98671F",
    "RP": "#356D9A",
}


def require_columns(data: pd.DataFrame, columns: Iterable[str], context: str = "data") -> None:
    """Raise a useful error when a plotting contract column is absent."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"{context} must be a pandas.DataFrame")
    missing = [column for column in dict.fromkeys(columns) if column and column not in data.columns]
    if missing:
        raise ValueError(f"{context} is missing required column(s): {', '.join(missing)}")


def resolve_font_family(requested: str = "Arial", fallback: str = "DejaVu Sans") -> tuple[str, bool]:
    """Return an installed family and whether the requested family was found."""

    available = {entry.name for entry in font_manager.fontManager.ttflist}
    if requested in available:
        return requested, True
    if fallback in available:
        return fallback, False
    raise ValueError(f"Neither requested font {requested!r} nor fallback {fallback!r} is installed")


def check_font_glyphs(text: str, families: Sequence[str], *, weight="normal", style="normal") -> dict:
    """Check a declared font chain's cmap, not the correctness of rendered shaping.

    Use a separate call for every face used. MathText/TeX have separate fonts.
    """
    if not families or isinstance(families, str):
        raise ValueError("families must be a non-empty sequence of installed family names")
    available = {entry.name for entry in font_manager.fontManager.ttflist}
    missing_families = set(families) - available
    if missing_families:
        raise ValueError(f"Font families are not installed: {sorted(missing_families)}")
    fonts = []
    covered = set()
    for family in dict.fromkeys(families):
        path = font_manager.findfont(font_manager.FontProperties(family=family, weight=weight, style=style),
                                     fallback_to_default=False)
        face = font_manager.get_font(path)
        covered.update(face.get_charmap())
        fonts.append({"family": family, "path": path, "resolved_style": face.style_name})
    required = {ord(char) for char in text if not char.isspace()}
    absent = sorted(required - covered)
    if absent:
        raise ValueError("Missing glyphs in declared font chain: " + ", ".join(f"U+{value:04X}" for value in absent))
    return {"fonts": fonts, "checked_codepoints": len(required), "weight": weight, "style": style,
            "scope": "declared text and face cmap only; inspect the rendered export"}


@contextmanager
def publication_context(
    base_size: float = 8.0,
    font_family: str = "Arial",
    fallback_family: str = "DejaVu Sans",
    cjk_family: str | None = None,
    glyphs: str = "",
):
    """Apply EasyPlot's scoped publication style and report font resolution."""

    resolved_family, requested_available = resolve_font_family(font_family, fallback_family)
    families = list(dict.fromkeys([resolved_family] + ([cjk_family] if cjk_family else [])))
    coverage = check_font_glyphs(glyphs, families)
    rc = {
        "font.family": families,
        "font.size": base_size,
        "axes.titlesize": base_size,
        "axes.labelsize": base_size,
        "xtick.labelsize": base_size - 0.7,
        "ytick.labelsize": base_size - 0.7,
        "legend.fontsize": base_size - 0.8,
        "axes.linewidth": 0.65,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "axes.edgecolor": EASYPLOT_FRAME,
        "axes.labelcolor": EASYPLOT_INK,
        "xtick.color": EASYPLOT_INK,
        "ytick.color": EASYPLOT_INK,
        "text.color": EASYPLOT_INK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.edgecolor": "white",
        "pdf.fonttype": 42,
        "pdf.use14corefonts": False,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
    with matplotlib.rc_context(rc):
        yield {
            "requested_font": font_family,
            "resolved_font": resolved_family,
            "requested_font_available": requested_available,
            "font_families": families,
            "glyph_coverage": coverage,
        }


def make_scientific_plate(
    nrows: int = 2,
    ncols: int = 2,
    width_mm: float = 180,
    height_mm: float = 120,
    dpi: int = 600,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
):
    """Create an aligned panel grid with a physical canvas size in millimetres."""

    if nrows < 1 or ncols < 1:
        raise ValueError("nrows and ncols must be positive")
    if width_mm <= 0 or height_mm <= 0 or dpi <= 0:
        raise ValueError("width_mm, height_mm, and dpi must be positive")
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        squeeze=False,
        constrained_layout=True,
        gridspec_kw={
            "width_ratios": width_ratios,
            "height_ratios": height_ratios,
        },
    )
    fig.patch.set_facecolor("white")
    return fig, axes


def format_axes(ax, grid: bool = False) -> None:
    """Apply the light structural frame used by EasyPlot panels."""

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.65)
    ax.spines["bottom"].set_linewidth(0.65)
    ax.tick_params(direction="out", width=0.65, length=3, colors=EASYPLOT_INK)
    ax.xaxis.label.set_color(EASYPLOT_INK)
    ax.yaxis.label.set_color(EASYPLOT_INK)
    ax.set_axisbelow(True)
    if grid:
        ax.yaxis.grid(True, color="#E8ECEF", linewidth=0.45)
    else:
        ax.grid(False)


def add_panel_tag(ax, tag: str, fontsize: float = 9.0, **kwargs) -> None:
    """Add a lowercase structural panel tag in axes coordinates."""

    defaults = {
        "x": 0.01,
        "y": 0.99,
        "ha": "left",
        "va": "top",
        "fontsize": fontsize,
        "fontweight": "normal",
        "color": EASYPLOT_INK,
        "transform": ax.transAxes,
        "clip_on": False,
    }
    defaults.update(kwargs)
    ax.text(ha=defaults.pop("ha"), va=defaults.pop("va"), **defaults, s=tag)


def _palette_for(order: Sequence[str], palette: Mapping[str, str] | None) -> list[str]:
    source = dict(EASYPLOT_PALETTE)
    if palette:
        source.update(palette)
    fallback = ["#D8DDE2", "#D8898D", "#D6A15A", "#6C9DC5", "#A98FB8", "#8CA6A8"]
    return [source.get(str(label), fallback[index % len(fallback)]) for index, label in enumerate(order)]


def _ordered_keys(data: pd.DataFrame, column: str, order: Sequence[str] | None) -> list[str]:
    values = data[column].astype(str)
    if order is None:
        return list(dict.fromkeys(values.tolist()))
    requested = [str(value) for value in order]
    present = set(values)
    missing = [value for value in requested if value not in present]
    if missing:
        raise ValueError(f"{column} order contains values absent from data: {', '.join(missing)}")
    return requested


def plot_bar_pastel(
    ax,
    summary: pd.DataFrame,
    condition: str = "condition",
    estimate: str = "estimate",
    lower: str | None = None,
    upper: str | None = None,
    raw: pd.DataFrame | None = None,
    raw_value: str = "value",
    sig_label: str | None = None,
    order: Sequence[str] | None = None,
    palette: Mapping[str, str] | None = None,
    bar_width: float = 0.58,
    seed: int = 20260923,
):
    """Draw summary bars with declared intervals, raw points, and labels."""

    require_columns(summary, [condition, estimate, lower, upper, sig_label], "bar summary")
    if raw is not None:
        require_columns(raw, [condition, raw_value], "bar raw observations")
    if (lower is None) != (upper is None):
        raise ValueError("lower and upper must be supplied together")

    keys = _ordered_keys(summary, condition, order)
    plotted = summary.assign(_easyplot_key=summary[condition].astype(str)).set_index("_easyplot_key").loc[keys]
    x = np.arange(len(keys), dtype=float)
    colors = _palette_for(keys, palette)
    ax.bar(
        x,
        plotted[estimate].to_numpy(float),
        width=bar_width,
        color=colors,
        edgecolor=EASYPLOT_INK,
        linewidth=0.65,
        zorder=2,
    )

    if lower is not None and upper is not None:
        values = plotted[estimate].to_numpy(float)
        yerr = np.vstack([values - plotted[lower].to_numpy(float), plotted[upper].to_numpy(float) - values])
        ax.errorbar(
            x,
            values,
            yerr=yerr,
            fmt="none",
            ecolor=EASYPLOT_INK,
            elinewidth=1.0,
            capsize=3.0,
            capthick=1.0,
            zorder=4,
        )

    if raw is not None:
        rng = np.random.default_rng(seed)
        raw_keys = raw[condition].astype(str)
        for index, key in enumerate(keys):
            values = raw.loc[raw_keys == key, raw_value].to_numpy(float)
            if len(values):
                jitter = rng.uniform(-0.11, 0.11, len(values))
                ax.scatter(
                    np.full(len(values), x[index]) + jitter,
                    values,
                    s=13,
                    facecolor="white",
                    edgecolor=EASYPLOT_INK,
                    linewidth=0.45,
                    alpha=0.82,
                    zorder=5,
                )

    if sig_label is not None:
        for index, (_, row) in enumerate(plotted.iterrows()):
            label = row[sig_label]
            if pd.notna(label) and str(label):
                clearance = 0.05 * max(1.0, float(plotted[estimate].max()))
                y = float(row[upper]) + clearance if upper is not None else float(row[estimate]) + clearance
                ax.text(x[index], y, str(label), ha="center", va="bottom", color=EASYPLOT_INK, zorder=6)

    ax.set_xticks(x, keys)
    format_axes(ax)
    return ax


def plot_box_jitter(
    ax,
    raw: pd.DataFrame,
    condition: str = "condition",
    value: str = "value",
    order: Sequence[str] | None = None,
    palette: Mapping[str, str] | None = None,
    seed: int = 20260923,
):
    """Draw boxplots with visible raw observations."""

    require_columns(raw, [condition, value], "box raw observations")
    keys = _ordered_keys(raw, condition, order)
    raw_keys = raw[condition].astype(str)
    values = [raw.loc[raw_keys == key, value].to_numpy(float) for key in keys]
    x = np.arange(1, len(keys) + 1, dtype=float)
    colors = _palette_for(keys, palette)
    box = ax.boxplot(
        values,
        positions=x,
        widths=0.50,
        patch_artist=True,
        showfliers=False,
        boxprops={"edgecolor": EASYPLOT_INK, "linewidth": 0.65},
        whiskerprops={"color": EASYPLOT_INK, "linewidth": 0.65},
        capprops={"color": EASYPLOT_INK, "linewidth": 0.65},
        medianprops={"color": EASYPLOT_INK, "linewidth": 1.0},
    )
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.88)

    rng = np.random.default_rng(seed)
    for index, group_values in enumerate(values):
        jitter = rng.uniform(-0.10, 0.10, len(group_values))
        ax.scatter(
            np.full(len(group_values), x[index]) + jitter,
            group_values,
            s=11,
            color=EASYPLOT_INK,
            alpha=0.34,
            linewidth=0,
            zorder=4,
        )
    ax.set_xticks(x, keys)
    format_axes(ax)
    return ax


def plot_timecourse(
    ax,
    summary: pd.DataFrame,
    series: str = "series",
    time: str = "time",
    estimate: str = "estimate",
    lower: str | None = None,
    upper: str | None = None,
    raw: pd.DataFrame | None = None,
    raw_value: str = "value",
    palette: Mapping[str, str] | None = None,
    seed: int = 20260923,
    markers: Mapping[str, str] | None = None,
    linestyles: Mapping[str, str] | None = None,
    fill_palette: Mapping[str, str] | None = None,
):
    """Draw trajectories with optional group-specific markers and line styles.

    Colour/shape/style maps use series names, so reordering input rows does not
    change identity. fill_palette lets ribbons retain lighter condition fills.
    """

    require_columns(summary, [series, time, estimate, lower, upper], "time-course summary")
    if raw is not None:
        require_columns(raw, [series, time, raw_value], "time-course raw observations")
    if (lower is None) != (upper is None):
        raise ValueError("lower and upper must be supplied together")

    palette_map = dict(EASYPLOT_PALETTE)
    if palette:
        palette_map.update(palette)
    keys = set(summary[series].astype(str))
    for name, mapping in (("markers", markers), ("linestyles", linestyles), ("fill_palette", fill_palette)):
        if mapping is not None and keys - mapping.keys():
            raise ValueError(f"{name} must cover every series: {', '.join(sorted(keys - mapping.keys()))}")
    rng = np.random.default_rng(seed)
    for key, frame in summary.groupby(series, sort=False, observed=True):
        frame = frame.sort_values(time)
        key_text = str(key)
        color = palette_map.get(key_text, "#6C9DC5")
        if lower is not None and upper is not None:
            fill = fill_palette[key_text] if fill_palette is not None else color
            ax.fill_between(frame[time], frame[lower], frame[upper], color=fill, alpha=0.20, linewidth=0)
        ax.plot(
            frame[time], frame[estimate], color=color, linewidth=1.5,
            marker=markers[key_text] if markers is not None else "o",
            linestyle=linestyles[key_text] if linestyles is not None else "-",
            markersize=3.2, label=key_text,
        )
        if raw is not None:
            raw_frame = raw.loc[raw[series].astype(str) == key_text]
            for time_value, observations in raw_frame.groupby(time, sort=False, observed=True):
                jitter = rng.uniform(-0.7, 0.7, len(observations))
                ax.scatter(
                    np.full(len(observations), time_value) + jitter,
                    observations[raw_value],
                    color=color,
                    s=11,
                    alpha=0.24,
                    linewidth=0,
                    zorder=1,
                )
    format_axes(ax)
    return ax


def plot_heatmap(
    ax,
    matrix: Sequence[Sequence[float]] | np.ndarray,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    cmap: str | Colormap = "RdBu_r",
    vmin: float | None = None,
    vmax: float | None = None,
    colorbar_label: str | None = None,
):
    """Draw a compact matrix with explicit row/column semantics."""

    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    if values.shape != (len(row_labels), len(column_labels)):
        raise ValueError("matrix dimensions must match row_labels and column_labels")
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xticks(np.arange(len(column_labels)), column_labels)
    ax.set_yticks(np.arange(len(row_labels)), row_labels)
    ax.set_xticks(np.arange(-0.5, len(column_labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.55)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="x", length=0, pad=4)
    ax.tick_params(axis="y", length=0, pad=4)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#B8B8B8")
        spine.set_linewidth(0.55)
    if colorbar_label is not None:
        colorbar = ax.figure.colorbar(image, ax=ax, pad=0.04, fraction=0.06)
        colorbar.set_label(colorbar_label)
        colorbar.outline.set_visible(False)
        colorbar.ax.tick_params(width=0.45, length=2.5)
    return image


def save_figure(
    fig,
    filename: str | Path,
    dpi: int = 600,
    overwrite: bool = False,
    metadata: Mapping[str, str] | None = None,
    svg_text: str = "editable",
) -> Path:
    """Atomically save one static figure without implicit overwrite."""

    path = Path(filename)
    if path.suffix.lower() not in {".png", ".pdf", ".svg"}:
        raise ValueError("EasyPlot Python supports .png, .pdf, and .svg outputs")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_save_figure(fig, path, dpi=dpi, metadata=metadata, overwrite=overwrite, svg_text=svg_text)
    return path


def _atomic_save_figure(
    fig,
    path: Path,
    dpi: int,
    metadata: Mapping[str, str] | None,
    overwrite: bool,
    svg_text: str = "editable",
) -> None:
    """Write beside the destination, then replace it in one rename operation."""

    if svg_text not in {"editable", "outline"}:
        raise ValueError("svg_text must be 'editable' or 'outline'")
    if not np.isfinite(dpi) or dpi <= 0:
        raise ValueError("dpi must be finite and positive")
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}-",
        suffix=path.suffix,
        dir=path.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        # Enforce at save time: figures can be exported outside publication_context.
        # A global savefig.bbox='tight' would otherwise override bbox_inches=None.
        with matplotlib.rc_context({"svg.fonttype": "none" if svg_text == "editable" else "path",
                                    "pdf.fonttype": 42, "pdf.use14corefonts": False, "savefig.bbox": None}):
            fig.savefig(
                temporary_path,
                dpi=dpi,
                facecolor="white",
                edgecolor="white",
                transparent=False,
                bbox_inches=None,
                metadata=dict(metadata) if metadata else None,
            )
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing output: {path}")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_manifest(path: str | Path, overwrite: bool = False, **metadata) -> Path:
    """Atomically write a compact JSON provenance note beside exported figures."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing manifest: {target}")
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
        suffix=target.suffix or ".json",
        dir=target.parent,
        text=True,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(temporary_path, target)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return target


def export_figure(
    fig,
    stem: str | Path,
    formats: Sequence[str] = ("png", "pdf"),
    dpi: int = 600,
    overwrite: bool = False,
    provenance: Mapping[str, object] | None = None,
    write_manifest_file: bool = True,
    svg_text: str = "editable",
) -> dict[str, object]:
    """Export several formats and a provenance manifest as one guarded operation.

    The figure keeps its existing physical size. Each output is written to a
    sibling temporary file and renamed into place only after the render closes.
    Existing outputs and the manifest are rejected unless ``overwrite=True``.
    """

    stem_path = Path(stem)
    if stem_path.suffix.lower() in {".png", ".pdf", ".svg"}:
        stem_path = stem_path.with_suffix("")
    normalized_formats = tuple(dict.fromkeys(format_value.lower().lstrip(".") for format_value in formats))
    unsupported = set(normalized_formats) - {"png", "pdf", "svg"}
    if not normalized_formats or unsupported:
        raise ValueError("formats must contain one or more of: png, pdf, svg")
    if svg_text not in {"editable", "outline"}:
        raise ValueError("svg_text must be 'editable' or 'outline'")
    if not np.isfinite(dpi) or dpi <= 0:
        raise ValueError("dpi must be finite and positive")

    output_paths = [stem_path.with_suffix(f".{format_value}") for format_value in normalized_formats]
    manifest_path = stem_path.with_suffix(".manifest.json")
    targets = output_paths + ([manifest_path] if write_manifest_file else [])
    existing = [path for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing export(s): " + ", ".join(str(path) for path in existing)
        )

    stem_path.parent.mkdir(parents=True, exist_ok=True)
    width_in, height_in = fig.get_size_inches()
    manifest = {
        "backend": "python/matplotlib",
        "template_version": EASYPLOT_TEMPLATE_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "width_mm": round(float(width_in) * 25.4, 4),
        "height_mm": round(float(height_in) * 25.4, 4),
        "dpi": int(dpi),
        "formats": list(normalized_formats),
        "svg_text": svg_text if "svg" in normalized_formats else None,
        "pdf_fonttype": 42 if "pdf" in normalized_formats else None,
        "software": {"python": platform.python_version(), "matplotlib": matplotlib.__version__},
        "overwrite_requested": bool(overwrite),
        "provenance": dict(provenance or {}),
    }
    written: list[Path] = []
    try:
        for path in output_paths:
            _atomic_save_figure(fig, path, dpi=dpi, metadata=None, overwrite=overwrite, svg_text=svg_text)
            written.append(path)
        manifest["outputs"] = [
            {"path": str(path), "bytes": path.stat().st_size} for path in output_paths
        ]
        if write_manifest_file:
            write_manifest(manifest_path, overwrite=overwrite, **manifest)
            written.append(manifest_path)
    except Exception:
        if not overwrite:
            for path in written:
                path.unlink(missing_ok=True)
        raise

    return {"outputs": output_paths, "manifest": manifest_path if write_manifest_file else None}
