# EasyPlot shared style guide

This file is the visual contract shared by the built-in templates. Treat values as defaults that can be overridden by a user's venue, existing project theme, or explicit request.

## `publication_pastel` defaults

```r
EASYPLOT_FONT <- "Times New Roman"  # declare and verify an installed fallback
EASYPLOT_TEXT_PT <- 8
EASYPLOT_PANEL_TITLE_PT <- 8  # only for a true in-panel descriptor when justified
EASYPLOT_AXIS_LINE_MM <- 0.28
EASYPLOT_DATA_LINE_MM <- 0.45
EASYPLOT_BAR_WIDTH <- 0.62
EASYPLOT_ERRORBAR_WIDTH <- 0.12
```

- Use a white panel and white figure background.
- Keep the left and bottom axes as the default structural frame. Remove top/right borders and avoid a heavy grid unless the scale needs a faint guide.
- Use a fine dark-grey or black bar outline; use heavier strokes for error bars and data lines than for the frame.
- Do not place a figure number, figure title, or figure caption on the plot by default. Use panel tags, axis labels, direct labels, or a short in-panel descriptor only when the figure structure or venue calls for it.
- Put manuscript-facing figure titles/captions, statistical methods, and source notes in the caption or sidecar text. Use an explicit italic style for Latin species names rather than relying on a font's automatic behavior.
- Put units in axis labels. Use mathematical notation for exponents and Greek symbols; keep a readable fallback for CJK text.
- Use lowercase panel tags by default (`a`, `b`, `c`) and keep them clear of axis decorations.

## Reference palette

The following palette is adapted from the supplied visual reference:

```r
easyplot_pastel <- c(
  mist        = "#F4F9FC",
  blush       = "#FBDDD7",
  coral       = "#F59092",
  sand        = "#E5D8D4",
  rose        = "#BB9491",
  powder_blue = "#C6D4EA",
  steel_blue  = "#568FC3"
)
```

Use names tied to semantic groups where possible, then map them with an explicit `scale_fill_manual()` or `scale_colour_manual()`. Keep the same semantic color across panels. Add a neutral grey for controls or references when the palette is not enough.

When colour-vision robustness is requested or required, prefer a clearly documented palette such as Okabe–Ito and check its supported class count. Keep colour as the primary cue; add another encoding only if the selected palette and geometry still leave groups ambiguous. Do not silently replace a user's requested colours; report the contrast or grayscale consequence and offer the fallback.

### Choose cues for the geometry

- Labelled bars/boxes: fixed category positions plus readable tick labels usually identify groups. Keep the pastel fills and fine dark outlines; add patterns only when group identity still relies on the legend colour (for example, repeated or stacked groups).
- Multiple curves: use one stable colour per series with a common solid line by default. Follow crossings and close runs at final size; if colour alone no longer makes identity clear, add one targeted cue such as direct end labels, markers, or line styles. Do not stack cues automatically. A common outline increases visibility but does not distinguish one curve from another.
- Scatter: use one common point shape and group colour by default. Tune point size/transparency or use faceting to manage overlap; add group-specific shapes only when colour-only identity remains unclear in the intended viewing condition.
- Keep fill and stroke roles explicit. The optional `easyplot_lines` palette is CK `#707983`, Rh `#AB4B53`, Ps `#98671F`, RP `#356D9A`; it keeps the colour families of the condition fills while making thin marks darker. Record this deliberate role change in the figure script. Darkening alone need not improve pairwise grayscale separation.
- `delta CIE L* < 10` is a tunable EasyPlot heuristic, not a WCAG cutoff or a journal rule. Preserve and report numerical flags, but do not automatically decorate a colour-view figure in response to a palette-only flag. If monochrome output or another explicit access requirement applies, address that requirement with a better-suited palette or one minimal, targeted cue.
- For a demonstration, compare identical data, axes, figure dimensions, and grayscale values. Change only the declared cues in the corrected grayscale panel. Put the optional darker-colour version in a separate export so the visual comparison remains interpretable.

