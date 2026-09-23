# EasyPlot publication preflight

Use this reference for journal-targeted figures, multi-panel compositions, or deliverables intended for manuscript submission. For a quick exploratory plot, the minimal final check in `SKILL.md` is sufficient.

## Figure brief

Before coding, record a compact brief:

- **Claim:** the conclusion the figure should make visible.
- **Evidence role:** observation, replicate, group summary, model estimate, time point, image, or schematic.
- **Panel roles:** hero panel, supporting quantitative panel, context panel, or mechanism panel.
- **Data contract:** variables, units, factor order, replicate unit, uncertainty definition, exclusions, and transformations.
- **Destination:** exact journal, article type, submission phase, final width, height, format, and intended medium.

Keep the brief close to the script or in the delivery notes. A style reference cannot supply missing data, statistical results, or provenance.

## Text placement and typography

- Keep figure number, figure title, figure caption, statistical methods, and source/provenance notes outside the image by default.
- Keep axis titles, tick labels, panel tags, direct labels, scale bars, and necessary in-panel descriptors on the canvas.
- If a user or venue explicitly requires an in-figure title or caption, record that exception in the delivery notes and keep it visually subordinate to the evidence.
- Record the journal's Latin/Greek font rule, CJK or other non-Latin fallback, final text size, panel-label size, and embedding/editability expectation.
- Verify actual glyph coverage and rendered fallback for every script present. A named font in the R script does not prove that the target device contains all required glyphs.

## Check levels

### Core checks for every publication output

- Render at the intended physical dimensions in millimetres.
- Confirm the expected groups, observations, factor order, units, and scale transformation.
- Check clipping, label collisions, legend placement, error-bar extent, and annotation placement.
- Confirm that figure-level title/caption text is outside the image unless an explicit exception is recorded.
- Inspect a final-size raster preview and the editable vector output when available.
- Record source data, transformations, exclusions, uncertainty, software versions, device, DPI, and output paths.

### Extended checks for named journals or complex multi-panel figures

- Load the exact journal profile and record whether it is verified or provisional.
- Check panel alignment and shared plot-area geometry; document deliberate exemptions.
- For a four-panel plate, inspect the left/right panel boundaries and top/bottom panel boundaries at final size. Keep guides and axes local when units differ; collect them only when the scales and semantics are shared. Record any fixed-aspect map exemption.
- Check text and line sizes at final output size, editable text, font fallback, and grayscale/color-vision readability.
- Check Latin/Greek and CJK/non-Latin glyph coverage, mixed-script baseline/weight consistency, and any journal-specific font or embedding rule.
- Check a shared color semantic across panels and use labels, shapes, linetypes, or hatching when color alone carries a distinction.
- Interpret palette warnings in the plot context: labelled category positions can identify bar/box groups; crossing curves need traceable identities. Treat `delta CIE L* < 10` as a heuristic and record the smallest relevant change, or the existing adequate cues. A common dark outline provides boundaries, not group identity. Inspect any darker stroke palette separately from the pastel fills.
- Check that statistical annotations have a named analysis or supplied result, with n and uncertainty definitions available in the caption or notes.
- Inspect the assembled figure at final size after export. Keep automated QA output alongside the figure, not as a substitute for visual inspection.
- For dense mechanistic or omics plates, verify the evidence ladder: context/design, observation, quantitative summary, and validation/mechanism each have a declared role. Confirm that the hero panel is readable and that local guides are not being collected solely to imitate a source figure.
- For map-led plates, verify projection/extent/aspect, colour limits, missing-value mask, scale-bar units, and the meaning of any smoothed trajectory. Treat rainbow ramps, decorative basemaps, and independently rescaled comparable maps as warnings requiring an explicit scientific reason.
- If a source-figure teaching card is produced, check that its title, DOI, palette strip, and curator metadata are exported as a separate wrapper and are absent from the manuscript-ready figure.

The runtime alignment contract follows the [patchwork layout guide](https://patchwork.data-imaginist.com/articles/guides/layout.html) and the [cowplot alignment guide](https://wilkelab.org/cowplot/articles/aligning_plots.html). The venue-facing layout principle is consistent with Nature guidance to use a neat, space-efficient arrangement and let panel content and legibility determine panel size ([building and exporting figure panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)).

## External-source boundary

External figure skills may be consulted for general ideas about evidence hierarchy, panel roles, export metadata, or QA. EasyPlot keeps those ideas as local instructions.

- Do not install, clone, register startup/session hooks for, or auto-update an external figure-skill repository during ordinary plotting.
- Do not synchronize external skill directories or introduce their package/dependency graph into EasyPlot.
- Do not copy palettes, templates, assets, or journal claims from a visual reference based on similarity alone. Check provenance and licensing for any explicitly requested reuse.
- Treat repository-specific “Nature style” or “publication quality” labels as design guidance. Journal compliance comes from the selected profile and the current official author guidance.

The review of [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) informed the workflow boundaries above. EasyPlot adopts only the useful ideas around figure contracts, panel QA, final-size inspection, and provenance. Its visual defaults, assets, runtime hooks, auto-update scripts, and internal routing are excluded.

## Delivery note

Use a short note such as:

```text
Profile: nature / science_provisional / none
Final size: <width> × <height> mm
Core QA: dimensions, groups/order, clipping, collisions, final-size preview
Extended QA: alignment, editable text, contrast, annotation/provenance review
Warnings: <none or list>
Source data and script: <path or archive member>
```

Automated reports and style presets are evidence of completed checks only. They do not prove scientific validity, accessibility certification, or acceptance by a journal.
