# Unified EasyPlot palettes. Source this file to load ../assets/palettes.json
# using installed jsonlite. All IDs and filters are exact, case-sensitive strings,
# including percent-encoded IDs. There is no network or external palette package.
# The registry is a snapshot loaded once per source(); R copy-on-modify semantics
# and a locked private environment isolate returned records and colour vectors.
#
# easyplot_palettes(family = NULL, kind = NULL, cvd = NULL) returns a data.frame
# in registry order with id, label, family, kind, selection, n_colours, max_n,
# cvd_status, cvd_evidence, cvd_note. Filters are nonempty scalar strings; unknown
# strings return zero rows. cvd is a status, not a logical safety claim. max_n is
# the largest explicit request; native sizes can have gaps.
# easyplot_palette_info(id) returns every record field, including tags and source.
#
# easyplot_palette(id, n = NULL, reverse = FALSE):
# * NULL returns every stored colour, for all selection policies.
# * prefix takes the first n colours, refusing requests beyond capacity.
# * native takes the exact stored n-colour scheme. n=1 or 2 takes the first n
#   colours of the smallest stored scheme. Unstored sizes raise an error.
# * lut selects stored entries without interpolation. The zero-based index for
#   n=1 is floor((length-1)/2 + 0.5); for n>=2 it is
#   floor(i*(length-1)/(n-1) + 0.5), including both endpoints. Up to 65536
#   samples are allowed. Repeated colours add no precision beyond the table.
# reverse reverses the selected subset. n accepts a finite, positive, integer-
# valued numeric scalar (including ordinary R literals such as 3); reverse must
# be a single nonmissing logical. Logical n, vectors and classed n are rejected.
#
# scale_fill_easyplot(id, levels, ..., reverse = FALSE) and scale_colour_easyplot
# accept only qualitative palettes and explicit unique, nonempty character levels.
# Named values plus fixed limits preserve group identity, with drop=FALSE by
# default and missing values #E2E2E2. ggplot2 is required only when these are used.
# For continuous data, use ggplot2 directly and declare limits/normalization:
# ggplot2::scale_fill_gradientn(colours = easyplot_palette("viridis.viridis"),
#                              limits = c(0, 1), na.value = "#E2E2E2")
# gradientn interpolates while rendering; use a stepped/binned scale when original
# source swatches must remain exact. Declare a meaningful centre for diverging data.

