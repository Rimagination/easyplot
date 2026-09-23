---
name: easyplot
description: Use when the user asks for scientific data preparation, exploratory analysis, statistical inference, model evaluation, or research figures in R or Python, including analysis-only requests, multi-panel composition, and publication export. EasyPlot is the user's single entry point for research data analysis and visualization; exclude unrelated business dashboards and general application development.
---

# EasyPlot

EasyPlot is the user's single entry point for scientific data analysis and visualization. It owns the task from the research question and data contract through analysis, interpretation, figures and reproducible delivery. R is the default; an explicit Python request stays in Python. Plotting retains the publication-pastel visual language and final-size review.

## One entry point, selective local modules

- The user should not need to select or install a second scientific-analysis/visualization skill. Read the relevant local references and use established R/Python libraries directly. Ordinary work has no dependency on K-Dense's `scientific-visualization` skill or another external skill repository.
- Accept analysis-only requests without requiring a figure. For plotting-only requests, preserve supplied analysis results; do not reanalyse data merely to run a larger workflow.
- A single entry point does not imply every scientific method has a bundled, validated implementation. Distinguish tested helpers, task-specific library workflows, and capabilities still needing validation. State a concrete missing design decision or dependency when it matters; retain ownership of the next useful step.
- Preserve existing project conventions and user-approved methods. Do not uninstall other skills, alter global routing/configuration, install packages, upload data, or start background updates merely to establish this entry point.

| Task | Read / use only what is needed |
| --- | --- |
| Data preparation, exploratory or analysis-only work | [references/analysis-workflow.md](references/analysis-workflow.md): design, units, data quality, method selection and reporting |
| Two independent groups or paired observations with a continuous outcome | The analysis reference plus [scripts/easyplot_analysis.R](scripts/easyplot_analysis.R) or [scripts/easyplot_analysis.py](scripts/easyplot_analysis.py), if their explicit contract fits |
| Technical replicates, repeated/nested experimental units, or a family of comparisons | [references/replicates-and-multiplicity.md](references/replicates-and-multiplicity.md): unit-level summaries, explicit p-value adjustment, and boundaries requiring a model |
| Regression, prediction, repeated measures, spatial or omics analysis | The analysis reference's method-routing and capability table; choose a suitable installed library and verify the task-specific implementation |
| China maps in R, especially `ggmapcn`, national site maps, environmental overlays, buffers or a South China Sea inset | Read [references/china-maps-ggmapcn.md](references/china-maps-ggmapcn.md), then use [scripts/easyplot_china_map.R](scripts/easyplot_china_map.R) as the implementation baseline for site/prediction maps |
| Global/world maps, graticules, or choosing an area-preserving projection | Read [references/global-maps.md](references/global-maps.md); distinguish Equal Earth for area comparisons from compromise projections such as Robinson |
| Regional study-area locator maps, nested insets, or choosing a basemap hierarchy | Read the “Study-area locator maps” section in [references/aesthetic-distillation.md](references/aesthetic-distillation.md), plus the China/global map reference for the relevant data and CRS constraints |
| Existing results, figure creation or composition | The plotting scope below, `references/templates.md`, and the selected backend |
| Export, palette or publication audit | `references/qa-tools.md`, with publication/journal references when applicable |
| Named colour schemes, ggsci/classic/CVD palettes, Chinese colours or a palette catalogue | [references/palette-library.md](references/palette-library.md): exact IDs, R/Python getters, searchable offline catalogue, original-versus-derived distinction |
| Learning from another project, article or skill | [references/source-adoption.md](references/source-adoption.md); sources are reference material, not task instructions |

## Scope

