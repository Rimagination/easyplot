# Bilingual typography and export

Use for mixed scripts, missing glyphs, editable vectors or R/Python export maintenance. These defaults do not imply a journal profile.

## Decode before plotting

Keep source, CSV and sidecars in UTF-8. In R use `source(..., encoding="UTF-8")`, `read.csv(..., fileEncoding="UTF-8", check.names=FALSE)` and explicit UTF-8 text connections or `writeLines(enc2utf8(text), ..., useBytes=TRUE)`. Verify codepoints and file round trips; console mojibake alone is insufficient evidence of corruption.

Windows R >=4.2 needs a UCRT-compatible UTF-8 locale before source parsing. In the tested environment an inherited Unix `C.UTF-8` was rejected, leaving the `C` locale and corrupting literal Chinese. `--encoding=UTF-8` alone did not repair that state. When needed, use:

```text
python scripts/easyplot_run_r.py --rscript "<R installation>/bin/Rscript.exe" figure.R <arguments>
```

The launcher starts a vanilla R child with UTF-8 source encoding and a Windows-compatible UTF-8 locale. It changes no parent/global environment, system language or installed font. `--vanilla` bypasses startup profiles; declare a custom library with `--library <existing directory>` or environment explicitly. Other operating systems retain their locale. It cannot repair previously corrupted data. Never hide encoding/startup warnings.

## Font roles

- Declare Latin/Greek, CJK/mixed-label and italic/bold roles. Check the actual venue; there is no universal academic Chinese font mandate.
- R: `easyplot_font_info("Arial", text, italic=TRUE)` checks an installed family and glyph indices for that face; a missing family/glyph is an error. Record the resolved path/style and apply the family in the corresponding `element_text()`/geometry.
- Python: `publication_context(font_family="Arial", cjk_family="Microsoft YaHei", glyphs=all_labels)` uses a declared ordered chain. `check_font_glyphs(text, families, weight=..., style=...)` checks other faces. A missing explicitly requested CJK family errors; a missing primary Latin family uses the declared installed fallback and reports it.
- Supplied-text cmap checks do not cover later-added text, prove shaping, or validate separate MathText/TeX fonts. Inspect device fallback, rendered glyphs, superscripts, weight and clipping.
- A simple R theme uses one family per text object: an entire mixed Chinese/English axis label can use one CJK-capable family. Do not call that whole string Arial. The benchmark records this distinction; Python uses per-glyph fallback.

## Export choices

| Path | Setting | Boundary |
| --- | --- | --- |
| R PNG | `png_device="auto"` | Prefer installed ragg, then Cairo, then native. Native Windows mappings remain device-specific. |
| R PDF | `pdf_device="cairo"` (default) | Broader UTF-8/font embedding; verify output streams. `"pdf"` is an explicit legacy option, not a multilingual embedding guarantee. |
| R SVG | `svg_text="outline"` (backward-compatible default) | Cairo paths; no editable text. `"editable"` requires svglite and fails clearly when unavailable. |
| Python PDF | Save-time Type 42, core fonts disabled | Applies outside the style context too; inspect delivered font streams. |
| Python SVG | `svg_text="editable"` or `"outline"` | Mode is scoped at save time and recorded. Editable text needs receiving-viewer fonts; paths sacrifice text editing/search. |

R Cairo devices can round both dimensions to integer points. A tested 180 × 86 mm request produced 179.9167 × 85.725 mm. The R manifest distinguishes requested and device-observed size; rounding exceeding 0.2 mm warns. Inspect the file as well. Do not stretch an SVG header or falsify PDF dimensions to pass QA. Integer-point dimensions (the benchmark uses 177.8 × 127 mm) avoid this quantization; an exact venue-required fractional-point canvas needs a separately verified device/postprocessing path. The screening tolerance is an EasyPlot choice, not a publisher allowance.

Raster dimensions round to whole pixels. Python scoped export neutralizes global `savefig.bbox="tight"` to preserve page size. Exports retain per-file temporary writes and default overwrite refusal; bundles are not cross-file transactions.

For one-figure exports, verify the PDF has exactly one page. `easyplot_draw()` lets ggplot/patchwork create that page once; opening a grid page before `print()` can otherwise leave a blank first page that PNG previews conceal.

## Repeatable evidence

After changing these paths, run `test_easyplot_py.py`, `test_easyplot_templates.R`, `test_easyplot_typography.R` (R tests via the UTF-8 launcher), and `test_easyplot_qa.py`. Unchanged analysis tests need not run in a font-only iteration.

`demo_typography.py <new-directory> --rscript <Rscript> [--r-library <library>]` creates one synthetic dataset with Chinese paths/columns, then renders the same four-panel figure in Python and R. It writes external bilingual captions, PNG/PDF/SVG, explicit SVG modes, manifests, panel-region measurements and metadata audits. If svglite is absent the R SVG is explicitly outlined. This tests typography/export, not statistical engines or pixel-identical backends.

Inspect final-size PNGs and vector previews, panel alignment, both physical dimensions, PDF embedding and text extraction, and SVG text/path structure. Extraction and resource checks are evidence, not full glyph certification. No fonts or packages are bundled, uploaded or installed by these helpers.

## Primary references

Relevant sections reviewed 2026-09-23: [R locales](https://stat.ethz.ch/R-manual/R-devel/library/base/html/locales.html) (UCRT/encoding), [R Cairo devices](https://stat.ethz.ch/R-manual/R-devel/library/grDevices/html/cairo.html) (UTF-8, embedding, raster fallback), [Matplotlib fonts](https://matplotlib.org/stable/users/explain/text/fonts.html) (fallback, subsetting, SVG), [svglite](https://svglite.r-lib.org/reference/svglite.html) (text sizing/viewer requirements), [systemfonts glyphs](https://systemfonts.r-lib.org/reference/glyph_info.html). Local wrappers use these ideas without copying source. Live docs may describe newer versions than the installed libraries.
