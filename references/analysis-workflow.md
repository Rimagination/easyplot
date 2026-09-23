# Research analysis inside EasyPlot

Use for data preparation, exploratory analysis, inference, prediction or interpretation, including requests with no figure. Keep EasyPlot as the user-facing owner. Use established scientific libraries directly; no external analysis skill is required. A method outside the bundled helper's scope can still be implemented as a task-specific R/Python workflow after its assumptions and implementation are checked.

## Start with the scientific contract

Record only choices relevant to this task:

- Question and target quantity: descriptive pattern, group difference, association, prediction, or a causal effect requiring an explicit identification strategy.
- Data provenance and units: source path/version, variable definitions, valid ranges, measurement units, ID semantics and any approved transformations.
- Design: independent biological/experimental units, assignment level, technical repetitions, paired subjects, repeated visits, sites/blocks/batches and nesting.
- Target population/sample and outcome; prespecified contrasts when available. Separate exploratory from confirmatory work.
- Missing/censored/excluded observations and the proposed policy; keep zero, missing and below-detection values distinct.
- Deliverable and language: explanation, analysis script/results, figures, or both. Existing project conventions take priority unless the user explicitly selects another language.

Unknown independence, pairing, exposure/outcome definitions or censoring can prevent valid inference. Ask about that specific ambiguity while continuing safe inventory or descriptive work. Do not manufacture a study design from column names. Unique IDs check row identity; they do not prove biological independence.

## Prepare data without losing the experiment

Preserve raw inputs. Keep transformations in code with row/unit counts before and after each consequential operation. Confirm numeric parsing, duplicate keys, unit conversions and many-to-many joins. Preserve identifier strings and leading zeros. Check that joins and reshapes conserve the intended observations.

Import long numeric-looking identifiers as strings when they are labels. The Python helper preserves distinct identities already present in its input, including mixed large-integer/float labels; it cannot recover digits lost during an earlier CSV/spreadsheet import or floating-point conversion.

