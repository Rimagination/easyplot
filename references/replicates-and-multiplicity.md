# Experimental units, repeated observations and comparison families

Use with `analysis-workflow.md` when there are multiple measurements per unit, linked conditions, nested sampling, or several statistical comparisons. Use the local analysis module in the chosen language; no external scientific skill is required.

## Decide which observations can be summarized

Record the allocation/sampling unit and the quantity to estimate. Distinguish technical readings, subsamples, repeated conditions/visits, biological units and higher-level blocks. A column named `replicate` cannot establish its scientific role.

| Design | Suitable route | Preserve |
| --- | --- | --- |
| Comparable technical readings of one unit in one condition | Arithmetic mean per unit/condition when that summary matches the estimand | Raw readings, counts, missingness and within-cell SD |
| Independent units each assigned to one condition | Compare unit-level values; the two-group helper can use Welch inference when appropriate | Independent-unit n; unequal reading counts do not automatically give units more weight |
| The same unit measured in two conditions | Summarize technical readings separately within condition, then match unit IDs for paired analysis | Pair identity, direction and complete-pair policy |
| More visits, treatment-by-time questions, nesting or crossed blocks | An explicitly specified repeated/multilevel/correlation-aware model, or scientifically justified unit summaries | All relevant time, dose, batch and allocation levels |

An equal-unit mean targets the average unit. A pooled mean over all readings weights units by their reading counts; it can target a different quantity. Unequal counts can also imply unequal precision. The bundled summarizer does not choose model weights or solve informative sampling; record the estimand and evaluate a suitable model when necessary.

