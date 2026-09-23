# Opt-in synthetic palette demonstration, with no scientific claim.
# Rscript demo_dongfang.R output-dir [--overwrite]
# Inputs already present in output-dir:
# observations.csv: group, replicate, response, x, y
# trajectories.csv: group, time, estimate (illustrative trajectories, no CI)

args <- commandArgs(trailingOnly = TRUE)
overwrite <- "--overwrite" %in% args
args <- args[args != "--overwrite"]
if (length(args) != 1L || !nzchar(args[[1L]]) || startsWith(args[[1L]], "--")) {
  stop("Usage: demo_dongfang.R output-dir [--overwrite]", call. = FALSE)
}
output_dir <- normalizePath(args[[1L]], mustWork = TRUE)
script_arg <- grep("^--file=", commandArgs(), value = TRUE)[1L]
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE))
source(file.path(script_dir, "easyplot_templates.R"), encoding = "UTF-8")
source(file.path(script_dir, "easyplot_dongfang.R"), encoding = "UTF-8")
registry_path <- normalizePath(file.path(script_dir, "..", "assets", "dongfang.json"), mustWork = TRUE)
registry_version <- jsonlite::fromJSON(registry_path, simplifyVector = FALSE)$version
suppressPackageStartupMessages(library(ggplot2))

# Shared semantics, final geometry and reproducible display jitter.
groups <- c("A", "B", "C", "D")
fill_colours <- stats::setNames(dongfang_palette("danqing", 4), groups)
line_colours <- stats::setNames(dongfang_palette("danqing", 4, role = "line"), groups)
shapes <- c(A = 21, B = 24, C = 22, D = 23)
linetypes <- c(A = "solid", B = "dashed", C = "dotdash", D = "dotted")
font <- "Arial"
text_pt <- 8
width_mm <- 180
height_mm <- 135
dpi <- 300
seed <- 20260923L
ink <- "#303030"
if (!font %in% systemfonts::system_fonts()$family) {
  stop("The demo requires the installed Arial font.", call. = FALSE)
}
if (.Platform$OS.type == "windows") {
  grDevices::windowsFonts(Arial = grDevices::windowsFont("Arial"))
}

