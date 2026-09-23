# K-Dense adaptation note

## Source

This note records the ideas adapted from K-Dense's public `scientific-visualization` skill:

- Source skill: [K-Dense scientific-visualization](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-visualization/SKILL.md)
- Source repository: [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills)
- Source metadata version reviewed: `1.2`
- Source license: MIT
- Reviewed: 2026-09-22; entry point and selected tooling rechecked 2026-09-23

The content below is a concise adaptation for EasyPlot, not a copy of the source skill.

## What EasyPlot adopts

1. Evidence before appearance: define audience, destination, variable semantics, units, replication, transformations, missingness, uncertainty, and provenance before styling.
2. Honest encodings: use baselines, scales, log transforms, normalization, smoothing, bins, and dual axes only when their scientific meaning is explicit.
3. Accessibility by construction: use color redundantly, audit rendered contrast, distinguish missing/out-of-range values, and provide alt text plus an underlying data alternative where relevant.
4. Explicit export: keep physical dimensions, device, format, background, DPI, overwrite behavior, and provenance visible.
5. Final-size inspection: inspect the delivered image and metadata instead of treating a successful plotting command as visual QA.
6. Boundary between general principles and venue rules: label provisional choices and verify live journal guidance only when a specific destination is named.

## How it maps into EasyPlot

| K-Dense idea | EasyPlot location |
| --- | --- |
| Evidence and destination record | `SKILL.md` workflow and `templates.md` preflight |
| Honest bars, log axes, missingness, uncertainty | `SKILL.md` integrity rules and `templates.md` |
| Palette semantics and contrast | `style-guide.md` |
| Alt text and static fallback | `SKILL.md` output contract and `style-guide.md` |
| Export/provenance review | `SKILL.md` workflow and `style-guide.md` |
| Multi-panel and final-size inspection | `templates.md` and `style-guide.md` |

## Independence and remaining coverage gaps

EasyPlot's local rendering and QA implementations run without installing, loading or invoking K-Dense's skill. Its new research-analysis entry point also uses local helpers and established libraries directly. Source attribution documents intellectual/implementation provenance; it is not a runtime dependency.

Coverage checked against the reviewed main skill and selected [export-planning](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-visualization/scripts/export_plan.py) and [metadata](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-visualization/scripts/image_metadata.py) tooling:

| Area | EasyPlot local coverage | Remaining boundary |
| --- | --- | --- |
| Evidence-first figure decisions | Local rules and templates | Scientific validity still depends on the design/data |
| Static R/Python rendering | `easyplot_templates.R`, `easyplot_py.py` | Backend features are not identical |
| Metadata inspection | `easyplot_metadata.py`: common raster, PDF, SVG | No equivalent complete EPS/PS path; no exhaustive embedded-raster/glyph audit |
| Contrast and grayscale | `easyplot_palette_audit.py`, geometry-aware cue declarations | Declared cues need visual verification; no accessibility certification |
| Provenance and guarded export | Local R/Python export helpers | Per-file temporary writes do not make the whole output bundle transactional; stronger concurrent/failure-path tests remain useful |
| Journal export planning | Local dated references and explicit dimensions | No equivalent general machine-readable phase/type-aware `export_plan` CLI yet |
| Font review | Declared-face glyph preflight, mixed-script fallback, PDF font-stream inspection and explicit SVG text modes | Cmap/resources do not prove all rendered glyphs; editable SVG depends on viewer fonts; Cairo dimensions may round |
| Interactive output | Task-specific existing-stack use | Plotly/offline assets/static parity need per-task verification |
| General research analysis | Local design workflow, technical-replicate summaries, two-group inference and explicit p-value-family correction in R/Python | Advanced models and simultaneous intervals need task-specific validation; no universally validated engine |

Therefore, a user can use EasyPlot as the sole scientific workflow entry point now. Full one-for-one replacement of every upstream tool is not claimed. Uncovered operations should be implemented/verified locally as needed or explicitly reported; they do not require the user to manage another scientific skill. See `source-adoption.md` for how coverage is promoted with evidence.

## Deliberate differences

- EasyPlot is R/ggplot2-first by default and now provides an explicit Python/Matplotlib backend when the user requests Python. It keeps the user's pastel publication style. K-Dense's implementation examples target Matplotlib, Seaborn, and Plotly.
- EasyPlot does not import K-Dense's Python dependency pins, bundled CLIs, publisher snapshots, or network workflows. Static plotting uses Matplotlib/NumPy/pandas; the focused analysis helper additionally uses SciPy. R uses native statistical functions and the existing plotting stack. Packages are selected for the task, not inherited from an external skill repository.
- EasyPlot's statistical annotations remain data-backed inputs or explicitly declared analyses; visual similarity to the reference image never justifies inventing letters, stars, intervals, or p-values.

When this skill evolves, update this note if a new K-Dense principle is adopted or an adaptation is intentionally removed.
