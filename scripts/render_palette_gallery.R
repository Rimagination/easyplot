# Render quantitative colour specifications as a local guide, not a manuscript figure.
args <- commandArgs(trailingOnly = TRUE)
overwrite <- "--overwrite" %in% args
only_arg <- grep("^--only=", args, value = TRUE)
wanted <- if (length(only_arg)) strsplit(sub("^--only=", "", only_arg[[1L]]), ",", fixed = TRUE)[[1L]] else NULL
args <- args[!grepl("^--", args)]
if (length(args) < 1L) stop("Usage: render_palette_gallery.R OUTPUT_DIR [REGISTRY]")
source_files <- Filter(Negate(is.null), lapply(sys.frames(), function(frame) frame$ofile))
script_path <- if (length(source_files)) tail(source_files, 1L)[[1L]] else sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[[1L]])
skill_dir <- normalizePath(file.path(dirname(script_path), ".."), winslash = "/")
source(file.path(skill_dir, "scripts/easyplot_templates.R"), encoding = "UTF-8")
registry_path <- if (length(args) > 1L) args[[2L]] else file.path(skill_dir, "assets/palettes.json")
registry <- jsonlite::read_json(registry_path, simplifyVector = FALSE)
out <- args[[1L]]
dir.create(out, recursive = TRUE, showWarnings = FALSE)
palettes <- registry$palettes
names(palettes) <- vapply(palettes, `[[`, character(1), "id")
is_extension <- function(p) "extension" %in% unlist(p$tags)
core <- Filter(function(p) !is_extension(p), palettes)
ink <- "#29343B"
muted <- "#6D7B85"
font <- "Microsoft YaHei"
actual_labels <- c(vapply(core, `[[`, character(1), "label"), vapply(core, `[[`, character(1), "id"),
  unlist(lapply(core, function(p) p$colour_names)),
  "分类顺序发散循环多段原色名称组合由策划色值来自未改色源未评估有来源有条件慎用色觉模拟")
font_info <- easyplot_font_info(font, paste(actual_labels, collapse = " "))

contrast_text <- function(hex) {
  rgb <- grDevices::col2rgb(hex) / 255
  linear <- ifelse(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055)^2.4)
  lum <- colSums(linear * c(.2126, .7152, .0722))
  ifelse((lum + .05) / .05 >= 1.05 / (lum + .05), "#000000", "#FFFFFF")
}
kind_labels <- c(qualitative = "分类", sequential = "顺序", diverging = "发散", cyclic = "循环", multisequential = "多段")
cvd_labels <- c(reported = "色觉设计有来源", conditional = "色觉适用有条件", not_assessed = "色觉未评估", not_recommended = "色觉任务慎用")

make_sheet <- function(entries, title, subtitle) {
  items <- list()
  add <- function(item) items[[length(items) + 1L]] <<- item
  txt <- function(label, x, y, size = 9, col = ink, just = "left", family = font) {
    add(grid::textGrob(label, x = x, y = y, just = just,
      gp = grid::gpar(fontfamily = family, fontsize = size, col = col)))
  }
  txt(title, .035, .959, 20)
  txt(subtitle, .035, .923, 9, muted)
  large <- length(entries) == 1L && entries[[1L]]$kind == "qualitative" && length(entries[[1L]]$colours) > 24L
  for (i in seq_along(entries)) {
    p <- entries[[i]]
    column <- (i - 1L) %% 3L
    row <- (i - 1L) %/% 3L
    x <- .035 + column * .322
    y <- .87 - row * .204
    w <- if (large) .93 else .294
    colours <- unlist(p$colours)
    txt(p$label, x, y, 10.5)
    txt(p$id, x, y - .025, 7, muted, family = "Arial")
    if (p$kind == "qualitative") {
      cols <- if (p$family == "china") 3L else if (large) 10L else if (length(colours) <= 8L) 4L else if (length(colours) <= 12L) 5L else 6L
      rows <- ceiling(length(colours) / cols)
      tile_h <- if (large) .055 else min(.044, .116 / rows)
      tile_w <- w / cols
      x_pos <- x + (((seq_along(colours) - 1L) %% cols) + .5) * tile_w
      y_pos <- y - .067 - ((seq_along(colours) - 1L) %/% cols) * (tile_h + .002)
      add(grid::rectGrob(x = x_pos, y = y_pos, width = tile_w - .002, height = tile_h,
                         gp = grid::gpar(col = NA, fill = colours)))
      text_size <- if (large) 9 else if (length(colours) > 24L) 4.7 else 6.5
      add(grid::textGrob(colours, x = x_pos, y = y_pos - if (p$family == "china") .009 else 0,
                        gp = grid::gpar(fontfamily = "Arial", fontsize = text_size, col = contrast_text(colours))))
      if (p$family == "china") {
        add(grid::textGrob(unlist(p$colour_names), x = x_pos, y = y_pos + .009,
                          gp = grid::gpar(fontfamily = font, fontsize = 6.8, col = contrast_text(colours))))
      }
      if (!is.null(p$cvd$by_n)) {
        status_labels <- c(reported = "友好", conditional = "有条件", not_recommended = "谨慎", not_assessed = "未评估")
        status <- unlist(p$cvd$by_n)
        line <- paste(paste0(names(status), "色", status_labels[status]), collapse = " / ")
        txt(line, x, y - .155, 5.2, muted)
      }
    } else {
      add(grid::rasterGrob(matrix(colours, nrow = 1), x = x + w / 2, y = y - .081,
                           width = w, height = .046, interpolate = FALSE))
      add(grid::rectGrob(x = x + w / 2, y = y - .081, width = w, height = .046,
                         gp = grid::gpar(fill = NA, col = "#DEE3E6", lwd = .3)))
      positions <- floor(seq(0, length(colours) - 1L, length.out = 3L) + .5) + 1L
      for (j in 1:3) txt(colours[[positions[[j]]]], x + c(0, w / 2, w)[[j]], y - .118,
                         7, muted, just = c("left", "centre", "right")[[j]], family = "Arial")
      if (p$family == "china") {
        txt(paste(unlist(p$colour_names)[1:4], collapse = " / "), x, y - .150, 6.4, muted)
        txt(paste(unlist(p$colour_names)[5:7], collapse = " / "), x, y - .171, 6.4, muted)
      } else {
        txt(sprintf("%s / %d stored colours / %s", kind_labels[[p$kind]], length(colours), cvd_labels[[p$cvd$status]]),
            x, y - .156, 6.7, muted)
      }
    }
  }
  txt("EASYPLOT  /  唯一 ID 可直接用于 easyplot_palette()；色觉友好声明仍需按图检查", .035, .035, 7.5, muted)
  grid::gTree(children = do.call(grid::gList, items))
}

