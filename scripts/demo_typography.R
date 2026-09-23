# Same input tables as demo_typography.py; no new observations/statistical claims.
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE))
source(file.path(dirname(script), "easyplot_templates.R"), encoding = "UTF-8")
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Supply the benchmark directory from demo_typography.py")
root <- normalizePath(args[[1]], mustWork = TRUE)
output <- file.path(root, "R")
dir.create(output, showWarnings = FALSE)
read_table <- function(name) read.csv(file.path(root, "数据", name), fileEncoding = "UTF-8", check.names = FALSE)
raw <- read_table("原始观测.csv")
summary <- read_table("均值和标准差.csv")
curve <- read_table("时间序列.csv")
matrix <- read_table("热图.csv")
groups <- c("CK", "Rh", "Ps", "RP")
raw$处理 <- factor(raw$处理, groups)
summary$处理 <- factor(summary$处理, groups)
curve$处理 <- factor(curve$处理, groups)
matrix$处理 <- factor(matrix$处理, groups)
matrix$特征 <- factor(matrix$特征, paste0("M", 1:5))
labels <- list(x = "处理 Treatment", y1 = "生物量 Biomass (mg)", y2 = "生物量 Biomass (mg)",
               time = "时间 Time (h)", signal = "信号 Signal (μmol/L)", feature = "特征 Feature")
cjk <- "Microsoft YaHei"
font_info <- list(latin = easyplot_font_info("Arial", "CK Rh Ps RP abcd 0123456789 μ −"),
                  mixed_labels = easyplot_font_info(cjk, paste(unlist(labels), collapse = " ")))
fills <- c(CK = "#D8DDE2", Rh = "#D8898D", Ps = "#D6A15A", RP = "#6C9DC5")
lines <- c(CK = "#707983", Rh = "#AB4B53", Ps = "#98671F", RP = "#356D9A")
theme <- easyplot_scientific_theme(base_size = 8, base_family = "Arial") +
  ggplot2::theme(axis.title = ggplot2::element_text(family = cjk),
                 axis.text = ggplot2::element_text(size = 7.3),
                 legend.title = ggplot2::element_text(family = cjk, size = 7),
                 legend.text = ggplot2::element_text(size = 7),
                 legend.key.height = grid::unit(3, "mm"))
a <- ggplot2::ggplot(summary, ggplot2::aes(x = 处理, y = 均值, fill = 处理)) +
  ggplot2::geom_col(width = 0.62, colour = "#333333", linewidth = 0.25) +
  ggplot2::geom_errorbar(ggplot2::aes(ymin = 下限, ymax = 上限), width = 0.12, linewidth = 0.35) +
  ggplot2::geom_point(data = raw, ggplot2::aes(x = 位置, y = 生物量), inherit.aes = FALSE,
                       size = 1.05, colour = "#333333") +
  ggplot2::scale_fill_manual(values = fills, guide = "none") +
  ggplot2::scale_y_continuous(limits = c(0, 5), expand = ggplot2::expansion(mult = c(0, .02))) +
  ggplot2::labs(x = labels$x, y = labels$y1) + theme
b <- ggplot2::ggplot(raw, ggplot2::aes(x = 处理, y = 生物量, fill = 处理)) +
  ggplot2::geom_boxplot(width = 0.6, outlier.shape = NA, linewidth = 0.3) +
  ggplot2::geom_point(ggplot2::aes(x = 位置), size = 1.05, colour = "#333333") +
  ggplot2::scale_fill_manual(values = fills, guide = "none") +
  ggplot2::scale_y_continuous(limits = c(0, 5), expand = ggplot2::expansion(mult = c(0, .02))) +
  ggplot2::labs(x = labels$x, y = labels$y2) + theme
