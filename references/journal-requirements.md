# Journal figure requirements

These are dated planning snapshots for figure construction. They are not acceptance guarantees. Journal families, article types, and submission phases can use different rules; when the user names a target, check the exact journal's current official author page immediately before submission and record the page date in the sidecar notes.

All sizes below are final physical dimensions in millimetres unless stated otherwise. Do not design at an arbitrary pixel size and scale later.

## Profile status

- `verified`: the cited official page was readable and the value was taken from it during the review date below.
- `provisional`: the value is useful for planning, but the current official page was blocked, ambiguous, or only indirectly recoverable. Do not call it compliant.

## Nature — flagship primary-research planning profile

**Profile ID:** `nature`

**Status:** verified against the Nature Research Figure Guide and Nature final-submission guidance on 2026-09-22.

| Parameter | Default planning value |
| --- | --- |
| Single-column width | 89 mm |
| One-and-a-half-column width | 120–136 mm |
| Double-column width | 183 mm |
| Maximum figure height | 170 mm, leaving room for the legend |
| Ordinary text at final size | 5–7 pt |
| Multipart panel labels | 8 pt bold upright `a`, `b`, `c` |
| Line/stroke range | 0.25–1 pt at final size |
| Figure font | Arial or Helvetica; keep one family throughout |
| Non-Latin scripts | Verify the target article's CJK/other-script font and embedding rule; do not infer it from the Latin rule |
| Colour | RGB is recommended for submitted artwork |
| Output preference | Editable vector for line art and text; raster images at the required final resolution |

Nature's formatting guide also rounds the standard widths to 90 mm single-column and 180 mm double-column. Keep both values available as an explicit `nature_rounded` variant when matching a particular Nature Portfolio page; do not mix the variants inside one figure.

Useful implementation defaults:

```r
journal_profile <- "nature"
FIG_WIDTH_MM <- 89       # use 183 for a double-column figure
FIG_HEIGHT_MM <- 120     # choose from the evidence; stay <= 170 mm
TEXT_PT <- 6
PANEL_TAG_PT <- 8
LINE_PT <- 0.5
FONT_FAMILY <- "Arial"
```

Sources:

- [Nature Research figure guide: building and exporting figure panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
- [Nature final submission guidance](https://www.nature.com/nature/for-authors/final-submission)
- [Nature initial submission guidance](https://www.nature.com/nature/for-authors/initial-submission)
- [Nature formatting guide](https://www.nature.com/nature/for-authors/formatting-guide)

## Science — AAAS planning profile

**Profile ID:** `science`

**Status:** provisional as of 2026-09-22. The official Science author pages were reachable by URL but returned a Cloudflare verification page in the browser session, so the exact dimensions were not independently re-read from the current page.

The following values are retained as planning values reported by a current secondary digest that attributes them to the Science revised-manuscript instructions:

| Parameter | Provisional planning value |
| --- | --- |
| One-column width | 57 mm |
| Two-column width | 121 mm |
| Three-column/full width | 184 mm |
| Maximum height | Not recorded; verify for the target article type |
| Minimum text size | 5 pt after reduction |
| Typical text size | About 7 pt after reduction |
| Minimum symbol size | 6 pt |
| Minimum line width | 0.5 pt |
| Font guidance | Helvetica preferred in the accessible Science-family author guidance; verify the main Science guide |
| Non-Latin scripts | Verify the target article's CJK/other-script font and embedding rule; do not infer it from the Latin rule |
| Output planning | Prefer editable vector for line art; use TIFF or another accepted raster format for image-heavy panels |

Use this profile to size a draft, then recheck the live Science instructions before submission. Do not silently convert the provisional values into a compliance claim.

```r
journal_profile <- "science_provisional"
FIG_WIDTH_MM <- 57       # use 121 or 184 for wider layouts
FIG_HEIGHT_MM <- 100     # provisional; verify the target article's height rule
TEXT_PT <- 7
MIN_TEXT_PT <- 5
MIN_SYMBOL_PT <- 6
MIN_LINE_PT <- 0.5
FONT_FAMILY <- "Helvetica"
```

Sources and verification notes:

- [Science instructions for preparing a revised manuscript](https://www.science.org/content/page/instructions-preparing-revised-manuscript) — official source to recheck; access was blocked by Cloudflare during this snapshot.
- [Science-family author guidance with figure scaling and legibility rules](https://spj.science.org/page/research/for-authors/) — official AAAS Science Partner Journal guidance, useful for common figure conventions but not a substitute for the main Science page.
- [Secondary digest reporting the 57/121/184 mm planning widths](https://scifigure.org/zh/journal-figure-requirements) — planning reference only; not a primary source.

## Applying a profile in EasyPlot

When the user asks for a journal-specific figure:

1. Identify the exact journal, article type, submission phase, and width variant.
2. Load the profile and write its status (`verified` or `provisional`) into the script or sidecar note.
3. Set the physical width first, then choose a height that preserves the evidence and respects the profile's maximum when known.
4. Set text and line sizes at final output size. Inspect a rendered PNG/PDF at that size; do not rely on a zoomed viewer.
5. Prefer vector export for plots and editable text. Use raster output only when the target or embedded image content requires it.
6. Preserve a copy of the official source URL, access date, selected values, and any unresolved rule in the delivery notes.

## Extending the registry

Add a new profile only when a current official author page or publisher guide has been checked. Keep the profile small: final widths, height limits, text/line constraints, color or format rules that affect plotting, source URL, access date, and verification status. Do not turn a remembered journal convention into a permanent rule.