pick <- function(ids) unname(palettes[intersect(ids, names(palettes))])
selected <- list(
  "01-ggsci-journals" = list(
    entries = pick(c("ggsci.npg.nrc", "ggsci.aaas.default", "ggsci.nejm.default", "ggsci.lancet.lanonc",
                     "ggsci.jama.default", "ggsci.bmj.default", "ggsci.jco.default", "ggsci.d3.category10",
                     "ggsci.uchicago.default", "ggsci.locuszoom.default", "ggsci.cosmic.hallmarks_light", "ggsci.startrek.uniform")),
    title = "ggsci / 原版科研常用配色", subtitle = "官方固定色值与顺序 · 标题下方为 EasyPlot 唯一 ID · 期刊名表示配色灵感"),
  "02-china-original" = list(
    entries = unname(Filter(function(p) p$family == "china" && p$kind == "qualitative", core)),
    title = "东方原色 / 十二套分类组合", subtitle = "每个 HEX 均来自 2kil 原色 · 保留原色名 · 组合与方案名由 EasyPlot 策划，供审美选择"),
  "03-china-stepped" = list(
    entries = unname(Filter(function(p) p$family == "china" && p$kind != "qualitative", core)),
    title = "东方原色 / 分级色带", subtitle = "仅使用来源原色，保持有限分级 · 顺序色表示大小，青朱用于有意义的中心值"),
  "04-cvd-friendly" = list(
    entries = pick(c("cud.okabe_ito", "tol.bright", "brewer.Set2", "colorspace.dark3",
                     "viridis.viridis", "cetcolor.cbl1", "cetcolor.cbtl1",
                     "colorspace.green_brown", "colorspace.blue_red3", "cetcolor.cbd1", "cetcolor.cbtd1")),
    title = "色觉友好 / 按图形语义选用", subtitle = "红绿、蓝黄专用表与经典候选 · Set2 依类别数标示范围（详见离线目录） · 仍需搭配形状、线型和标签"),
  "05-classics" = list(
    entries = pick(c("brewer.Set1", "brewer.Set2", "brewer.Set3", "brewer.Dark2", "brewer.Paired", "brewer.Pastel1",
                     "brewer.Blues", "brewer.YlGnBu", "brewer.RdBu", "brewer.PRGn", "matplotlib.tab10", "matplotlib.coolwarm")),
    title = "科研经典 / 分类与数值", subtitle = "ColorBrewer 原生分级 · Matplotlib 经典色表 · 按数据含义选择，而非只按色彩喜好")
)

for (stem in names(selected)) {
  if (!is.null(wanted) && !stem %in% wanted) next
  entry <- selected[[stem]]
  sheet <- make_sheet(entry$entries, entry$title, entry$subtitle)
  easyplot_export(sheet, file.path(out, stem), width_mm = 304.8, height_mm = 254,
    dpi = 300, formats = "png", overwrite = overwrite, provenance = list(registry = registry_path, version = registry$version,
      palette_ids = vapply(entry$entries, `[[`, character(1), "id"), purpose = "Palette guide", font = font_info))
}

