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

# Audit declared plotting-frame geometry before rendering. Coordinates are
# normalized to the assembled figure: left/right in [0, 1], bottom/top in
# [0, 1]. This catches layout-contract failures that ordinary patchwork cell
# alignment cannot see, especially external legends and fixed-aspect maps.
easyplot_layout_audit <- function(
  frames,
  alignment = list(),
  tolerance = 0.002,
  allow_overlap = character()
) {
  required <- c("panel_id", "left", "right", "top", "bottom")
  if (!is.data.frame(frames)) {
    stop("frames must be a data.frame.", call. = FALSE)
  }
  missing_columns <- setdiff(required, names(frames))
  if (length(missing_columns)) {
    stop("frames is missing required column(s): ", paste(missing_columns, collapse = ", "), call. = FALSE)
  }
  if (length(tolerance) != 1L || !is.numeric(tolerance) || !is.finite(tolerance) || tolerance < 0) {
    stop("tolerance must be one finite non-negative number.", call. = FALSE)
  }

  plotted <- frames[, required, drop = FALSE]
  plotted$panel_id <- as.character(plotted$panel_id)
  if (any(!nzchar(plotted$panel_id)) || anyDuplicated(plotted$panel_id)) {
    stop("frames$panel_id must contain unique non-empty identifiers.", call. = FALSE)
  }
  numeric_columns <- required[-1L]
  for (column in numeric_columns) plotted[[column]] <- as.numeric(plotted[[column]])

  errors <- character()
  warnings <- character()
  if (any(!is.finite(as.matrix(plotted[numeric_columns])))) {
    errors <- c(errors, "Frame coordinates must be finite numbers.")
  }
  if (any(plotted[numeric_columns] < 0 | plotted[numeric_columns] > 1, na.rm = TRUE)) {
    errors <- c(errors, "Frame coordinates must lie in the normalized [0, 1] range.")
  }
  if (any(plotted$left >= plotted$right, na.rm = TRUE)) {
    errors <- c(errors, "Every frame must have left < right.")
  }
  if (any(plotted$bottom >= plotted$top, na.rm = TRUE)) {
    errors <- c(errors, "Every frame must have bottom < top.")
  }

  check_alignment <- function(side, groups) {
    if (is.null(groups)) return(invisible(NULL))
    if (is.character(groups)) groups <- list(groups)
    if (!is.list(groups)) {
      errors <<- c(errors, paste0("alignment$", side, " must be a list of panel groups."))
      return(invisible(NULL))
    }
    for (group in groups) {
      group <- unique(as.character(group))
      missing_ids <- setdiff(group, plotted$panel_id)
      if (length(missing_ids)) {
        errors <<- c(errors, paste0("alignment$", side, " references unknown panel(s): ", paste(missing_ids, collapse = ", "), "."))
        next
      }
      values <- plotted[[side]][match(group, plotted$panel_id)]
      if ((max(values) - min(values)) > tolerance) {
        errors <<- c(errors, paste0("Panels ", paste(group, collapse = ", "), " are not aligned on ", side, "."))
      }
    }
    invisible(NULL)
  }

  for (side in intersect(names(alignment), c("left", "right", "top", "bottom"))) {
    check_alignment(side, alignment[[side]])
  }

  overlap_key <- function(first, second) paste(sort(c(first, second)), collapse = "::")
  allowed <- as.character(allow_overlap)
  for (first_index in seq_len(max(0L, nrow(plotted) - 1L))) {
    for (second_index in (first_index + 1L):nrow(plotted)) {
      first <- plotted[first_index, ]
      second <- plotted[second_index, ]
      overlap_width <- min(first$right, second$right) - max(first$left, second$left)
      overlap_height <- min(first$top, second$top) - max(first$bottom, second$bottom)
      if (overlap_width > tolerance && overlap_height > tolerance) {
        key <- overlap_key(first$panel_id, second$panel_id)
        if (!(key %in% allowed)) {
          warnings <- c(warnings, paste0("Frames ", first$panel_id, " and ", second$panel_id, " overlap; declare allow_overlap when intentional."))
        }
      }
    }
  }

  result <- list(
    ok = length(errors) == 0L,
    errors = unique(errors),
    warnings = unique(warnings),
    frames = plotted,
    alignment = alignment,
    tolerance = tolerance
  )
  class(result) <- c("easyplot_layout_audit", "list")
  result
}