Use separate columns for variables, rows for observations at a declared level, and linked tables for different observational units. An observation row can be nested within a subject or experiment; a tidy table does not establish independence. This organization follows [Tidy Data](https://www.jstatsoft.org/article/view/v059i10).

Show distributions and missingness before fitting. Investigate outliers as observations; apply exclusions only with a defensible recorded rule, and preserve a sensitivity result when the decision could change the conclusion. Never replace missingness with zero by default. Complete-case analysis, imputation and model-based missing-data handling require explicit choices and assumptions.

For technical repetitions, identify the experimental unit first. A transparent unit-level summary may fit the estimand; a hierarchical model may be needed to retain multiple levels. Do not turn hundreds of measurements from a few independent experiments into hundreds of independent replicates. Use separate visual cues for within-unit observations and between-unit summaries when useful; see [SuperPlots](https://doi.org/10.1083/jcb.202001064).

Read [replicates-and-multiplicity.md](replicates-and-multiplicity.md) for the bundled unit-summary helper, repeated/nested design decisions, and an analysis-to-figure example. Summarizing technical readings does not remove dependence between repeated conditions of the same unit.

## Select the method from design and estimand

This table selects a workflow, not an automatic test based on a normality-test p-value. Describe relevant assumptions, influential observations, residual structure and sensitivity. An assumption screen cannot establish that a study is valid.

| Situation | Workflow | Important boundary |
| --- | --- | --- |
| Descriptive/EDA only | Counts, missingness, distributions and appropriate summaries | No unsolicited hypothesis testing or mandatory image |
| Two independent groups, continuous outcome, mean difference | Bundled Welch helper when its contract fits | One observation per independent unit; assess suitability for small samples/heavy tails |
| Two paired conditions, continuous outcome, mean change | Bundled paired helper, joined by unit ID | Review the distribution of within-unit differences; never pair by row order |
| More than two groups or covariate adjustment | Model matching outcome/estimand, declared contrasts, family-level error control | Avoid treating many independent t-tests as a complete analysis |
| Counts, proportions, binary or ordinal outcomes | Appropriate outcome likelihood/link and exposure/denominator | Check overdispersion, separation or boundary behavior as applicable |
| Nested, longitudinal or clustered observations | Unit-level estimand or suitable multilevel/GEE/cluster-aware approach | Respect randomization level, dependence and number of independent units |
| Correlation/association | Match scale, functional form and sampling; show effect and uncertainty | Association alone does not identify a causal effect |
| Survival/censoring, compositional data, spatial or omics analysis | Domain-appropriate libraries and an explicitly validated task recipe | Preserve censoring, denominators, coordinate/dependence or multiple-testing semantics |
| Predictive modelling | Honest holdout/CV, appropriate splits, baseline, calibration and uncertainty as relevant | Train preprocessing only inside training folds; protect groups/time order |

For a family of comparisons, define the family and desired error criterion before adjusting p-values. Choose and disclose the method and its assumptions; preserve both raw and adjusted results. The existence of a `fdr_bh` or `holm` function does not choose the family for you. See [statsmodels multiple-testing documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

The local `adjust_pvalues()` / `easyplot_adjust_pvalues()` helper supports explicit Holm, Bonferroni, BH and BY methods without a statsmodels dependency. Read the [family and interval contract](replicates-and-multiplicity.md) before use; a p-value correction does not turn pointwise confidence intervals into simultaneous intervals.

Report the effect in meaningful units with its interval and direction, supported by actual sample/unit counts. A p-value does not measure effect size, practical importance, or the probability that a hypothesis is true. Avoid equating a non-significant result with equivalence. Separate supported findings from speculative interpretation. These reporting priorities follow the [ASA statement](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf).

## Bundled two-group helper

Only use after choosing the mean-difference estimand and establishing that the design fits. Helpers use SciPy or R's native `t.test`; they do not select the scientific design. They do not implement mixed models, multiple endpoints, covariate adjustment, power analysis or causal identification.

Python (NumPy/pandas/SciPy >= 1.11; no plotting imports required):

```python
from easyplot_analysis import analyze_two_groups

report = analyze_two_groups(
    data, group="condition", value="response", unit="subject_id",
    order=["before", "after"], design="paired",
    missing="error", confidence=0.95,
)
# effect direction is always after - before
```

R: source `scripts/easyplot_analysis.R` from the installed skill location, then:

```r
report <- easyplot_analyze_two_groups(
  data, group = "condition", value = "response", unit = "subject_id",
  order = c("before", "after"), design = "paired",
  missing = "error", confidence = 0.95
)
```

Contracts:

- `design="independent"` uses Welch's unequal-variance two-sample t-test. Every supplied unit ID must identify one independent observation across the table. If IDs restart per group, explicitly form the correct composite identity after confirming the design.
- `design="paired"` uses a paired t-test. Each unit/condition combination must be unique. Pair by ID even when input rows are shuffled.
- Default missing policy is an error. With explicit `missing="complete-case"`, remove incomplete paired units together and report exclusions; the helper warns about possible selection bias. Do not infer that complete-case analysis is justified because the command runs.
- Reject unexpected groups, empty identities, duplicate units, invalid values, insufficient observations and degenerate inference. Repeated technical readings require a justified upstream summary or a different model, not relaxed ID checks.
- The focused independent helper conservatively requires positive sample variance in each group. A constant-control case can fall outside this helper even when a direct library analysis is mathematically defined; assess the design and use a separately checked recipe rather than describing that limitation as a universal statistical rule.
- Return group summaries, second-minus-first mean difference and confidence interval, test statistic/df/p-value, counts, exclusions, warnings and assumptions. Do not generate significance stars automatically.
- `n_input`, `n_used` and `n_removed` count actual input rows; `n_pairs` counts retained complete pairs. `removed_units` lists excluded identities. An absent pair member has no input row to count, so keep row exclusions distinct from excluded units.
- Preserve the input table. Keep raw-data paths and scientific decisions in the caller's analysis record; the helper cannot infer them.

The official APIs specify [Welch testing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html), [paired testing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_rel.html), and [R t.test](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/t.test.html). Library documentation may describe newer versions than the project environment; check actual installed signatures and record versions.

## Predictive validation safeguards

Split according to the intended generalization target. Fit imputation, scaling, feature selection and dimension reduction on training data within each resampling fold; apply learned transforms to validation data. Prefer a pipeline that enforces this separation. Keep a final test set out of tuning. [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)

When predicting unseen subjects/sites, keep each group out of both train and validation partitions simultaneously. For forecasting, evaluate on later observations with appropriate gaps/horizons and comparable evaluation windows; random row splits can leak time structure. Irregular observations may need custom time-based splits rather than direct `TimeSeriesSplit`. Record split IDs, seeds, metrics and a reasonable baseline. [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)

These are local workflow rules. A full predictive pipeline is a task-specific implementation and must be tested on the user's design; it is not a prevalidated EasyPlot AutoML engine.

## Compact analysis record and delivery

Keep a short record beside the code, as JSON, a table or prose; avoid mandatory boilerplate for simple explanations:

```text
Question / estimand / effect direction:
Design / independent unit / pairing or clustering:
Source data / variables / units:
Input counts / retained units / exclusions / missing policy:
Method / contrasts / multiplicity / model assumptions:
Effect estimates / uncertainty / diagnostics / sensitivity:
Language / package versions / random seeds / split IDs if applicable:
Outputs / limitations / exploratory or confirmatory status:
```

Deliver a script and reusable result table for executed analysis, plus an interpretation calibrated to the design and uncertainty. If the user only requests a plan or explanation, do not execute new analyses or mutate their data. For an existing-results plotting request, validate the supplied result contract instead of adding a fresh analysis. Statistical details and the figure caption belong outside manuscript images.

## Capability and validation boundary

| Capability | Current evidence level |
| --- | --- |
| R/Python two-group independent and paired analysis | Bundled helpers; `test_easyplot_analysis.R` and `.py` validate inputs, numeric results and cross-language agreement |
| Technical-replicate summaries and explicit Holm/Bonferroni/BH/BY adjustment | Local helpers and cross-language contract tests; aggregation is not a mixed-model fit, and correction does not choose the comparison family |
| R/Python scientific plots, aligned plates, provenance export | Existing local runtimes and their regression suites; retain current backend limitations |
| Metadata, WCAG contrast and grayscale screening | Existing local QA scripts; limited inspection, no certification |
| Data-preparation, EDA, method selection and prediction safeguards | Local decision workflow; each task's actual data transformations/models require execution and checks |
| Generalized/mixed models, survival, spatial/omics workflows, robust/resampling and Bayesian methods | Choose established libraries and validate task-specific recipes; no claim of a bundled validated engine |
| Journal/font acceptance and full embedded-raster/font inspection | Partial automation and manual/live-source review; see `kdense-adaptation.md` gaps |

Only promote a method to bundled/validated after a representative example, a failure case, a numerical reference and any relevant rendered-output review. Definitions and current evidence live together so that a new assistant does not mistake a roadmap for implemented capability.
