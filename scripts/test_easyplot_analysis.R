# One executable suite. Optional positional JSON path; existing files are refused.
script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_arg)
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 1L) stop("Usage: Rscript test_easyplot_analysis.R [fixture.json | --only=replicates | --only=multiplicity]", call. = FALSE)
if (length(args) && file.exists(args[[1L]])) stop("Refusing to overwrite fixture", call. = FALSE)
source(file.path(dirname(script_path), "easyplot_analysis.R"), local = TRUE)

run <- function(data, ...) {
  before <- data
  on.exit(stopifnot(identical(data, before)))
  options <- utils::modifyList(list(data = data, group = "arm", value = "measurement", unit = "id",
                                   order = c("A", "B"), design = "independent", confidence = .90),
                               list(...), keep.null = TRUE)
  do.call(easyplot_analyze_two_groups, options)
}
rejects <- function(data, message, ...) {
  error <- tryCatch({ run(data, ...); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(message, conditionMessage(error), fixed = TRUE))
}
same <- function(actual, expected) stopifnot(isTRUE(all.equal(actual, expected, tolerance = 1e-12)))
check_library <- function(report, first, second) {
  paired <- report$design == "paired"
  expected <- stats::t.test(second, first, paired = paired, var.equal = FALSE,
                            alternative = "two.sided", conf.level = report$effect$confidence)
  same(report$test, list(method = if (paired) "Paired t-test" else "Welch Two Sample t-test",
                         statistic = unname(expected$statistic), df = unname(expected$parameter),
                         p_value = expected$p.value, alternative = "two-sided"))
  same(report$effect, list(label = "mean difference (second - first)",
                           estimate = if (paired) mean(second - first) else mean(second) - mean(first),
                           ci_low = unname(expected$conf.int[1L]), ci_high = unname(expected$conf.int[2L]),
                           confidence = report$effect$confidence))
  samples <- list(first, second)
  for (i in seq_along(samples)) {
    x <- samples[[i]]
    same(report$summary[[i]], list(group = report$order[[i]], n = length(x), mean = mean(x),
                                  sd = stats::sd(x), se = stats::sd(x) / sqrt(length(x))))
  }
}

expect_error <- function(expr, message) {
  error <- tryCatch({ force(expr); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(message, conditionMessage(error), fixed = TRUE))
}
summarize <- function(data, ...) {
  before <- data
  on.exit(stopifnot(identical(data, before)))
  options <- utils::modifyList(list(data = data, group = "arm", value = "measurement", unit = "id",
                                   replicate = "reading", design = "independent"), list(...), keep.null = TRUE)
  do.call(easyplot_summarize_replicates, options)
}
summary_table <- function(report) {
  do.call(rbind, lapply(report$summary, function(s) {
    data.frame(id = s$unit, arm = s$group, measurement = if (is.null(s$value)) NA_real_ else s$value)
  }))
}

check_replicates <- function() {
  data <- data.frame(id = c("u1", "u1", "u2", "u3", "u4"),
                     arm = c("A", "A", "A", "B", "B"), reading = c(1, 2, 1, 1, 1),
                     measurement = c(1, 3, 10, 4, 8))
  report <- summarize(data)
  same(report$summary, list(
    list(unit = "u1", group = "A", value = 2, n_input = 2L, n_used = 2L, n_missing = 0L, sd = sqrt(2)),
    list(unit = "u2", group = "A", value = 10, n_input = 1L, n_used = 1L, n_missing = 0L, sd = NULL),
    list(unit = "u3", group = "B", value = 4, n_input = 1L, n_used = 1L, n_missing = 0L, sd = NULL),
    list(unit = "u4", group = "B", value = 8, n_input = 1L, n_used = 1L, n_missing = 0L, sd = NULL)))
  reports <- list(replicates_independent = report)
  downstream <- run(summary_table(report))
  stopifnot(downstream$summary[[1L]]$mean == 6, downstream$summary[[1L]]$n == 2L,
            mean(data$measurement[data$arm == "A"]) != 6)
  reports$replicates_equal_weight <- downstream
  repeated <- data.frame(
    id = c("u2", "u1", "u1", "u2", "u1", "u3", "u3", "u4", "u4", "u5"),
    arm = c("B", "A", "A", "A", "B", "A", "B", "A", "B", "A"),
    reading = c(1, 1, 2, 1, 1, 1, 1, 1, 2, 1),
    measurement = c(8, 1, 3, 3, 3, 5, NA, NaN, NA, 9))
  expect_error(summarize(repeated, design = "repeated"), "missing")
  available <- summarize(repeated, design = "repeated", missing = "available")
  reports$replicates_available <- available
  stopifnot(available$n_input == 10L, available$n_used == 7L, available$n_missing == 3L,
            available$n_units == 5L, available$n_unit_conditions == 9L)
  same(lapply(available$summary, function(s) c(s$unit, s$group)),
       list(c("u2", "B"), c("u1", "A"), c("u2", "A"), c("u1", "B"), c("u3", "A"),
            c("u3", "B"), c("u4", "A"), c("u4", "B"), c("u5", "A")))
  stopifnot(sum(vapply(available$summary, function(s) is.null(s$value), logical(1))) == 3L,
            any(grepl("selection bias", unlist(available$warnings), fixed = TRUE)),
            any(grepl("All-missing", unlist(available$warnings), fixed = TRUE)))
  # Missing cells survive aggregation; absent u5/B is never fabricated.
  table <- summary_table(available)
  rejects(table, "missing", design = "paired")
  paired_report <- run(table, design = "paired", missing = "complete-case")
  reports$replicates_paired_complete_case <- paired_report
  stopifnot(paired_report$n_input == 9L, paired_report$n_used == 4L,
            paired_report$n_removed == 5L, paired_report$n_pairs == 2L)
  same(paired_report$removed_units, list("u3", "u4", "u5"))
  check_library(paired_report, c(3, 2), c(8, 3))
  shuffled <- repeated[c(8, 3, 9, 5, 1, 10, 2, 6, 4, 7), ]
  shuffled_report <- summarize(shuffled, design = "repeated", missing = "available")
  reports$replicates_shuffled <- shuffled_report
  same(shuffled_report$summary, available$summary[c(7, 2, 8, 4, 1, 9, 5, 3, 6)])
  numeric_data <- data
  numeric_data$id <- c(11, 11, 12, 21, 22)
  numeric_data$arm <- c(2, 2, 2, 1, 1)
  numeric_data$reading <- c(.5, 1.5, .5, .5, .5)
  reports$replicates_numeric <- summarize(numeric_data)
  categories <- data
  for (column in c("id", "arm", "reading")) categories[[column]] <- factor(data[[column]])
  same(summarize(categories), report)
  all_missing <- data
  all_missing$measurement <- rep(NA_real_, nrow(data))
  reports$replicates_all_missing <- summarize(all_missing, missing = "available")
  partial <- data
  partial$measurement[[2L]] <- NA_real_
  reports$replicates_partial <- summarize(partial, missing = "available")
  same(reports$replicates_partial$summary[[1L]],
       list(unit = "u1", group = "A", value = 1, n_input = 2L, n_used = 1L, n_missing = 1L, sd = NULL))
  reports$replicates_single <- summarize(data[1, ])
  reports$replicates_repeated_complete <- summarize(repeated[1:5, ], design = "repeated")
  zero <- data
  zero$measurement <- rep(0, nrow(data))
  reports$replicates_zero <- summarize(zero)
  stopifnot(reports$replicates_zero$summary[[1L]]$sd == 0)

  extra <- data[1, ]
  extra$measurement <- NA_real_
  expect_error(summarize(rbind(data, extra), missing = "available"), "duplicate unit/group/replicate")
  expect_error(summarize(repeated, missing = "available"), "single group")
  extra$arm <- "B"
  expect_error(summarize(rbind(data, extra), missing = "available"), "single group")
  expect_error(summarize(data[0, ]), "nonempty")
  expect_error(summarize(as.matrix(data)), "data.frame")
  for (options in list(list(replicate = "id"), list(group = "measurement"), list(unit = "absent"), list(value = " "))) {
    expect_error(do.call(summarize, c(list(data = data), options)), "columns")
  }
  duplicate_columns <- cbind(data, data["id"])
  names(duplicate_columns)[5L] <- "id"
  expect_error(summarize(duplicate_columns), "columns")
  for (design in list(NULL, TRUE, "paired", "auto", c("repeated", "independent"))) {
    expect_error(summarize(data, design = design), "design")
  }
  expect_error(easyplot_summarize_replicates(data, "arm", "measurement", "id", "reading"), "design")
  for (policy in list(NULL, TRUE, "complete-case", "drop")) {
    expect_error(summarize(data, missing = policy), "missing")
  }
  for (values in list(rep(TRUE, 5), as.character(data$measurement), as.complex(data$measurement),
                      as.list(data$measurement), list(TRUE, 3, 10, 4, 8))) {
    bad <- data
    bad$measurement <- values
    expect_error(summarize(bad), "real numeric")
  }
  for (number in c(Inf, -Inf)) {
    bad <- data
    bad$measurement[[1L]] <- number
    expect_error(summarize(bad, missing = "available"), "infinite")
  }
  bad <- data
  bad$measurement[1:2] <- c(1.7e308, -1.7e308)
  expect_error(summarize(bad), "nonfinite replicate")
  for (column in c("id", "arm", "reading")) {
    for (values in list(c("", "b", "c", "d", "e"), c(" \t", "b", "c", "d", "e"),
                        c("\u3000", "b", "c", "d", "e"), c(NA, 2, 3, 4, 5),
                        c(NaN, 2, 3, 4, 5), c(Inf, 2, 3, 4, 5), rep(TRUE, 5),
                        as.complex(1:5), list(1, "two", 3, 4, 5))) {
      bad <- data
      bad[[column]] <- values
      bad$measurement[[1L]] <- NA_real_
      expect_error(summarize(bad, missing = "available"), "identities")
    }
  }
  keys <- c("schema_version", "design", "columns", "estimator", "missing_policy", "n_input",
            "n_used", "n_missing", "n_units", "n_unit_conditions", "summary", "warnings", "assumptions")
  for (result in reports) {
    if (is.null(result$estimator)) next
    stopifnot(setequal(names(result), keys), result$schema_version == "1.0.0",
              result$estimator == "arithmetic mean within unit/condition",
              identical(result$columns, list(group = "arm", value = "measurement", unit = "id", replicate = "reading")),
              result$n_input == result$n_used + result$n_missing,
              result$n_units == length(unique(lapply(result$summary, function(s) s$unit))),
              result$n_unit_conditions == length(result$summary))
    for (field in c("n_input", "n_used", "n_missing")) {
      stopifnot(result[[field]] == sum(vapply(result$summary, function(s) s[[field]], integer(1))))
    }
    for (cell in result$summary) {
      stopifnot(setequal(names(cell), c("unit", "group", "value", "n_input", "n_used", "n_missing", "sd")),
                is.null(cell$value) == (cell$n_used == 0L), is.null(cell$sd) == (cell$n_used < 2L))
    }
    stopifnot(any(grepl("independent sample size", unlist(result$warnings), fixed = TRUE)),
              length(result$assumptions) > 0L)
  }
  reports
}

check_multiplicity <- function() {
  pvalues <- c(.2, .01, .04)
  expected <- list(holm = c(.2, .03, .08), bonferroni = c(.6, .03, .12),
                   BH = c(.2, .03, .06), BY = c(11/30, .055, .11))
  reports <- list()
  for (method in names(expected)) {
    report <- easyplot_adjust_pvalues(pvalues, labels = c("c3", "c1", "c2"),
                                      method = method, family = "Prespecified contrasts")
    same(report$results, lapply(seq_along(pvalues), function(i) {
      list(comparison = c("c3", "c1", "c2")[[i]], p_raw = pvalues[[i]],
           p_adjusted = expected[[method]][[i]], reject = expected[[method]][[i]] <= .05)
    }))
    reports[[paste0("adjust_", method)]] <- report
    permutation <- c(3L, 1L, 2L)
    reordered <- easyplot_adjust_pvalues(pvalues[permutation], c("c3", "c1", "c2")[permutation], method, report$family)
    same(reordered$results, report$results[permutation])
    cases <- list(ties = list(p = c(1, .04, .04, 0, .9, .001), alpha = .05),
                  single = list(p = .05, alpha = .05), threshold = list(p = c(.025, .2), alpha = .05),
                  alpha_small = list(p = c(0, 1), alpha = .Machine$double.xmin * .Machine$double.eps),
                  alpha_large = list(p = c(0, 1), alpha = 1 - .Machine$double.eps))
    for (name in names(cases)) {
      case <- cases[[name]]
      result <- easyplot_adjust_pvalues(case$p, labels = paste0("c", seq_along(case$p) - 1L),
                                        method = method, family = "Prespecified contrasts", alpha = case$alpha)
      reports[[paste0("adjust_", method, "_", name)]] <- result
      if (name == "single") same(result$results[[1L]], list(comparison = "c0", p_raw = .05, p_adjusted = .05, reject = TRUE))
      if (name == "threshold") stopifnot(result$results[[1L]]$reject == (method != "BY"))
      if (startsWith(name, "alpha_")) same(lapply(result$results, function(x) x$reject), list(TRUE, FALSE))
    }
  }
  for (result in reports) {
    stopifnot(setequal(names(result), c("schema_version", "family", "method", "error_control", "alpha", "m", "results", "assumptions")),
              result$schema_version == "1.0.0", result$m == length(result$results),
              result$error_control == if (result$method %in% c("holm", "bonferroni")) "FWER" else "FDR")
    raw <- vapply(result$results, function(x) x$p_raw, numeric(1))
    same(vapply(result$results, function(x) x$p_adjusted, numeric(1)), stats::p.adjust(raw, method = result$method))
    for (row in result$results) {
      stopifnot(setequal(names(row), c("comparison", "p_raw", "p_adjusted", "reject")),
                row$p_raw >= 0, row$p_raw <= row$p_adjusted, row$p_adjusted <= 1,
                is.logical(row$reject), identical(row$reject, row$p_adjusted <= result$alpha))
    }
    stopifnot(grepl(if (result$method == "BH") "PRDS" else "arbitrary dependence", result$assumptions[[3L]], fixed = TRUE))
  }
  adjust <- function(values, ...) {
    before <- values
    on.exit(stopifnot(identical(values, before)))
    options <- utils::modifyList(list(pvalues = values, labels = c("a", "b"), method = "holm", family = "Primary contrasts"),
                                 list(...), keep.null = TRUE)
    do.call(easyplot_adjust_pvalues, options)
  }
  for (values in list(numeric(), "0.1", list(.1, .2), matrix(c(.1, .2)), array(c(.1, .2), c(1, 1, 2)),
                      c(TRUE, FALSE), list(TRUE, .1), as.complex(c(.1, .2)), c("0.1", "0.2"),
                      c(NaN, .1), c(NA, .1), c(Inf, .1), c(-.01, .1), c(1.01, .1), factor(c(.1, .2)))) {
    expect_error(adjust(values), "pvalues")
  }
  for (labels in list("a", c("a", "a"), c("a", ""), c("a", "\u3000"), c("a", NA), 1:2,
                      list("a", "b"), matrix(c("a", "b")), factor(c("a", "b")))) {
    expect_error(adjust(c(.1, .2), labels = labels), "labels")
  }
  for (method in list("auto", "bh", "fdr_bh", NULL, TRUE, c("holm", "BH"))) {
    expect_error(adjust(c(.1, .2), method = method), "method")
  }
  for (family in list("", " \t", "\u3000", NULL, TRUE, c("a", "b"), matrix("family"))) {
    expect_error(adjust(c(.1, .2), family = family), "family")
  }
  for (alpha in list(0, 1, -1, NaN, Inf, TRUE, "0.05", NULL, list(.05), matrix(.05))) {
    expect_error(adjust(c(.1, .2), alpha = alpha), "alpha")
  }
  for (required in c("labels", "method", "family")) {
    options <- list(pvalues = c(.1, .2), labels = c("a", "b"), method = "holm", family = "Primary contrasts")
    options[[required]] <- NULL
    expect_error(do.call(easyplot_adjust_pvalues, options), required)
  }
  same(adjust(c(first = .1, second = .2)), adjust(c(.1, .2)))
  reports
}

if (length(args) && args[[1L]] %in% c("--only=replicates", "--only=multiplicity")) {
  selected <- if (args[[1L]] == "--only=replicates") check_replicates else check_multiplicity
  reports <- selected()
  cat("EasyPlot", args[[1L]], "R checks passed:", length(reports), "reports.\n")
  quit(status = 0L)
}

first <- c(1, 2, 4, 7)
second <- c(3, 5, 8, 10, 12)
after <- c(2, 6, 5, 12)
independent <- data.frame(id = paste0("u", 0:8), arm = c(rep("A", 4), rep("B", 5)),
                          measurement = c(first, second))
paired <- data.frame(id = rep(paste0("u", 0:3), 2), arm = c(rep("A", 4), rep("B", 4)),
                     measurement = c(first, after))
reports <- list(independent = run(independent), paired = run(paired, design = "paired"))
check_library(reports$independent, first, second)
check_library(reports$paired, first, after)
for (design in c("independent", "paired")) {
  data <- if (design == "independent") independent else paired
  reversed <- run(data, design = design, order = c("B", "A"))
  reports[[paste0(design, "_reversed")]] <- reversed
  effect <- reports[[design]]$effect
  stopifnot(effect$estimate > 0, reversed$effect$estimate < 0)
  same(reversed$effect$estimate, -effect$estimate)
  same(reversed$effect$ci_low, -effect$ci_high)
  same(reversed$effect$ci_high, -effect$ci_low)
  same(reversed$test$statistic, -reports[[design]]$test$statistic)
  same(reversed$test$p_value, reports[[design]]$test$p_value)
}
same(run(paired[c(7, 1, 6, 4, 5, 3, 8, 2), ], design = "paired"), reports$paired)

independent_missing <- rbind(independent, data.frame(
  id = c("gone_a", "gone_b"), arm = c("A", "B"), measurement = c(NA_real_, NA_real_)))
paired_missing <- rbind(paired, data.frame(
  id = c("u4", "u4", "u5", "u6", "u7", "u7"), arm = c("A", "B", "A", "B", "A", "B"),
  measurement = c(9, NA, 9, 12, NaN, NA)))
for (design in c("independent", "paired")) {
  data <- if (design == "independent") independent_missing else paired_missing
  rejects(data, "missing", design = design)
  report <- run(data, design = design, missing = "complete-case")
  reports[[paste0(design, "_complete_case")]] <- report
  same(report$removed_units, if (design == "independent") list("gone_a", "gone_b") else as.list(paste0("u", 4:7)))
  stopifnot(report$n_input == nrow(data), report$n_used == if (design == "independent") 9L else 8L,
            report$n_removed == if (design == "independent") 2L else 6L,
            length(report$warnings) == 1L, grepl("selection bias", report$warnings[[1L]], fixed = TRUE))
  check_library(report, first, if (design == "independent") second else after)
}
rejects(paired[-8, ], "absent", design = "paired")
numeric_labels <- independent
numeric_labels$id <- 0:8
numeric_labels$arm <- c(rep(1, 4), rep(2, 5))
reports$numeric_labels <- run(numeric_labels, order = c(1, 2))
constant_margin <- paired
constant_margin$measurement[constant_margin$arm == "A"] <- 1
reports$paired_constant_margin <- run(constant_margin, design = "paired")
check_library(reports$paired_constant_margin, rep(1, 4), after)
zero_effect <- paired
zero_effect$measurement[zero_effect$arm == "B"] <- c(2, 3, 4, 5)
reports$paired_zero_effect <- run(zero_effect, design = "paired")
stopifnot(reports$paired_zero_effect$test$p_value == 1)

for (design in c("independent", "paired")) {
  data <- if (design == "independent") independent else paired
  extra <- data[1, ]
  extra$measurement <- NA_real_
  rejects(rbind(data, extra), "duplicate unit", design = design, missing = "complete-case")
  data$measurement <- rep(NA_real_, nrow(data))
  rejects(data, "at least two", design = design, missing = "complete-case")
}
cross_duplicate <- independent
cross_duplicate$id[5] <- "u0"
rejects(cross_duplicate, "duplicate unit")
rejects(paired, "duplicate unit", design = "independent")
constant <- independent
constant$measurement[constant$arm == "A"] <- 1
rejects(constant, "variance")
constant_difference <- paired
constant_difference$measurement[constant_difference$arm == "B"] <- first + 2
rejects(constant_difference, "variance", design = "paired")
near_constant <- paired
near_constant$id <- 1:8
near_constant$measurement <- 1e15 + c(0, 1, 2, 3, 3, 4, 5, 6)
rejects(near_constant, "essentially constant")
near_constant_pair <- paired
near_constant_pair$measurement <- c(first, first + 1e15 + c(0, 1, 2, 3))
rejects(near_constant_pair, "essentially constant", design = "paired")
rejects(independent[c(1, 5, 6), ], "at least two")
rejects(paired[c(1, 5), ], "at least two", design = "paired")
rejects(independent[0, ], "nonempty")
rejects(as.matrix(independent), "data.frame")
for (values in list(as.character(independent$measurement), rep(TRUE, 9),
                    as.complex(independent$measurement), as.list(independent$measurement))) {
  data <- independent
  data$measurement <- values
  rejects(data, "real numeric")
}
for (number in c(Inf, -Inf)) {
  data <- independent
  data$measurement[1] <- number
  rejects(data, "infinite", missing = "complete-case")
}
for (column in c("id", "arm")) {
  for (invalid in c("", "  \t", "\u3000", NA_character_)) {
    data <- independent
    data[[column]][1] <- invalid
    rejects(data, "identities", missing = "complete-case")
  }
}
extra_group <- independent
extra_group$arm[1] <- "C"
extra_group$measurement[1] <- NA_real_
rejects(extra_group, "outside order", missing = "complete-case")
for (order in list("A", c("A", "B", "C"), c("A", "A"), c("A", ""), "AB", c(1, 2))) {
  rejects(independent, "order", order = order)
}
for (design in list("auto", NULL, TRUE)) rejects(independent, "design", design = design)
for (confidence in list(0, 1, -1, NaN, Inf, TRUE, "0.95")) {
  rejects(independent, "confidence", confidence = confidence)
}
rejects(independent, "missing", missing = "drop")
rejects(independent, "columns", unit = "absent")
rejects(independent, "columns", unit = "arm")
duplicated_columns <- independent
duplicated_columns$extra <- duplicated_columns$id
names(duplicated_columns)[4] <- "id"
rejects(duplicated_columns, "columns")
categories <- independent
categories$arm <- factor(categories$arm, levels = c("B", "A", "unused"))
categories$id <- factor(categories$id)
same(run(categories), reports$independent)
default <- easyplot_analyze_two_groups(independent, group = "arm", value = "measurement", unit = "id",
                                       order = c("A", "B"), design = "independent")
stopifnot(default$effect$confidence == .95)
check_library(default, first, second)

keys <- c("schema_version", "design", "columns", "order", "missing_policy", "n_input", "n_used",
          "n_removed", "n_pairs", "removed_units", "summary", "effect", "test", "warnings", "assumptions")
for (report in reports) {
  stopifnot(setequal(names(report), keys), report$schema_version == "1.0.0",
            identical(report$columns, list(group = "arm", value = "measurement", unit = "id")),
            report$n_input == report$n_used + report$n_removed,
            sum(vapply(report$summary, function(x) x$n, integer(1))) == report$n_used,
            length(report$assumptions) > 0L)
  if (report$design == "paired") stopifnot(report$n_pairs * 2L == report$n_used)
  else stopifnot(is.null(report$n_pairs))
  if (report$n_removed == 0L) stopifnot(identical(report$removed_units, list()), identical(report$warnings, list()))
}
stopifnot(!any(c("ggplot2", "patchwork") %in% loadedNamespaces()))
reports <- c(reports, check_replicates(), check_multiplicity())
if (length(args)) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is needed only for fixture export")
  if (file.exists(args[[1L]])) stop("Refusing to overwrite fixture", call. = FALSE)
  connection <- file(args[[1L]], open = "wx", encoding = "UTF-8")
  tryCatch(jsonlite::write_json(reports, connection, auto_unbox = TRUE, null = "null", digits = 17, pretty = TRUE),
           finally = close(connection))
  cat("R fixture written:", args[[1L]], "\n")
}
cat("EasyPlot analysis R checks passed:", length(reports), "reports; inference, replicates, multiplicity, validation, immutability.\n")