easyplot_spatial_evidence_layout <- function() {
  list(
    design = c("AAAAAB", "AAAAAB", "CCCCCC", "DDDEEE", "DDDEEE"),
    heights = c(1.9, 1.9, 1.28, 1.11, 1.11),
    small_multiple_width = "full_plate",
    alignment = list(
      top = list(c("map", "side_strip")),
      bottom = list(c("map", "side_strip")),
      left = list(c("map", "small_multiples")),
      right = list(c("side_strip", "small_multiples"))
    ),
    notes = c(
      "Keep the side-strip frame aligned to the map plotting frame, not to an external legend band.",
      "Use a full-width small-multiple row spanning the map and side strip.",
      "Place legends outside a frame when an internal legend would cover the border."
    )
  )
}

easyplot_spatial_evidence_plate <- function(
  map,
  side_strip,
  small_multiples,
  distribution,
  temporal,
  heights = NULL,
  guides = "keep"
) {
  panels <- list(
    A = map,
    B = side_strip,
    C = small_multiples,
    D = distribution,
    E = temporal
  )
  if (!all(vapply(panels, inherits, logical(1), what = "ggplot"))) {
    stop("Every spatial evidence plate panel must be a ggplot object.", call. = FALSE)
  }
  guides <- match.arg(guides, c("keep", "collect"))
  if (!requireNamespace("patchwork", quietly = TRUE)) {
    stop("easyplot_spatial_evidence_plate requires the patchwork package.", call. = FALSE)
  }

  layout <- easyplot_spatial_evidence_layout()
  if (is.null(heights)) heights <- layout$heights
  if (length(heights) != length(layout$heights) || any(!is.finite(heights)) || any(heights <= 0)) {
    stop("heights must contain five positive finite values.", call. = FALSE)
  }
  result <- patchwork::wrap_plots(panels, design = layout$design) +
    patchwork::plot_layout(heights = heights, guides = guides)
  attr(result, "easyplot_layout_contract") <- layout
  attr(result, "easyplot_panel_names") <- c("map", "side_strip", "small_multiples", "distribution", "temporal")
  class(result) <- c("easyplot_composite", class(result))
  result
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
  fill_parent_width = FALSE,
  panel_border_colour = "#111111",
  panel_border_width = 0.35,
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
        colour = panel_border_colour,
        fill = NA,
        linewidth = panel_border_width
      )
    )
  if (isTRUE(fill_parent_width)) preserve_aspect <- FALSE
  if (isTRUE(preserve_aspect)) {
    p <- p + ggplot2::coord_equal(expand = FALSE)
  } else {
    p <- p + ggplot2::coord_cartesian(expand = FALSE)
  }
  if (!is.null(facet)) {
    p <- p + ggplot2::facet_wrap(stats::as.formula(paste("~", facet)))
  }
  attr(p, "easyplot_spatial_contract") <- list(
    preserve_aspect = isTRUE(preserve_aspect),
    fill_parent_width = isTRUE(fill_parent_width),
    panel_border_colour = panel_border_colour,
    panel_border_width = panel_border_width
  )
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

