# EasyPlot template registry

Choose the smallest template that answers the scientific question. The names below are stable handles for future requests and can be extended when a real use case justifies it.

Before selecting geometry, record the audience and medium, intended final width, source-data path, variable units, replicate unit, missing/censored-value rules, transformations, estimator, uncertainty, and output formats. This keeps a visually attractive template from hiding an unresolved evidence decision.

The registry is backend-neutral. Use the R runtime for the default R/ggplot2 path and the Python runtime when the user explicitly requests Python; the data contract and visual semantics remain the same.

## Data contract

Common columns are named here for clarity; use the user's actual names in the delivered script.

| Field | Meaning | Required |
| --- | --- | --- |
| `x` | primary categorical or numeric x variable | always |
| `y` | observed value or estimate | always |
| `group` | color/line/fill grouping variable | when multiple series exist |
| `facet` | panel or facet variable | when panels are needed |
| `lower`, `upper` | explicit uncertainty bounds | when uncertainty is shown |
| `error_type` | SD, SE, CI, percentile interval, or named model interval | when uncertainty is shown |
| `sig_label` | supplied letters, stars, or bracket result | optional |
| `replicate_id` | experimental/biological replicate unit | when raw points or summaries use replication |

Never infer `error_type` from column names alone. If the source only contains a single value per group, make a bar without error bars or request the missing uncertainty.

## `bar_pastel` — primary reference template

Use for independent groups or one-factor summaries where the reader compares group magnitudes.

- Geometry: narrow `geom_col()` bars, fine outline, `geom_errorbar()`, optional jittered raw points.
- Default fill: one named pastel color per group; use a neutral grey for the reference/control group when appropriate.
- Annotation: letters or stars above the upper interval bound, supplied by the user or a declared test.
- Scale: zero-baseline linear scale for ordinary amounts; positive `log10` scale for abundance or other multiplicative measurements when scientifically justified.
- Avoid: stacked bars unless the question is part-to-whole composition; 3D, gradients, decorative shadows, and unexplained axis breaks.

Compact implementation pattern:

```r
ggplot(summary_df, aes(x = group, y = estimate, fill = group)) +
  geom_col(width = EASYPLOT_BAR_WIDTH, colour = "#333333", linewidth = 0.25) +
  geom_errorbar(
    aes(ymin = lower, ymax = upper),
    width = EASYPLOT_ERRORBAR_WIDTH,
    linewidth = EASYPLOT_DATA_LINE_MM
  ) +
  geom_text(
    data = subset(summary_df, !is.na(sig_label)),
    aes(x = group, y = label_y, label = sig_label),
    inherit.aes = FALSE,
    family = EASYPLOT_FONT,
    size = 8 / ggplot2::.pt
  )
```

`label_y` must be computed from `upper` with a scale-aware offset. The snippet is a geometry pattern, not a complete script: add explicit factor order, named scales, labels, theme, data checks, and export calls.

## `bar_grouped` — two-factor grouped bars

Use when an x factor contains a second treatment, genotype, time, or condition factor and the interaction is visible through side-by-side bars.

- Use `position_dodge()` or `position_dodge2()` with one declared dodge width for bars, intervals, points, and labels.
- Map the second factor to fill and preserve its order with a factor or `breaks`.
- Keep one colour meaning across facets and panels. X positions and labels already identify the x factor; use colour for the second factor, adding another cue only if the grouped marks remain ambiguous at final size.
- Add a small bracket or letters only when the comparison set is clear.

## `box_jitter` — distributions with raw observations

Use when within-group spread, outliers, or replicate density matters more than a mean alone.

- Use a light pastel box/violin layer plus semi-transparent raw points.
- Show median and quartile structure explicitly; do not hide all observations behind a bar.
- For factorial designs, separate groups with stable x order and thin panel dividers rather than multiple competing legends.
- Place stars/brackets using a declared comparison table and reserve headroom for them.

## `timecourse` — repeated measurements over time

Use for time, dose, depth, or another ordered sequence.

