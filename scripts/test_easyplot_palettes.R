# Contracts: Rscript test_easyplot_palettes.R [output-dir] [--real | --registry PATH]
# Isolated fixture installation; installed assets are never modified. --real also
# checks ../assets/palettes.json; --registry checks a staged JSON in a temporary
# installation. With an output directory, r_palette_parity.csv contains the
# selected registry, otherwise the test fixture.

args <- commandArgs(trailingOnly = TRUE)
real <- "--real" %in% args
args <- args[args != "--real"]
registry_path <- NULL
registry_arg <- which(args == "--registry")
if (length(registry_arg)) {
  if (length(registry_arg) != 1L || registry_arg == length(args) || real) {
    stop("Use either --real or --registry PATH.", call. = FALSE)
  }
  registry_path <- args[[registry_arg + 1L]]
  args <- args[-c(registry_arg, registry_arg + 1L)]
}
if (length(args) > 1L || any(startsWith(args, "--"))) {
  stop("Usage: test_easyplot_palettes.R [output-dir] [--real | --registry PATH]", call. = FALSE)
}
output_dir <- if (length(args)) args[[1L]] else NULL
script_arg <- grep("^--file=", commandArgs(), value = TRUE)[1L]
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE))
runtime <- file.path(script_dir, "easyplot_palettes.R")
if (!file.exists(runtime)) stop("Public API runtime is missing: ", runtime, call. = FALSE)

fixture_registry <- function() {
  record <- function(id, colours, selection = "prefix", kind = "qualitative", ...) {
    c(list(
      id = id, label = id, family = strsplit(id, ".", fixed = TRUE)[[1L]][1L], kind = kind,
      colours = as.list(colours), selection = selection,
      cvd = list(status = "not_assessed", evidence = "https://example.invalid/fixture",
                 note = "Synthetic test fixture; no accessibility claim."),
      source = list(url = "https://example.invalid/fixture", version = "test-1", license = "fixture"),
      tags = list("fixture")
    ), list(...))
  }
  set2 <- c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3")
  blues3 <- c("#DEEBF7", "#9ECAE1", "#3182BD")
  blues5 <- c("#EFF3FF", "#BDD7E7", "#6BAED6", "#3182BD", "#08519C")
  records <- list(
    record("ggsci.npg.nrc", c("#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
                              "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85")),
    record("brewer.Set2", set2, "native", native_sizes = list(`3` = as.list(set2[1:3]), `4` = as.list(set2[1:4]), `8` = as.list(set2))),
    record("brewer.Blues", blues5, "native", "sequential", native_sizes = list(`3` = as.list(blues3), `5` = as.list(blues5))),
    record("viridis.viridis", c("#440154", "#31688E", "#35B779", "#FDE725"), "lut", "sequential"),
    record("test.odd", c("#111111", "#333333", "#777777", "#BBBBBB", "#EEEEEE"), "lut", "diverging"),
    record("test.single", "#112233", "lut", "cyclic"),
    record("test.multi", c("#111122", "#222244", "#333366"), "lut", "multisequential"),
    record("cud.okabe_ito", c("#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000")),
    record("china.jiangnan", c("#123456", "#789ABC"), colour_names = list("\u9752", "\u7eff"), notes = "Synthetic colours."),
    record("dongfang.qingya", c("#654321", "#CBA987")),
    record("ggsci.iterm.Ocean%20%28Night%29.dark", c("#123123", "#456456")),
    record("china.stepped", c("#123456", "#234567", "#345678", "#456789", "#56789A", "#6789AB", "#789ABC"), "lut", "sequential")
  )
  records[[4L]]$cvd$status <- "conditional"
  records[[5L]]$cvd$status <- "not_recommended"
  records[[8L]]$cvd$status <- "reported"
  records[[9L]]$label <- "\u6c5f\u5357\uff08\u6d4b\u8bd5\uff09"
  records[[11L]]$tags <- c(records[[11L]]$tags, "extension")
  list(schema_version = 1L, version = "1.0.0", palettes = records, sources = list(), omissions = list())
}

load_api <- function(path, chdir = FALSE) {
  api <- new.env(parent = baseenv())
  source(path, local = api, chdir = chdir, encoding = "UTF-8")
  stopifnot(identical(sort(ls(api, all.names = TRUE)), sort(c(
    "easyplot_palettes", "easyplot_palette_info", "easyplot_palette",
    "scale_fill_easyplot", "scale_colour_easyplot"
  ))))
  api
}

