# 东方色 · Dongfang classic-based candidate v0.2

For **unmodified 2kil original-colour combinations**, use `china.*` in [palette-library.md](palette-library.md). This document describes the earlier **derived** `dongfang.*` candidates; their HEX values must not be presented as original 2kil swatches. Both families remain available under distinct IDs.

An opt-in EasyPlot colour family using **classic palettes as the structural starting point**, with small Chinese-colour-inspired edits. Traditional hues from [东方色 / 2kil](https://www.2kil.com/) supply references, while established lightness trajectories and colour relationships supply the organization. The existing `publication_pastel` default remains unchanged.

User preference: preserve the successful structure of a classic palette, then tune it toward Chinese colours. Do not compose a palette merely by collecting attractive traditional names, and do not equate Chinese style with desaturation or compressed grayish ramps. Candidate v0.1 was rejected for a dull, grayish effect; v0.2 supersedes its curated schemes. Old demo outputs remain historical trials.

## Choose a scheme

| Scheme | Classic reference | Type / capacity | Edit and intended use |
| --- | --- | --- | --- |
| `danqing` 丹青 | `tab10` / Tableau 10, declared subset/order | Qualitative, up to 6 | Retain strong categorical relationships; tune toward bamboo blue, vermilion, gold, green and earth hues. General comparisons and multi-panel figures. |
| `qingya` 清雅 | `Set2`, declared subset/order | Qualitative, up to 6 | Retain soft but chromatic fills; small shifts toward silver-blue, pink, peach and green. Bars, boxes and distributions. |
| `qiushan` 秋山 | `Dark2`, declared subset/order | Qualitative, up to 5 | Orange/gold lead, with teal/green/purple as contrasts; small earth-tone edits. Ecological/environmental groups. |
| `qingci` 青瓷 | `GnBu` | Sequential, 257 stored steps | Preserve the light green → cyan → deep blue span; tune toward celadon and blue porcelain. Magnitudes and heatmaps. |
| `qinglan` 青岚 | `YlGnBu` | Sequential, 257 stored steps | Preserve light yellow → green/cyan → deep blue; slightly soften yellow and reduce the blue end's violet tendency. Richer magnitude variation. |
| `qingzhu` 青朱 | `RdBu_r` | Diverging, 257 stored steps | Preserve the light midpoint and dark endpoints; blue shifts toward porcelain and red toward vermilion. Signed changes with a meaningful centre. |
| `moyun` 墨韵 | `Greys`, unchanged | Sequential, 257 stored steps | Neutral utility option, kept outside the six recommended candidates. |

The Chinese scheme names, selections and edits are EasyPlot curation, not schemes endorsed by the source website or classic palette authors. These are candidates for visual evaluation, not colour-blind-safe certifications. The qualitative order is fixed: requesting fewer groups takes a stable prefix. Do not imply an ordered magnitude from these qualitative sequences.

### Bounded edits, with a visible reference

The registry retains the original classic colours in `classic.fill`, the reference name, and selected category indices. CIELCh hue shifts are bounded at 6° for categories and 8° for continuous ramps; target chroma is 96% of the classic. L* is retained before quantization. If a hue edit leaves sRGB, back off toward the original classic colour instead of clipping it or stripping its chroma. The builder rejects an edit above ΔE00=5 or |ΔL*|=0.3 from its classic input. These are local design budgets, not universal perceptual or accessibility thresholds. 墨韵 remains the unmodified classic gray ramp.

Render the classic reference and the candidate on identical data, geometry, group order and normalization. Show that comparison before adopting a candidate. Tiny numerical edits do not automatically improve aesthetics. Use [Matplotlib's colormap guidance](https://matplotlib.org/stable/users/explain/colors/colormaps.html) and [ColorBrewer](https://colorbrewer2.org/) for variable-type/structure references; assess the edited result itself.

## Colour roles and safeguards

- `role="fill"`: returns the curated classic-based colours, **not exact traditional source values**. Use for visible areas such as bars and boxes; keep clear axes, outlines and group labels. `dongfang_color(name)` remains the separate exact-source lookup.
- `role="line"`: qualitative schemes return explicitly derived deeper variants. The builder preserves HLS hue/saturation and reduces lightness until the quantized colour reaches 4.5:1 against white. This is an opaque swatch target; alpha, mark thickness, background and overlap still require rendered review. Do not label derived values as original traditional colours.
- Use one named group-to-colour map throughout a figure. Prefer fixed group positions and readable labels for bars/boxes. For curves or overlapping points, add group-specific line styles, markers or direct labels. A common dark outline identifies boundaries, not individual series.
- Sequential/diverging schemes are frozen 257-step classic ramps with bounded CIELCh edits. Values are derived. The odd number gives 青朱 an exact centre entry. A sequential ramp accepts `role="fill"` only; do not treat its samples as an automatically good category palette.
- Declare normalization and limits. For 青朱 use a meaningful midpoint, usually zero for signed changes, and disclose any asymmetry or clipping. Equal colour positions must keep the same numerical meaning across comparable panels.
- Missing data use a neutral swatch (`#E2E2E2`) and an explicit label or additional mark; zero and missing remain distinct. The demo marks missing cells with an X.
- More than 6/6/5 categories respectively raises an error. Use faceting or a deliberately selected larger palette; never recycle colours silently. Continuous tables can be resampled, but requesting more than 257 values does not add distinct precision.
- There is no blanket grayscale or colour-vision guarantee. Several soft fills have similar lightness. Keep measured audit warnings/notes and review existing non-colour cues. Simulations support inspection; they do not model every viewer or display.
- Fonts, final dimensions, panel alignment and caption placement remain governed by EasyPlot and the target venue. Chinese colour names belong in the palette guide or notes; they need not appear in an English manuscript figure.

## Minimal Python use

Use the existing project environment with NumPy and Matplotlib. Add the EasyPlot `scripts` directory to the project's import path once, then:

```python
from easyplot_dongfang import (
    dongfang_color, dongfang_palettes, dongfang_palette, dongfang_cmap,
)
from matplotlib.colors import TwoSlopeNorm

group_order = ["Control", "Low", "Medium", "High"]
fills = dict(zip(group_order, dongfang_palette("qingya", 4)))
lines = dict(zip(group_order, dongfang_palette("qingya", 4, role="line")))
vermilion = dongfang_color("朱砂")  # explicit alias of source name 硃砂
signed_cmap = dongfang_cmap("qingzhu")
signed_norm = TwoSlopeNorm(vmin=-2, vcenter=0, vmax=2)
```

`dongfang_palettes()` returns the catalogue and selection rationale. `dongfang_palette(..., reverse=True)` reverses the selected subset. For a continuous scheme, `n=1` selects its centre; `n>=2` samples its frozen table including both endpoints. `dongfang_cmap()` refuses qualitative schemes, and declares its missing-data colour.

## Minimal R use

Source `scripts/easyplot_dongfang.R` by its installed absolute path; it reads the same JSON registry using the installed `jsonlite` package.

```r
group_order <- c("Control", "Low", "Medium", "High")
fills <- setNames(dongfang_palette("qingya", 4), group_order)
lines <- setNames(dongfang_palette("qingya", 4, role = "line"), group_order)

# Add to an existing ggplot; group factor levels use group_order.
scale_fill_manual(values = fills, limits = group_order, drop = FALSE)
scale_colour_manual(values = lines, limits = group_order, drop = FALSE)

# A signed variable with a declared symmetric range centred on zero:
scale_fill_gradientn(
  colours = dongfang_palette("qingzhu"),
  limits = c(-2, 2), na.value = "#E2E2E2"
)
```

R uses the same scheme names, role rules, stable prefixes and lookup-table sampling as Python. Rendering engines may differ slightly in typography or antialiasing; colour identity and statistical meaning should agree. Preserve a fixed `na.value` and explicitly mark missingness in the figure or legend.

## Source and derivation record

`assets/dongfang.json` stores 320 original card entries: original names, explicit simplified aliases where supplied, pinyin as displayed, HEX, RGB, and displayed CMYK. It also stores the classic references, all curated schemes, bounded-edit metrics, derived line-colour factors and ramp provenance. Original source labels and values remain unchanged. A name alias is a lookup convenience, not a claim that all alternative traditional names are equivalent. Curated `source_names` describe hue inspiration only; they do not name the resulting HEX as an authentic original swatch.

The builder selects the original colour cards and excludes the page's initial details-panel placeholder. It verifies HEX/RGB agreement and unique source names. HEX values are interpreted as sRGB for this trial. Displayed CMYK values have no declared ICC profile and are not a print-conversion recipe.

The source footer credits Frank Lin (© 2020). At collection time, the page did not supply explicit dataset redistribution terms. Retain attribution, keep this as a local trial, and clarify permission/licensing before publicly distributing a copied colour catalogue. Do not copy the website's visual assets or interface. The shipped trial uses a fixed snapshot; plotting never contacts the website.

Classic colours are supplied through the installed Matplotlib library, whose version is recorded in the registry. ColorBrewer attribution: This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/). See the retained [ColorBrewer license](../assets/colorbrewer-LICENSE.txt) and the [upstream terms](https://colorbrewer2.org/export/LICENSE.txt). This local adaptation is not an endorsement by its source authors.

## Reproduce and maintain

- `scripts/build_dongfang.py`: maintainer tool. Existing snapshot is reused by default. `--fetch` explicitly refreshes source cards; `--overwrite` is required to replace an existing registry. Only the builder needs installed `scikit-image` for CIELCh edits and ΔE00 measurement; runtime getters do not.
- `scripts/test_easyplot_dongfang.py`: source identities/aliases, category capacities, positive integer counts, role/type guards, line contrast, lightness ordering, diverging midpoint, and caller isolation.
- `scripts/test_easyplot_dongfang.R`: R contracts and optional parity/simulation fixtures in a supplied output directory. Colour-vision simulations use the installed R `colorspace` implementation with declared parameters.
- `scripts/demo_dongfang.py OUTPUT_DIR`: source-attributed palette guide, identical-data scheme comparison, continuous examples, and three four-panel examples, with PNG/PDF manifests and artifact audits. `--stage data` prepares the three synthetic CSV files without rendering; `--stage classic` renders only the classic-versus-edited continuous and categorical comparisons; `--stage continuous` renders only the three edited heatmaps; `--stage cvd` uses the R-generated simulation fixture. Existing figure outputs require explicit `--overwrite`.
- `scripts/demo_dongfang.R OUTPUT_DIR`: a four-panel R example using the same CSV data, group order, colour identities and declared sample SD.

Demo data are synthetic. Bars show mean ± sample SD with 24 observations per group; boxes use those same observations; trajectories are illustrative values without confidence intervals. The sequential heatmaps share one normalized matrix; the diverging example uses `2 * magnitude - 1`, with a zero midpoint. All manuscript-style four-panels keep the title/caption outside the canvas; scheme labels on the guide/comparison sheets are deliberate teaching descriptors.