easyplot_schematic_lint <- function(
  nodes,
  edges = NULL,
  id = "id",
  x = "x",
  y = "y",
  label = "label",
  kind = NULL,
  node_width = 0.72,
  node_height = 0.36
) {
  errors <- character()
  warnings <- character()
  node_count <- if (is.data.frame(nodes)) nrow(nodes) else 0L
  edge_count <- if (is.data.frame(edges)) nrow(edges) else 0L

  if (!is.data.frame(nodes)) {
    errors <- c(errors, "Schematic nodes must be a data.frame.")
  } else {
    required <- unique(c(id, x, y, label, kind))
    missing <- setdiff(required, names(nodes))
    if (length(missing) > 0L) {
      errors <- c(errors, paste0("Schematic nodes are missing columns: ", paste(missing, collapse = ", "), "."))
    } else {
      node_ids <- as.character(nodes[[id]])
      if (anyNA(node_ids) || any(!nzchar(node_ids))) {
        errors <- c(errors, "Schematic node ids must be non-empty.")
      }
      if (anyDuplicated(node_ids)) {
        errors <- c(errors, "Schematic node ids must be unique.")
      }
      if (!is.numeric(nodes[[x]]) || !is.numeric(nodes[[y]]) ||
        any(!is.finite(nodes[[x]])) || any(!is.finite(nodes[[y]]))) {
        errors <- c(errors, "Schematic node coordinates must be finite numeric values.")
      }
      if (is.numeric(node_width) && length(node_width) == 1L && is.finite(node_width) && node_width > 0 &&
        is.numeric(node_height) && length(node_height) == 1L && is.finite(node_height) && node_height > 0 &&
        length(node_ids) > 1L) {
        # ponytail: O(n^2) overlap scan is deliberate for small schematic node sets; use a spatial index if this becomes a large graph.
        overlap_pairs <- utils::combn(seq_along(node_ids), 2L, simplify = FALSE)
        overlapping <- vapply(overlap_pairs, function(pair) {
          abs(nodes[[x]][pair[1L]] - nodes[[x]][pair[2L]]) < node_width &&
            abs(nodes[[y]][pair[1L]] - nodes[[y]][pair[2L]]) < node_height
        }, logical(1))
        if (any(overlapping)) {
          pairs <- vapply(overlap_pairs[overlapping], function(pair) {
            paste(node_ids[pair], collapse = " / ")
          }, character(1))
          warnings <- c(warnings, paste0("Schematic nodes overlap: ", paste(pairs, collapse = "; "), "."))
        }
      }
    }
  }

  if (!is.null(edges)) {
    if (!is.data.frame(edges)) {
      errors <- c(errors, "Schematic edges must be a data.frame.")
    } else {
      missing_edges <- setdiff(c("from", "to"), names(edges))
      if (length(missing_edges) > 0L) {
        errors <- c(errors, paste0("Schematic edges are missing columns: ", paste(missing_edges, collapse = ", "), "."))
      } else if (is.data.frame(nodes) && all(c(id, x, y) %in% names(nodes))) {
        node_ids <- as.character(nodes[[id]])
        from_ids <- as.character(edges$from)
        to_ids <- as.character(edges$to)
        if (any(!from_ids %in% node_ids) || any(!to_ids %in% node_ids)) {
          errors <- c(errors, "Every schematic edge must refer to an existing node id.")
        }
        if (any(from_ids == to_ids, na.rm = TRUE)) {
          warnings <- c(warnings, "Self-loop schematic edges are not trimmed by the rectangular node model.")
        }
        edge_keys <- paste(from_ids, to_ids, sep = " -> ")
        if (anyDuplicated(edge_keys)) {
          warnings <- c(warnings, "Duplicate schematic edges may be visually indistinguishable.")
        }
      }
    }
  }

  list(
    ok = length(errors) == 0L,
    errors = errors,
    warnings = warnings,
    node_count = node_count,
    edge_count = edge_count
  )
}