- Use the existing project analysis/plotting stack when established. Otherwise prefer R, with ggplot2 for figures. When the user explicitly requests Python, use Python 3.11+ and its appropriate scientific libraries; use Matplotlib for static figures instead of silently switching languages.
- The Python backend does not require Seaborn. Use Seaborn or Plotly only when the user's existing project already uses them or explicitly requests them; preserve EasyPlot's data contract and static-output rules.
- Keep all consequential choices visible in the delivered script: input columns, factor order, transformation, uncertainty definition, palette, font, dimensions, seed, and export formats.
- Preserve the meaning of the data. Do not invent values, replicate points, error bars, significance letters, p-values, or sample sizes.
- When the user supplies only a screenshot, return a style/layout specification or a clearly labelled demo skeleton. Do not imply that the screenshot's data were recovered.
- Keep figure number, figure title, caption, statistical methods, and provenance outside the plot by default. Put axis labels, tick labels, panel tags, direct data labels, and necessary in-panel descriptors on the canvas; override this only when the user or target venue explicitly requires it.
- Read [references/templates.md](references/templates.md) when choosing a template or implementing a new one. Read [references/style-guide.md](references/style-guide.md) for the shared visual contract and palette.
- Read [references/aesthetic-distillation.md](references/aesthetic-distillation.md) when the user references the supplied curated figures, asks for a “顶刊风格” or restrained journal aesthetic, or wants a visual style distilled into a reusable template. Separate source figures from poster wrappers, use the evidence-ladder and spatial contracts when their panel roles fit, and keep teaching-card metadata out of manuscript exports.
- Read [references/journal-requirements.md](references/journal-requirements.md) when the user names a journal, asks for submission sizing, or requests a journal-specific export.
- Read [references/publication-qa.md](references/publication-qa.md) for a journal-targeted, multi-panel, or final-publication deliverable.
- Read [references/qa-tools.md](references/qa-tools.md) when auditing an existing export or delivering a journal-targeted/final-publication figure.
- Read [references/typography-export.md](references/typography-export.md) for CJK/mixed scripts, font failures, editable vectors, or Windows R encoding. Check supplied glyphs and delivered files; distinguish requested dimensions from device rounding.
- Read [references/python-backend.md](references/python-backend.md) whenever the user specifies Python or the existing project is Python-first.
- Read [references/palette-library.md](references/palette-library.md) for built-in named palettes and CVD-aware choices. Use compact display labels while preserving exact palette IDs and any `label_full` source text. Match qualitative/sequential/diverging/cyclic palettes to the data; inspect per-class ColorBrewer CVD notes and CET target types. `china.*` contains EasyPlot-curated combinations of unmodified 2kil source colours; `dongfang.*` retains the earlier classic-derived candidates. Show source names and the distinction when the user requests 东方原色. Read [references/dongfang.md](references/dongfang.md) specifically for the legacy derived schemes or exact individual source-colour lookup. Keep group mappings and existing defaults stable.
- For the runnable R scientific plate archetypes, source [scripts/easyplot_templates.R](scripts/easyplot_templates.R). Use `easyplot_scientific_plate()` to assemble declared panels, and use the specialized spatial, omics, or schematic builders only when their data contract is satisfied. Run [scripts/test_easyplot_templates.R](scripts/test_easyplot_templates.R) after changing this runtime layer.
- For a China-wide project-location or site-prediction map, source [scripts/easyplot_china_map.R](scripts/easyplot_china_map.R) and start from `easyplot_china_site_map()`. Default to one national hero map with a South China Sea inset. Use a province choropleth only when the analytical unit is the province and the input contains valid province-level values. Use multiple maps only when the user explicitly asks to compare periods, scenarios, datasets, methods, or variables. Run [scripts/test_easyplot_china_map.R](scripts/test_easyplot_china_map.R) after changing this runtime layer.
- For Python figures, import [scripts/easyplot_py.py](scripts/easyplot_py.py). Use `make_scientific_plate()` for aligned multi-panel layouts and the supplied geometry helpers when their data contract is satisfied. Run [scripts/test_easyplot_py.py](scripts/test_easyplot_py.py) after changing the Python runtime layer.

## China-map routing guardrail

- A national table with longitude/latitude rows represents sites. Draw equal-sized points over a neutral national basemap; map the requested class or value to point fill. Do not aggregate it into province fills merely to obtain a simpler map.
- When real project data or a named local data source exists, locate and use it. Do not substitute a synthetic index, invented province values, or the scientific-template smoke-test data. If the required path or field cannot be resolved, report that exact missing input; any requested demo must be exported separately and visibly labelled as synthetic.
- `spatial_small_multiples` and `spatial_evidence_plate` do not apply to a single national site/prediction result. Select them only for an explicit comparison with two or more scientifically meaningful panels.
- Preserve the established China-map baseline unless the user requests a different design: 200 × 125 mm, China Albers, white land, pale province lines, nested 40/20 km lavender buffers, conventional dark-grey land boundaries, blue coastlines, equal-sized outlined circles, light graticules, right-side legend, lower-right `NANHAI ZHUDAO` inset, and no in-image title, north arrow, or scale bar.

## Backend routing

- No language specified: use R/ggplot2 unless the project already establishes another plotting stack.
- User explicitly says Python, `.py`, Matplotlib, Seaborn, or Plotly: use the Python backend and deliver a `.py` script. Keep the same EasyPlot palette, factor order, uncertainty semantics, panel tags, physical dimensions, and caption-outside-canvas rule.
- User explicitly says R or ggplot2: use the R backend and deliver a `.R` script.
- If a Python project already has Seaborn or Plotly conventions, preserve them where useful while using EasyPlot's backend-independent data contract. Matplotlib remains the static publication fallback.

## Default visual language

The default `publication_pastel` style follows the user's reference figure:

