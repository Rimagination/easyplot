# EasyPlot scientific template runtime
#
# These functions keep the figure contract explicit while providing small,
# reusable building blocks for the scientific plate archetypes. They require
# ggplot2 and use gtable only for assembling already-created panels.

if (!requireNamespace("ggplot2", quietly = TRUE)) {
  stop("EasyPlot templates require the ggplot2 package.", call. = FALSE)
}

EASYPLOT_TEMPLATE_VERSION <- "0.3.0"

easyplot_font_info <- function(family, text = "", italic = FALSE, weight = "normal") {
  if (!requireNamespace("systemfonts", quietly = TRUE)) {
    stop("Font preflight requires systemfonts.", call. = FALSE)
  }
  if (length(family) != 1L || is.na(family) || !nzchar(family) ||
      !family %in% systemfonts::system_fonts()$family) {
    stop("Requested font family is not installed: ", family, call. = FALSE)
  }
  if (!isTRUE(l10n_info()[["UTF-8"]]) && any(grepl("[^ -~]", text))) {
    stop("Start R in a UTF-8 locale before reading the figure script; see easyplot_run_r.py.", call. = FALSE)
  }
  info <- systemfonts::font_info(family = family, italic = italic, weight = weight)
  glyphs <- unique(strsplit(paste(text, collapse = ""), "", fixed = TRUE)[[1L]])
  glyphs <- glyphs[!grepl("^[[:space:]]$", glyphs)]
  if (length(glyphs)) {
    coverage <- systemfonts::glyph_info(glyphs, path = info$path[[1L]], index = info$index[[1L]])
    absent <- coverage$glyph[coverage$index == 0L]
    if (length(absent)) {
      stop("Missing glyphs in ", family, ": ", paste(absent, collapse = " "), call. = FALSE)
    }
  }
  list(requested_family = family, resolved_family = info$family[[1L]],
       path = info$path[[1L]], index = info$index[[1L]], style = info$style[[1L]],
       checked_glyphs = length(glyphs),
       scope = "Declared text and face only; inspect device fallback and rendered export.")
}

easyplot_export_devices <- function(png_device = "auto", pdf_device = "cairo", svg_text = "outline") {
  png_device <- match.arg(png_device, c("auto", "ragg", "cairo", "native"))
  pdf_device <- match.arg(pdf_device, c("cairo", "pdf"))
  svg_text <- match.arg(svg_text, c("outline", "editable"))
  if (png_device == "auto") {
    png_device <- if (requireNamespace("ragg", quietly = TRUE)) "ragg" else if (capabilities("cairo")) "cairo" else "native"
  }
  list(png = png_device, pdf = pdf_device, svg = svg_text)
}

easyplot_require_columns <- function(data, columns, context = "data") {
  if (!is.data.frame(data)) {
    stop(context, " must be a data.frame.", call. = FALSE)
  }
  missing_columns <- setdiff(unique(columns), names(data))
  if (length(missing_columns) > 0L) {
    stop(
      context, " is missing required column(s): ",
      paste(missing_columns, collapse = ", "),
      call. = FALSE
    )
  }
  invisible(data)
}

easyplot_or <- function(x, y) {
  if (is.null(x)) y else x
}

easyplot_scientific_theme <- function(base_size = 8, base_family = "sans") {
  ggplot2::theme_classic(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      axis.line = ggplot2::element_line(linewidth = 0.28, colour = "#303030"),
      axis.ticks = ggplot2::element_line(linewidth = 0.28, colour = "#303030"),
      panel.grid = ggplot2::element_blank(),
      strip.background = ggplot2::element_blank(),
      strip.text = ggplot2::element_text(size = base_size, face = "plain"),
      legend.key = ggplot2::element_blank(),
      plot.title = ggplot2::element_blank(),
      plot.subtitle = ggplot2::element_blank(),
      plot.caption = ggplot2::element_blank(),
      plot.margin = ggplot2::margin(4, 4, 4, 4, unit = "pt")
    )
}