- Use one stable colour per series, a common point shape, and solid lines by default; add a ribbon or interval only when its definition is known. Add group-specific markers or line styles only when colour-only identity is unclear under the intended viewing conditions.
- Preserve missing time points as gaps. Do not connect across missing observations without an explicit interpolation/model rule.
- Use a log y scale when the response spans orders of magnitude, and keep the axis ticks readable.
- Direct-label a small number of series when a legend would consume the data area.

## `multipanel` — composition of complementary panels

Use when the figure combines bars, distributions, time courses, or a schematic around one scientific message.

- Keep a shared palette, font, line hierarchy, and panel-tag convention.
- Keep the figure number, figure title, and figure caption outside the assembled image by default; use panel tags or concise in-panel descriptors only when they clarify panel roles.
- Align data-panel edges and collect guides only when the scales and semantics truly match.
- Give each panel a short purpose; use one figure-level note for shared uncertainty, test, transformation, and sample-size details.
- Render at final physical dimensions and inspect the composite. Do not shrink the data panels to make long captions fit inside the image.
- Add a figure-level alt text/long description and retain the underlying data table when the destination is web or interactive.

The supplied reference image is a good composition example: bar panels establish group differences, box/jitter panels show distributions, time-course panels show trajectories, and a schematic explains mechanism. EasyPlot should reuse the visual language while retaining the user's actual data and panel purpose.

## Scientific plate archetypes

These handles cover recurring real-figure structures observed across the full reference collection. They are composition templates layered on top of the geometry templates above; they do not authorize inventing missing panels or data.

### `scientific_plate` — story-driven mixed geometry

Use when a result needs several evidence types in one figure. Declare a `panel_id`, panel role, geometry, scale, guide owner, and shared encodings before assembly. Align comparable plot regions and let the narrative determine panel size.

### `china_site_map` — single national site or prediction map

Use when rows are projects, stations, samples or prediction sites with longitude and latitude. The default is one national hero map with equal-sized points and a South China Sea inset. Map a requested category or continuous result to point fill; keep the land neutral. Do not convert site rows into a synthetic province choropleth. Do not create `a`/`b` panels unless the scientific question explicitly compares two maps. The R implementation baseline is `easyplot_china_site_map()` in [scripts/easyplot_china_map.R](../scripts/easyplot_china_map.R).

### `spatial_small_multiples` — comparable maps or sections

Use when location, depth, time, or scenario is the comparison. Hold projection, extent, aspect ratio, colour limits, missing-value mask, and scale-bar convention constant unless a deliberate exception is stated. Keep local colour bars readable and avoid decorative basemaps that compete with the measured layer.

### `omics_evidence_plate` — matrix plus validation

Use for a heatmap or matrix supported by distributions, differential points, correlation, pathway, or enrichment panels. Reuse condition colours across annotations and plots, separate statistical significance from effect size, and make row/column ordering and filtering reproducible.

### `data_schematic` — quantitative evidence plus mechanism

Use when a mechanism, workflow, or experimental design is needed to interpret the data. Keep the schematic's symbols and arrows in a separate vocabulary from measured marks; label the connection to each data panel explicitly.

### `dense_mechanistic_plate` — evidence-ladder composition

Use when the figure combines a design/timeline, primary image or assay evidence, quantitative summaries, and a mechanism or validation layer. This is a composition contract over `easyplot_scientific_plate()`, not a new geometry. Declare panel roles in the order the reader should use them, promote one hero result, and keep every local scale interpretable at final size. Reuse condition semantics across bars, raw points, distributions, matrices, and schematic labels; never create a panel only to imitate a reference screenshot.

### `spatial_evidence_plate` — map plus summary plus trajectory

Use when maps, raster fields, regional estimates, and ordered trajectories answer one spatial question. Combine `easyplot_spatial_small_multiples()` with other panels through `easyplot_scientific_plate()`. Declare projection, extent, aspect ratio, colour limits, missing-value mask, scale-bar convention, and whether a smooth line is descriptive or model-based. Treat a fixed-aspect map as an intentional alignment exception and record it in the preflight note.

### `source_figure_card` — optional teaching wrapper

Use only for a slide, lab meeting, or reference library that intentionally displays a paper figure with title, DOI, citation, or palette notes. Keep it in a separate export path from manuscript figures. The wrapper is a presentation asset, not a journal style and not a replacement for the source figure's caption or provenance.