# Compact original/protan/deutan/tritan/grayscale screen for discrete candidates.
cvd_ids <- intersect(c("cud.okabe_ito", "tol.bright", "tol.vibrant", "tol.muted", "tol.high_contrast", "tol.medium_contrast"), names(palettes))
if (length(cvd_ids) && (is.null(wanted) || "06-cvd-simulation" %in% wanted)) {
  cvd_items <- list()
  add <- function(x) cvd_items[[length(cvd_items) + 1L]] <<- x
  label <- function(x, y, text, size = 9, just = "left") add(grid::textGrob(text, x = x, y = y, just = just,
      gp = grid::gpar(fontfamily = font, fontsize = size, col = ink)))
  label(.035, .953, "色觉模拟 / 保留真实差异与局限", 19)
  label(.035, .900, "colorspace / severity = 1 / linear RGB；灰度为 desaturate() 预览。模拟有边界，标签与点形仍然重要。", 8.5)
  headers <- c("原色", "Protan", "Deutan", "Tritan", "灰度")
  for (j in 1:5) label(.263 + (j - 1L) * .157, .812, headers[[j]], 10, "centre")
  for (i in seq_along(cvd_ids)) {
    p <- palettes[[cvd_ids[[i]]]]
    colours <- unlist(p$colours)
    views <- list(colours, colorspace::protan(colours, severity = 1, linear = TRUE),
                  colorspace::deutan(colours, severity = 1, linear = TRUE),
                  colorspace::tritan(colours, severity = 1, linear = TRUE), colorspace::desaturate(colours))
    y <- .724 - (i - 1L) * .107
    label(.035, y, p$id, 8)
    for (j in 1:5) add(grid::rasterGrob(matrix(views[[j]], nrow = 1), x = .263 + (j - 1L) * .157,
                                      y = y, width = .141, height = .052, interpolate = FALSE))
  }
  easyplot_export(grid::gTree(children = do.call(grid::gList, cvd_items)), file.path(out, "06-cvd-simulation"),
    formats = "png", width_mm = 304.8, height_mm = 177.8, dpi = 300, overwrite = overwrite,
    provenance = list(palettes = cvd_ids, package = "colorspace", version = as.character(packageVersion("colorspace")),
                      severity = 1, linear = TRUE, certification = FALSE))
}

# One guarded multi-page PDF containing every core palette, no repeated preview selections.
if (!is.null(wanted) && !"atlas" %in% wanted) quit(status = 0L)
pdf_path <- file.path(out, "palette-atlas.pdf")
manifest_path <- file.path(out, "palette-atlas.manifest.json")
if (any(file.exists(c(pdf_path, manifest_path))) && !overwrite) stop("Refusing atlas overwrite")
temp_pdf <- tempfile(".atlas-", tmpdir = out, fileext = ".pdf")
families <- unique(vapply(core, `[[`, character(1), "family"))
pages <- list()
grDevices::cairo_pdf(temp_pdf, width = 12, height = 10, family = font, onefile = TRUE)
tryCatch({
  for (family in families) {
    entries <- unname(Filter(function(p) p$family == family, core))
    large_entries <- Filter(function(p) p$kind == "qualitative" && length(p$colours) > 24L, entries)
    small_entries <- Filter(function(p) !(p$kind == "qualitative" && length(p$colours) > 24L), entries)
    chunks <- c(if (length(small_entries)) split(small_entries, ceiling(seq_along(small_entries) / 12L)) else list(),
                lapply(large_entries, function(p) list(p)))
    for (j in seq_along(chunks)) {
      title <- sprintf("%s / %d of %d", family, j, length(chunks))
      sheet <- make_sheet(chunks[[j]], title, "完整核心目录 · 每套名称、唯一 ID、原始顺序；iTerm 扩展见可搜索 HTML")
      easyplot_draw(sheet)
      pages[[length(pages) + 1L]] <- list(title = title, ids = unname(lapply(chunks[[j]], `[[`, "id")))
    }
  }
  grDevices::dev.off()
  if (!file.rename(temp_pdf, pdf_path)) stop("Could not finalize atlas")
}, error = function(e) {
  if (grDevices::dev.cur() > 1L) grDevices::dev.off()
  if (file.exists(temp_pdf)) unlink(temp_pdf)
  stop(e)
})
jsonlite::write_json(list(registry = registry_path, version = registry$version, pages = pages,
  width_mm = 304.8, height_mm = 254, font = font_info, core_palettes = length(core),
  excluded_extensions = sum(vapply(palettes, is_extension, logical(1))),
  licence_note = "See each palette source. 2kil swatches are local preview only pending redistribution terms."),
  manifest_path, pretty = TRUE, auto_unbox = TRUE)
cat("Rendered", length(pages), "atlas pages covering", length(core), "core palettes\n")