easyplot_add_panel_tag <- function(plot, tag, base_size = 8) {
  plot +
    ggplot2::labs(tag = tag) +
    ggplot2::theme(
      plot.tag = ggplot2::element_text(
        size = base_size,
        face = "plain",
        hjust = 0,
        vjust = 1
      ),
      plot.tag.position = c(0.01, 0.99),
      plot.margin = ggplot2::margin(5, 4, 4, 8, unit = "pt")
    )
}

easyplot_has_fixed_aspect <- function(plot) {
  if (!inherits(plot, "ggplot")) return(FALSE)
  coordinates <- plot$coordinates
  !is.null(coordinates$ratio) ||
    inherits(coordinates, "CoordPolar") ||
    inherits(coordinates, "CoordSf")
}

easyplot_compose_panels <- function(
  panels,
  ncol = 2L,
  widths = NULL,
  heights = NULL,
  guides = "keep",
  axes = "keep",
  axis_titles = "keep"
) {
  if (!is.list(panels) || length(panels) == 0L) {
    stop("panels must be a non-empty list of ggplot objects.", call. = FALSE)
  }
  if (!all(vapply(panels, inherits, logical(1), what = "ggplot"))) {
    stop("Every panel must be a ggplot object.", call. = FALSE)
  }
  if (length(ncol) != 1L || !is.numeric(ncol) || ncol < 1 || ncol != as.integer(ncol)) {
    stop("ncol must be one positive integer.", call. = FALSE)
  }
  guides <- match.arg(guides, c("keep", "collect"))
  axes <- match.arg(axes, c("keep", "collect"))
  axis_titles <- match.arg(axis_titles, c("keep", "collect"))
  if (!requireNamespace("gtable", quietly = TRUE)) {
    stop("Panel composition requires the gtable package, installed with ggplot2.", call. = FALSE)
  }

  ncol <- as.integer(ncol)
  n_panels <- length(panels)
  nrow <- ceiling(n_panels / ncol)
  fixed_aspect <- vapply(panels, easyplot_has_fixed_aspect, logical(1))
  if (is.null(widths) && !any(fixed_aspect)) widths <- rep(1, ncol)
  if (is.null(heights) && !any(fixed_aspect)) heights <- rep(1, nrow)
  if (!is.null(widths) && (length(widths) != ncol || any(!is.finite(widths)) || any(widths <= 0))) {
    stop("widths must contain one positive value per column.", call. = FALSE)
  }
  if (!is.null(heights) && (length(heights) != nrow || any(!is.finite(heights)) || any(heights <= 0))) {
    stop("heights must contain one positive value per row.", call. = FALSE)
  }

  if (requireNamespace("patchwork", quietly = TRUE)) {
    result <- patchwork::wrap_plots(
      panels,
      ncol = ncol,
      widths = widths,
      heights = heights,
      guides = guides,
      axes = axes,
      axis_titles = axis_titles
    )
    attr(result, "easyplot_panel_names") <- names(panels)
    attr(result, "easyplot_alignment") <- list(
      method = "patchwork",
      panel_regions = "automatic",
      fixed_aspect_panels = names(panels)[fixed_aspect],
      guides = guides,
      axes = axes,
      axis_titles = axis_titles,
      fixed_aspect_note = "Leave widths/heights NULL for coord_fixed(), coord_equal(), coord_polar(), or coord_sf() panels so patchwork can preserve their aspect ratio."
    )
    class(result) <- c("easyplot_composite", class(result))
    return(result)
  }

  if (is.null(widths)) widths <- rep(1, ncol)
  if (is.null(heights)) heights <- rep(1, nrow)
  warning(
    "patchwork is unavailable; using a gtable fallback. ",
    "Panel-cell widths are controlled, but mixed-axis panel regions may require manual review.",
    call. = FALSE
  )
  result <- gtable::gtable(
    widths = grid::unit(widths, "null"),
    heights = grid::unit(heights, "null"),
    name = "easyplot_scientific_plate"
  )
  grobs <- lapply(panels, ggplot2::ggplotGrob)
  for (index in seq_along(grobs)) {
    row <- ceiling(index / ncol)
    column <- ((index - 1L) %% ncol) + 1L
    result <- gtable::gtable_add_grob(
      result,
      grobs[[index]],
      t = row,
      l = column,
      clip = "off",
      name = paste0("panel-", index)
    )
  }
  attr(result, "easyplot_panel_names") <- names(panels)
  attr(result, "easyplot_alignment") <- list(
    method = "gtable-fallback",
    panel_regions = "cell",
    fixed_aspect_panels = names(panels)[fixed_aspect],
    guides = guides,
    axes = axes,
    axis_titles = axis_titles
  )
  class(result) <- c("easyplot_composite", class(result))
  result
}

