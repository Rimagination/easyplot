# Explicit unit summaries and inference. Base R/stats; no exports or global options.
# Schema 1.0.0 matches easyplot_analysis.py. Effect = order[2] - order[1].
# Identity columns/order: homogeneous nonblank text/factors or finite numbers.
# n_input/n_used/n_removed count actual rows; n_pairs counts retained pairs or NULL.
# removed_units is a list in first-appearance order. Input data is never modified.
.easyplot_nonblank <- function(x) nzchar(trimws(x, whitespace = "[\\h\\v]"))
.easyplot_text_scalar <- function(x) {
  is.character(x) && length(x) == 1L && is.null(dim(x)) && !is.na(x) && .easyplot_nonblank(x)
}
.easyplot_real_numeric <- function(x) is.numeric(x) && !is.complex(x) && !is.object(x) && is.null(dim(x))
.easyplot_identities <- function(x, name) {
  if (is.factor(x)) x <- as.character(x)
  if ((!is.character(x) && !.easyplot_real_numeric(x)) || !is.null(dim(x)) || anyNA(x) ||
      (is.character(x) && any(!.easyplot_nonblank(x))) ||
      (is.numeric(x) && any(!is.finite(x)))) {
    stop(paste(name, "must contain nonempty text or finite numeric identities"), call. = FALSE)
  }
  unname(x)
}

easyplot_summarize_replicates <- function(data, group, value, unit, replicate, design, missing = "error") {
  fail <- function(message) stop(message, call. = FALSE)
  if (!is.data.frame(data) || nrow(data) == 0L) fail("data must be a nonempty data.frame")
  columns <- list(group, value, unit, replicate)
  if (!all(vapply(columns, .easyplot_text_scalar, logical(1))) ||
      length(unique(unlist(columns))) != 4L || anyDuplicated(names(data)) ||
      !all(unlist(columns) %in% names(data))) {
    fail("group, value, unit and replicate must name distinct, existing, unique columns")
  }
  if (!.easyplot_text_scalar(design) || !design %in% c("independent", "repeated")) {
    fail("design must be 'independent' or 'repeated'")
  }
  if (!.easyplot_text_scalar(missing) || !missing %in% c("error", "available")) {
    fail("missing must be 'error' or 'available'")
  }
  groups <- .easyplot_identities(data[[group]], "group")
  units <- .easyplot_identities(data[[unit]], "unit")
  replicates <- .easyplot_identities(data[[replicate]], "replicate")
  # Integer codes preserve identity without pasted-label collisions or sorting.
  unit_codes <- match(units, unique(units))
  group_codes <- match(groups, unique(groups))
  keys <- data.frame(unit = unit_codes, group = group_codes,
                     replicate = match(replicates, unique(replicates)))
  if (anyDuplicated(keys)) fail("duplicate unit/group/replicate")
  cells <- !duplicated(keys[c("unit", "group")])
  if (design == "independent" && anyDuplicated(unit_codes[cells])) {
    fail("independent design requires each unit in a single group")
  }
  measurements <- data[[value]]
  if (!.easyplot_real_numeric(measurements)) fail("value must be a real numeric column, excluding booleans")
  measurements <- as.numeric(measurements)
  if (any(is.infinite(measurements))) fail("value must not contain infinite measurements")
  n_missing <- sum(is.na(measurements))
  if (n_missing > 0L && missing == "error") fail("missing measurements require missing='available'")
  # Pasting integer codes is unambiguous; split once instead of scanning per cell.
  cell_keys <- paste(unit_codes, group_codes, sep = "/")
  rows <- split(seq_along(measurements), match(cell_keys, unique(cell_keys)))
  summary <- lapply(seq_along(rows), function(i) {
    indices <- rows[[as.character(i)]]
    x <- measurements[indices]
    x <- x[!is.na(x)]
    mean_value <- if (length(x)) mean(x) else NULL
    sd <- if (length(x) > 1L) stats::sd(x) else NULL
    if (any(!is.finite(c(mean_value, sd)))) fail("nonfinite replicate summary; rescale measurements")
    list(unit = units[[indices[[1L]]]], group = groups[[indices[[1L]]]], value = mean_value,
         n_input = length(indices), n_used = length(x), n_missing = length(indices) - length(x), sd = sd)
  })
  warnings <- list("Technical readings must not be counted as independent sample size (n).",
                   "Within-unit SD describes technical dispersion only; biological SE/CI require unit-level inference.")
  if (missing == "available") {
    warnings <- c(warnings, list("Available-readings summaries may introduce selection bias when readings are missing."))
  }
  if (any(vapply(summary, function(x) x$n_used == 0L, logical(1)))) {
    warnings <- c(warnings, list("All-missing unit/condition rows are retained with null value and SD; absent conditions are not imputed."))
  }
  list(schema_version = "1.0.0", design = design,
       columns = list(group = group, value = value, unit = unit, replicate = replicate),
       estimator = "arithmetic mean within unit/condition", missing_policy = missing,
       n_input = nrow(data), n_used = nrow(data) - n_missing, n_missing = n_missing,
       n_units = length(unique(units)), n_unit_conditions = length(summary), summary = summary,
       warnings = warnings, assumptions = list(
         "Readings within each unit/condition are comparable technical repetitions.",
         "Unit/condition keys capture all relevant design dimensions; no time, dose, or other dimension is ignored.",
         "The estimand is the arithmetic mean within each unit/condition; downstream unit means receive equal weight regardless of the number of readings.",
         "Design and replicate roles are declared by the caller; hierarchical or mixed-model estimands require separate validation."))
}

