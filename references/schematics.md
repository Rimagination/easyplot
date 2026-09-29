# EasyPlot schematic contract

EasyPlot treats a mechanism, workflow, architecture, or graphical-abstract schematic as a geometric layer that can sit beside quantitative evidence. The schematic has its own vocabulary: nodes describe concepts or stages, edges describe relationships, and coordinates describe layout. It does not replace statistical evidence and it does not authorize inventing a mechanism that the supplied study does not support.

## When to use it

Use `data_schematic` when the reader needs a compact explanation of a process, intervention path, experimental design, model architecture, or relationship between panels. Use an ordinary plot when the marks represent measured observations, estimates, distributions, or model diagnostics.

For a manuscript figure, use the formal default. A hand-drawn or illustrated treatment can be added later as a clearly labelled teaching/graphical-abstract variant; it is not the EasyPlot publication default.

## Data contract

`nodes` must contain:

- `id`: unique stable identifier used by edges;
- `x`, `y`: finite numeric layout coordinates;
- `label`: displayed node text;
- `kind`: optional semantic class used for fill colours.

`edges` is optional. When supplied, it must contain `from` and `to`, each referring to an existing node ID. Keep scientific meaning in the data: do not add a node or arrow only to imitate a reference image.

```r
nodes <- data.frame(
  id = c("input", "process", "readout"),
  x = c(0, 1, 2), y = c(0, 0, 0),
  label = c("Input", "Process", "Readout"),
  kind = c("measurement", "mechanism", "measurement")
)
edges <- data.frame(
  from = c("input", "process"),
  to = c("process", "readout")
)

source("scripts/easyplot_templates.R")
lint <- easyplot_schematic_lint(nodes, edges)
stopifnot(lint$ok)
plot <- easyplot_data_schematic(
  nodes, edges,
  node_colours = c(measurement = "#FBDDD7", mechanism = "#C6D4EA")
)
```

## Geometry rules

- Declare coordinates instead of relying on text-order side effects. Manual coordinates make panel composition reproducible and let the author align a schematic with quantitative panels.
- EasyPlot trims straight arrows against a rectangular node envelope. `node_width`, `node_height`, and `edge_pad` define that envelope; tune them when labels are substantially longer than the default.
- For publication-scale tuning, use `arrow_length_mm`, `edge_linewidth`, `label_padding`, `label_radius`, and `node_border_width`. Keep labels short or use explicit line breaks; do not compensate for a crowded mechanism by shrinking the entire figure.
- Keep `preserve_aspect = FALSE` for layout coordinates. Use `TRUE` only when geometric proportions have meaning.
- Keep arrows behind nodes and use one restrained edge colour by default. Use colour for semantic node classes, with the selected EasyPlot palette recorded in the script.
- For a dense graph, split it into meaningful stages or panels. A large number of crossings is a layout problem; adding more colours rarely solves it.
- Export SVG/PDF when editability matters. The returned plot carries an `easyplot_schematic` attribute containing the lint result, node table, trimmed edge coordinates, and geometry settings.

## Lint before export

`easyplot_schematic_lint()` reports:

- missing required columns;
- non-unique, empty, or missing node IDs;
- non-finite or non-numeric coordinates;
- edges that refer to missing nodes;
- approximate rectangular node overlaps;
- self-loop and duplicate-edge warnings.

Lint is a geometry and reference check. It does not verify that a mechanism is scientifically valid, that an icon is semantically correct, or that the final figure is legible at a journal's physical size. Inspect the rendered export at final size and run the normal EasyPlot publication preflight for submission work.

## Four-panel composition

Use `easyplot_scientific_plate()` to place a schematic beside evidence panels. Give the schematic an explicit `panel_spec` role such as `mechanism`, keep its local axes hidden, and keep its labels inside the panel. Do not collect guides from a schematic with quantitative panels. The schematic should explain the evidence, not compete with the hero result.

## Scope of the adopted practice

The design contract is inspired by the public `sketch-infographic` project: reusable geometry, stable node/edge references, clearance-aware connections, and linting before rendering. EasyPlot keeps its formal scientific visual language, R/ggplot2 backend, journal-aware export and existing palette registry. The current module intentionally excludes rough-stroke generation, icon packs, and a second Node rendering runtime.