R uses named `scale_colour_manual()`, `scale_fill_manual()`, `scale_shape_manual()` and `scale_linetype_manual()` mappings. Python uses `palette`, `fill_palette`, `markers` and `linestyles` in `plot_timecourse()`. Both backends follow the same rules above.

## Bar-chart details

- Prefer `geom_col()` for pre-computed summaries and `geom_bar(stat = "summary")` only when the summary rule is visible in the script.
- Use `geom_errorbar()` with a declared lower and upper bound. Centered `mean ± SD` is one option; it is not interchangeable with SE or a confidence interval.
- Compute the annotation y-position from the upper uncertainty bound plus a scale-aware clearance. Do not hard-code a fixed fraction of the y range across linear and log axes.
- Use letters or stars only when the associated result is available. Keep annotation layers independent from the main aesthetics with `inherit.aes = FALSE` when appropriate.
- Add raw points with controlled jitter and transparency when showing replicate spread. Make their sample unit clear.

## Typography, scales, and export

For Unicode source loading, checked font roles, SVG modes and actual file dimensions, follow [typography-export.md](typography-export.md). The Windows R launcher applies UTF-8 before source parsing; the export helpers do not repair already-corrupted text.

- Make font roles explicit: Latin/Greek family, CJK or other non-Latin fallback, final text size, panel-label size, and line width. Verify each requested family on the target device; if a glyph family is absent, choose an installed fallback and state it.
- Apply the exact journal profile for font family, character coverage, minimum size, and embedding/editability rules. Do not assume that an English/Latin font rule covers Chinese, Japanese, Korean, Greek, or mathematical glyphs.
- Inspect the final-size figure for missing glyphs, fallback substitution, mixed baselines, and inconsistent weights. Keep figure-level title/caption text outside the image unless explicitly required.
- With R's native Windows raster device, a family listed by `systemfonts` may still need a `grDevices::windowsFonts()` mapping in the figure process. Verify that device path and resolve its warnings; do not claim the requested font was used solely because it is installed. This mapping is process-local, with no global font installation required.
- Use `scale_y_log10()` only for positive values and label the axis with the transformed meaning or scientific notation expected by the reader.
- Prefer final physical dimensions in millimetres. A single-panel figure commonly starts around 85–95 mm wide; a multi-panel figure commonly starts around 170–190 mm wide, then adjusts after inspection.
- Export with an explicit device, width, height, background, and DPI. Keep a vector output for editing when supported.
- Inspect the final-size raster, not only an oversized viewer preview. Check tick labels, superscripts, italic text, legend coverage, annotation clearance, and clipping.

## Semantic and accessibility checks

- Choose qualitative, sequential, diverging, or cyclic color according to the variable meaning. Avoid using a sequential palette for categories or a diverging palette without a meaningful center.
- Audit foreground/background contrast at the rendered size. Use colour as the default group cue when it is clear in the intended medium; add redundant encoding only for an explicit requirement or demonstrated ambiguity.
- Show missing, censored, excluded, and out-of-range values deliberately. Keep gaps visible in ordered data unless interpolation or model prediction is explicitly part of the figure.
- Add concise alt text for every delivered plot. For a complex multi-panel figure, add a longer description and retain an underlying data table when the destination supports it.
- Treat grayscale and color-vision previews as screening tools. They do not establish accessibility or journal compliance by themselves.

## Provenance and venue boundaries

- Keep source-data paths or identifiers, transformations, aggregation, normalization, smoothing/binning, uncertainty definition, missing-data treatment, random seeds, and package versions available in the script or a sidecar manifest.
- Use explicit physical dimensions, device, format, background, DPI, and overwrite policy. Do not use `bbox_inches = "tight"`-style cropping when it changes the intended page size without saying so.
- Separate static and interactive deliverables. A tooltip does not replace visible labels, alt text, keyboard access, a data alternative, or a static fallback.
- Do not claim publisher compliance from this preset. Verify live requirements only after the user identifies the exact journal, article type, and submission phase.