expect_error <- function(expr, pattern) {
  error <- tryCatch({ force(expr); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(pattern, conditionMessage(error), ignore.case = TRUE))
}
as_hex <- function(x) unlist(x, use.names = FALSE)
sample_sizes <- function(record) {
  if (record$selection == "prefix") return(seq_along(record$colours))
  if (record$selection == "native") return(sort(unique(c(1L, 2L, as.integer(names(record$native_sizes))))))
  size <- length(record$colours)
  sort(unique(c(1L, 2L, 3L, 4L, 5L, 7L, 17L, size, min(size + 1L, 65536L), min(2L * size - 1L, 65536L))))
}

check_registry <- function(api, registry) {
  palette <- api$easyplot_palette
  info <- api$easyplot_palette_info
  catalogue <- api$easyplot_palettes
  records <- registry$palettes
  ids <- vapply(records, function(record) record$id, character(1L))
  metadata <- catalogue()
  stopifnot(is.data.frame(metadata), identical(metadata$id, ids), !anyDuplicated(ids),
            identical(palette("ggsci.npg.nrc", 1), "#E64B35"),
            identical(palette("brewer.Set2", 3), c("#66C2A5", "#FC8D62", "#8DA0CB")))
  for (field in c("family", "kind", "cvd")) {
    empty <- do.call(catalogue, stats::setNames(list("no-such-value"), field))
    stopifnot(nrow(empty) == 0L, identical(names(empty), names(metadata)))
    for (bad in list(TRUE, 1, list(), c("brewer", "ggsci"), "", "  ", NA_character_, character())) {
      expect_error(do.call(catalogue, stats::setNames(list(bad), field)), field)
    }
    key <- if (field == "cvd") "cvd_status" else field
    for (value in unique(metadata[[key]])) {
      selected <- do.call(catalogue, stats::setNames(list(value), field))
      stopifnot(identical(selected$id, metadata$id[metadata[[key]] == value]))
    }
  }
  combinations <- unique(metadata[c("family", "kind", "cvd_status")])
  for (i in seq_len(nrow(combinations))) {
    combination <- combinations[i, ]
    selected <- catalogue(combination$family, combination$kind, combination$cvd_status)
    expected <- metadata$id[metadata$family == combination$family & metadata$kind == combination$kind &
                            metadata$cvd_status == combination$cvd_status]
    stopifnot(identical(selected$id, expected))
  }
  for (record in records) {
    id <- record$id
    full <- as_hex(record$colours)
    meta <- metadata[metadata$id == id, , drop = FALSE]
    stopifnot(identical(info(id), record), identical(palette(id), full),
              identical(palette(id, reverse = TRUE), rev(full)), meta$n_colours == length(full),
              meta$selection == record$selection, meta$cvd_status == record$cvd$status,
              meta$cvd_note == record$cvd$note)
    for (n in sample_sizes(record)) {
      colours <- palette(id, n)
      stopifnot(length(colours) == n, identical(palette(id, n, reverse = TRUE), rev(colours)))
      if (record$selection == "prefix") {
        stopifnot(identical(colours, full[seq_len(n)]))
      } else if (record$selection == "native") {
        schemes <- record$native_sizes
        expected <- if (n < 3L) as_hex(schemes[[as.character(min(as.integer(names(schemes))))]])[seq_len(n)] else as_hex(schemes[[as.character(n)]])
        stopifnot(identical(colours, expected))
      } else {
        # Integer-ratio oracle, including exact half-way ties.
        indices <- if (n == 1L) floor(length(full) / 2) else
          (2 * (seq_len(n) - 1) * (length(full) - 1) + n - 1) %/% (2 * (n - 1))
        stopifnot(identical(colours, full[indices + 1L]))
        if (n >= 2L) stopifnot(colours[1L] == full[1L], colours[n] == full[length(full)])
      }
    }
    if (record$selection == "lut") {
      stopifnot(meta$max_n == 65536L)
      expect_error(palette(id, 65537), "65536")
    } else {
      capacity <- if (record$selection == "native") max(as.integer(names(record$native_sizes))) else length(full)
      stopifnot(meta$max_n == capacity)
      expect_error(palette(id, capacity + 1L), "at most")
      if (record$selection == "native" && capacity > 3L) {
        for (missing in setdiff(seq.int(3L, capacity - 1L), as.integer(names(record$native_sizes)))) {
          expect_error(palette(id, missing), "stored")
        }
      }
    }
    for (bad in list(0, -1, 1.5, TRUE, FALSE, NA_real_, NaN, Inf, -Inf, "2", numeric(), c(1, 2), 1i, list(2), factor("2"), matrix(2))) {
      expect_error(palette(id, bad), "positive integer")
    }
    for (bad in list(NULL, NA, 0, 1, "TRUE", logical(), c(TRUE, FALSE), matrix(TRUE))) {
      expect_error(palette(id, reverse = bad), "reverse")
    }
    stopifnot(length(full) > 0L, all(grepl("^#[0-9A-Fa-f]{6}$", full)))
  }
  for (bad in list(NULL, "", " ", "npg", "ggsci.NPG.nrc", "brewer.set2", "brewer.Set2 ", "unknown", 1, TRUE, list(), NA_character_, character(), ids[1:2])) {
    expect_error(info(bad), "id")
    expect_error(palette(bad), "id")
  }
  changed <- info("brewer.Set2")
  changed$colours[[1L]] <- "#FFFFFF"
  changed$native_sizes[["3"]][[1L]] <- "#FFFFFF"
  changed$cvd$status <- "not_recommended"
  changed$source$url <- "changed"
  changed$tags <- c(changed$tags, "changed")
  metadata$label[1L] <- "changed"
  returned <- palette("ggsci.npg.nrc")
  returned[1L] <- "#FFFFFF"
  stopifnot(identical(info("brewer.Set2"), records[[match("brewer.Set2", ids)]]),
            catalogue()$label[1L] == records[[1L]]$label,
            identical(palette("ggsci.npg.nrc", 1), "#E64B35"))
}

check_fixture_edges <- function(api) {
  palette <- api$easyplot_palette
  stopifnot(
    identical(palette("brewer.Blues", 3), c("#DEEBF7", "#9ECAE1", "#3182BD")),
    !identical(palette("brewer.Blues", 3), palette("brewer.Blues")[1:3]),
    identical(palette("brewer.Blues", 2), c("#DEEBF7", "#9ECAE1")),
    identical(palette("brewer.Blues", 2, reverse = TRUE), c("#9ECAE1", "#DEEBF7")),
    identical(palette("viridis.viridis", 1), "#35B779"),
    identical(palette("viridis.viridis", 3), c("#440154", "#35B779", "#FDE725")),
    identical(palette("test.odd", 1), "#777777"),
    identical(palette("test.odd", 9), c("#111111", "#333333", "#333333", "#777777", "#777777", "#BBBBBB", "#BBBBBB", "#EEEEEE", "#EEEEEE")),
    identical(palette("test.single", 3), rep("#112233", 3))
  )
  maximum <- palette("viridis.viridis", 65536)
  stopifnot(length(maximum) == 65536L, maximum[1L] == "#440154", maximum[65536L] == "#FDE725",
            setequal(maximum, palette("viridis.viridis")))
  changed <- api$easyplot_palette_info("china.jiangnan")
  changed$colour_names[[1L]] <- "changed"
  stopifnot(identical(as_hex(api$easyplot_palette_info("china.jiangnan")$colour_names), c("\u9752", "\u7eff")))
  stopifnot(identical(palette("ggsci.iterm.Ocean%20%28Night%29.dark", 1), "#123123"),
            "extension" %in% as_hex(api$easyplot_palette_info("ggsci.iterm.Ocean%20%28Night%29.dark")$tags),
            all(palette("china.stepped", 17) %in% palette("china.stepped")))
  expect_error(palette("ggsci.iterm.Ocean (Night).dark"), "id")
}

check_scales <- function(api) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    cat("ggplot2 unavailable: optional manual scale contract skipped.\n")
    return(invisible(NULL))
  }
  groups <- c("control", "low", "high")
  colours <- api$easyplot_palette("brewer.Set2", 3)
  for (scale_fn in list(api$scale_fill_easyplot, api$scale_colour_easyplot)) {
    scale <- scale_fn("brewer.Set2", groups)
    stopifnot(identical(scale$get_limits(), groups), identical(scale$palette(3L), stats::setNames(colours, groups)),
              identical(scale$na.value, "#E2E2E2"), identical(scale$drop, FALSE))
    scale$train(c("high", "control"))
    stopifnot(identical(scale$map(c("high", "control", "low", NA, "absent")), c(colours[c(3L, 1L, 2L)], "#E2E2E2", "#E2E2E2")))
    reversed <- scale_fn("brewer.Set2", groups, reverse = TRUE, name = "Dose")
    stopifnot(identical(reversed$palette(3L), stats::setNames(rev(colours), groups)), reversed$name == "Dose")
    for (bad in list(NULL, character(), "", " ", c("a", "a"), c("a", NA), 1:3, factor(groups), list("a"), matrix("a"))) {
      expect_error(scale_fn("brewer.Set2", bad), "levels")
    }
    expect_error(scale_fn("brewer.Set2", letters[1:9]), "at most")
    expect_error(scale_fn("viridis.viridis", groups), "qualitative")
    expect_error(scale_fn("brewer.Set2", groups, reverse = 1), "reverse")
    expect_error(scale_fn("brewer.Set2", groups, limits = rev(groups)), "controlled")
    expect_error(scale_fn("brewer.Set2", groups, values = rep("red", 3)), "controlled")
  }
}