easyplot_draw <- function(x, newpage = TRUE) {
  if (inherits(x, "ggplot")) {
    # ggplot/patchwork owns page creation. Calling grid.newpage() first adds a
    # blank PDF page even though single-frame raster exports appear normal.
    print(x, newpage = newpage)
  } else if (inherits(x, "grob")) {
    if (isTRUE(newpage)) grid::grid.newpage()
    grid::grid.draw(x)
  } else {
    stop("x must be a ggplot object or a grid grob.", call. = FALSE)
  }
  invisible(x)
}

easyplot_save <- function(
  x,
  filename,
  width_mm = 180,
  height_mm = 120,
  dpi = 600,
  background = "white",
  overwrite = FALSE,
  png_device = "auto",
  pdf_device = "cairo",
  svg_text = "outline",
  return_metadata = FALSE
) {
  if (length(filename) != 1L || !nzchar(filename)) {
    stop("filename must be one non-empty path.", call. = FALSE)
  }
  dimensions <- list(width_mm, height_mm, dpi)
  if (!all(vapply(dimensions, function(z) is.numeric(z) && length(z) == 1L && is.finite(z) && z > 0, logical(1)))) {
    stop("width_mm, height_mm, and dpi must be finite positive scalars.", call. = FALSE)
  }
  devices <- easyplot_export_devices(png_device, pdf_device, svg_text)
  if (file.exists(filename) && !isTRUE(overwrite)) {
    stop("Refusing to overwrite existing output: ", filename, call. = FALSE)
  }

  output_dir <- dirname(filename)
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  extension <- tolower(tools::file_ext(filename))
  if (!extension %in% c("png", "pdf", "svg")) {
    stop("Supported output extensions are .png, .pdf, and .svg.", call. = FALSE)
  }
  if (extension == "svg" && devices$svg == "editable" && !requireNamespace("svglite", quietly = TRUE)) {
    stop("Editable SVG requires svglite. Install it with approval or request svg_text='outline'; no silent conversion.", call. = FALSE)
  }
  if ((extension == "pdf" && devices$pdf == "cairo" || extension == "svg" && devices$svg == "outline" ||
       extension == "png" && devices$png == "cairo") && !capabilities("cairo")) {
    stop("The selected export device requires Cairo support.", call. = FALSE)
  }
  temporary_path <- tempfile(
    pattern = ".easyplot-",
    tmpdir = output_dir,
    fileext = paste0(".", extension)
  )
  device_open <- FALSE
  on.exit({
    if (isTRUE(device_open)) try(grDevices::dev.off(), silent = TRUE)
    if (file.exists(temporary_path)) unlink(temporary_path)
  }, add = TRUE)
  if (extension == "png") {
    if (devices$png == "ragg") {
      if (!requireNamespace("ragg", quietly = TRUE)) stop("png_device='ragg' requires ragg.", call. = FALSE)
      ragg::agg_png(temporary_path, width = width_mm, height = height_mm, units = "mm", res = dpi, background = background)
    } else {
      arguments <- list(filename = temporary_path, width = width_mm, height = height_mm, units = "mm", res = dpi, bg = background)
      if (devices$png == "cairo") arguments$type <- "cairo"
      do.call(grDevices::png, arguments)
    }
    device_open <- TRUE
  } else if (extension == "pdf") {
    if (devices$pdf == "cairo") {
      grDevices::cairo_pdf(temporary_path, width = width_mm / 25.4, height = height_mm / 25.4, bg = background)
    } else {
      grDevices::pdf(temporary_path, width = width_mm / 25.4, height = height_mm / 25.4, bg = background, useDingbats = FALSE)
    }
    device_open <- TRUE
  } else if (extension == "svg") {
    if (devices$svg == "editable") {
      svglite::svglite(temporary_path, width = width_mm / 25.4, height = height_mm / 25.4, bg = background)
    } else {
      grDevices::svg(temporary_path, width = width_mm / 25.4, height = height_mm / 25.4, bg = background)
    }
    device_open <- TRUE
  }
  actual_mm <- unname(grDevices::dev.size("in") * 25.4)
  if (extension != "png" && any(abs(actual_mm - c(width_mm, height_mm)) > 0.2)) {
    warning(sprintf("Vector device rounded the canvas to %.4f x %.4f mm (requested %.4f x %.4f mm). Inspect exported dimensions.",
                    actual_mm[[1]], actual_mm[[2]], width_mm, height_mm), call. = FALSE)
  }
  easyplot_draw(x)
  grDevices::dev.off()
  device_open <- FALSE
  # Same-directory rename replaces an allowed target without deleting it first.
  # If finalization fails, the previous file remains intact.
  if (file.exists(filename) && !isTRUE(overwrite)) {
    stop("Refusing to overwrite existing output: ", filename, call. = FALSE)
  }
  if (!file.rename(temporary_path, filename)) {
    stop("Could not finalize atomic export: ", filename, call. = FALSE)
  }
  if (isTRUE(return_metadata)) {
    return(invisible(list(path = filename, bytes = file.info(filename)$size, device = devices[[extension]],
                          device_width_mm = actual_mm[[1]], device_height_mm = actual_mm[[2]])))
  }
  invisible(filename)
}