local({
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("EasyPlot palettes require the installed jsonlite package.", call. = FALSE)
  }
  source_frames <- Filter(function(frame) !is.null(frame$ofile), sys.frames())
  if (!length(source_frames)) stop("Load easyplot_palettes.R with source().", call. = FALSE)
  source_frame <- source_frames[[length(source_frames)]]
  script_path <- if (isTRUE(source_frame$chdir)) basename(source_frame$ofile) else source_frame$ofile
  script_path <- normalizePath(script_path, mustWork = TRUE)
  registry <- jsonlite::fromJSON(
    file.path(dirname(script_path), "..", "assets", "palettes.json"), simplifyVector = FALSE
  )
  text_scalar <- function(value) {
    is.character(value) && length(value) == 1L && !is.na(value) &&
      is.null(dim(value)) && !is.object(value) && nzchar(trimws(value))
  }
  check_colours <- function(values, context) {
    if (!is.list(values) || !length(values) || !all(vapply(values, function(value) {
      text_scalar(value) && grepl("^#[0-9A-Fa-f]{6}$", value)
    }, logical(1L)))) stop("Invalid #RRGGBB colours in ", context, call. = FALSE)
  }
  if (!is.list(registry) || !identical(registry$schema_version, 1L)) {
    stop("Unsupported palette registry schema_version; expected 1.", call. = FALSE)
  }
  if (!is.list(registry$palettes)) stop("Palette registry palettes must be an array.", call. = FALSE)
  for (record in registry$palettes) {
    if (!is.list(record) || !all(vapply(record[c("id", "label", "family")], text_scalar, logical(1L)))) {
      stop("Each palette needs a nonempty id, label and family.", call. = FALSE)
    }
    if (!text_scalar(record$kind) || !record$kind %in% c("qualitative", "sequential", "diverging", "cyclic", "multisequential")) {
      stop("Invalid palette kind for ", record$id, call. = FALSE)
    }
    if (!text_scalar(record$selection) || !record$selection %in% c("prefix", "native", "lut")) {
      stop("Invalid palette selection for ", record$id, call. = FALSE)
    }
    check_colours(record$colours, record$id)
    if (!is.list(record$cvd) || !text_scalar(record$cvd$status) ||
        !record$cvd$status %in% c("reported", "conditional", "not_assessed", "not_recommended")) {
      stop("Invalid cvd status for ", record$id, call. = FALSE)
    }
    if (!all(vapply(record$cvd[c("evidence", "note")], function(value) {
      is.character(value) && length(value) == 1L && !is.na(value)
    }, logical(1L)))) stop("Missing cvd evidence or note for ", record$id, call. = FALSE)
    if (record$selection == "native") {
      schemes <- record$native_sizes
      if (!is.list(schemes) || !length(schemes) || is.null(names(schemes)) ||
          anyDuplicated(names(schemes)) || any(!grepl("^[1-9][0-9]*$", names(schemes)))) {
        stop("Missing or invalid stored native sizes for ", record$id, call. = FALSE)
      }
      for (size in names(schemes)) {
        check_colours(schemes[[size]], paste(record$id, "native size", size))
        if (length(schemes[[size]]) != as.double(size)) {
          stop("Invalid stored native size ", size, " for ", record$id, call. = FALSE)
        }
      }
    }
  }
  ids <- vapply(registry$palettes, function(record) record$id, character(1L))
  if (anyDuplicated(ids)) stop("Duplicate palette id in registry.", call. = FALSE)
  palettes <- stats::setNames(registry$palettes, ids)
  capacity <- function(record) {
    if (record$selection == "lut") return(65536L)
    if (record$selection == "native") return(max(as.integer(names(record$native_sizes))))
    length(record$colours)
  }
  get_record <- function(id) {
    if (!text_scalar(id) || !id %in% ids) {
      stop("Unknown palette id; use easyplot_palettes() for exact IDs.", call. = FALSE)
    }
    palettes[[id, exact = TRUE]]
  }
  metadata <- as.data.frame(stats::setNames(lapply(c("id", "label", "family", "kind", "selection"), function(key) {
    vapply(palettes, function(record) record[[key]], character(1L), USE.NAMES = FALSE)
  }), c("id", "label", "family", "kind", "selection")), stringsAsFactors = FALSE)
  metadata$n_colours <- vapply(palettes, function(record) length(record$colours), integer(1L), USE.NAMES = FALSE)
  metadata$max_n <- vapply(palettes, capacity, integer(1L), USE.NAMES = FALSE)
  for (key in c("status", "evidence", "note")) {
    metadata[[paste0("cvd_", key)]] <- vapply(palettes, function(record) record$cvd[[key]], character(1L), USE.NAMES = FALSE)
  }

  easyplot_palettes <- function(family = NULL, kind = NULL, cvd = NULL) {
    filters <- list(family = family, kind = kind, cvd = cvd)
    for (key in names(filters)) {
      if (!is.null(filters[[key]]) && !text_scalar(filters[[key]])) {
        stop(key, " must be a nonempty string or NULL.", call. = FALSE)
      }
    }
    keep <- rep(TRUE, nrow(metadata))
    if (!is.null(family)) keep <- keep & metadata$family == family
    if (!is.null(kind)) keep <- keep & metadata$kind == kind
    if (!is.null(cvd)) keep <- keep & metadata$cvd_status == cvd
    result <- metadata[keep, , drop = FALSE]
    rownames(result) <- NULL
    result
  }

  easyplot_palette_info <- function(id) get_record(id)

  easyplot_palette <- function(id, n = NULL, reverse = FALSE) {
    record <- get_record(id)
    if (!is.logical(reverse) || length(reverse) != 1L || is.na(reverse) ||
        !is.null(dim(reverse)) || is.object(reverse)) {
      stop("reverse must be TRUE or FALSE.", call. = FALSE)
    }
    if (!is.null(n) && (!typeof(n) %in% c("integer", "double") || length(n) != 1L ||
        is.object(n) || !is.null(dim(n)) || !is.finite(n) || n < 1 || n != floor(n))) {
      stop("n must be one positive integer.", call. = FALSE)
    }
    values <- unlist(record$colours, use.names = FALSE)
    if (!is.null(n)) {
      maximum <- capacity(record)
      if (n > maximum) stop(id, " supports at most ", maximum, " requested colours.", call. = FALSE)
      if (record$selection == "prefix") {
        values <- values[seq_len(n)]
      } else if (record$selection == "native") {
        size <- if (n < 3) min(as.integer(names(record$native_sizes))) else n
        scheme <- record$native_sizes[[as.character(size), exact = TRUE]]
        if (is.null(scheme) || length(scheme) < n) {
          stop("No stored native size ", n, " for ", id, "; available sizes: ",
               paste(names(record$native_sizes), collapse = ", "), call. = FALSE)
        }
        values <- unlist(scheme, use.names = FALSE)[seq_len(n)]
      } else {
        indices <- if (n == 1) floor(length(values) / 2) else
          floor((seq_len(n) - 1) * (length(values) - 1) / (n - 1) + 0.5)
        values <- values[indices + 1L]
      }
    }
    if (reverse) rev(values) else values
  }

  manual_scale <- function(aesthetic, id, levels, reverse, ...) {
    if (!is.character(levels) || !length(levels) || anyNA(levels) ||
        any(!nzchar(trimws(levels))) || anyDuplicated(levels) ||
        !is.null(dim(levels)) || is.object(levels)) {
      stop("levels must be explicit, nonempty, unique character values.", call. = FALSE)
    }
    if (get_record(id)$kind != "qualitative") {
      stop("EasyPlot manual scales require a qualitative palette.", call. = FALSE)
    }
    levels <- unname(levels)
    values <- stats::setNames(easyplot_palette(id, length(levels), reverse), levels)
    dots <- list(...)
    if (any(names(dots) %in% c("values", "limits", "aesthetics", "palette", "na.value"))) {
      stop("values, limits, aesthetics, palette and na.value are controlled by EasyPlot.", call. = FALSE)
    }
    if (!"drop" %in% names(dots)) dots$drop <- FALSE
    if (!requireNamespace("ggplot2", quietly = TRUE)) {
      stop("EasyPlot manual scales require the installed ggplot2 package.", call. = FALSE)
    }
    scale <- if (aesthetic == "fill") ggplot2::scale_fill_manual else ggplot2::scale_colour_manual
    do.call(scale, c(list(values = values, limits = levels, na.value = "#E2E2E2"), dots))
  }
  scale_fill_easyplot <- function(id, levels, ..., reverse = FALSE) {
    manual_scale("fill", id, levels, reverse, ...)
  }
  scale_colour_easyplot <- function(id, levels, ..., reverse = FALSE) {
    manual_scale("colour", id, levels, reverse, ...)
  }

  for (name in c("easyplot_palettes", "easyplot_palette_info", "easyplot_palette",
                 "scale_fill_easyplot", "scale_colour_easyplot")) {
    assign(name, get(name), envir = parent.env(environment()))
  }
  lockEnvironment(environment(), bindings = TRUE)
})
