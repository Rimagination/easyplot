# Minimal executable check for EasyPlot's scientific template runtime.

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1L) stop("Run this file with Rscript.", call. = FALSE)
script_path <- sub("^--file=", "", script_arg)
skill_root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = TRUE)
source(file.path(skill_root, "scripts", "easyplot_templates.R"), local = TRUE)

set.seed(42)

spatial_data <- expand.grid(
  x = seq_len(5),
  y = seq_len(4),
  scenario = c("baseline", "treated"),
  KEEP.OUT.ATTRS = FALSE,
  stringsAsFactors = FALSE
)
spatial_data$value <- with(
  spatial_data,
  x + y + ifelse(scenario == "treated", 2, 0) + rnorm(nrow(spatial_data), sd = 0.1)
)
spatial_plot <- easyplot_spatial_small_multiples(
  spatial_data,
  facet = "scenario",
  preserve_aspect = FALSE,
  fill_label = "synthetic signal"
)

heatmap_data <- expand.grid(
  feature = paste0("feature_", seq_len(6)),
  sample = paste0("sample_", seq_len(4)),
  KEEP.OUT.ATTRS = FALSE,
  stringsAsFactors = FALSE
)
heatmap_data$value <- rnorm(nrow(heatmap_data))
heatmap_plot <- easyplot_omics_heatmap(heatmap_data, fill_label = "synthetic z")

effect_data <- data.frame(
  feature = paste0("feature_", seq_len(6)),
  estimate = c(-0.8, -0.2, 0.1, 0.35, 0.65, 1.0),
  lower = c(-1.1, -0.6, -0.25, 0.05, 0.3, 0.7),
  upper = c(-0.5, 0.2, 0.45, 0.65, 1.0, 1.3),
  condition = rep(c("control", "treated"), 3),
  stringsAsFactors = FALSE
)
effect_plot <- easyplot_omics_effects(
  effect_data,
  lower = "lower",
  upper = "upper",
  condition = "condition",
  condition_colours = c(control = "#8D8D8D", treated = "#568FC3"),
  x_label = "synthetic effect"
)

nodes <- data.frame(
  id = c("input", "process", "output"),
  x = c(0, 1, 2),
  y = c(0, 0, 0),
  label = c("input", "process", "output"),
  kind = c("measurement", "mechanism", "measurement"),
  stringsAsFactors = FALSE
)
edges <- data.frame(from = c("input", "process"), to = c("process", "output"))
schematic_plot <- easyplot_data_schematic(
  nodes,
  edges,
  node_colours = c(measurement = "#FBDDD7", mechanism = "#C6D4EA")
)

panel_spec <- data.frame(
  panel_id = c("spatial", "heatmap", "effects", "schematic"),
  role = c("overview", "matrix", "validation", "mechanism"),
  geometry = c("raster", "heatmap", "interval", "schematic"),
  scale = c("shared spatial", "feature x sample", "effect", "diagram"),
  guide_owner = c("spatial", "heatmap", "effects", "none"),
  stringsAsFactors = FALSE
)
plate <- easyplot_scientific_plate(
  panels = list(
    spatial = spatial_plot,
    heatmap = heatmap_plot,
    effects = effect_plot,
    schematic = schematic_plot
  ),
  panel_spec = panel_spec,
  ncol = 2
)

stopifnot(inherits(plate, "easyplot_composite"))
stopifnot(identical(attr(plate, "easyplot_panel_names"), panel_spec$panel_id))
stopifnot(identical(attr(plate, "easyplot_panel_spec")$role, panel_spec$role))
if (requireNamespace("patchwork", quietly = TRUE)) {
  stopifnot(inherits(plate, "patchwork"))
  stopifnot(identical(attr(plate, "easyplot_alignment")$method, "patchwork"))
}

spatial_fixed_plot <- easyplot_spatial_small_multiples(
  spatial_data,
  facet = "scenario",
  preserve_aspect = TRUE
)
fixed_plate <- easyplot_scientific_plate(
  panels = list(map = spatial_fixed_plot, context = schematic_plot),
  ncol = 2
)
stopifnot(identical(attr(fixed_plate, "easyplot_alignment")$fixed_aspect_panels, "map"))

omics_plate <- easyplot_omics_evidence_plate(
  heatmap_data = heatmap_data,
  effect_data = effect_data,
  effect_args = list(
    lower = "lower",
    upper = "upper",
    condition = "condition",
    condition_colours = c(control = "#8D8D8D", treated = "#568FC3")
  ),
  ncol = 2
)
stopifnot(inherits(omics_plate, "easyplot_composite"))

requested_output <- Sys.getenv("EASYPLOT_TEST_OUTPUT", unset = "")
output_path <- if (nzchar(requested_output)) {
  requested_output
} else {
  file.path(tempdir(), "easyplot-scientific-plate.png")
}
easyplot_save(plate, output_path, width_mm = 180, height_mm = 140, dpi = 120)
stopifnot(file.exists(output_path), file.info(output_path)$size > 1000)
output_stem <- tools::file_path_sans_ext(output_path)
pdf_path <- paste0(output_stem, ".pdf")
svg_path <- paste0(output_stem, ".svg")
easyplot_save(plate, pdf_path, width_mm = 180, height_mm = 140)
easyplot_save(plate, svg_path, width_mm = 180, height_mm = 140)
stopifnot(
  file.exists(pdf_path),
  file.info(pdf_path)$size > 1000,
  file.exists(svg_path),
  file.info(svg_path)$size > 1000
)

export_stem <- file.path(tempdir(), "easyplot-export-bundle")
exported <- easyplot_export(
  plate,
  export_stem,
  formats = c("png", "pdf", "svg"),
  width_mm = 180,
  height_mm = 140,
  dpi = 120,
  provenance = list(synthetic = TRUE, seed = 42)
)
stopifnot(
  length(exported$outputs) == 3L,
  all(file.exists(exported$outputs)),
  all(file.info(exported$outputs)$size > 1000),
  file.exists(exported$manifest),
  file.info(exported$manifest)$size > 100
)
overwrite_error <- tryCatch(
  {
    easyplot_export(plate, export_stem, formats = c("png"), dpi = 120)
    FALSE
  },
  error = function(error) TRUE
)
stopifnot(overwrite_error)

cat("EasyPlot scientific template runtime checks passed\n")