easyplot_export <- function(
  x,
  stem,
  formats = c("png", "pdf"),
  width_mm = 180,
  height_mm = 120,
  dpi = 600,
  background = "white",
  overwrite = FALSE,
  provenance = list(),
  manifest = TRUE,
  png_device = "auto",
  pdf_device = "cairo",
  svg_text = "outline"
) {
  if (length(stem) != 1L || !nzchar(stem)) {
    stop("stem must be one non-empty path.", call. = FALSE)
  }
  formats <- unique(tolower(sub("^\\.", "", formats)))
  devices <- easyplot_export_devices(png_device, pdf_device, svg_text)
  if (length(formats) == 0L || any(!formats %in% c("png", "pdf", "svg"))) {
    stop("formats must contain one or more of: png, pdf, svg", call. = FALSE)
  }
  stem_extension <- tolower(tools::file_ext(stem))
  if (stem_extension %in% c("png", "pdf", "svg")) {
    stem <- substr(stem, 1L, nchar(stem) - nchar(stem_extension) - 1L)
  }
  output_dir <- dirname(stem)
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  output_paths <- paste0(stem, ".", formats)
  manifest_path <- paste0(stem, ".manifest.json")
  targets <- c(output_paths, if (isTRUE(manifest)) manifest_path)
  existing <- targets[file.exists(targets)]
  if (length(existing) > 0L && !isTRUE(overwrite)) {
    stop("Refusing to overwrite existing export(s): ", paste(existing, collapse = ", "), call. = FALSE)
  }

  written <- character()
  output_metadata <- list()
  tryCatch({
    for (path in output_paths) {
      details <- easyplot_save(
        x,
        path,
        width_mm = width_mm,
        height_mm = height_mm,
        dpi = dpi,
        background = background,
        overwrite = overwrite,
        png_device = devices$png, pdf_device = devices$pdf, svg_text = devices$svg,
        return_metadata = TRUE
      )
      written <- c(written, path)
      output_metadata[[length(output_metadata) + 1L]] <- details
    }
    manifest_written <- NULL
    if (isTRUE(manifest)) {
      if (!requireNamespace("jsonlite", quietly = TRUE)) {
        stop("Writing a JSON manifest requires the jsonlite package.", call. = FALSE)
      }
      manifest_data <- c(
        list(
          backend = "R/ggplot2",
          template_version = EASYPLOT_TEMPLATE_VERSION,
          created_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
          width_mm = width_mm,
          height_mm = height_mm,
          dpi = dpi,
          formats = formats,
          devices = devices[formats],
          svg_text = if ("svg" %in% formats) devices$svg else NULL,
          size_note = "Dimensions above are requested. Inspect actual files: raster pixels and Cairo vector points may round; no post-export stretching is applied.",
          software = list(R = R.version.string, ggplot2 = as.character(utils::packageVersion("ggplot2"))),
          outputs = output_metadata,
          overwrite_requested = isTRUE(overwrite),
          provenance = provenance
        )
      )
      manifest_temp <- tempfile(
        pattern = ".easyplot-manifest-",
        tmpdir = output_dir,
        fileext = ".json"
      )
      on.exit(if (file.exists(manifest_temp)) unlink(manifest_temp), add = TRUE)
      jsonlite::write_json(manifest_data, manifest_temp, pretty = TRUE, auto_unbox = TRUE, na = "null")
      if (file.exists(manifest_path) && !isTRUE(overwrite)) {
        stop("Refusing to overwrite existing manifest: ", manifest_path, call. = FALSE)
      }
      if (!file.rename(manifest_temp, manifest_path)) {
        stop("Could not finalize atomic manifest: ", manifest_path, call. = FALSE)
      }
      manifest_written <- manifest_path
      written <- c(written, manifest_path)
    }
    invisible(list(outputs = output_paths, manifest = manifest_written))
  }, error = function(error) {
    if (!isTRUE(overwrite) && length(written) > 0L) unlink(written[file.exists(written)])
    stop(error)
  })
}