write_parity <- function(api, registry, path) {
  rows <- list()
  ids <- vapply(registry$palettes, function(record) record$id, character(1L))
  for (record in registry$palettes[order(ids, method = "radix")]) {
    for (n in c(list(NULL), as.list(sample_sizes(record)))) {
      for (reverse in c(FALSE, TRUE)) {
        colours <- api$easyplot_palette(record$id, n, reverse)
        rows[[length(rows) + 1L]] <- data.frame(
          id = record$id, n = if (is.null(n)) "default" else as.character(n),
          reverse = as.integer(reverse), index = seq_along(colours), colour = colours,
          stringsAsFactors = FALSE
        )
      }
    }
  }
  utils::write.table(do.call(rbind, rows), path, sep = ",", row.names = FALSE, col.names = TRUE,
                     quote = TRUE, fileEncoding = "UTF-8", eol = "\n")
}

main <- function() {
  if (!is.null(output_dir) && !dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  root <- tempfile("r-palette-", tmpdir = if (is.null(output_dir)) tempdir() else output_dir)
  dir.create(file.path(root, "scripts"), recursive = TRUE)
  dir.create(file.path(root, "assets"))
  root <- normalizePath(root, winslash = "/", mustWork = TRUE)
  on.exit(unlink(root, recursive = TRUE), add = TRUE) # Only this test's unique temporary tree.
  fixture <- fixture_registry()
  fixture_path <- file.path(root, "assets", "palettes.json")
  jsonlite::write_json(fixture, fixture_path, auto_unbox = TRUE, pretty = TRUE)
  stopifnot(file.copy(runtime, file.path(root, "scripts", basename(runtime))))
  namespaces_before <- loadedNamespaces()
  api <- load_api(file.path(root, "scripts", basename(runtime)))
  check_registry(api, fixture)
  check_fixture_edges(api)
  stopifnot(!"ggplot2" %in% setdiff(loadedNamespaces(), namespaces_before))
  previous_dir <- getwd()
  setwd(root)
  relative_api <- tryCatch(load_api("scripts/easyplot_palettes.R", chdir = TRUE), finally = setwd(previous_dir))
  stopifnot(identical(relative_api$easyplot_palettes(), api$easyplot_palettes()))
  check_scales(api)
  cat("R fixture contracts passed: ", length(fixture$palettes), " palettes; source paths and named manual scales.\n", sep = "")
  if (real) {
    registry <- jsonlite::fromJSON(file.path(script_dir, "..", "assets", "palettes.json"), simplifyVector = FALSE)
    api <- load_api(runtime)
    check_registry(api, registry)
    cat("R real-registry contracts passed: ", length(registry$palettes), " palettes.\n", sep = "")
  } else if (!is.null(registry_path)) {
    stopifnot(file.copy(registry_path, fixture_path, overwrite = TRUE))
    registry <- jsonlite::fromJSON(fixture_path, simplifyVector = FALSE)
    api <- load_api(file.path(root, "scripts", basename(runtime)))
    check_registry(api, registry)
    cat("R staged-registry contracts passed: ", length(registry$palettes), " palettes.\n", sep = "")
  } else registry <- fixture
  if (!is.null(output_dir)) {
    path <- file.path(output_dir, "r_palette_parity.csv")
    write_parity(api, registry, path)
    cat(normalizePath(path, winslash = "/"), "\n")
  }
}
main()