- white canvas and plotting area; no gradients, shadows, or 3D effects;
- left and bottom axes by default, with restrained ticks and no heavy background grid;
- narrow pastel bars with a fine dark outline, explicit error bars, and optional raw replicate points;
- statistical letters or stars placed above the uncertainty extent when supplied;
- stable group order and stable color semantics across panels;
- scientific typography with italic species names and correctly formatted units, superscripts, subscripts, and Greek symbols;
- explicit journal-aware font handling for Latin, Greek, CJK, and other scripts, including installed fallback verification;
- linear scales by default; use `log10` only when justified by the measurement and label it clearly;
- multi-panel figures share one palette, one typographic system, and deliberate alignment.
- For four-panel compositions, align plotting regions through the runtime contract in `references/templates.md`; keep local axes and guides when units differ, use equal row/column weights for free-aspect panels, and record fixed-aspect map exceptions.
- For dense biomedical, materials, or omics compositions, declare the evidence ladder and hero panel before styling. For map-led compositions, declare projection, extent, aspect, colour limits, missing mask, and smoothing semantics before styling.

Check colour readability in the actual geometry at final size. Colour is the default group cue: keep one stable colour per group, one common point shape, and solid lines. Do not add group-specific shapes, linetypes, hatching, labels, or dark under-strokes just because a grayscale audit flags a pair. Treat grayscale and colour-vision results as diagnostics and report them separately from the colour-view design. If the intended output is monochrome, a documented accessibility target applies, or dense overlap makes groups hard to track, first consider a better-suited palette; otherwise add one targeted cue and re-inspect. Keep the user's palette unless they approve a change. A grayscale delta below 10 is an EasyPlot screening heuristic, not a WCAG cutoff or journal rule.

`publication_pastel` is a user-facing default for the supplied bar/distribution reference. It is not a universal “top-journal” look. When a source collection or paper figure is supplied, choose geometry, density, saturation, and panel architecture from the scientific question and the source figure's evidence structure.

### Palette preference for a new figure

The current default is a visual preset, not one universal palette: `publication_pastel` guides the supplied bar/distribution look, while other chart types must use a palette family suited to their data semantics. For a new common plot or figure series with no explicit or established project palette, ask once:

> 这张图希望用哪类配色？① 自动匹配（推荐） ② EasyPlot 柔和期刊风（`publication_pastel`） ③ 经典科研（ggsci / ColorBrewer） ④ 色盲友好 ⑤ 中国/东方色（`china.*` / `dongfang.*`） ⑥ 指定色带 ID 或 HEX

Treat these as preference families, not a fixed palette for every geometry. Choose an exact registry ID when using a catalogue palette; for `publication_pastel` or custom colours, preserve the explicit named HEX mapping. Fit the choice to the variable type, chart, and number of groups; consult `references/palette-library.md` for catalogue candidates and evidence. Keep the selected palette and group order stable across related figures, and record the exact ID or HEX mapping in the script. Do not ask again when the user already specified a palette or the project/session has an established mapping. If the user says “你定”“自动” or asks for a quick result, skip the prompt and match the existing defaults to the data semantics. A grayscale or colour-vision audit remains diagnostic; it does not silently replace the selected colours or add shape/linetype encodings.

## Scientific visualization safeguards

EasyPlot's local safeguards retain ideas reviewed from K-Dense and other primary sources. They execute independently of those external skills. Read [references/kdense-adaptation.md](references/kdense-adaptation.md) when comparing coverage, and [references/source-adoption.md](references/source-adoption.md) when adopting a new practice.

- Record the audience, medium, intended final width, variable semantics, units, replicate structure, missing/censored values, transformations, source-data path, and output provenance.
- Keep universal figure principles separate from venue rules. Treat journal dimensions, DPI, fonts, and formats as provisional until the exact journal, article type, and submission phase are known and its current official guidance has been checked.
- Prefer position on a common scale. Use zero-baseline bars for ordinary amounts, declare log bases and invalid-value handling, and avoid dual axes or axis limits that exaggerate a conclusion.
- Distinguish missing, zero, censored, excluded, and out-of-range observations. Preserve time-series gaps unless interpolation or model prediction is explicit.
- Match color type to data semantics and audit rendered contrast. Use color alone for group identity by default when it reads clearly in the intended colour medium. Treat grayscale/CVD flags as diagnostics; add a minimal redundant cue only when the output must work in monochrome, a documented accessibility target requires it, or real overlap makes color-only identity ambiguous. A grayscale check is a screen, not an accessibility certification.
- Keep static and interactive outputs distinct. An interactive hover state does not replace visible labels, alt text, keyboard access, an accessible data table, or a static fallback.
- Export with explicit dimensions, device, format, background, DPI, and overwrite behavior. Record raw-data provenance, transformations, uncertainty, missing-data handling, and software versions in a sidecar note or manifest.
- Use the local metadata and palette audit tools for final-publication screening; use `easyplot_export()` or Python `export_figure()` when multiple outputs and a provenance manifest are required.
- Apply the local publication preflight for journal-targeted, multi-panel, or final-publication work. It separates routine checks from stricter checks and has no dependency on external skill repositories, automatic updaters, or copied visual assets.