## Runnable scientific template layer

The R registry is implemented by [scripts/easyplot_templates.R](../scripts/easyplot_templates.R). Source it from a self-contained figure script; it does not calculate statistics, infer missing values, or create panels for which the user has not supplied evidence.

The Python static backend is implemented by [scripts/easyplot_py.py](../scripts/easyplot_py.py). Import it from a self-contained `.py` figure script when Python is requested. Its Matplotlib helpers follow the same evidence and export contract without requiring Seaborn.

### Four-panel alignment contract

easyplot_scientific_plate() uses patchwork when it is available because its default layout aligns plotting regions and axis dimensions across separate ggplot objects. It keeps guides and axes local by default; use guides = "collect" or axes = "collect" only when their semantics and scales are genuinely shared.

The Python equivalent, `make_scientific_plate()`, uses Matplotlib's `constrained_layout=True` with a physical-size canvas. Keep colorbars and legends local when panel units differ, and inspect the final-size composite because constrained layout cannot resolve every combination of fixed-aspect maps, long labels, and external annotations automatically.

- widths and heights control relative plotting regions. Leave them NULL when a panel uses coord_fixed(), coord_equal(), coord_polar(), or coord_sf() so the fixed aspect can be preserved.
- A fixed-aspect map is a deliberate alignment exception: it cannot simultaneously have an equal cell size and share every boundary with free-aspect plots. Give it an intentional row/column size and record the exception in the preflight note.
- For raster small multiples that are comparisons on a regular grid rather than geographic maps, set preserve_aspect = FALSE when a strict four-panel grid is the priority.
- Mechanism and workflow schematics use preserve_aspect = FALSE by default because their coordinates describe layout positions; set it to TRUE only when geometric proportions carry meaning.
- Keep guides = "keep" and axes = "keep" for panels with different units. Collect only duplicate/shared guides or truly identical axes.
- If patchwork is unavailable, the runtime uses a gtable fallback and marks the result with easyplot_alignment$method = "gtable-fallback"; inspect mixed-axis layouts manually.

This distinction follows the [patchwork layout guide](https://patchwork.data-imaginist.com/articles/guides/layout.html) and the [cowplot alignment guide](https://wilkelab.org/cowplot/articles/aligning_plots.html): alignment is a relationship between panel regions and selected axes, not simply equal outer cell widths.

| Handle | Runtime entry point | Output |
| --- | --- | --- |
| `scientific_plate` | `easyplot_scientific_plate()` | A patchwork composite (gtable fallback) with a validated `panel_spec` attribute. |
| `china_site_map` | `easyplot_china_site_map()` in `easyplot_china_map.R` | One China-wide point map with nested boundary buffers, dark-grey land boundaries, blue coastlines, a right-side guide and a lower-right South China Sea inset. |
| `spatial_small_multiples` | `easyplot_spatial_small_multiples()` | A faceted raster/heatmap with fixed aspect ratio and explicit missing-value colour. |
| `omics_evidence_plate` | `easyplot_omics_evidence_plate()` | A heatmap-led plate with optional effect and schematic panels. |
| `data_schematic` | `easyplot_data_schematic()` | A node-and-arrow `ggplot` for mechanism or workflow context. |
| `dense_mechanistic_plate` | `easyplot_scientific_plate()` with a role-first `panel_spec` | A declared evidence-ladder composition for dense biomedical, materials, and omics figures. |
| `spatial_evidence_plate` | `easyplot_scientific_plate()` plus `easyplot_spatial_small_multiples()` | A map-led composition with an explicit fixed-aspect and colour-limit contract. |
| `source_figure_card` | external layout wrapper, kept out of manuscript exports | A teaching/reference card with citation metadata and optional palette notes. |

Shared R helpers include `easyplot_add_panel_tag()`, `easyplot_draw()`, `easyplot_save()`, and `easyplot_export()`. The executable smoke test is [scripts/test_easyplot_templates.R](../scripts/test_easyplot_templates.R); its synthetic values are only for runtime checks and must not be reused as scientific results.