easyplot_adjust_pvalues <- function(pvalues, labels, method, family, alpha = .05) {
  fail <- function(message) stop(message, call. = FALSE)
  if (!.easyplot_text_scalar(method) || !method %in% c("holm", "bonferroni", "BH", "BY")) {
    fail("method must be 'holm', 'bonferroni', 'BH' or 'BY'")
  }
  if (!.easyplot_text_scalar(family)) fail("family must be a nonempty description of the comparison family")
  if (!.easyplot_real_numeric(alpha) || length(alpha) != 1L || !is.finite(alpha) || alpha <= 0 || alpha >= 1) {
    fail("alpha must be a finite number strictly between 0 and 1")
  }
  if (!.easyplot_real_numeric(pvalues) || !length(pvalues) || any(!is.finite(pvalues)) ||
      any(pvalues < 0 | pvalues > 1)) {
    fail("pvalues must be a nonempty one-dimensional sequence of finite real numbers in [0, 1], without missing values")
  }
  if (!is.character(labels) || !is.null(dim(labels)) || length(labels) != length(pvalues) ||
      anyNA(labels) || any(!.easyplot_nonblank(labels)) || anyDuplicated(labels)) {
    fail("labels must be unique nonempty strings matching pvalues")
  }
  adjusted <- stats::p.adjust(pvalues, method = method)
  dependence <- if (method %in% c("holm", "bonferroni")) {
    "FWER control is valid under arbitrary dependence among comparisons."
  } else if (method == "BH") {
    "BH controls FDR under independence or positive regression dependence on a subset (PRDS) of the true null hypotheses."
  } else {
    "BY controls FDR under arbitrary dependence among comparisons."
  }
  list(schema_version = "1.0.0", family = family, method = method,
       error_control = if (method %in% c("holm", "bonferroni")) "FWER" else "FDR",
       alpha = unname(alpha), m = length(pvalues),
       results = lapply(seq_along(pvalues), function(i) {
         list(comparison = unname(labels[[i]]), p_raw = unname(pvalues[[i]]),
              p_adjusted = unname(adjusted[[i]]), reject = unname(adjusted[[i]] <= alpha))
       }), assumptions = list("All supplied raw p-values are valid for their null hypotheses.",
                              "The comparison family was specified by the caller; no failed or missing p-values were removed.",
                              dependence))
}

