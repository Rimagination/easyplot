# UTF-8 source fixture: invoke through easyplot_run_r.py on Windows.
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE))
source(file.path(dirname(script), "easyplot_templates.R"), encoding = "UTF-8")
stopifnot(isTRUE(l10n_info()[["UTF-8"]]))
label <- "中文标签 α μ − 生物量"
stopifnot(identical(utf8ToInt(substr(label, 1, 2)), c(20013L, 25991L)))
output <- tempfile("easyplot-typography-")
dir.create(output)
output <- file.path(output, "中文路径")
dir.create(output)
data <- data.frame(处理 = c("对照", "处理"), 生物量 = c(1.5, 2.2), check.names = FALSE)
csv <- file.path(output, "中文数据.csv")
write.csv(data, csv, row.names = FALSE, fileEncoding = "UTF-8")
back <- read.csv(csv, fileEncoding = "UTF-8", check.names = FALSE)
stopifnot(identical(data, back))
caption <- "图注：模拟数据，仅用于验证。"
caption_path <- file.path(output, "图注.txt")
writeLines(enc2utf8(caption), caption_path, useBytes = TRUE)
stopifnot(identical(readLines(caption_path, encoding = "UTF-8"), caption))
expect_error <- function(expr) stopifnot(inherits(tryCatch(force(expr), error = identity), "error"))
expect_error(easyplot_font_info("EasyPlot-absent-font", "A"))
expect_error(easyplot_font_info("Arial", "中文"))
font <- easyplot_font_info("Microsoft YaHei", label)
stopifnot(font$checked_glyphs > 5, font$resolved_family == "Microsoft YaHei")
latin <- easyplot_font_info("Arial", "R. erythropolis", italic = TRUE)
stopifnot(grepl("Italic", latin$style))
plot <- ggplot2::ggplot(data, ggplot2::aes(x = 处理, y = 生物量)) +
  ggplot2::geom_col(fill = "#C6D4EA", colour = "#333333", linewidth = 0.25) +
  easyplot_scientific_theme(base_family = "Microsoft YaHei") + ggplot2::labs(y = label)
svg_mode <- if (requireNamespace("svglite", quietly = TRUE)) "editable" else "outline"
result <- easyplot_export(plot, file.path(output, "双语图"), formats = c("png", "pdf", "svg"),
                          width_mm = 177.8, height_mm = 127, dpi = 120, svg_text = svg_mode,
                          provenance = list(font = font, caption = caption))
stopifnot(all(file.info(result$outputs)$size > 100))
manifest <- jsonlite::read_json(result$manifest, simplifyVector = TRUE)
stopifnot(manifest$svg_text == svg_mode, manifest$devices$pdf == "cairo", manifest$provenance$caption == caption)
expect_error(easyplot_export(plot, file.path(output, "双语图")))
expect_error(easyplot_save(plot, file.path(output, "invalid.png"), width_mm = Inf))
expect_error(easyplot_save(plot, file.path(output, "invalid.svg"), svg_text = "unknown"))
if (svg_mode == "outline") {
  expect_error(easyplot_save(plot, file.path(output, "editable.svg"), svg_text = "editable"))
} else {
  svg <- readLines(result$outputs[[3]], encoding = "UTF-8", warn = FALSE)
  stopifnot(any(grepl("<text", svg, fixed = TRUE)), any(grepl(label, svg, fixed = TRUE)))
}
# Isolated fault injection: both replacement paths must preserve old bytes.
runtime <- new.env(parent = globalenv())
source(file.path(dirname(script), "easyplot_templates.R"), local = runtime, encoding = "UTF-8")
bytes <- function(path) readBin(path, "raw", n = file.info(path)$size)
pdf_path <- result$outputs[[2L]]
old_pdf <- bytes(pdf_path)
runtime$file.rename <- function(from, to) FALSE
expect_error(runtime$easyplot_save(plot, pdf_path, width_mm = 177.8, height_mm = 127, overwrite = TRUE))
stopifnot(file.exists(pdf_path), identical(bytes(pdf_path), old_pdf))
rm("file.rename", envir = runtime)
stopifnot(identical(runtime$easyplot_save(plot, pdf_path, width_mm = 177.8, height_mm = 127, overwrite = TRUE), pdf_path))
old_manifest <- bytes(result$manifest)
runtime$file.rename <- function(from, to) {
  if (endsWith(to, ".manifest.json")) FALSE else base::file.rename(from, to)
}
expect_error(runtime$easyplot_export(plot, file.path(output, "双语图"), formats = "pdf", width_mm = 177.8,
                                    height_mm = 127, overwrite = TRUE))
stopifnot(file.exists(result$manifest), identical(bytes(result$manifest), old_manifest))
rm("file.rename", envir = runtime)
replaced <- runtime$easyplot_export(plot, file.path(output, "双语图"), formats = "pdf", width_mm = 177.8,
                                    height_mm = 127, overwrite = TRUE, provenance = list(replacement_check = TRUE))
stopifnot(isTRUE(jsonlite::read_json(replaced$manifest)$provenance$replacement_check))
stopifnot(length(list.files(output, all.files = TRUE, pattern = "^\\.easyplot-")) == 0L)
cat("EasyPlot UTF-8, font, export and replacement-failure checks passed; SVG mode:", svg_mode, "\n")
