# One executable contract check; no test framework or new dependencies.
# Rscript test_easyplot_dongfang.R [output-dir] [--overwrite]

args <- commandArgs(trailingOnly = TRUE)
overwrite <- "--overwrite" %in% args
args <- args[args != "--overwrite"]
if (length(args) > 1L || any(startsWith(args, "--"))) {
  stop("Usage: test_easyplot_dongfang.R [output-dir] [--overwrite]", call. = FALSE)
}
output_dir <- if (length(args)) args[[1L]] else file.path(tempdir(), "easyplot-dongfang")
targets <- file.path(output_dir, c("r_palette_parity.json", "cvd_simulations.json"))
if (!overwrite && any(file.exists(targets))) {
  stop("Refusing to overwrite existing output(s): ",
       paste(targets[file.exists(targets)], collapse = ", "), call. = FALSE)
}
script_arg <- grep("^--file=", commandArgs(), value = TRUE)[1L]
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE))
api <- new.env(parent = baseenv())
source(file.path(script_dir, "easyplot_dongfang.R"), local = api, encoding = "UTF-8")
stopifnot(identical(sort(ls(api, all.names = TRUE)),
                    sort(c("dongfang_color", "dongfang_palette", "dongfang_palettes"))))
dongfang_color <- api$dongfang_color
dongfang_palette <- api$dongfang_palette
dongfang_palettes <- api$dongfang_palettes
stopifnot(identical(dongfang_palette(), dongfang_palette("danqing")))
# Also source from a relative path while source() changes the working directory.
relative_api <- new.env(parent = baseenv())
previous_dir <- getwd()
setwd(dirname(script_dir))
tryCatch(
  source("scripts/easyplot_dongfang.R", local = relative_api, chdir = TRUE, encoding = "UTF-8"),
  finally = setwd(previous_dir)
)
stopifnot(identical(relative_api$dongfang_palettes(), dongfang_palettes()))
registry <- jsonlite::fromJSON(
  file.path(script_dir, "..", "assets", "dongfang.json"), simplifyVector = FALSE
)
expect_error <- function(expr, pattern) {
  error <- tryCatch({ force(expr); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(pattern, conditionMessage(error)))
}
as_hex <- function(x) unlist(x, use.names = FALSE)

stopifnot(
  length(registry$source_colours) == 320L,
  # Unicode escapes also exercise the source spellings under an R C locale.
  identical(dongfang_color("\u7843\u7802"), "#B84B48"), # 硃砂
  identical(dongfang_color("\u6731\u7802"), "#B84B48"), # 朱砂
  identical(dongfang_color("\u5976\u7dd1"), "#AFC8BA"), # 奶緑
  identical(dongfang_color("\u5976\u7eff"), "#AFC8BA"), # 奶绿
  setequal(names(dongfang_palettes()),
           c("danqing", "qingya", "qiushan", "qingci", "moyun", "qingzhu", "qinglan"))
)
for (colour in registry$source_colours) {
  for (name in c(colour$name, as_hex(colour$aliases))) {
    stopifnot(identical(dongfang_color(name), colour$hex))
  }
}

source_check_names <- c("\u7843\u7802", "\u6731\u7802", "\u5976\u7dd1", "\u5976\u7eff")
parity <- list(
  registry_version = registry$version, r_version = as.character(getRversion()),
  source_checks = stats::setNames(lapply(source_check_names, dongfang_color), source_check_names),
  palettes = list()
)
sample_sizes <- c(1L, 2L, 3L, 4L, 6L, 17L, 256L, 257L, 258L, 513L)
for (name in names(registry$palettes)) {
  spec <- registry$palettes[[name]]
  fill <- dongfang_palette(name)
  # Fills follow the derived registry values; source_names record colour anchors.
  # Original source-colour identities are tested separately above.
  classic_fill <- as_hex(spec$classic$fill)
  stopifnot(
    identical(fill, as_hex(spec$fill)), all(grepl("^#[0-9A-Fa-f]{6}$", fill)),
    is.character(spec$classic$name), length(spec$classic$name) == 1L,
    !is.na(spec$classic$name), nzchar(trimws(spec$classic$name)),
    length(classic_fill) == length(fill), all(grepl("^#[0-9A-Fa-f]{6}$", classic_fill)),
    identical(spec$derived, name != "moyun")
  )
  if (name == "moyun") stopifnot(identical(fill, classic_fill))
  record <- list(type = spec$type, fill = I(fill))
  if (spec$type == "qualitative") {
    stopifnot(length(fill) == spec$max_n, length(spec$line) == spec$max_n)
    for (role in c("fill", "line")) {
      full <- dongfang_palette(name, role = role)
      stopifnot(identical(full, as_hex(spec[[role]])))
      for (n in seq_len(spec$max_n)) {
        stopifnot(
          identical(dongfang_palette(name, n, role), full[seq_len(n)]),
          identical(dongfang_palette(name, n, role, reverse = TRUE), rev(full[seq_len(n)]))
        )
      }
      expect_error(dongfang_palette(name, spec$max_n + 1L, role), "at most")
    }
    record$line <- I(dongfang_palette(name, role = "line"))
  } else {
    stopifnot(length(fill) == 257L)
    expect_error(dongfang_palette(name, role = "line"), "qualitative")
    record$samples <- list()
    for (n in sample_sizes) {
      # Half-up rounding, including ties (513 samples) and the one-colour centre.
      indices <- if (n == 1L) 129L else floor(seq(0, 256, length.out = n) + 0.5) + 1L
      sampled <- dongfang_palette(name, n)
      stopifnot(identical(sampled, fill[indices]),
                identical(dongfang_palette(name, n, reverse = TRUE), rev(sampled)))
      record$samples[[as.character(n)]] <- I(sampled)
    }
  }
  stopifnot(identical(dongfang_palette(name, reverse = TRUE), rev(fill)))
  parity$palettes[[name]] <- record
}

for (bad in list(NULL, "", "  ", "unknown", NA_character_, 1, character(), c("danqing", "qingya"))) {
  expect_error(dongfang_color(bad), "Unknown or empty")
  expect_error(dongfang_palette(bad), "Unknown or empty")
}
expect_error(dongfang_color(), "missing")
for (name in names(registry$palettes)) {
  for (bad in list(0, -1, 1.5, TRUE, NA_real_, NaN, Inf, -Inf, "2", numeric(), c(1, 2), 1i, list(2))) {
    expect_error(dongfang_palette(name, n = bad), "positive integer")
  }
}
for (bad in list(NULL, "", "f", "stroke", NA_character_, c("fill", "line"), 1)) {
  expect_error(dongfang_palette("danqing", role = bad), "Role must")
}
for (bad in list(NULL, NA, 1, "TRUE", c(TRUE, FALSE))) {
  expect_error(dongfang_palette("danqing", reverse = bad), "reverse must")
}
metadata <- dongfang_palettes()
metadata$danqing$label <- "modified"
modified <- dongfang_palette("danqing")
modified[1L] <- "#000000"
stopifnot(identical(dongfang_palettes()$danqing$label, registry$palettes$danqing$label),
          identical(dongfang_palette("danqing"), as_hex(registry$palettes$danqing$fill)))
expect_error(assign("registry", list(), envir = environment(dongfang_palette)), "locked binding")

if (!requireNamespace("colorspace", quietly = TRUE)) {
  stop("CVD fixtures require the installed colorspace package.", call. = FALSE)
}
# Model/linear-RGB notes checked against the installed help('protan', 'colorspace').
cvd <- list(
  registry_version = registry$version,
  colorspace_version = as.character(utils::packageVersion("colorspace")),
  model = "Machado, Oliveira and Fernandes (2009), doi:10.1109/TVCG.2009.113",
  severity = 1,
  linear = TRUE,
  notes = paste(
    "colorspace::protan/deutan/tritan apply the model to linearized RGB, then convert back to sRGB.",
    "Explicit linear=TRUE uses the behavior introduced in colorspace 2.1-0;",
    "versions through 2.0-3 transformed gamma-corrected sRGB instead.",
    "Severity 1 is the full-severity simulation. These previews support visual screening."
  ),
  help_topic = "colorspace::simulate_cvd (aliases: protan, deutan, tritan)",
  palettes = list()
)
for (name in names(registry$palettes)) {
  if (registry$palettes[[name]]$type != "qualitative") next
  cvd$palettes[[name]] <- list()
  for (role in c("fill", "line")) {
    colours <- dongfang_palette(name, role = role)
    simulations <- list(
      original = colours,
      protan = colorspace::protan(colours, severity = 1, linear = TRUE),
      deutan = colorspace::deutan(colours, severity = 1, linear = TRUE),
      tritan = colorspace::tritan(colours, severity = 1, linear = TRUE)
    )
    stopifnot(all(lengths(simulations) == length(colours)),
              all(grepl("^#[0-9A-Fa-f]{6}$", unlist(simulations))))
    cvd$palettes[[name]][[role]] <- lapply(simulations, I)
  }
}
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
jsonlite::write_json(parity, targets[1L], pretty = TRUE, auto_unbox = TRUE)
jsonlite::write_json(cvd, targets[2L], pretty = TRUE, auto_unbox = TRUE)
stopifnot(all(file.info(targets)$size > 0))
cat("Dongfang R contracts passed: 320 source colours and aliases; all ", length(parity$palettes), " palettes;\n",
    "classic bases and derived fills; ",
    "prefixes, capacities, LUT sampling, reversal, validation and mutation isolation.\n",
    "CVD simulations: all ", length(cvd$palettes), " qualitative palettes, fill + line, protan/deutan/tritan.\n",
    paste(normalizePath(targets, winslash = "/"), collapse = "\n"), "\n", sep = "")
