# EasyPlot Python backend

Use this reference when the user explicitly requests Python, provides a `.py` project, or names Matplotlib, Seaborn, or Plotly.

## Routing and dependencies

- Python is selected only when the user or the existing project makes it explicit. R/ggplot2 remains the default for an unspecified request.
- The canonical static backend is Matplotlib's object-oriented API. The bundled runtime requires Python 3.11+, Matplotlib, NumPy, and pandas.
- Seaborn is optional. Use it when an existing project already depends on it or the user asks for it; do not add it solely to draw an ordinary EasyPlot bar, distribution, trajectory, or heatmap.
- Plotly is optional and remains a separate interactive/static path. An interactive HTML file does not replace the requested static PNG/PDF/SVG output, visible labels, alt text, or data alternative.

## Runtime entry points

Import [scripts/easyplot_py.py](../scripts/easyplot_py.py) in a self-contained figure script. The stable helpers are:

| Helper | Purpose |
| --- | --- |
| `publication_context()` | Scoped font, line, face-colour, and editable-font settings; reports requested/resolved font. |
| `check_font_glyphs()` | Check a declared font chain/face against supplied Unicode text and report resolved font files. |
| `make_scientific_plate()` | Physical-size Matplotlib grid with `constrained_layout=True` for aligned panel regions. |
| `plot_bar_pastel()` | Summary bars with explicit lower/upper intervals, raw points, and supplied significance labels. |
| `plot_box_jitter()` | Boxplots with visible raw observations. |
| `plot_timecourse()` | Ordered trajectories with optional intervals/raw points and named `markers`, `linestyles`, and `fill_palette` mappings. |
| `plot_heatmap()` | Matrix display with explicit row/column labels and optional colorbar. |
| `add_panel_tag()` | Lowercase structural panel tags. |
| `save_figure()` | Atomic PNG/PDF/SVG export at the existing physical figure size; refuses implicit overwrite. |
| `export_figure()` | Guarded multi-format export plus a JSON provenance manifest. |
| `write_manifest()` | Atomic JSON provenance sidecar for dimensions, backend, seed, data path, and software details. |

The helpers do not calculate statistics or infer missing values. The calling script must supply estimators, uncertainty bounds, factor order, significance results, and transformations.

## Backend parity contract

Python output should preserve the EasyPlot choices made in the R backend:

- use the named semantic palette rather than implicit color order;
- keep titles, captions, statistical methods, and provenance outside the canvas by default;
- keep units and transformations visible in axis labels or the sidecar note;
- show raw observations when they improve interpretation;
- keep missing time points as gaps;
- use zero-baseline bars for ordinary amounts and declare any log transform;
- preserve factor order across panels;
- use `make_scientific_plate()` for mixed four-panel figures and keep guides local when units differ;
- record the requested font and the resolved fallback in the manifest when the requested family is unavailable.

For curves whose identities depend on colour alone, supply group-specific maps such as `markers={"Rh": "o", "Ps": "^", "RP": "s"}` and `linestyles={"Rh": "-", "Ps": "--", "RP": "-."}`. Each supplied mapping must cover all plotted series; omitted arguments retain the existing defaults. `EASYPLOT_LINE_PALETTE` provides optional darker strokes while `fill_palette` can keep ribbons pastel. Direct end labels can be added in the calling script with room reserved on the axes. Labelled bars and boxes usually need no additional patterns.

## Export rules

Create the figure with its intended physical size in millimetres, for example:

```python
from easyplot_py import export_figure, make_scientific_plate, publication_context

with publication_context(font_family="Arial") as font_info:
    fig, axes = make_scientific_plate(width_mm=180, height_mm=130, dpi=600)
    # Populate axes with a declared data contract.
    export_figure(
        fig,
        "outputs/figure",
        formats=("png", "pdf"),
        dpi=600,
        provenance={"font": font_info},
    )
```

Do not use `bbox_inches="tight"` for manuscript exports when it changes the declared page size. Use `overwrite=True` only when the user explicitly wants replacement or the output path is a disposable render directory.

For mixed scripts, supply `cjk_family` and `glyphs` to `publication_context()`. Pass `svg_text="editable"` (default) or `"outline"` to `save_figure()` / `export_figure()`; the save-time mode is scoped and recorded. PDF font type is enforced at save time too. See [typography-export.md](typography-export.md) for coverage limits and the bilingual benchmark.

## Validation

Run [scripts/test_easyplot_py.py](../scripts/test_easyplot_py.py) after changing the Python runtime. For a user figure, run the generated `.py` script, inspect the final-size PNG, and inspect the vector output when available. Automated rendering does not establish scientific validity, accessibility certification, or journal acceptance.
