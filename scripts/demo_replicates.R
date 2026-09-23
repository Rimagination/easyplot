# Synthetic acceptance example only; never use these values as research data.
# Run: Rscript demo_replicates.R <new-output-directory>
# The installed skill owns the analysis and plotting helpers; no external skill.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Usage: Rscript demo_replicates.R <output-directory>", call. = FALSE)
script_file <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1L])
script_dir <- dirname(normalizePath(script_file, winslash = "/", mustWork = TRUE))
source(file.path(script_dir, "easyplot_analysis.R"), encoding = "UTF-8")
source(file.path(script_dir, "easyplot_templates.R"), encoding = "UTF-8")
for (package in c("ggplot2", "patchwork", "jsonlite", "systemfonts")) {
  if (!requireNamespace(package, quietly = TRUE)) stop("Required installed package: ", package)
}
font <- "Arial"
if (!font %in% systemfonts::system_fonts()$family) stop("Arial is not installed; choose and record an available font.")
# Windows' native PNG device needs its own process-local family mapping.
if (.Platform$OS.type == "windows") {
  do.call(grDevices::windowsFonts, setNames(list(grDevices::windowsFont(font)), font))
}
output_dir <- args[[1L]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
output_dir <- normalizePath(output_dir, winslash = "/", mustWork = TRUE)
stem <- file.path(output_dir, "replicates_and_contrasts")
targets <- c(paste0(stem, c(".png", ".svg", ".manifest.json")),
             file.path(output_dir, c("raw_readings.csv", "unit_means.csv", "contrasts.csv",
                                    "analysis.json", "caption.md")))
if (any(file.exists(targets))) stop("Refusing to overwrite demo outputs; choose a new directory.", call. = FALSE)

conditions <- c("Control", "Low", "High", "Comparator")
batches <- paste0("B", 1:5)
baseline <- c(8.1, 10.4, 9.7, 11.2, 8.8)
changes <- cbind(Control = rep(0, 5), Low = c(-.1, .4, .8, 1.2, .3),
                 High = c(1.1, 1.7, .8, 2.2, 1.4), Comparator = c(-.8, .9, -.2, .7, -.5))
raw <- do.call(rbind, lapply(seq_along(conditions), function(j) {
  do.call(rbind, lapply(seq_along(batches), function(i) {
    nr <- 2L + (i + j) %% 3L
    data.frame(batch = batches[i], condition = conditions[j], reading = seq_len(nr),
               response = baseline[i] + changes[i, j] + seq(-.4, .4, length.out = nr),
               stringsAsFactors = FALSE)
  }))
}))
seed <- 20260923L
set.seed(seed)
raw <- raw[sample.int(nrow(raw)), ]
rownames(raw) <- NULL
original <- raw
summary <- easyplot_summarize_replicates(
  raw, group = "condition", value = "response", unit = "batch", replicate = "reading",
  design = "repeated", missing = "error"
)
units <- do.call(rbind, lapply(summary$summary, function(row) as.data.frame(row, stringsAsFactors = FALSE)))
stopifnot(identical(raw, original), summary$n_units == 5L, summary$n_unit_conditions == 20L,
          summary$n_input == nrow(raw), summary$n_used == nrow(raw), summary$n_missing == 0L)
expected <- baseline[match(units$unit, batches)] + changes[cbind(match(units$unit, batches), match(units$group, conditions))]
stopifnot(isTRUE(all.equal(units$value, unname(expected), tolerance = 1e-12)))

# Three contrasts and their family are declared before evaluating any p-value.
contrast_groups <- conditions[-1L]
contrast_labels <- paste(contrast_groups, "- Control")
reports <- lapply(contrast_groups, function(treatment) {
  easyplot_analyze_two_groups(
    units[units$group %in% c("Control", treatment), ], group = "group", value = "value", unit = "unit",
    order = c("Control", treatment), design = "paired", missing = "error", confidence = .95
  )
})
names(reports) <- contrast_labels
adjusted <- easyplot_adjust_pvalues(
  vapply(reports, function(r) r$test$p_value, numeric(1)), labels = contrast_labels,
  method = "holm", family = "Three planned treatment-versus-control contrasts for response", alpha = .05
)
results <- do.call(rbind, lapply(seq_along(reports), function(i) {
  r <- reports[[i]]
  stopifnot(r$n_pairs == 5L, r$n_removed == 0L, r$test$df == 4)
  data.frame(comparison = contrast_labels[i], estimate = r$effect$estimate,
             ci_low = r$effect$ci_low, ci_high = r$effect$ci_high,
             interval = "pointwise 95% CI; unadjusted", n_pairs = r$n_pairs,
             p_raw = r$test$p_value, p_holm = adjusted$results[[i]]$p_adjusted,
             stringsAsFactors = FALSE)
}))
stopifnot(isTRUE(all.equal(results$estimate, unname(colMeans(changes)[-1L]), tolerance = 1e-12)))

# Display positions carry no analytical weight. All data layers keep true y.
offsets <- setNames(seq(-.20, .20, length.out = 5), batches)
fills <- setNames(c("#F59092", "#568FC3", "#E5D8D4", "#BB9491", "#C6D4EA"), batches)
strokes <- setNames(c("#AB4B53", "#356D9A", "#72635A", "#76544F", "#687EA0"), batches)
shapes <- setNames(21:25, batches)
plot_raw <- raw
plot_raw$x <- match(raw$condition, conditions) + offsets[raw$batch] + (raw$reading - 2.5) * .018
plot_units <- units
plot_units$x <- match(units$group, conditions) + offsets[units$unit]
library(ggplot2)
base <- easyplot_scientific_theme(base_size = 8, base_family = font) +
  theme(legend.position = "bottom", legend.title = element_blank(), legend.text = element_text(size = 7),
        legend.key.width = grid::unit(5, "mm"), legend.spacing.x = grid::unit(0, "mm"))
observations <- ggplot() +
  geom_line(data = plot_units, aes(x, value, group = unit, colour = unit), linewidth = .25, alpha = .6) +
  geom_point(data = plot_raw, aes(x, response, colour = batch), size = .7, alpha = .55, show.legend = FALSE) +
  geom_point(data = plot_units, aes(x, value, fill = unit, shape = unit), size = 2.3, stroke = .3, colour = "#303030") +
  scale_fill_manual(values = fills, breaks = batches) + scale_shape_manual(values = shapes, breaks = batches) +
  scale_colour_manual(values = strokes, breaks = batches, guide = "none") +
  scale_x_continuous(breaks = 1:4, labels = conditions, limits = c(.6, 4.4)) +
  labs(x = "Condition", y = "Response (a.u.)") + base
plot_results <- results
plot_results$y <- rev(seq_len(nrow(results)))
effects <- ggplot(plot_results, aes(estimate, y)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "#7A7A7A", linewidth = .28) +
  geom_segment(aes(x = ci_low, xend = ci_high, yend = y), linewidth = .5, colour = "#356D9A") +
  geom_point(shape = 21, size = 2.5, fill = "#C6D4EA", colour = "#303030", stroke = .3) +
  scale_y_continuous(breaks = plot_results$y, labels = contrast_labels, limits = c(.5, 3.5)) +
  labs(x = "Paired mean change (a.u.)", y = NULL) + base + theme(legend.position = "none")
panels <- list(observations = easyplot_add_panel_tag(observations, "a"),
               effects = easyplot_add_panel_tag(effects, "b"))
spec <- data.frame(panel_id = names(panels), role = c("technical and unit-level observations", "planned paired effects"),
                   geometry = c("raw points, unit means, paired lines", "point and interval"),
                   scale = c("response", "mean difference"), guide_owner = c("local batch guide", "comparison labels"))
plate <- easyplot_scientific_plate(panels, spec, ncol = 2L, widths = c(1, 1), guides = "keep", axes = "keep")
caption <- c(
  "# Synthetic example: repeated batches and planned contrasts", "",
  "All values are constructed for teaching and acceptance checks, not research results.",
  "a: Five independent batches each measured in four conditions, with 2-4 technical readings per cell. Small dots are readings; larger symbols are unit means. Colour and shape identify the batch; lines connect matched unit means only.",
  "b: Paired mean treatment-minus-Control changes. Intervals are unadjusted pointwise 95% confidence intervals, with five complete pairs per contrast.",
  "The declared family contains Low, High and Comparator versus Control, with Holm FWER adjustment. Both raw and adjusted p-values are retained in contrasts.csv. P-value adjustment does not make the displayed intervals simultaneous.",
  "Batches receive equal weight. Technical reading counts are not inferential sample sizes. Independence and distributional assumptions come from the declared design; five batches limit precision. No missing data, imputation, outlier exclusions or automatic significance stars.",
  "Title, caption and methods are outside the canvas. Size: 180 x 86 mm; Arial 8 pt; PNG at 300 dpi and SVG. No target journal. SVG fonts may be outlined by the device; editable text and journal compliance are not claimed.", "",
  "Alt text: Left, technical readings and linked means from five batches across four conditions. Right, three treatment-control mean differences with pointwise confidence intervals."
)
write.csv(raw, file.path(output_dir, "raw_readings.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(units, file.path(output_dir, "unit_means.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(results, file.path(output_dir, "contrasts.csv"), row.names = FALSE, fileEncoding = "UTF-8")
jsonlite::write_json(list(synthetic = TRUE, summary = summary, contrasts = reports, multiplicity = adjusted),
                     file.path(output_dir, "analysis.json"), pretty = TRUE, auto_unbox = TRUE, null = "null", digits = 17)
writeLines(enc2utf8(caption), file.path(output_dir, "caption.md"), useBytes = TRUE)
exported <- easyplot_export(
  plate, stem, formats = c("png", "svg"), width_mm = 180, height_mm = 86, dpi = 300, background = "white",
  provenance = list(synthetic = TRUE, source_data = file.path(output_dir, "raw_readings.csv"),
                    analysis = file.path(output_dir, "analysis.json"), caption = file.path(output_dir, "caption.md"),
                    replicate_unit = "Independent batch; five batches measured at all four conditions",
                    transformations = "Arithmetic mean within batch/condition, then equally weighted paired contrasts",
                    uncertainty = "Pointwise 95% t confidence intervals; not multiplicity adjusted",
                    multiplicity = list(method = "holm", m = 3L, family = adjusted$family),
                    missingness = "No missing input; both stages use error policy",
                    seed = seed, font = list(family = font, size_pt = 8),
                    palette = list(batch_fills = as.list(fills), batch_strokes = as.list(strokes), batch_shapes = as.list(shapes)),
                    software = setNames(lapply(c("ggplot2", "patchwork", "jsonlite", "systemfonts"),
                                              function(p) as.character(utils::packageVersion(p))),
                                        c("ggplot2", "patchwork", "jsonlite", "systemfonts")),
                    preflight = list(profile = "none", alignment = attr(plate, "easyplot_alignment"), panel_spec = spec,
                                     figure_title_caption = "Outside canvas"))
)
if (length(warnings())) print(warnings())
cat("Synthetic demo checks passed:", nrow(raw), "readings,", nrow(units), "unit/condition means, 5 paired units, 3 contrasts.\n")
cat(paste(c(exported$outputs, exported$manifest), collapse = "\n"), "\n")
