# EasyPlot export and palette QA tools

Use these tools for a final-publication, journal-targeted, or existing-export audit. They report evidence for review; they do not certify scientific validity, accessibility, or journal acceptance.

## 1. File metadata audit

`easyplot_metadata.py` inspects raster dimensions, mode, alpha, ICC presence, DPI, all PDF page sizes/font resources (including nested Form XObjects), and SVG physical dimensions/text/path/image evidence.

It uses Pillow for raster files and pypdf for PDF files; SVG inspection uses Python's standard XML parser.

```text
python scripts/easyplot_metadata.py figure.png figure.pdf figure.svg \
  --min-dpi 300 --target-width-mm 180 --target-height-mm 120 \
  --require-embedded-fonts --alpha-policy forbid \
  --json --fail-on-warning
```

With a declared target width, the check uses effective raster DPI at that placement size. Otherwise it uses the lower of embedded horizontal/vertical DPI. Raw values remain in the report. The `dpi_check` property records the value and rounding allowance: one canvas pixel at the target width, or half a PNG pixels/metre step (0.0127 dpi) / JPEG density step (0.5 dpi). This avoids treating nominal 300-dpi PNG metadata stored as 299.9994 as a real deficiency. Enlarged figures and genuinely low-resolution files still warn. The checker does not inspect every embedded raster inside a PDF/SVG.

`--target-height-mm` also checks height and vertical effective DPI. `--size-tolerance-mm` defaults to 0.2 mm; raster size comparisons additionally allow pixel/DPI quantization. Missing/invalid SVG physical units warn. This tolerance is a local screening choice, not journal approval.

For an SVG audit, add `--expected-svg-text editable` or `outline`. The report distinguishes actual text candidates from referenced path evidence; zero text alone does not prove a correctly outlined figure. Inline/presentation style and local references provide structural evidence, not full CSS/filter/occlusion rendering. Inspect the vector preview.

`--require-embedded-fonts` warns when an inventoried PDF font has missing or unknown embedding evidence. `pdf_fonts` inventories each page and nested Form resources, descendant font streams and Type 3 CharProcs separately. `all_fonts_embedded` can be `true`, `false` or `null`; a file with no font resources reports `null` and needs review for outlined/rasterized/absent text. A font stream is evidence of embedding, not proof of correct glyph rendering, font licensing, editability or venue acceptance. PDF dimensions use unrotated MediaBox/UserUnit. See [typography-export.md](typography-export.md) for encoding, devices and export-mode choices.

## 2. Palette audit

`easyplot_palette_audit.py` reports exact WCAG sRGB contrast against the declared background and foreground, plus pairwise CIE L* grayscale separation.

It reuses the EasyPlot Python palette/runtime and therefore follows the Python backend's Matplotlib/NumPy environment.

```text
python scripts/easyplot_palette_audit.py \
  --palette easyplot_conditions --role graphical \
  --background FFFFFF --foreground 252A2E \
  --json --fail-on-warning
```

This is a screening tool. Pastel fills can intentionally have low contrast against white while remaining readable through dark outlines, labels, position, and raw points; the warning should trigger a visual review and redundant encoding, not an automatic palette replacement.

Specify the actual geometry and cues already present to obtain a smaller, relevant recommendation:

```text
python scripts/easyplot_palette_audit.py --palette easyplot_conditions --geometry bar --cue position-labels --cue outline
python scripts/easyplot_palette_audit.py --palette easyplot_conditions --geometry line
python scripts/easyplot_palette_audit.py --palette easyplot_lines --geometry line --cue markers --cue linestyles --cue direct-labels --foreground-placement outside-marks
```

The tool accepts `bar`, `box`, `line`, `scatter`, or `unspecified`. Cues are caller declarations, not automatically detected features. `position-labels` means each group has a distinct, readable category position. `markers` and `linestyles` mean group-specific mappings, not one shape/style shared by every group. Dark outlines alone do not identify overlapping lines.

Declare `--foreground-placement outside-marks` only after confirming foreground labels lie on the declared background, clear of the coloured marks. The default `unspecified` and explicit `on-marks` retain low foreground/mark contrast warnings. Outside labels also receive a foreground/background text contrast check (4.5:1, or 3:1 with `--role large_text`). An `outline` cue keeps the foreground/mark check active because that boundary still touches the mark.

Numbers remain unchanged when context changes: pairs below the threshold retain `below_heuristic=true` and `passes_grayscale_screen=false`. When relevant identity cues are declared, the flag becomes an informational note asking for final-size inspection. `--fail-on-warning` applies to remaining contextual warnings. It is not an accessibility pass/fail test.

The default `min_gray_delta=10` is an EasyPlot heuristic, separate from the WCAG contrast ratios. Equal-luminance grayscale is a screening view, not a simulation of a printer or colour-vision deficiency. `grayscale_hex()` is available for reproducible visual comparisons. Compact teaching cards should show only the unique flagged pairs, using their real colours and grayscale swatches plus numeric differences; avoid a red/green matrix whose colour scale adds another accessibility dependency.

## 3. Guarded export and provenance

Python figure scripts should prefer `export_figure()` when several output formats are requested. It writes each output through a same-directory temporary file, refuses implicit overwrite, and writes a JSON manifest containing physical size, DPI, backend, formats, output sizes, and caller-supplied provenance.

R figure scripts can use `easyplot_export()` after sourcing `scripts/easyplot_templates.R`. JSON manifest writing requires the `jsonlite` package. `easyplot_save()` also refuses implicit overwrite and uses an atomic temporary file for single-format output.

On permitted replacement, R uses a same-directory `file.rename()` without pre-deleting the destination. A failed rename leaves the previous figure/manifest intact; local fault-injection checks cover both paths. This follows [R's file-operation contract](https://stat.ethz.ch/R-manual/R-devel/library/base/html/files.html), checked 2026-09-23. It does not make the full multi-file bundle transactional or remove all concurrent-writer races. Network filesystem/OS rename guarantees remain platform-dependent.

Use `overwrite=True` only for a deliberate replacement or a disposable render directory. Keep raw-data identifiers, transformations, uncertainty, missingness, seed, and software versions in the `provenance` object or sidecar note.

## 4. Journal and font boundary

Metadata inspection can report dimensions and font resources. It cannot decide whether a target journal accepts a given font, minimum point size, width variant, color mode, or submission phase. When a journal is named, load the corresponding EasyPlot profile and verify current official author guidance before upload.