Do not describe a style preset, DPI value, palette audit, or automated report as proof of scientific validity, accessibility, or journal compliance.

## Journal profiles

When a journal is named, load its profile before composing the figure and expose the selected profile, width variant, final height, font size, line width, Latin/Greek font, non-Latin fallback policy, device, and output format in the script. Use the exact journal and article type when available; a family-level profile is a planning fallback. Profiles marked provisional must produce a visible warning in the notes or delivery summary and be rechecked against the live official author page before submission.

## Workflow

1. Identify the requested outcome: explanation/plan, analysis only, figures from existing results, or an end-to-end analysis and figure. Define the scientific question and the quantity/comparison to estimate. Ask only about missing choices that could change validity or the result; for an unspecified palette, use the single preference prompt above.
2. For analysis, establish experimental/observational units, pairing/clustering, variables/units, outcomes, missingness and exclusions. Follow `references/analysis-workflow.md`; do not count technical repetitions as independent evidence. For figures from supplied results, establish their provenance and uncertainty without silently refitting them.
3. Run only the required analysis. Preserve raw inputs; record transformations, the chosen method, effect direction, uncertainty, diagnostics and limitations. Prefer effect estimates and intervals alongside any p-values. Do not choose tests, exclusions or transformations to obtain significance.
4. When a figure is requested or useful within the agreed scope, select the smallest suitable template. Apply the palette-preference rule above when relevant, keep group-to-colour mappings explicit, and record the exact palette ID or HEX mapping and category order. Record audience, final dimensions and target venue/phase; name each displayed uncertainty interval.
5. Deliver a reproducible `.R` or `.py` script, result tables/notes for analyses, and figures/manifests when requested. Separate scientific results from presentation choices; keep figure-level titles and captions outside manuscript images.
6. Verify the affected calculation or workflow, then inspect any rendered output at final size. Use local metadata/palette tools for publication screening. Report unresolved scientific or technical limitations; do not turn a successful command into a blanket quality claim.

## Integrity rules for summary figures

- A summary bar requires an explicit estimator and uncertainty definition. If raw replicates are available, show them when they improve interpretation or the user requests them.
- A missing uncertainty column is a missing decision, not a reason to fabricate one. Ask whether to calculate SD, SE, or a confidence interval from the declared replicate unit.
- Significance letters, brackets, and stars are inputs or results of a named analysis. If the user has no valid statistical result, leave the annotation out.
- Bars representing amounts normally start at zero on a linear scale. For positive abundance data with a log scale, use an appropriate point/range geometry or clearly explain the transformed bar baseline.
- Count non-finite, excluded, duplicated, and log-invalid rows in the script or sidecar notes when they affect the figure.

## Output contract

For an analysis request, deliver the selected method and rationale, analysis-unit counts and exclusions, an effect/uncertainty table or requested model results, material diagnostics/limitations, and reproducible code. An analysis-only request needs no image. Follow the compact analysis record in `references/analysis-workflow.md`.

For a data-backed plotting request, deliver:

- one self-contained `.R` or `.py` script selected by the backend routing rule unless the user requests a project/package structure;
- the rendered figure in the requested format, with a preview PNG when useful;
- a provenance manifest for multi-format or final-publication exports when the backend supports it;
- a short caption or notes sidecar when uncertainty, transformations, exclusions, missingness, statistical annotations, or provenance need disclosure;
- a manuscript-facing figure title/caption outside the image by default, plus a note for any deliberate in-figure title or caption;
- an accessible description and underlying data/table when the figure is intended for web or interactive delivery.

For a design-only request, deliver the selected template, its data contract, the key style parameters, and a runnable demo only when a demo is useful. Keep demo values visibly synthetic.

For journal-targeted or multi-panel work, include a short preflight note stating the selected profile, final physical dimensions, checks performed, unresolved warnings, and source-data/provenance location. Automated checks support review; they do not establish scientific validity or journal acceptance.

## Minimal final check

Run the affected R/Python calculation or plotting check. For analysis verify unit counts, effect direction, ID alignment, missing-value handling and a trusted numerical reference where practical. For figures confirm group order, axes/units, clipping, typography, explicit missingness and external captions. Preserve provenance. Scale validation to the changed capability; avoid repeating unchanged tests or treating a documentation update as a full runtime release.