easyplot_scientific_plate <- function(
  panels,
  panel_spec = NULL,
  ncol = 2L,
  widths = NULL,
  heights = NULL,
  guides = "keep",
  axes = "keep",
  axis_titles = "keep"
) {
  if (is.null(names(panels))) {
    names(panels) <- paste0("panel_", seq_along(panels))
  }
  if (anyDuplicated(names(panels))) {
    stop("panel names must be unique.", call. = FALSE)
  }
  if (is.null(panel_spec)) {
    panel_spec <- data.frame(
      panel_id = names(panels),
      role = rep("evidence", length(panels)),
      geometry = rep("ggplot", length(panels)),
      scale = rep("panel", length(panels)),
      guide_owner = rep("local", length(panels)),
      stringsAsFactors = FALSE
    )
  }
  easyplot_require_columns(
    panel_spec,
    c("panel_id", "role", "geometry", "scale", "guide_owner"),
    "panel_spec"
  )
  if (anyDuplicated(panel_spec$panel_id)) {
    stop("panel_spec$panel_id must be unique.", call. = FALSE)
  }
  if (!setequal(panel_spec$panel_id, names(panels))) {
    stop("panel_spec$panel_id must match the panel names exactly.", call. = FALSE)
  }
  ordered_panels <- panels[match(panel_spec$panel_id, names(panels))]
  result <- easyplot_compose_panels(
    ordered_panels,
    ncol = ncol,
    widths = widths,
    heights = heights,
    guides = guides,
    axes = axes,
    axis_titles = axis_titles
  )
  attr(result, "easyplot_panel_spec") <- panel_spec
  result
}

easyplot_spatial_small_multiples <- function(
  data,
  x = "x",
  y = "y",
  value = "value",
  facet = NULL,
  value_limits = NULL,
  colours = c("#F7FBFF", "#C6D4EA", "#568FC3"),
  missing_colour = "#F2F2F2",
  preserve_aspect = TRUE,
  base_size = 8,
  base_family = "sans",
  x_label = NULL,
  y_label = NULL,
  fill_label = NULL
) {
  easyplot_require_columns(data, c(x, y, value, facet), "spatial data")
  if (length(colours) < 2L) stop("colours must contain at least two colours.", call. = FALSE)
  p <- ggplot2::ggplot(
    data,
    ggplot2::aes(x = .data[[x]], y = .data[[y]], fill = .data[[value]])
  ) +
    ggplot2::geom_raster(na.rm = FALSE) +
    ggplot2::scale_fill_gradientn(
      colours = colours,
      limits = value_limits,
      na.value = missing_colour,
      name = easyplot_or(fill_label, value)
    ) +
    ggplot2::labs(
      x = easyplot_or(x_label, x),
      y = easyplot_or(y_label, y)
    ) +
    easyplot_scientific_theme(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      axis.line = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_blank(),
      panel.border = ggplot2::element_rect(
        colour = "#B8B8B8",
        fill = NA,
        linewidth = 0.25
      )
    )
  if (isTRUE(preserve_aspect)) {
    p <- p + ggplot2::coord_equal(expand = FALSE)
  } else {
    p <- p + ggplot2::coord_cartesian(expand = FALSE)
  }
  if (!is.null(facet)) {
    p <- p + ggplot2::facet_wrap(stats::as.formula(paste("~", facet)))
  }
  p
}