c <- ggplot2::ggplot(curve, ggplot2::aes(x = 时间, y = 信号, colour = 处理, shape = 处理, linetype = 处理)) +
  ggplot2::geom_line(linewidth = .45) + ggplot2::geom_point(size = 1.7) +
  ggplot2::geom_text(data = subset(curve, 时间 == 72), ggplot2::aes(label = 处理),
                     nudge_x = 4, hjust = 0, size = 7 / ggplot2::.pt, family = "Arial", show.legend = FALSE) +
  ggplot2::scale_colour_manual(values = lines, guide = "none") +
  ggplot2::scale_shape_manual(values = c(CK = 15, Rh = 16, Ps = 17, RP = 18), guide = "none") +
  ggplot2::scale_linetype_manual(values = c(CK = "dashed", Rh = "solid", Ps = "dotdash", RP = "dotted"), guide = "none") +
  ggplot2::scale_x_continuous(limits = c(0, 87), breaks = c(0, 24, 48, 72)) +
  ggplot2::scale_y_continuous(limits = c(0, 10), breaks = seq(0, 10, 2)) +
  ggplot2::labs(x = labels$time, y = labels$signal) + theme
d <- ggplot2::ggplot(matrix, ggplot2::aes(x = 处理, y = 特征, fill = 数值)) +
  ggplot2::geom_tile(colour = "white", linewidth = .3) +
  ggplot2::scale_y_discrete(limits = rev(levels(matrix$特征)), expand = c(0, 0)) +
  ggplot2::scale_x_discrete(expand = c(0, 0)) +
  ggplot2::scale_fill_gradientn(colours = c("#EFF3FF", "#6BAED6", "#08519C"), limits = c(0, 1), na.value = "#DDDDDD",
                                name = "Scaled\nvalue", breaks = c(0, .5, 1)) +
  ggplot2::labs(x = labels$x, y = labels$feature) + theme
panels <- Map(function(p, tag) easyplot_add_panel_tag(p, tag), list(a, b, c, d), letters[1:4])
names(panels) <- c("mean_sd", "distribution", "trajectory", "matrix")
plate <- easyplot_scientific_plate(panels, guides = "keep", axes = "keep")
svg_mode <- if (requireNamespace("svglite", quietly = TRUE)) "editable" else "outline"
exported <- easyplot_export(plate, file.path(output, "双语四联图"), formats = c("png", "pdf", "svg"),
                            width_mm = 177.8, height_mm = 127, dpi = 300, svg_text = svg_mode,
                            provenance = list(synthetic = TRUE, font = font_info, input_directory = file.path(root, "数据"),
                                              uncertainty = "sample SD, n=8 independent synthetic units per group",
                                              journal_profile = "none", caption = "../图注.md"))
if (svg_mode == "editable") {
  easyplot_export(plate, file.path(output, "双语四联图-outline"), formats = "svg", width_mm = 177.8,
                 height_mm = 127, svg_text = "outline", provenance = list(synthetic = TRUE, font = font_info))
}
# Measure actual grid panel viewports on a same-device render; no title/caption on canvas.
ragg::agg_capture(width = 177.8, height = 127, units = "mm", res = 300)
easyplot_draw(plate)
grid::grid.force()
viewports <- grid::grid.ls(viewports = TRUE, grobs = FALSE, print = FALSE)$name
viewports <- unique(viewports[grepl("^panel-[1-4]\\.", viewports)])
positions <- lapply(viewports, function(vp) {
  grid::seekViewport(vp)
  lower <- grid::deviceLoc(grid::unit(0, "npc"), grid::unit(0, "npc"), valueOnly = TRUE)
  upper <- grid::deviceLoc(grid::unit(1, "npc"), grid::unit(1, "npc"), valueOnly = TRUE)
  list(panel = sub("^panel-([1-4]).*", "\\1", vp), left = lower$x * 25.4, bottom = lower$y * 25.4,
       right = upper$x * 25.4, top = upper$y * 25.4)
})
grDevices::dev.off()
jsonlite::write_json(list(svg_text = svg_mode, panels_mm = positions, font = font_info),
                     file.path(output, "layout.json"), pretty = TRUE, auto_unbox = TRUE)
cat("R bilingual plate exported; SVG mode:", svg_mode, "\n")