easyplot_schematic_clip_point <- function(x_start, y_start, x_end, y_end, half_width, half_height, pad = 0) {
  dx <- x_end - x_start
  dy <- y_end - y_start
  if (!all(is.finite(c(x_start, y_start, x_end, y_end)))) {
    return(c(x_start, y_start))
  }
  if (abs(dx) < .Machine$double.eps && abs(dy) < .Machine$double.eps) {
    return(c(x_start, y_start))
  }
  half_width <- max(as.numeric(half_width) + as.numeric(pad), .Machine$double.eps)
  half_height <- max(as.numeric(half_height) + as.numeric(pad), .Machine$double.eps)
  x_ratio <- if (abs(dx) < .Machine$double.eps) 0 else abs(dx) / half_width
  y_ratio <- if (abs(dy) < .Machine$double.eps) 0 else abs(dy) / half_height
  step <- if (x_ratio >= y_ratio) half_width / abs(dx) else half_height / abs(dy)
  c(x_start + dx * step, y_start + dy * step)
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
  base_family = "sans",
  node_width = 0.72,
  node_height = 0.36,
  edge_pad = 0.02,
  edge_colour = "#6C6C6C",
  edge_linewidth = 0.45,
  arrow_length_mm = 1.8,
  label_padding = 0.14,
  label_radius = 0.08,
  node_border_width = 0.25
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

  lint <- easyplot_schematic_lint(
    nodes, edges, id = id, x = x, y = y, label = label, kind = kind,
    node_width = node_width, node_height = node_height
  )
  if (!isTRUE(lint$ok)) {
    stop(paste(lint$errors, collapse = " "), call. = FALSE)
  }

  edge_data <- NULL
  if (!is.null(edges)) {
    edge_data <- as.data.frame(edges, stringsAsFactors = FALSE)
    node_ids <- as.character(plotted_nodes[[id]])
    from_index <- match(as.character(edge_data$from), node_ids)
    to_index <- match(as.character(edge_data$to), node_ids)
    edge_data$x_start <- plotted_nodes[[x]][from_index]
    edge_data$y_start <- plotted_nodes[[y]][from_index]
    edge_data$x_end <- plotted_nodes[[x]][to_index]
    edge_data$y_end <- plotted_nodes[[y]][to_index]
    if (nrow(edge_data) > 0L) {
      starts <- lapply(seq_len(nrow(edge_data)), function(i) {
        easyplot_schematic_clip_point(
          edge_data$x_start[i], edge_data$y_start[i],
          edge_data$x_end[i], edge_data$y_end[i],
          half_width = node_width / 2, half_height = node_height / 2, pad = edge_pad
        )
      })
      ends <- lapply(seq_len(nrow(edge_data)), function(i) {
        easyplot_schematic_clip_point(
          edge_data$x_end[i], edge_data$y_end[i],
          edge_data$x_start[i], edge_data$y_start[i],
          half_width = node_width / 2, half_height = node_height / 2, pad = edge_pad
        )
      })
      edge_data$x_start <- vapply(starts, `[[`, numeric(1), 1L)
      edge_data$y_start <- vapply(starts, `[[`, numeric(1), 2L)
      edge_data$x_end <- vapply(ends, `[[`, numeric(1), 1L)
      edge_data$y_end <- vapply(ends, `[[`, numeric(1), 2L)
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
      linewidth = edge_linewidth,
      colour = edge_colour,
      arrow = grid::arrow(length = grid::unit(arrow_length_mm, "mm"), type = "closed")
    )
  }
  p <- p +
    ggplot2::geom_label(
      ggplot2::aes(label = .data[[label]], fill = .data[[kind_column]]),
      colour = "#303030",
      linewidth = node_border_width,
      label.padding = grid::unit(label_padding, "lines"),
      label.r = grid::unit(label_radius, "lines"),
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
  attr(p, "easyplot_schematic") <- list(
    lint = lint,
    nodes = plotted_nodes,
    edge_data = edge_data,
    geometry = list(
      node_width = node_width,
      node_height = node_height,
      edge_pad = edge_pad,
      preserve_aspect = preserve_aspect,
      arrow_length_mm = arrow_length_mm,
      label_padding = label_padding,
      label_radius = label_radius,
      node_border_width = node_border_width
    )
  )
  p
}
