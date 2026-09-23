"""Explicit unit summaries and inference: pandas/NumPy/SciPy, no file writes."""

from numbers import Real

import numpy as np
import pandas as pd
from scipy import stats


def _identities(values, name):
    """Keep homogeneous text/numeric identities without string coercion."""
    values = [x.item() if isinstance(x, np.generic) else x for x in values]
    kinds = set()
    for x in values:
        if isinstance(x, str) and x.strip():
            kinds.add("text")
        elif (isinstance(x, Real) and not isinstance(x, bool)
              and (isinstance(x, int) or np.isfinite(x))):
            kinds.add("numeric")
        else:
            raise ValueError(f"{name} must contain nonempty text or finite numeric identities")
    if len(kinds) != 1:
        raise ValueError(f"{name} must contain one identity type (text or numeric)")
    return values, kinds.pop()


def summarize_replicates(data, *, group, value, unit, replicate, design, missing="error"):
    """Average comparable technical readings per unit/condition, in first-seen order.

    Design is declared as independent or repeated. Identity checks precede
    exclusions. Available readings retain all-missing cells as None and never
    create absent conditions. SD is within-cell sample dispersion, not SE/CI.
    Downstream unit means have equal weight regardless of technical counts.
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("data must be a nonempty DataFrame")
    columns = [group, value, unit, replicate]
    if (any(not isinstance(x, str) or not x.strip() for x in columns)
            or len(set(columns)) != 4 or not data.columns.is_unique
            or any(x not in data.columns for x in columns)):
        raise ValueError("group, value, unit and replicate must name distinct, existing, unique columns")
    if not isinstance(design, str) or design not in ("independent", "repeated"):
        raise ValueError("design must be 'independent' or 'repeated'")
    if not isinstance(missing, str) or missing not in ("error", "available"):
        raise ValueError("missing must be 'error' or 'available'")
    groups, _ = _identities(data[group], "group")
    units, _ = _identities(data[unit], "unit")
    replicates, _ = _identities(data[replicate], "replicate")
    # Native tuple keys avoid pandas' lossy inference for mixed large ints/floats.
    seen, cells, unit_groups = set(), {}, {}
    for i, (u, g, r) in enumerate(zip(units, groups, replicates)):
        key = (u, g, r)
        if key in seen:
            raise ValueError("duplicate unit/group/replicate")
        seen.add(key)
        if design == "independent" and u in unit_groups and unit_groups[u] != g:
            raise ValueError("independent design requires each unit in a single group")
        unit_groups[u] = g
        cells.setdefault((u, g), []).append(i)
    dtype = data[value].dtype
    if (not pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype)
            or pd.api.types.is_complex_dtype(dtype)):
        raise ValueError("value must be a real numeric column, excluding booleans")
    measurements = data[value].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(measurements).any():
        raise ValueError("value must not contain infinite measurements")
    n_missing = int(np.isnan(measurements).sum())
    if n_missing and missing == "error":
        raise ValueError("missing measurements require missing='available'")
    summary = []
    for (u, g), rows in cells.items():
        sample = measurements[rows]
        sample = sample[~np.isnan(sample)]
        with np.errstate(over="ignore", invalid="ignore"):
            mean = float(np.mean(sample)) if len(sample) else None
            sd = float(np.std(sample, ddof=1)) if len(sample) > 1 else None
        if any(x is not None and not np.isfinite(x) for x in (mean, sd)):
            raise ValueError("nonfinite replicate summary; rescale measurements")
        summary.append(dict(unit=u, group=g, value=mean, n_input=len(rows),
                            n_used=len(sample), n_missing=len(rows) - len(sample), sd=sd))
    warnings = ["Technical readings must not be counted as independent sample size (n).",
                "Within-unit SD describes technical dispersion only; biological SE/CI require unit-level inference."]
    if missing == "available":
        warnings.append("Available-readings summaries may introduce selection bias when readings are missing.")
    if any(s["n_used"] == 0 for s in summary):
        warnings.append("All-missing unit/condition rows are retained with null value and SD; absent conditions are not imputed.")
    return {
        "schema_version": "1.0.0", "design": design,
        "columns": dict(group=group, value=value, unit=unit, replicate=replicate),
        "estimator": "arithmetic mean within unit/condition", "missing_policy": missing,
        "n_input": len(data), "n_used": len(data) - n_missing, "n_missing": n_missing,
        "n_units": len(unit_groups), "n_unit_conditions": len(summary), "summary": summary,
        "warnings": warnings,
        "assumptions": [
            "Readings within each unit/condition are comparable technical repetitions.",
            "Unit/condition keys capture all relevant design dimensions; no time, dose, or other dimension is ignored.",
            "The estimand is the arithmetic mean within each unit/condition; downstream unit means receive equal weight regardless of the number of readings.",
            "Design and replicate roles are declared by the caller; hierarchical or mixed-model estimands require separate validation.",
        ],
    }


def adjust_pvalues(pvalues, *, labels, method, family, alpha=.05):
    """Adjust one explicit, complete comparison family; preserve input order."""
    if not isinstance(method, str) or method not in ("holm", "bonferroni", "BH", "BY"):
        raise ValueError("method must be 'holm', 'bonferroni', 'BH' or 'BY'")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a nonempty description of the comparison family")
    if (isinstance(alpha, (bool, np.bool_)) or not isinstance(alpha, Real)
            or not 0 < alpha < 1 or not np.isfinite(alpha)):
        raise ValueError("alpha must be a finite number strictly between 0 and 1")
    sequences = (list, tuple, np.ndarray, pd.Series, pd.Index)
    if (not isinstance(pvalues, sequences) or isinstance(pvalues, np.ma.MaskedArray)
            or getattr(pvalues, "ndim", 1) != 1 or not len(pvalues)):
        raise ValueError("pvalues must be a nonempty one-dimensional sequence")
    raw = list(pvalues)
    if any(isinstance(x, (bool, np.bool_)) or not isinstance(x, Real)
           or not 0 <= x <= 1 or not np.isfinite(x) for x in raw):
        raise ValueError("pvalues must contain finite real numbers in [0, 1], without missing values")
    if (not isinstance(labels, sequences) or isinstance(labels, np.ma.MaskedArray)
            or getattr(labels, "ndim", 1) != 1 or len(labels) != len(raw)):
        raise ValueError("labels must be a one-dimensional sequence matching pvalues")
    labels = list(labels)
    if (any(not isinstance(x, str) or not x.strip() for x in labels)
            or len(set(labels)) != len(labels)):
        raise ValueError("labels must be unique nonempty strings")
    ps = np.array(raw, dtype=float)
    m = len(ps)
    if method == "bonferroni":
        adjusted = np.minimum(1., ps * m)
    elif method == "holm":
        order = np.argsort(ps, kind="stable")
        adjusted = np.empty(m)
        adjusted[order] = np.minimum(1., np.maximum.accumulate(ps[order] * np.arange(m, 0, -1)))
    else:
        adjusted = stats.false_discovery_control(ps, method=method.lower())
    dependence = ("FWER control is valid under arbitrary dependence among comparisons."
                  if method in ("holm", "bonferroni") else
                  "BH controls FDR under independence or positive regression dependence on a subset (PRDS) of the true null hypotheses."
                  if method == "BH" else
                  "BY controls FDR under arbitrary dependence among comparisons.")
    return {
        "schema_version": "1.0.0", "family": family, "method": method,
        "error_control": "FWER" if method in ("holm", "bonferroni") else "FDR",
        "alpha": float(alpha), "m": m,
        "results": [dict(comparison=label, p_raw=float(p), p_adjusted=float(q), reject=bool(q <= alpha))
                    for label, p, q in zip(labels, ps, adjusted)],
        "assumptions": ["All supplied raw p-values are valid for their null hypotheses.",
                        "The comparison family was specified by the caller; no failed or missing p-values were removed.",
                        dependence],
    }


def analyze_two_groups(data, *, group, value, unit, order, design,
                       missing="error", confidence=.95):
    """Return schema 1.0.0; effect direction is always order[1] - order[0].

    `data` is an unchanged DataFrame; column names must be distinct strings.
    Group/order and unit identities are homogeneous nonblank text or finite
    real numbers (factors/categoricals are accepted). Values must have a real
    numeric dtype, excluding booleans. No string-to-number coercion is done.

    Independent samples require globally unique units, n >= 2 and positive
    sample variance per group. Paired samples require unique unit/group rows,
    >= 2 complete ID-matched pairs and positive variance of their differences.
    Complete-case deletion is opt-in. n_input/n_used/n_removed count actual
    rows; n_pairs counts retained pairs (None for independent). removed_units
    lists excluded identities once, in first-appearance order. Warnings are
    returned as text, not emitted. No input files or global state are changed.
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("data must be a nonempty DataFrame")
    columns = [group, value, unit]
    if (any(not isinstance(x, str) or not x.strip() for x in columns)
            or len(set(columns)) != 3 or not data.columns.is_unique
            or any(x not in data.columns for x in columns)):
        raise ValueError("group, value and unit must name distinct, existing, unique columns")
    if not isinstance(design, str) or design not in ("independent", "paired"):
        raise ValueError("design must be 'independent' or 'paired'")
    if not isinstance(missing, str) or missing not in ("error", "complete-case"):
        raise ValueError("missing must be 'error' or 'complete-case'")
    if (isinstance(confidence, (bool, np.bool_)) or not isinstance(confidence, Real)
            or not np.isfinite(confidence) or not 0 < confidence < 1):
        raise ValueError("confidence must be a finite number strictly between 0 and 1")
    if isinstance(order, (str, bytes, dict, set, frozenset)):
        raise ValueError("order must be an ordered sequence of exactly two distinct groups")
    try:
        order = list(order)
    except TypeError as exc:
        raise ValueError("order must contain exactly two distinct groups") from exc
    if len(order) != 2:
        raise ValueError("order must contain exactly two distinct groups")
    order, order_kind = _identities(order, "order")
    groups, group_kind = _identities(data[group], "group")
    units, _ = _identities(data[unit], "unit")
    if order[0] == order[1] or order_kind != group_kind:
        raise ValueError("order must contain two distinct groups of the group column's type")
    # Encode identities before pandas can infer a lossy float dtype. Python
    # dict equality preserves distinct large-int/float labels through pivoting.
    unit_labels = list(dict.fromkeys(units))
    unit_codes = {label: i for i, label in enumerate(unit_labels)}
    group_codes = {label: i for i, label in enumerate(order)}
    if any(label not in group_codes for label in groups):
        raise ValueError("data contains a group outside order")
    work = pd.DataFrame({"unit": [unit_codes[label] for label in units],
                         "group": [group_codes[label] for label in groups]})
    # Identity checks precede every exclusion, including missing measurements.
    keys = ["unit"] if design == "independent" else ["unit", "group"]
    if work.duplicated(keys).any():
        raise ValueError("duplicate unit" if design == "independent" else "duplicate unit/group")
    dtype = data[value].dtype
    if (not pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype)
            or pd.api.types.is_complex_dtype(dtype)):
        raise ValueError("value must be a real numeric column, excluding booleans")
    measurements = data[value].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(measurements).any():
        raise ValueError("value must not contain infinite measurements")
    work["value"] = measurements
    n_input = len(work)
    if design == "independent":
        absent = work["value"].isna()
        if absent.any() and missing == "error":
            raise ValueError("missing measurements require missing='complete-case'")
        removed_units = [unit_labels[i] for i in work.loc[absent, "unit"]]
        used = work.loc[~absent]
        samples = [used.loc[used["group"] == i, "value"].to_numpy() for i in range(2)]
        n_used, n_pairs = len(used), None
    else:
        wide = work.pivot(index="unit", columns="group", values="value").reindex(
            index=work["unit"].drop_duplicates(), columns=range(2))
        absent = wide.isna().any(axis=1)
        if absent.any() and missing == "error":
            raise ValueError("missing or absent pair members require missing='complete-case'")
        removed_units = [unit_labels[i] for i in wide.index[absent]]
        used = wide.loc[~absent]
        samples = [used[i].to_numpy() for i in range(2)]
        n_pairs = len(used)
        n_used = 2 * n_pairs
    if any(len(sample) < 2 for sample in samples):
        raise ValueError("at least two observations per group or two complete pairs are required")

    first, second = samples
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        summary = [{"group": label, "n": len(sample), "mean": float(np.mean(sample)),
                    "sd": float(np.std(sample, ddof=1)),
                    "se": float(stats.sem(sample))}
                   for label, sample in zip(order, samples)]
        variance_samples = samples if design == "independent" else [second - first]
        variances = [np.var(sample, ddof=1) for sample in variance_samples]
        if any(not np.isfinite(x) or x <= 0 for x in variances):
            raise ValueError("positive finite sample variance is required (paired: differences)")
        if any(not np.isfinite(s[key]) for s in summary for key in ("mean", "sd", "se")):
            raise ValueError("nonfinite sample summary; rescale measurements")
        # Match R t.test's numerical admissibility guard; inference stays in SciPy.
        precision_se = (np.hypot(summary[0]["se"], summary[1]["se"])
                        if design == "independent" else stats.sem(second - first))
        precision_scale = (max(abs(s["mean"]) for s in summary) if design == "independent"
                           else abs(np.mean(second - first)))
        if precision_se < 10 * np.finfo(float).eps * precision_scale:
            raise ValueError("data are essentially constant")
        if design == "independent":
            result = stats.ttest_ind(second, first, equal_var=False, alternative="two-sided")
            estimate = float(np.mean(second) - np.mean(first))
        else:
            result = stats.ttest_rel(second, first, alternative="two-sided")
            estimate = float(np.mean(second - first))
        ci = result.confidence_interval(confidence_level=float(confidence))
    if not np.isfinite([estimate, ci.low, ci.high, result.statistic, result.df, result.pvalue]).all():
        raise ValueError("nonfinite inference result; check variance and measurement scale")

    n_removed = n_input - n_used
    warnings = (["Complete-case exclusions may introduce selection bias."] if n_removed else [])
    assumptions = (["Units are independent within and between groups.",
                    "Within-group observations are approximately normal, or sample sizes justify the t approximation.",
                    "Equal population variances are not required."] if design == "independent" else
                   ["Pairs are matched by unit ID; different units are independent.",
                    "Within-unit differences are approximately normal, or the number of pairs justifies the t approximation."])
    assumptions.append("Design and distributional assumptions are supplied by the caller, not inferred from data.")
    return {
        "schema_version": "1.0.0", "design": design,
        "columns": {"group": group, "value": value, "unit": unit}, "order": order,
        "missing_policy": missing, "n_input": n_input, "n_used": n_used,
        "n_removed": n_removed, "n_pairs": n_pairs, "removed_units": removed_units,
        "summary": summary,
        "effect": {"label": "mean difference (second - first)", "estimate": estimate,
                   "ci_low": float(ci.low), "ci_high": float(ci.high), "confidence": float(confidence)},
        "test": {"method": "Welch Two Sample t-test" if design == "independent" else "Paired t-test",
                 "statistic": float(result.statistic), "df": float(result.df),
                 "p_value": float(result.pvalue), "alternative": "two-sided"},
        "warnings": warnings, "assumptions": assumptions,
    }