easyplot_omics_heatmap <- function(
  data,
  feature = "feature",
  sample = "sample",
  value = "value",
  feature_order = NULL,
  sample_order = NULL,
  value_limits = NULL,
  colours = c("#F7FBFF", "#C6D4EA", "#568FC3"),
  base_size = 7.5,
  base_family = "sans",
  fill_label = NULL
) {
  easyplot_require_columns(data, c(feature, sample, value), "omics heatmap data")
  plotted <- data
  feature_levels <- easyplot_or(feature_order, unique(as.character(plotted[[feature]])))
  sample_levels <- easyplot_or(sample_order, unique(as.character(plotted[[sample]])))
  plotted[[feature]] <- factor(as.character(plotted[[feature]]), levels = rev(feature_levels))
  plotted[[sample]] <- factor(as.character(plotted[[sample]]), levels = sample_levels)

  ggplot2::ggplot(
    plotted,
    ggplot2::aes(x = .data[[sample]], y = .data[[feature]], fill = .data[[value]])
  ) +
    ggplot2::geom_tile(colour = "white", linewidth = 0.15, na.rm = FALSE) +
    ggplot2::scale_fill_gradientn(
      colours = colours,
      limits = value_limits,
      na.value = "#F2F2F2",
      name = easyplot_or(fill_label, value)
    ) +
    ggplot2::labs(x = NULL, y = NULL) +
    easyplot_scientific_theme(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      axis.line = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_blank(),
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1, vjust = 1),
      panel.border = ggplot2::element_rect(
        colour = "#B8B8B8",
        fill = NA,
        linewidth = 0.25
      )
    )
}

easyplot_omics_effects <- function(
  data,
  feature = "feature",
  estimate = "estimate",
  lower = NULL,
  upper = NULL,
  condition = NULL,
  condition_colours = NULL,
  base_size = 8,
  base_family = "sans",
  x_label = NULL
) {
  easyplot_require_columns(data, c(feature, estimate, lower, upper, condition), "omics effect data")
  plotted <- data
  plotted[[feature]] <- factor(as.character(plotted[[feature]]), levels = rev(unique(as.character(plotted[[feature]]))))
  p <- ggplot2::ggplot(
    plotted,
    ggplot2::aes(x = .data[[estimate]], y = .data[[feature]])
  )
  if (!is.null(lower) && !is.null(upper)) {
    p <- p + ggplot2::geom_segment(
      ggplot2::aes(
        x = .data[[lower]],
        xend = .data[[upper]],
        y = .data[[feature]],
        yend = .data[[feature]]
      ),
      linewidth = 0.45,
      colour = "#4A4A4A",
      na.rm = TRUE
    )
  }
  p <- p +
    ggplot2::geom_point(
      ggplot2::aes(colour = if (is.null(condition)) NULL else .data[[condition]]),
      size = 1.7,
      na.rm = TRUE
    ) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.28, colour = "#8A8A8A") +
    ggplot2::labs(x = easyplot_or(x_label, estimate), y = NULL, colour = condition) +
    easyplot_scientific_theme(base_size = base_size, base_family = base_family) +
    ggplot2::theme(axis.line.y = ggplot2::element_blank())
  if (!is.null(condition_colours)) {
    p <- p + ggplot2::scale_colour_manual(values = condition_colours, drop = FALSE)
  }
  p
}

