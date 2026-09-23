"""One executable suite; optional --r-fixture checks every R report field."""

import argparse
import json
from numbers import Real
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats

import easyplot_analysis as analysis
from easyplot_analysis import analyze_two_groups


def run(data, **options):
    args = dict(group="arm", value="measurement", unit="id", order=["A", "B"],
                design="independent", confidence=.90)
    args.update(options)
    before = data.copy(deep=True) if isinstance(data, pd.DataFrame) else None
    try:
        return analyze_two_groups(data, **args)
    finally:
        if before is not None:
            pd.testing.assert_frame_equal(data, before)


def rejects(data, message, **options):
    try:
        run(data, **options)
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection: {message}")


def same(actual, expected):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            same(actual[key], expected[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for left, right in zip(actual, expected):
            same(left, right)
    elif isinstance(expected, bool):
        assert type(actual) is bool and actual == expected
    elif isinstance(expected, int):
        assert isinstance(actual, Real) and not isinstance(actual, bool) and actual == expected
    elif isinstance(expected, Real):
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    else:
        assert actual == expected, (actual, expected)


def check_library(report, first, second):
    paired = report["design"] == "paired"
    expected = (stats.ttest_rel(second, first, alternative="two-sided") if paired else
                stats.ttest_ind(second, first, equal_var=False, alternative="two-sided"))
    ci = expected.confidence_interval(confidence_level=report["effect"]["confidence"])
    same(report["test"], dict(method="Paired t-test" if paired else "Welch Two Sample t-test",
                              statistic=expected.statistic, df=expected.df,
                              p_value=expected.pvalue, alternative="two-sided"))
    same(report["effect"], dict(label="mean difference (second - first)",
                                estimate=float(np.mean(second - first) if paired else
                                               np.mean(second) - np.mean(first)),
                                ci_low=ci.low, ci_high=ci.high,
                                confidence=report["effect"]["confidence"]))
    for label, sample, summary in zip(report["order"], (first, second), report["summary"]):
        same(summary, dict(group=label, n=len(sample), mean=float(np.mean(sample)),
                           sd=float(np.std(sample, ddof=1)), se=float(stats.sem(sample))))


def check_numeric_identity_precision():
    # These identities differ in Python but collapse if inferred as float64.
    large, rounded = 2**53 + 1, float(2**53)
    assert large != rounded
    data = pd.DataFrame({
        "id": [f"u{i}" for i in range(6)],
        "arm": pd.Series([large] * 3 + [rounded] * 3, dtype=object),
        "measurement": [1., 2., 4., 10., 12., 14.],
    })
    report = run(data, order=[large, rounded])
    assert [s["n"] for s in report["summary"]] == [3, 3]
    assert report["order"] == [large, rounded]
    check_library(report, np.array([1., 2., 4.]), np.array([10., 12., 14.]))
    rejects(data, "outside order", order=[float(large), rounded + 2.])

    paired = pd.DataFrame({
        "id": pd.Series([large, rounded, 1, 1, 2, 2], dtype=object),
        "arm": ["A", "B", "A", "B", "A", "B"],
        "measurement": [0., 100., 1., 2., 2., 4.],
    })
    rejects(paired, "absent", design="paired")
    report = run(paired, design="paired", missing="complete-case")
    assert report["n_pairs"] == 2 and report["n_used"] == 4 and report["n_removed"] == 2
    assert report["removed_units"] == [large, rounded]
    check_library(report, np.array([1., 2.]), np.array([2., 4.]))

    # Complete pairs also retain both the unit and group identities exactly.
    paired["id"] = pd.Series([large, large, rounded, rounded, 1, 1], dtype=object)
    paired["arm"] = pd.Series([large, rounded] * 3, dtype=object)
    report = run(paired, design="paired", order=[large, rounded])
    assert report["n_pairs"] == 3 and report["n_removed"] == 0
    check_library(report, np.array([0., 1., 2.]), np.array([100., 2., 4.]))


def expect_error(call, message):
    try:
        call()
    except (ValueError, TypeError) as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection: {message}")


def summarize(data, **options):
    args = dict(group="arm", value="measurement", unit="id", replicate="reading", design="independent")
    args.update(options)
    before = data.copy(deep=True) if isinstance(data, pd.DataFrame) else None
    try:
        return analysis.summarize_replicates(data, **args)
    finally:
        if before is not None:
            pd.testing.assert_frame_equal(data, before)


def summary_table(report):
    return pd.DataFrame([dict(id=s["unit"], arm=s["group"], measurement=s["value"])
                         for s in report["summary"]])


def check_replicates():
    data = pd.DataFrame({"id": ["u1", "u1", "u2", "u3", "u4"],
                         "arm": ["A", "A", "A", "B", "B"],
                         "reading": [1, 2, 1, 1, 1],
                         "measurement": [1., 3., 10., 4., 8.]})
    report = summarize(data)
    same(report["summary"], [
        dict(unit="u1", group="A", value=2., n_input=2, n_used=2, n_missing=0, sd=np.sqrt(2)),
        dict(unit="u2", group="A", value=10., n_input=1, n_used=1, n_missing=0, sd=None),
        dict(unit="u3", group="B", value=4., n_input=1, n_used=1, n_missing=0, sd=None),
        dict(unit="u4", group="B", value=8., n_input=1, n_used=1, n_missing=0, sd=None),
    ])
    reports = {"replicates_independent": report}
    # Two unit means get equal weight despite different numbers of readings.
    downstream = run(summary_table(report))
    assert downstream["summary"][0]["mean"] == 6.
    assert downstream["summary"][0]["n"] == 2
    assert np.mean(data.loc[data.arm == "A", "measurement"]) != 6.
    reports["replicates_equal_weight"] = downstream

    repeated = pd.DataFrame({
        "id": ["u2", "u1", "u1", "u2", "u1", "u3", "u3", "u4", "u4", "u5"],
        "arm": ["B", "A", "A", "A", "B", "A", "B", "A", "B", "A"],
        "reading": [1, 1, 2, 1, 1, 1, 1, 1, 2, 1],
        "measurement": [8., 1., 3., 3., 3., 5., np.nan, np.nan, np.nan, 9.],
    })
    expect_error(lambda: summarize(repeated, design="repeated"), "missing")
    available = summarize(repeated, design="repeated", missing="available")
    reports["replicates_available"] = available
    assert (available["n_input"], available["n_used"], available["n_missing"],
            available["n_units"], available["n_unit_conditions"]) == (10, 7, 3, 5, 9)
    assert [(s["unit"], s["group"]) for s in available["summary"]] == [
        ("u2", "B"), ("u1", "A"), ("u2", "A"), ("u1", "B"), ("u3", "A"),
        ("u3", "B"), ("u4", "A"), ("u4", "B"), ("u5", "A")]
    assert sum(s["value"] is None for s in available["summary"]) == 3
    assert any("selection bias" in w for w in available["warnings"])
    assert any("All-missing" in w for w in available["warnings"])
    # Missing cells survive aggregation; absent u5/B is never fabricated.
    table = summary_table(available)
    rejects(table, "missing", design="paired")
    paired = run(table, design="paired", missing="complete-case")
    reports["replicates_paired_complete_case"] = paired
    assert (paired["n_input"], paired["n_used"], paired["n_removed"], paired["n_pairs"]) == (9, 4, 5, 2)
    assert paired["removed_units"] == ["u3", "u4", "u5"]
    check_library(paired, np.array([3., 2.]), np.array([8., 3.]))
    shuffled = repeated.iloc[[7, 2, 8, 4, 0, 9, 1, 5, 3, 6]].copy()
    shuffled.index = [5] * len(shuffled)
    shuffled_report = summarize(shuffled, design="repeated", missing="available")
    reports["replicates_shuffled"] = shuffled_report
    expected_cells = {(s["unit"], s["group"]): s for s in available["summary"]}
    first_seen = list(dict.fromkeys(zip(shuffled.id, shuffled.arm)))
    same(shuffled_report["summary"], [expected_cells[key] for key in first_seen])
    same(summarize(repeated.assign(measurement=repeated.measurement.astype("Float64")),
                   design="repeated", missing="available"), available)
    reports["replicates_numeric"] = summarize(data.assign(
        id=[11, 11, 12, 21, 22], arm=[2, 2, 2, 1, 1], reading=[.5, 1.5, .5, .5, .5]))
    categories = data.copy()
    for column in ("id", "arm", "reading"):
        categories[column] = pd.Categorical(data[column])
    same(summarize(categories), report)
    reports["replicates_all_missing"] = summarize(data.assign(measurement=np.nan), missing="available")
    reports["replicates_partial"] = summarize(data.assign(measurement=[1., np.nan, 10., 4., 8.]),
                                               missing="available")
    same(reports["replicates_partial"]["summary"][0],
         dict(unit="u1", group="A", value=1., n_input=2, n_used=1, n_missing=1, sd=None))
    reports["replicates_single"] = summarize(data.iloc[:1])
    reports["replicates_repeated_complete"] = summarize(repeated.iloc[:5], design="repeated")
    reports["replicates_zero"] = summarize(data.assign(measurement=0.))
    assert reports["replicates_zero"]["summary"][0]["sd"] == 0.

    def invalid(frame, message, **options):
        expect_error(lambda: summarize(frame, **options), message)

    duplicate = pd.concat([data, data.iloc[[0]].assign(measurement=np.nan)])
    invalid(duplicate, "duplicate unit/group/replicate", missing="available")
    invalid(repeated, "single group", missing="available")
    cross = pd.concat([data, data.iloc[[0]].assign(arm="B", measurement=np.nan)])
    invalid(cross, "single group", missing="available")
    invalid(data.iloc[:0], "nonempty")
    invalid(data.to_dict(), "DataFrame")
    for options in (dict(replicate="id"), dict(group="measurement"), dict(unit="absent"), dict(value=" ")):
        invalid(data, "columns", **options)
    invalid(pd.concat([data, data[["id"]]], axis=1), "columns")
    for design in (None, True, "paired", "auto", ["repeated"]):
        invalid(data, "design", design=design)
    expect_error(lambda: analysis.summarize_replicates(
        data, group="arm", value="measurement", unit="id", replicate="reading"), "design")
    for policy in (None, True, "complete-case", "drop"):
        invalid(data, "missing", missing=policy)
    for values in ([True] * 5, data.measurement.astype(str), data.measurement.astype(complex),
                   data.measurement.astype(object), [True, 3., 10., 4., 8.]):
        invalid(data.assign(measurement=values), "real numeric")
    for number in (np.inf, -np.inf):
        invalid(data.assign(measurement=[number, 3., 10., 4., 8.]), "infinite", missing="available")
    invalid(data.assign(measurement=[1.7e308, -1.7e308, 10., 4., 8.]), "nonfinite replicate")
    for column in ("id", "arm", "reading"):
        for identity in ("", " \t", "\u3000", None, np.nan, np.inf, True, 1+0j):
            bad = data.copy()
            bad[column] = bad[column].astype(object)
            bad.loc[0, column] = identity
            bad.loc[0, "measurement"] = np.nan
            invalid(bad, "identit", missing="available")
        bad = data.copy()
        bad[column] = pd.Series([1, "two", 3, 4, 5], dtype=object)
        invalid(bad, "one identity type")
    # Exercise every identity column before pandas could infer a lossy dtype.
    for large, rounded in ((2**53 + 1, float(2**53)), (10**80 + 1, 1e80)):
        assert large != rounded
        for column in ("id", "arm", "reading"):
            precise = pd.DataFrame(dict(id=["u", "u"], arm=["A", "A"], reading=[1, 1], measurement=[1., 3.]))
            precise[column] = pd.Series([large, rounded], dtype=object)
            result = summarize(precise, design="repeated")
            assert result["n_unit_conditions"] == (1 if column == "reading" else 2)
            assert result["n_units"] == (2 if column == "id" else 1)
            if column != "reading":
                key = "unit" if column == "id" else "group"
                assert [s[key] for s in result["summary"]] == [large, rounded]
            else:
                assert result["summary"][0]["value"] == 2.
            json.dumps(result, allow_nan=False)
    keys = {"schema_version", "design", "columns", "estimator", "missing_policy", "n_input",
            "n_used", "n_missing", "n_units", "n_unit_conditions", "summary", "warnings", "assumptions"}
    for result in reports.values():
        if "estimator" not in result:
            continue
        assert result.keys() == keys and result["schema_version"] == "1.0.0"
        assert result["estimator"] == "arithmetic mean within unit/condition"
        assert result["columns"] == dict(group="arm", value="measurement", unit="id", replicate="reading")
        assert result["n_input"] == result["n_used"] + result["n_missing"]
        assert result["n_units"] == len({s["unit"] for s in result["summary"]})
        assert result["n_unit_conditions"] == len(result["summary"])
        for field in ("n_input", "n_used", "n_missing"):
            assert result[field] == sum(s[field] for s in result["summary"])
        for cell in result["summary"]:
            assert cell.keys() == {"unit", "group", "value", "n_input", "n_used", "n_missing", "sd"}
            assert (cell["value"] is None) == (cell["n_used"] == 0)
            assert (cell["sd"] is None) == (cell["n_used"] < 2)
        assert any("independent sample size" in w for w in result["warnings"])
        assert result["assumptions"]
        json.dumps(result, allow_nan=False)
    return reports


def check_multiplicity():
    pvalues = [.2, .01, .04]
    expected = {"holm": [.2, .03, .08], "bonferroni": [.6, .03, .12],
                "BH": [.2, .03, .06], "BY": [11/30, .055, .11]}
    reports = {}
    for method, adjusted in expected.items():
        report = analysis.adjust_pvalues(pvalues, labels=["c3", "c1", "c2"],
                                         method=method, family="Prespecified contrasts")
        same(report["results"], [dict(comparison=label, p_raw=p, p_adjusted=q, reject=q <= .05)
                                 for label, p, q in zip(["c3", "c1", "c2"], pvalues, adjusted)])
        reports[f"adjust_{method}"] = report
        permutation = [2, 0, 1]
        reordered = analysis.adjust_pvalues([pvalues[i] for i in permutation],
            labels=[["c3", "c1", "c2"][i] for i in permutation], method=method, family=report["family"])
        same(reordered["results"], [report["results"][i] for i in permutation])
        for name, values, alpha in (
                ("ties", [1., .04, .04, 0., .9, .001], .05),
                ("single", [.05], .05), ("threshold", [.025, .2], .05),
                ("alpha_small", [0., 1.], np.nextafter(0., 1.)),
                ("alpha_large", [0., 1.], 1. - np.finfo(float).eps)):
            result = analysis.adjust_pvalues(values, labels=[f"c{i}" for i in range(len(values))],
                                             method=method, family="Prespecified contrasts", alpha=alpha)
            reports[f"adjust_{method}_{name}"] = result
            if name == "single":
                assert result["results"][0] == dict(comparison="c0", p_raw=.05, p_adjusted=.05, reject=True)
            if name == "threshold":
                assert result["results"][0]["reject"] == (method != "BY")
            if name.startswith("alpha_"):
                assert [x["reject"] for x in result["results"]] == [True, False]
    for result in reports.values():
        assert result.keys() == {"schema_version", "family", "method", "error_control", "alpha", "m", "results", "assumptions"}
        assert result["schema_version"] == "1.0.0"
        assert result["error_control"] == ("FWER" if result["method"] in ("holm", "bonferroni") else "FDR")
        assert result["m"] == len(result["results"])
        for row in result["results"]:
            assert row.keys() == {"comparison", "p_raw", "p_adjusted", "reject"}
            assert 0 <= row["p_raw"] <= row["p_adjusted"] <= 1
            assert type(row["reject"]) is bool and row["reject"] == (row["p_adjusted"] <= result["alpha"])
        assert ("PRDS" if result["method"] == "BH" else "arbitrary dependence") in result["assumptions"][2]
        json.dumps(result, allow_nan=False)

    def adjust(values, **options):
        args = dict(labels=["a", "b"], method="holm", family="Primary contrasts")
        args.update(options)
        return analysis.adjust_pvalues(values, **args)

    for values in ([], .1, "0.1", {"a": .1}, {.1, .2}, iter([.1, .2]),
                   np.array(.1), [[.1, .2]], np.array([[.1], [.2]]),
                   np.ma.array([.1, .2], mask=[False, True]),
                   [True, .1], [np.bool_(False), .1], [.1+0j, .2], ["0.1", .2],
                   [np.nan, .1], [None, .1], [pd.NA, .1], [np.inf, .1], [-.01, .1], [1.01, .1]):
        expect_error(lambda: adjust(values), "pvalues")
    for labels in (["a"], ["a", "a"], ["a", ""], ["a", "\u3000"], ["a", None],
                   ["a", 1], "ab", {"a", "b"}, [["a", "b"]], np.array([["a"], ["b"]])):
        expect_error(lambda: adjust([.1, .2], labels=labels), "labels")
    for method in ("auto", "bh", "fdr_bh", None, True, ["holm"]):
        expect_error(lambda: adjust([.1, .2], method=method), "method")
    for family in ("", " \t", "\u3000", None, True, ["family"]):
        expect_error(lambda: adjust([.1, .2], family=family), "family")
    for alpha in (0, 1, -1, np.nan, np.inf, True, "0.05", None, [.05], np.array([.05])):
        expect_error(lambda: adjust([.1, .2], alpha=alpha), "alpha")
    for required in ("labels", "method", "family"):
        options = dict(labels=["a", "b"], method="holm", family="Primary contrasts")
        del options[required]
        expect_error(lambda: analysis.adjust_pvalues([.1, .2], **options), required)
    # All accepted containers retain raw p-values, labels, and caller data.
    baseline = adjust([.1, .2])
    for values in (np.array([.1, .2]), pd.Series([.1, .2]), (.1, .2)):
        before = list(values)
        same(adjust(values), baseline)
        assert list(values) == before
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r-fixture", type=Path)
    parser.add_argument("--only", choices=["replicates", "multiplicity"])
    args = parser.parse_args()
    if args.only:
        selected = check_replicates if args.only == "replicates" else check_multiplicity
        reports = selected()
        print(f"EasyPlot {args.only} Python checks passed: {len(reports)} reports.")
        return
    check_numeric_identity_precision()
    first = np.array([1., 2., 4., 7.])
    second = np.array([3., 5., 8., 10., 12.])
    after = np.array([2., 6., 5., 12.])
    independent = pd.DataFrame({"id": [f"u{i}" for i in range(9)],
                                "arm": ["A"] * 4 + ["B"] * 5,
                                "measurement": np.concatenate([first, second])})
    paired = pd.DataFrame({"id": [f"u{i}" for i in range(4)] * 2,
                           "arm": ["A"] * 4 + ["B"] * 4,
                           "measurement": np.concatenate([first, after])})
    reports = {"independent": run(independent), "paired": run(paired, design="paired")}
    check_library(reports["independent"], first, second)
    check_library(reports["paired"], first, after)
    for name, data, design in (("independent", independent, "independent"),
                               ("paired", paired, "paired")):
        reversed_report = run(data, design=design, order=["B", "A"])
        reports[f"{name}_reversed"] = reversed_report
        effect = reports[name]["effect"]
        assert effect["estimate"] > 0 > reversed_report["effect"]["estimate"]
        same(reversed_report["effect"]["estimate"], -effect["estimate"])
        same(reversed_report["effect"]["ci_low"], -effect["ci_high"])
        same(reversed_report["effect"]["ci_high"], -effect["ci_low"])
        same(reversed_report["test"]["statistic"], -reports[name]["test"]["statistic"])
        same(reversed_report["test"]["p_value"], reports[name]["test"]["p_value"])
    shuffled = paired.iloc[[6, 0, 5, 3, 4, 2, 7, 1]].copy()
    shuffled.index = [8] * 8  # DataFrame row labels must not define pairing either.
    same(run(shuffled, design="paired"), reports["paired"])

    independent_missing = pd.concat([independent, pd.DataFrame({
        "id": ["gone_a", "gone_b"], "arm": ["A", "B"], "measurement": [np.nan, np.nan]})],
        ignore_index=True)
    paired_missing = pd.concat([paired, pd.DataFrame({
        "id": ["u4", "u4", "u5", "u6", "u7", "u7"],
        "arm": ["A", "B", "A", "B", "A", "B"],
        "measurement": [9., np.nan, 9., 12., np.nan, np.nan]})], ignore_index=True)
    for name, data, design, removed in (
            ("independent_complete_case", independent_missing, "independent", ["gone_a", "gone_b"]),
            ("paired_complete_case", paired_missing, "paired", ["u4", "u5", "u6", "u7"])):
        rejects(data, "missing", design=design)
        report = run(data, design=design, missing="complete-case")
        reports[name] = report
        assert report["removed_units"] == removed
        assert report["n_input"] == len(data)
        assert report["n_used"] == (9 if design == "independent" else 8)
        assert report["n_removed"] == (2 if design == "independent" else 6)
        assert len(report["warnings"]) == 1 and "selection bias" in report["warnings"][0]
        check_library(report, first, second if design == "independent" else after)
    rejects(paired.iloc[:-1], "absent", design="paired")

    numeric = independent.assign(id=np.arange(9), arm=[1] * 4 + [2] * 5)
    reports["numeric_labels"] = run(numeric, order=[1, 2])
    constant_margin = paired.copy()
    constant_margin.loc[constant_margin["arm"] == "A", "measurement"] = 1.
    reports["paired_constant_margin"] = run(constant_margin, design="paired")
    check_library(reports["paired_constant_margin"], np.ones(4), after)
    zero_effect = paired.copy()
    zero_effect.loc[zero_effect["arm"] == "B", "measurement"] = [2., 3., 4., 5.]
    reports["paired_zero_effect"] = run(zero_effect, design="paired")
    assert reports["paired_zero_effect"]["test"]["p_value"] == 1.

    # Duplicate IDs remain invalid even when the duplicate's measurement is missing.
    for data, design in ((independent, "independent"), (paired, "paired")):
        extra = data.iloc[[0]].assign(measurement=np.nan)
        rejects(pd.concat([data, extra]), "duplicate unit", design=design, missing="complete-case")
        all_missing = data.assign(measurement=np.nan)
        rejects(all_missing, "at least two", design=design, missing="complete-case")
    cross_duplicate = independent.copy()
    cross_duplicate.loc[4, "id"] = "u0"
    rejects(cross_duplicate, "duplicate unit")
    rejects(paired, "duplicate unit", design="independent")
    constant = independent.copy()
    constant.loc[constant["arm"] == "A", "measurement"] = 1.
    rejects(constant, "variance")
    constant_difference = paired.copy()
    constant_difference.loc[constant_difference["arm"] == "B", "measurement"] = first + 2.
    rejects(constant_difference, "variance", design="paired")
    near_constant = paired.assign(id=range(8), measurement=1e15 + np.array([0, 1, 2, 3, 3, 4, 5, 6]))
    rejects(near_constant, "essentially constant")
    near_constant_pair = paired.assign(measurement=np.concatenate([first, first + 1e15 + [0, 1, 2, 3]]))
    rejects(near_constant_pair, "essentially constant", design="paired")
    rejects(independent.iloc[[0, 4, 5]], "at least two")
    rejects(paired.iloc[[0, 4]], "at least two", design="paired")
    rejects(independent.iloc[:0], "nonempty")
    rejects(independent.to_dict(), "DataFrame")

    for values in (independent["measurement"].astype(str), [True] * 9,
                   independent["measurement"].astype(complex),
                   [True, 2., 4., 7., 3., 5., 8., 10., 12.]):
        rejects(independent.assign(measurement=values), "real numeric")
    for number in (np.inf, -np.inf):
        rejects(independent.assign(measurement=[number] + [1.] * 8), "infinite", missing="complete-case")
    for column in ("id", "arm"):
        for invalid in ("", "  \t", "\u3000", None, np.nan):
            bad = independent.copy()
            bad.loc[0, column] = invalid
            rejects(bad, "identities", missing="complete-case")
    extra_group = independent.copy()
    extra_group.loc[0, "arm"] = "C"
    extra_group.loc[0, "measurement"] = np.nan
    rejects(extra_group, "outside order", missing="complete-case")
    for order in (["A"], ["A", "B", "C"], ["A", "A"], ["A", ""], "AB", {"A", "B"}, [1, 2]):
        rejects(independent, "order", order=order)
    for design in ("auto", None, True):
        rejects(independent, "design", design=design)
    for confidence in (0, 1, -1, np.nan, np.inf, True, "0.95"):
        rejects(independent, "confidence", confidence=confidence)
    rejects(independent, "missing", missing="drop")
    rejects(independent, "columns", unit="absent")
    rejects(independent, "columns", unit="arm")
    duplicated_columns = pd.concat([independent, independent[["id"]]], axis=1)
    rejects(duplicated_columns, "columns")
    categories = independent.copy()
    categories["arm"] = pd.Categorical(categories["arm"], categories=["B", "A", "unused"])
    categories["id"] = categories["id"].astype("category")
    same(run(categories), reports["independent"])
    nullable = independent_missing.copy()
    nullable["measurement"] = nullable["measurement"].astype("Float64")
    same(run(nullable, missing="complete-case"), reports["independent_complete_case"])
    default = analyze_two_groups(independent, group="arm", value="measurement", unit="id",
                                 order=["A", "B"], design="independent")
    assert default["effect"]["confidence"] == .95
    check_library(default, first, second)

    keys = {"schema_version", "design", "columns", "order", "missing_policy", "n_input", "n_used",
            "n_removed", "n_pairs", "removed_units", "summary", "effect", "test", "warnings", "assumptions"}
    for report in reports.values():
        assert report.keys() == keys and report["schema_version"] == "1.0.0"
        assert report["columns"] == {"group": "arm", "value": "measurement", "unit": "id"}
        assert report["n_input"] == report["n_used"] + report["n_removed"]
        assert sum(s["n"] for s in report["summary"]) == report["n_used"]
        assert report["n_pairs"] == (report["n_used"] // 2 if report["design"] == "paired" else None)
        if report["n_removed"] == 0:
            assert report["removed_units"] == report["warnings"] == []
        assert report["assumptions"]
        json.dumps(report, allow_nan=False)
    assert not any(name.split(".")[0] in ("matplotlib", "seaborn", "easyplot_py") for name in sys.modules)
    reports.update(check_replicates())
    reports.update(check_multiplicity())
    for report in reports.values():
        json.dumps(report, allow_nan=False)
    if args.r_fixture:
        same(reports, json.loads(args.r_fixture.read_text(encoding="utf-8")))
        print(f"R/Python parity passed: {len(reports)} complete reports (rtol=atol=1e-12).")
    print("EasyPlot analysis Python checks passed: inference, identity, missingness, types, metadata, immutability.")


if __name__ == "__main__":
    main()
