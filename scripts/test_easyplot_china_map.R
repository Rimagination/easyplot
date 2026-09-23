# Minimal executable check for EasyPlot's China site-map runtime.

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1L) stop("Run this file with Rscript.", call. = FALSE)
script_path <- sub("^--file=", "", script_arg)
skill_root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = TRUE)
source(file.path(skill_root, "scripts", "easyplot_china_map.R"), local = TRUE)

sites <- data.frame(
  site_id = paste0("site_", 1:8),
  longitude = c(87.6, 91.1, 103.8, 108.9, 113.2, 116.4, 121.5, 110.3),
  latitude = c(43.8, 29.7, 36.1, 34.3, 23.1, 39.9, 31.2, 19.2),
  prediction = c(78, 12, 35, 18, 55, 10, 82, 42),
  stringsAsFactors = FALSE
)

map <- suppressWarnings(easyplot_china_site_map(
  sites,
  lon = "longitude",
  lat = "latitude",
  id = "site_id",
  value = "prediction",
  mode = "continuous",
  legend_title = "Predicted intensity",
  value_trans = "log10",
  value_breaks = c(10, 20, 40, 80)
))

audit <- attr(map, "easyplot_china_map_audit")
stopifnot(
  inherits(map, "patchwork"),
  identical(audit$mode, "continuous"),
  identical(audit$n_sites, 8L),
  identical(audit$unique_coordinates, 8L),
  identical(audit$land_boundary_colour, "#333333"),
  identical(audit$coastline_colour, "#2F7F9F")
)

invalid_coordinate_error <- tryCatch(
  {
    bad <- sites
    bad$longitude[1] <- NA_real_
    easyplot_china_site_map(bad, "longitude", "latitude", value = "prediction")
    FALSE
  },
  error = function(error) grepl("invalid coordinates", conditionMessage(error), fixed = TRUE)
)
stopifnot(invalid_coordinate_error)

categorical <- transform(
  sites,
  aridity_class = factor(rep(c("Arid", "Humid"), 4), levels = c("Arid", "Humid"))
)
categorical_map <- suppressWarnings(easyplot_china_site_map(
  categorical,
  lon = "longitude",
  lat = "latitude",
  id = "site_id",
  value = "aridity_class",
  mode = "categorical",
  legend_title = "Aridity class",
  categorical_palette = c(Arid = "#D8B365", Humid = "#01665E")
))
categorical_audit <- attr(categorical_map, "easyplot_china_map_audit")
stopifnot(
  inherits(categorical_map, "patchwork"),
  identical(categorical_audit$mode, "categorical"),
  identical(categorical_audit$n_sites, 8L)
)

missing_palette_error <- tryCatch(
  {
    categorical_without_palette <- transform(sites, class = rep(c("A", "B"), 4))
    easyplot_china_site_map(
      categorical_without_palette,
      "longitude", "latitude", value = "class", mode = "categorical"
    )
    FALSE
  },
  error = function(error) grepl("categorical_palette", conditionMessage(error), fixed = TRUE)
)
stopifnot(missing_palette_error)

requested_output <- Sys.getenv("EASYPLOT_TEST_OUTPUT", unset = "")
output_path <- if (nzchar(requested_output)) {
  requested_output
} else {
  file.path(tempdir(), "easyplot-china-site-map.png")
}
dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
suppressWarnings(ggplot2::ggsave(
  output_path,
  map,
  width = 200,
  height = 125,
  units = "mm",
  dpi = 120,
  bg = "white"
))
stopifnot(file.exists(output_path), file.info(output_path)$size > 10000)

cat("EasyPlot China site-map runtime checks passed: ", output_path, "\n", sep = "")