easyplot_omics_evidence_plate <- function(
  heatmap_data,
  effect_data = NULL,
  schematic = NULL,
  heatmap_args = list(),
  effect_args = list(),
  panel_spec = NULL,
  ncol = 2L,
  widths = NULL,
  heights = NULL,
  guides = "keep",
  axes = "keep",
  axis_titles = "keep"
) {
  heatmap <- do.call(
    easyplot_omics_heatmap,
    c(list(data = heatmap_data), heatmap_args)
  )
  panels <- list(heatmap = heatmap)
  if (!is.null(effect_data)) {
    panels$effects <- do.call(
      easyplot_omics_effects,
      c(list(data = effect_data), effect_args)
    )
  }
  if (!is.null(schematic)) {
    if (!inherits(schematic, "ggplot")) stop("schematic must be a ggplot object.", call. = FALSE)
    panels$schematic <- schematic
  }
  easyplot_scientific_plate(
    panels = panels,
    panel_spec = panel_spec,
    ncol = ncol,
    widths = widths,
    heights = heights,
    guides = guides,
    axes = axes,
    axis_titles = axis_titles
  )
}

easyplot_data_schematic <- function(
  nodes,
  edges = NULL,
  id = "id",
  x = "x",
  y = "y",
  label = "label",
  kind = NULL,
  node_colours = NULL,
  preserve_aspect = FALSE,
  base_size = 8,
  base_family = "sans"
) {
  easyplot_require_columns(nodes, c(id, x, y, label, kind), "schematic nodes")
  plotted_nodes <- nodes
  kind_column <- kind
  if (is.null(kind_column)) {
    if ("kind" %in% names(plotted_nodes)) {
      kind_column <- "kind"
    } else {
      kind_column <- ".easyplot_kind"
      plotted_nodes[[kind_column]] <- "node"
    }
  }

  edge_data <- NULL
  if (!is.null(edges)) {
    easyplot_require_columns(edges, c("from", "to"), "schematic edges")
    positions <- plotted_nodes[, c(id, x, y), drop = FALSE]
    names(positions) <- c("node_id", "node_x", "node_y")
    from_positions <- positions
    names(from_positions)[2:3] <- c("x_start", "y_start")
    to_positions <- positions
    names(to_positions)[2:3] <- c("x_end", "y_end")
    edge_data <- merge(edges, from_positions, by.x = "from", by.y = "node_id", all.x = TRUE)
    edge_data <- merge(edge_data, to_positions, by.x = "to", by.y = "node_id", all.x = TRUE)
    if (any(!stats::complete.cases(edge_data[, c("x_start", "y_start", "x_end", "y_end")]))) {
      stop("Every schematic edge must refer to an existing node id.", call. = FALSE)
    }
  }

  p <- ggplot2::ggplot(plotted_nodes, ggplot2::aes(x = .data[[x]], y = .data[[y]]))
  if (!is.null(edge_data) && nrow(edge_data) > 0L) {
    p <- p + ggplot2::geom_segment(
      data = edge_data,
      ggplot2::aes(
        x = .data[["x_start"]],
        y = .data[["y_start"]],
        xend = .data[["x_end"]],
        yend = .data[["y_end"]]
      ),
      inherit.aes = FALSE,
      linewidth = 0.45,
      colour = "#6C6C6C",
      arrow = grid::arrow(length = grid::unit(3, "mm"), type = "closed")
    )
  }
  p <- p +
    ggplot2::geom_label(
      ggplot2::aes(label = .data[[label]], fill = .data[[kind_column]]),
      colour = "#303030",
      linewidth = 0.25,
      size = base_size / ggplot2::.pt,
      family = base_family,
      show.legend = FALSE
    ) +
    ggplot2::theme_void(base_size = base_size, base_family = base_family) +
    ggplot2::theme(plot.margin = ggplot2::margin(8, 8, 8, 8, unit = "pt"))
  if (isTRUE(preserve_aspect)) {
    p <- p + ggplot2::coord_equal(expand = TRUE, clip = "off")
  } else {
    p <- p + ggplot2::coord_cartesian(expand = TRUE, clip = "off")
  }
  if (!is.null(node_colours)) {
    p <- p + ggplot2::scale_fill_manual(values = node_colours, drop = FALSE)
  } else {
    p <- p + ggplot2::scale_fill_grey(start = 0.96, end = 0.78)
  }
  p
}