Do not collapse measurements from different times, doses, outcomes or subgroups merely to make the keys unique. If these dimensions matter, preserve them in a task-specific aggregation/model. Additional readings within one unit improve its characterization but do not create independently allocated units. This interpretation is informed by the unit-level discussion and Figure 1/S1 explanations in [SuperPlots](https://doi.org/10.1083/jcb.202001064); no source figure or tutorial code is bundled here.

## Local unit-summary helper

Python: `summarize_replicates()` in `scripts/easyplot_analysis.py`.
R: `easyplot_summarize_replicates()` in `scripts/easyplot_analysis.R`.

Both take `data`, `group`, `value`, `unit`, `replicate`, required `design`, and `missing="error"` by default. `design="independent"` requires each unit to belong to one condition. `design="repeated"` allows the same unit across conditions; it declares the input structure and performs no repeated-measures model fitting.

- Each unit/group/replicate key must be unique, including rows with missing values. IDs must already be complete and precise at import. If IDs restart in different batches, construct the scientifically correct composite ID explicitly.
- Numeric readings must be real, with no boolean, complex or infinite values. Missing readings raise an error unless `missing="available"` was explicitly selected.
- With `available`, summarize observed readings within each unit/condition. Keep a fully missing unit/condition as a summary row with `value=null`, `sd=null` and `n_used=0`. Never substitute zero or silently delete that unit. One observed reading has `sd=null`.
- Never create rows for unobserved unit/condition combinations. Compare against the planned sampling roster separately; input data alone cannot reveal a completely absent unit or condition.
- Output `summary` contains normalized fields `unit`, `group`, `value`, `n_input`, `n_used`, `n_missing`, `sd` in first-appearance order. Top-level counts distinguish raw reading rows, unique units and unit/condition cells. Input tables remain unchanged.
- `sd` describes within-unit/condition readings. It is not an SE or CI across biological units. Downstream inference must use the declared unit-level observations and dependence structure.

Python example, using already imported and design-checked data:

```python
import pandas as pd
from easyplot_analysis import summarize_replicates, analyze_two_groups, adjust_pvalues

summary = summarize_replicates(
    raw, group="condition", value="response", unit="batch_id",
    replicate="reading_id", design="repeated", missing="error",
)
units = pd.DataFrame(summary["summary"])
contrasts = [("Control", "Low"), ("Control", "High")]  # declare before testing
reports = [analyze_two_groups(
    units.loc[units["group"].isin(pair)], group="group", value="value", unit="unit",
    order=pair, design="paired", missing="error", confidence=.95,
) for pair in contrasts]
adjusted = adjust_pvalues(
    [r["test"]["p_value"] for r in reports],
    labels=[f"{b} - {a}" for a, b in contrasts], method="holm",
    family="Two planned treatment-versus-control contrasts for response", alpha=.05,
)
```

Use text IDs when constructing downstream tables if numeric-looking labels could be coerced or rounded. Helpers preserve identities present in their input, but cannot recover precision lost before the call. If missing unit-level values remain, choose and report the downstream policy separately; `available` is not automatic permission to remove whole pairs. Different complete-pair sets across contrasts require separate n/exclusion reports and a selection-bias caveat.

In R, the JSON-friendly summaries use `NULL` for an unavailable mean/SD. When constructing an analysis data.frame, retain the unit/group fields and translate the missing **value** to `NA_real_`; do not discard the whole summary row or substitute zero. Keep the full summary list as the aggregation audit.

## Comparison-family contract

Python: `adjust_pvalues(pvalues, *, labels, method, family, alpha=.05)`.
R: `easyplot_adjust_pvalues(pvalues, labels, method, family, alpha=.05)`.

Define which outcomes/contrasts belong together and the error criterion before inspecting significance. Keep every prespecified comparison in the analysis record, including failures. Supply all valid p-values from the declared family in the declared order; the helper rejects missing/invalid values instead of silently shrinking the family. Resolve unavailable tests explicitly before claiming full-family control. The helper cannot detect omitted tests or repair invalid primary analyses.

| Method | Error criterion | Dependence condition |
| --- | --- | --- |
| `holm` | Family-wise error rate (FWER) | Arbitrary dependence, assuming valid individual p-values |
| `bonferroni` | FWER | Same validity requirement; retains a common conservative option |
| `BH` | False discovery rate (FDR) | Independent tests or the required positive-dependence condition (PRDS) |
| `BY` | FDR | Arbitrary dependence, generally more conservative than BH |

`family` is a nonblank scientific description; `labels` are unique nonblank strings. P-values must be a nonempty one-dimensional sequence of finite real numbers in [0,1], with no string/boolean coercion. Each returned row retains `comparison`, `p_raw`, `p_adjusted` and `reject` at the declared alpha; input ordering is preserved. No automatic stars or letters are generated.

R uses `stats::p.adjust`. Python uses the installed SciPy FDR routine for BH/BY and compact NumPy Holm/Bonferroni formulas tested against R; no new package is needed. The method semantics and reference checks come from [R p.adjust](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html) and [SciPy false_discovery_control](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html).

Keep effect estimates and uncertainty alongside both p-value columns. These helpers adjust p-values only. Label existing t-test intervals **pointwise 95% CI** if multiple contrasts are displayed; they remain unadjusted. Simultaneous interval estimation needs a separately chosen and validated method. FDR describes an expected proportion among rejected hypotheses, not the probability that an individual discovery is false. Avoid labelling BH-adjusted p-values as a different estimator's q-values.

## When a mixed/repeated model is needed

Use a task-specific library workflow when unit averaging would discard the target time course, interaction, heterogeneous precision or relevant levels. State fixed effects, grouping levels, covariance/random-effect structure, contrast coding and interval method. Inspect residual structure, influential units, group counts, convergence and singularity; an optimizer exit code alone cannot validate inference.

The [lme4 singularity guidance](https://lme4.github.io/lme4/reference/isSingular.html) distinguishes boundary variance estimates from ordinary convergence issues, and notes the risks for standard inference. Follow the [convergence diagnostic guidance](https://lme4.github.io/lme4/reference/convergence.html) when fitting produces warnings: assess data/specification/scaling and stability as relevant. Do not automatically delete random effects or keep changing optimizers to obtain a desired p-value. These are reviewed workflow rules; this module does not bundle a validated mixed-model engine.

## Figure integration and verification

Show technical readings with smaller marks and unit means with larger, identified marks; link only genuine repeated units. Inferential intervals come from independent units or the specified model. Keep figure title, caption, n definitions, multiplicity and limitations outside the canvas. Raw readings and result tables remain deliverables alongside the image.

The executable [R example](../scripts/demo_replicates.R) creates a clearly synthetic repeated-batch dataset, unit means, planned paired contrasts, Holm-adjusted results, and a two-panel figure using the existing EasyPlot composition/export layer. It is a teaching/acceptance case, with no journal-compliance claim.

Changed calculations are covered by `test_easyplot_analysis.R` and `.py`: identity/duplicate checks, unequal reading counts, available/all-missing cells, invalid inputs, p-value ordering/ties/boundaries and R/Python result agreement. A source's methodological validity does not certify every downstream use; verify the actual study contract.
