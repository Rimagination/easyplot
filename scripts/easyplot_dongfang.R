# Opt-in Dongfang palettes. Source this file; the existing EasyPlot runtime
# and defaults are unchanged. Name returned colours by semantic group once.

local({
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("Dongfang palettes require jsonlite.", call. = FALSE)
  }
  source_frames <- Filter(function(frame) !is.null(frame$ofile), sys.frames())
  if (!length(source_frames)) {
    stop("Load easyplot_dongfang.R with source().", call. = FALSE)
  }
  source_frame <- source_frames[[length(source_frames)]]
  script_path <- if (isTRUE(source_frame$chdir)) basename(source_frame$ofile) else source_frame$ofile
  script_path <- normalizePath(script_path, mustWork = TRUE)
  registry <- jsonlite::fromJSON(
    file.path(dirname(script_path), "..", "assets", "dongfang.json"),
    simplifyVector = FALSE
  )
  colours <- unlist(lapply(registry$source_colours, function(colour) {
    keys <- c(colour$name, unlist(colour$aliases, use.names = FALSE))
    stats::setNames(rep(colour$hex, length(keys)), keys)
  }))
  check_name <- function(name, known, kind) {
    if (!is.character(name) || length(name) != 1L || is.na(name) ||
        !nzchar(trimws(name)) || !name %in% known) {
      stop("Unknown or empty Dongfang ", kind, " name.", call. = FALSE)
    }
  }

  dongfang_color <- function(name) {
    check_name(name, names(colours), "source colour")
    unname(colours[[name]])
  }

  dongfang_palette <- function(name = "danqing", n = NULL, role = "fill", reverse = FALSE) {
    check_name(name, names(registry$palettes), "palette")
    spec <- registry$palettes[[name]]
    if (!is.character(role) || length(role) != 1L || is.na(role) ||
        !role %in% c("fill", "line") || !role %in% names(spec)) {
      stop("Role must be 'fill', or 'line' for a qualitative palette.", call. = FALSE)
    }
    if (!is.logical(reverse) || length(reverse) != 1L || is.na(reverse)) {
      stop("reverse must be TRUE or FALSE.", call. = FALSE)
    }
    values <- unlist(spec[[role]], use.names = FALSE)
    if (is.null(n)) n <- length(values)
    if (!typeof(n) %in% c("integer", "double") || length(n) != 1L ||
        !is.finite(n) || n < 1 || n != floor(n)) {
      stop("n must be one positive integer.", call. = FALSE)
    }
    if (spec$type == "qualitative") {
      if (n > spec$max_n) {
        stop(name, " supports at most ", spec$max_n, " categories.", call. = FALSE)
      }
      values <- values[seq_len(n)]
    } else {
      indices <- if (n == 1) 129L else floor(seq(0, 256, length.out = n) + 0.5) + 1L
      values <- values[indices]
    }
    if (reverse) rev(values) else values
  }

  dongfang_palettes <- function() {
    lapply(registry$palettes, function(spec) {
      spec[c("label", "type", "max_n", "rationale", "uses")]
    })
  }

  # Only the three public helpers enter the sourcing environment. R's value
  # semantics isolate returned vectors/lists; locked bindings protect the cache.
  for (name in c("dongfang_color", "dongfang_palette", "dongfang_palettes")) {
    assign(name, get(name), envir = parent.env(environment()))
  }
  lockEnvironment(environment(), bindings = TRUE)
})