observations_path <- file.path(output_dir, "observations.csv")
trajectories_path <- file.path(output_dir, "trajectories.csv")
observations <- read.csv(observations_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
trajectories <- read.csv(trajectories_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
easyplot_require_columns(observations, c("group", "replicate", "response", "x", "y"), "observations")
easyplot_require_columns(trajectories, c("group", "time", "estimate"), "trajectories")
for (data in list(observations, trajectories)) {
  if (anyNA(data$group) || !setequal(data$group, groups)) {
    stop("Each input must contain exactly groups A, B, C and D.", call. = FALSE)
  }
}
if (anyNA(observations$replicate) || any(!nzchar(trimws(as.character(observations$replicate)))) ||
    anyDuplicated(observations[c("group", "replicate")])) {
  stop("Replicate IDs must be nonempty and unique within each group.", call. = FALSE)
}
numeric_columns <- c(observations[c("response", "x", "y")], trajectories[c("time", "estimate")])
if (!all(vapply(numeric_columns, function(x) is.numeric(x) && all(is.finite(x)), logical(1)))) {
  stop("Measurement/time columns must be numeric and finite; missing values are not imputed.", call. = FALSE)
}
if (anyDuplicated(trajectories[c("group", "time")])) {
  stop("Trajectory times must be unique within each group.", call. = FALSE)
}
observations$group <- factor(observations$group, levels = groups)
trajectories$group <- factor(trajectories$group, levels = groups)
if (any(table(observations$group) < 2L) || any(table(trajectories$group) < 2L)) {
  stop("Each group needs at least two replicates and two trajectory time points.", call. = FALSE)
}
trajectories <- trajectories[order(trajectories$group, trajectories$time), ]
response_by_group <- split(observations$response, observations$group)
summary_data <- data.frame(
  group = factor(groups, levels = groups),
  estimate = vapply(response_by_group, mean, numeric(1)),
  sd = vapply(response_by_group, stats::sd, numeric(1))
)

raw_points <- geom_point(
  data = observations, aes(group, response, fill = group, shape = group),
  inherit.aes = FALSE, position = position_jitter(width = 0.09, height = 0, seed = seed),
  size = 1.5, stroke = 0.25, colour = ink
)
bar <- ggplot(summary_data, aes(group, estimate, fill = group)) +
  geom_col(width = 0.62, colour = ink, linewidth = 0.25) +
  geom_errorbar(aes(ymin = estimate - sd, ymax = estimate + sd),
                width = 0.12, linewidth = 0.45, colour = ink) +
  raw_points + scale_y_continuous(breaks = seq(0, 8, 2), expand = expansion(mult = 0)) +
  coord_cartesian(ylim = c(0, 8.3)) +
  labs(x = "Group", y = "Response (a.u.)")
box <- ggplot(observations, aes(group, response, fill = group)) +
  geom_boxplot(width = 0.58, outlier.shape = NA, colour = ink, linewidth = 0.3) +
  raw_points + scale_y_continuous(breaks = seq(0, 8, 2), expand = expansion(mult = 0)) +
  coord_cartesian(ylim = c(0, 8.3)) +
  labs(x = "Group", y = "Response (a.u.)")
timecourse <- ggplot(trajectories, aes(time, estimate, group = group, colour = group)) +
  geom_line(aes(linetype = group), linewidth = 0.45) +
  geom_point(aes(fill = group, shape = group), size = 1.7, stroke = 0.3) +
  scale_linetype_manual(name = "Group", values = linetypes, limits = groups, drop = FALSE) +
  scale_x_continuous(breaks = c(0, 24, 48, 72)) +
  coord_cartesian(xlim = c(-3, 86), ylim = c(0.5, 5.1), expand = FALSE) +
  labs(x = "Time (h)", y = "Response (a.u.)")
scatter <- ggplot(observations, aes(x, y, colour = group, fill = group, shape = group)) +
  geom_point(size = 1.9, stroke = 0.3) +
  coord_cartesian(xlim = c(0, 3.5), ylim = c(0, 2.6), expand = FALSE) +
  labs(x = "Feature 1 (a.u.)", y = "Feature 2 (a.u.)")
shared_scales <- list(
  scale_colour_manual(name = "Group", values = line_colours, limits = groups, drop = FALSE),
  scale_shape_manual(name = "Group", values = shapes, limits = groups, drop = FALSE)
)
shared_theme <- easyplot_scientific_theme(base_size = text_pt, base_family = font) +
  theme(legend.position = "bottom", legend.title = element_blank(),
        legend.text = element_text(size = 7), legend.key.width = grid::unit(8, "mm"),
        legend.margin = margin(0, 0, 0, 0, unit = "pt"))
panels <- list(bar = bar, box = box, timecourse = timecourse, scatter = scatter)
for (index in seq_along(panels)) {
  panels[[index]] <- panels[[index]] + shared_scales + shared_theme +
    scale_fill_manual(name = "Group", values = if (index <= 2L) fill_colours else line_colours,
                      limits = groups, drop = FALSE)
  if (index <= 2L) panels[[index]] <- panels[[index]] + theme(legend.position = "none")
  panels[[index]] <- easyplot_add_panel_tag(panels[[index]], letters[index], base_size = text_pt)
}
panel_spec <- data.frame(
  panel_id = names(panels),
  role = c("group summary", "replicate distribution", "illustrative trajectory", "paired observations"),
  geometry = c("bar, SD and raw points", "box and raw points", "line and points", "scatter"),
  scale = c("response", "response", "estimate over time", "x and y"),
  guide_owner = c("category labels", "category labels", "local", "local")
)
plate <- easyplot_scientific_plate(
  panels, panel_spec, ncol = 2L, widths = c(1, 1), heights = c(1, 1),
  guides = "keep", axes = "keep", axis_titles = "keep"
)

# The existing SVG device resolves installed Arial; PNG provides the preview.
# Figure title, caption, data semantics and provenance remain in the manifest.
result <- easyplot_export(
  plate, file.path(output_dir, "danqing_four_panel_R"), formats = c("png", "svg"),
  width_mm = width_mm, height_mm = height_mm, dpi = dpi, background = "white",
  overwrite = overwrite,
  provenance = list(
    synthetic = TRUE,
    purpose = "Opt-in Dongfang palette trial; synthetic values demonstrate group encodings.",
    source_data = list(observations = observations_path, trajectories = trajectories_path),
    group_order = groups,
    palette = list(name = "danqing", registry_version = registry_version, registry_path = registry_path,
                   fill = as.list(fill_colours), line = as.list(line_colours)),
    colour_roles = "Bars/boxes use fill colours; timecourse and scatter use line colours.",
    shapes = as.list(shapes), linetypes = as.list(linetypes),
    observations_per_group = as.list(table(observations$group)),
    replicate_unit = "One input observation per group/replicate ID; synthetic arbitrary units.",
    transformations = "Arithmetic mean and sample SD of response within group; no other transformations.",
    uncertainty = "Bars: mean +/- one sample SD. Boxes: ggplot2 quartiles/1.5-IQR whiskers, all raw dots shown.",
    timecourse = "Input illustrative estimates joined in time order; no CI, fitting or inferred uncertainty.",
    missing_values = "Required missing/non-finite values and duplicate replicate/time keys are rejected.",
    seed = seed, jitter = "Display-only horizontal jitter, width 0.09, height 0.",
    font = list(family = font, size_pt = text_pt, legend_size_pt = 7),
    devices = list(png = "grDevices::png", svg = "grDevices::svg"),
    software = lapply(c("ggplot2", "patchwork", "jsonlite", "systemfonts"), function(package) {
      list(package = package, version = as.character(utils::packageVersion(package)))
    }),
    preflight = list(profile = "none", alignment = attr(plate, "easyplot_alignment"),
                     panel_spec = panel_spec, figure_title_caption = "Outside the canvas"),
    caption = paste(
      "Synthetic four-group Dongfang danqing demonstration. (a) Mean response +/- SD with raw replicates;",
      "(b) box plots with the same raw replicates; (c) illustrative trajectories without CI; (d) paired x/y observations.",
      "Named group colours and shapes are fixed across panels; curves additionally use named linetypes."
    ),
    alt_text = "Four aligned panels compare synthetic groups A-D through summary bars, distributions, trajectories and scatter points."
  )
)
cat(paste(c(result$outputs, result$manifest), collapse = "\n"), "\n", sep = "")