easyplot_analyze_two_groups <- function(data, group, value, unit, order, design,
                                        missing = "error", confidence = .95) {
  fail <- function(message) stop(message, call. = FALSE)
  text_scalar <- .easyplot_text_scalar
  real_numeric <- .easyplot_real_numeric
  identities <- .easyplot_identities
  if (!is.data.frame(data) || nrow(data) == 0L) fail("data must be a nonempty data.frame")
  columns <- list(group, value, unit)
  if (!all(vapply(columns, text_scalar, logical(1))) ||
      length(unique(unlist(columns))) != 3L || anyDuplicated(names(data)) ||
      !all(unlist(columns) %in% names(data))) {
    fail("group, value and unit must name distinct, existing, unique columns")
  }
  if (!text_scalar(design) || !design %in% c("independent", "paired")) {
    fail("design must be 'independent' or 'paired'")
  }
  if (!text_scalar(missing) || !missing %in% c("error", "complete-case")) {
    fail("missing must be 'error' or 'complete-case'")
  }
  if (!real_numeric(confidence) || length(confidence) != 1L ||
      !is.finite(confidence) || confidence <= 0 || confidence >= 1) {
    fail("confidence must be a finite number strictly between 0 and 1")
  }
  if (length(order) != 2L) fail("order must contain exactly two distinct groups")
  order <- identities(order, "order")
  groups <- identities(data[[group]], "group")
  units <- identities(data[[unit]], "unit")
  if (anyDuplicated(order) || is.character(order) != is.character(groups)) {
    fail("order must contain two distinct groups of the group column's type")
  }
  if (!all(groups %in% order)) fail("data contains a group outside order")
  # Validate identities before complete-case exclusion can hide duplicates.
  if (design == "independent" && anyDuplicated(units)) fail("duplicate unit")
  if (design == "paired" && anyDuplicated(data.frame(unit = units, group = groups))) {
    fail("duplicate unit/group")
  }
  measurements <- data[[value]]
  if (!real_numeric(measurements)) fail("value must be a real numeric column, excluding booleans")
  measurements <- as.numeric(measurements)
  if (any(is.infinite(measurements))) fail("value must not contain infinite measurements")
  n_input <- nrow(data)
  if (design == "independent") {
    absent <- is.na(measurements)
    if (any(absent) && missing == "error") fail("missing measurements require missing='complete-case'")
    removed_units <- as.list(units[absent])
    samples <- lapply(order, function(label) measurements[!absent & groups == label])
    n_used <- sum(!absent)
    n_pairs <- NULL
  } else {
    ids <- unique(units)
    samples <- lapply(order, function(label) {
      rows <- which(groups == label)
      measurements[rows[match(ids, units[rows])]]
    })
    absent <- is.na(samples[[1L]]) | is.na(samples[[2L]])
    if (any(absent) && missing == "error") {
      fail("missing or absent pair members require missing='complete-case'")
    }
    removed_units <- as.list(ids[absent])
    samples <- lapply(samples, function(x) x[!absent])
    n_pairs <- sum(!absent)
    n_used <- 2L * n_pairs
  }
  if (any(lengths(samples) < 2L)) {
    fail("at least two observations per group or two complete pairs are required")
  }
  first <- samples[[1L]]
  second <- samples[[2L]]
  summary <- lapply(seq_along(order), function(i) {
    x <- samples[[i]]
    list(group = order[[i]], n = length(x), mean = mean(x), sd = stats::sd(x),
         se = stats::sd(x) / sqrt(length(x)))
  })
  variance_samples <- if (design == "independent") samples else list(second - first)
  variances <- vapply(variance_samples, stats::var, numeric(1))
  if (any(!is.finite(variances) | variances <= 0)) {
    fail("positive finite sample variance is required (paired: differences)")
  }
  if (any(!is.finite(unlist(lapply(summary, function(x) x[c("mean", "sd", "se")]))))) {
    fail("nonfinite sample summary; rescale measurements")
  }
  result <- stats::t.test(second, first, paired = design == "paired", var.equal = FALSE,
                          alternative = "two.sided", conf.level = confidence)
  estimate <- if (design == "paired") mean(second - first) else mean(second) - mean(first)
  if (any(!is.finite(c(estimate, result$conf.int, result$statistic, result$parameter, result$p.value)))) {
    fail("nonfinite inference result; check variance and measurement scale")
  }
  n_removed <- n_input - n_used
  warnings <- if (n_removed > 0L) list("Complete-case exclusions may introduce selection bias.") else list()
  assumptions <- if (design == "independent") {
    list("Units are independent within and between groups.",
         "Within-group observations are approximately normal, or sample sizes justify the t approximation.",
         "Equal population variances are not required.")
  } else {
    list("Pairs are matched by unit ID; different units are independent.",
         "Within-unit differences are approximately normal, or the number of pairs justifies the t approximation.")
  }
  assumptions <- c(assumptions, list("Design and distributional assumptions are supplied by the caller, not inferred from data."))
  list(
    schema_version = "1.0.0", design = design,
    columns = list(group = group, value = value, unit = unit), order = as.list(order),
    missing_policy = missing, n_input = n_input, n_used = n_used, n_removed = n_removed,
    n_pairs = n_pairs, removed_units = removed_units, summary = summary,
    effect = list(label = "mean difference (second - first)", estimate = estimate,
                  ci_low = unname(result$conf.int[1L]), ci_high = unname(result$conf.int[2L]),
                  confidence = unname(confidence)),
    test = list(method = if (design == "independent") "Welch Two Sample t-test" else "Paired t-test",
                statistic = unname(result$statistic), df = unname(result$parameter),
                p_value = result$p.value, alternative = "two-sided"),
    warnings = warnings, assumptions = assumptions
  )
}
