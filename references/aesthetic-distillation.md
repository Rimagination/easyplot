# Aesthetic distillation: restrained journal figures

Use this reference when a user points to the supplied WeChat curation, asks for a “顶刊风格” figure, or wants the visual logic of selected paper figures distilled into a reusable EasyPlot template. It records recurring decisions observed across the original 82-entry curation and the additional source set reviewed below; it is a design reference, not a journal rulebook.

## Source boundary

The source material is the WeChat album [科研审美积累](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU4OTcyOTg0MA%3D%3D&action=getalbum&album_id=2999347064289607683), including representative entries [81](https://mp.weixin.qq.com/s?__biz=MzU4OTcyOTg0MA%3D%3D&mid=2247510180&idx=1&sn=77c400de9532c3851d97fb9fdc52c5db&chksm=fdcbf1fbcabc78ed1e9bd3bbde9605e4b892955957072f61ec1ee3deb783256179fa0459042e%23rd), [78](https://mp.weixin.qq.com/s?__biz=MzU4OTcyOTg0MA%3D%3D&mid=2247509046&idx=1&sn=d8057c03b39d3b2149303d8abafaca86&chksm=fdcbfd69cabc747f5d69271023d9bca60561f9d3d3fdf9d10dfb4eaa51ef20d58f300c0473dc%23rd), and [68](https://mp.weixin.qq.com/s?__biz=MzU4OTcyOTg0MA%3D%3D&mid=2247506635&idx=1&sn=ab5ea9931e7a47aab2eb2a791980fcf0&chksm=fdcb8394cabc0a82bb8ea3a0deb4316ef6516ab33e53d7b6a247d5e98526e2fc29665797330a%23rd).

Treat the album as a curator's selection of figures and colour schemes. The posts mix source figures, palette cards, screenshots, and promotional material; the source figure has priority for scientific inference. The collection shows recurring practices, not proof that every choice is required by Nature, Science, or another publisher. When a journal is named, read the journal profile and current official author guidance separately.

## Issue-by-issue audit status

The source set was audited issue by issue on 2026-09-22--23. Every listed article URL was opened in a browser session, its visible article content was read, and its embedded image assets were enumerated. Ordinary articles were checked through `#js_content` and all `data-src`/`src` images. Image-only WeChat cards were checked through their structured `cdn_url` records so that lazy-loaded swiper images were not mistaken for missing content. Representative contact sheets used three content images per issue; selected issues and both standalone posts were also inspected at larger size.

| Source | Listed issues/posts | Pages successfully opened | Embedded/structured images recorded | Audit consequence |
| --- | ---: | ---: | ---: | --- |
| [科研审美积累](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzU4OTcyOTg0MA%3D%3D&action=getalbum&album_id=2999347064289607683) | 82 | 82 | 2,317 | Strong source-figure material, mixed with palette sheets, screenshots, tool promotions, and repeated teaching assets |
| [TOP期刊科研绘图赏析](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkzNTU4MzA3Mg%3D%3D&scene=1&album_id=3158579626276552708) | 79 | 79 | 1,703 | Journal-labelled composite figures and source citations; useful for panel grammar and density |
| [TOP期刊科研绘图系列](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkzNTU4MzA3Mg%3D%3D&scene=1&album_id=3236941874732204038) | 89 | 89 | 1,872 | Shares all 79 article records with the preceding album and adds 10 distinct issues |
| [科研绘图品鉴](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzI1MTEwNTk0OQ%3D%3D&scene=1&album_id=4104386058702553093) | 87 | 87 | 599 | Image-card series with a strong spatial/environmental and geospatial grammar; also contains social/illustrative cards |
| [Nature palette post](https://mp.weixin.qq.com/s/mYjk6fIpxICd8oJpQfMIoQ?scene=1) and [Cancer Cell palette post](https://mp.weixin.qq.com/s/pr9v_j1Ho4UJKUALDgPtZw?scene=1) | 2 | 2 | 4 each | Four tall poster pages: palette strips are useful role hints, while the poster wrapper stays outside manuscript figures |

This audit supersedes the earlier preliminary description of the extra sources as representative-only. The counts above are provenance and coverage checks, not a claim that every embedded image is a good template. The source sets repeatedly include paper title pages, colour cards, file-browser screenshots, QR/promotional panels, generic illustrations, and repeated author assets; these must be classified before distillation.

## Additional source set reviewed

The additional sources reinforce the same boundary after the issue-by-issue audit:

- [Nature palette post](https://mp.weixin.qq.com/s/mYjk6fIpxICd8oJpQfMIoQ?scene=1) and [Cancer Cell palette post](https://mp.weixin.qq.com/s/pr9v_j1Ho4UJKUALDgPtZw?scene=1). These are curated poster pages whose scientific payloads combine experimental schematics, quantitative plots, microscopy or cytometry, distributions, and mechanistic or omics panels.
- [TOP期刊科研绘图赏析](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkzNTU4MzA3Mg%3D%3D&scene=1&album_id=3158579626276552708#wechat_redirect), 79 entries, and [TOP期刊科研绘图系列](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkzNTU4MzA3Mg%3D%3D&scene=1&album_id=3236941874732204038#wechat_redirect), 89 entries. They share 79 article records, so the second album contributes 10 distinct issues rather than 89 independent style exemplars.
- [科研绘图品鉴](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzI1MTEwNTk0OQ%3D%3D&scene=1&album_id=4104386058702553093#wechat_redirect), 87 entries. This set adds a strong spatial/environmental grammar: maps, fixed-extent small multiples, raster fields, 3D surfaces, regional statistics, and noisy time series with smooth summaries. Its image-card format also contains non-scientific illustrations and social packaging, which are excluded from the default scientific grammar.

The extra set reinforces the two-layer boundary above. A poster's paper title, DOI, tag list, palette strip, and curator branding are source metadata or teaching packaging. They are not manuscript-figure content. The useful scientific signal is the panel architecture, encoding contract, scale discipline, and final-size hierarchy visible in the embedded figures.

## The two-layer model

### Layer A: scientific figure language — reuse in EasyPlot

- **Quiet frame, informative content:** white or near-white plotting surfaces, fine structural lines, deliberate whitespace, and no ornamental gradients, shadows, or 3D effects. The data colours may be muted or saturated when the variable semantics and contrast justify them.
- **Story-first composition:** each panel has a role in a progression such as overview, comparison, distribution, spatial pattern, mechanism, or validation. A larger “hero” panel is useful when the scientific question has a clear primary result.
- **Geometry follows the variable:** use position and length for quantitative comparison, lines and ribbons for ordered trajectories, maps for spatial support, matrices or heatmaps for many-by-many structure, network or flow layouts for relationships, and image panels for observed morphology. Do not force every panel into bars or a shared grid.
- **Cross-panel encoding:** keep the same group, condition, tissue, species, or time meaning mapped to the same colour, line type, point shape, and ordering throughout the figure. A collected legend is valuable only when that meaning is genuinely shared.
- **Evidence layers:** combine raw observations, summaries or model estimates, uncertainty, reference lines, and statistical annotations in a visible hierarchy. Each layer needs a declared meaning and should remain readable at final size.
- **Semantic colour:** use a neutral for controls or references, a short categorical set for groups, sequential scales for magnitude, and diverging scales only around a meaningful midpoint. Use grey for missing or masked regions. Saturation is a decision variable, not a universal aesthetic rule.
- **Compact annotation:** lowercase panel tags, concise direct labels, local reference lines, legends or colour bars with units, and small in-panel descriptors when they help the reader decode the panel. Annotation should explain the evidence rather than compete with it.
- **Reproducible density:** complex figures may be information-dense. Preserve scale honesty, units, uncertainty definitions, sample structure, missingness, and panel alignment while managing density through hierarchy, spacing, repeated scales, and selective labelling.

### Layer B: curation packaging — keep optional and separate

The album also uses a recognisable mobile poster wrapper: a dark muted header, large white Chinese title, vertical collage, and a small source footer. This is useful for an optional presentation or teaching-card template. It should not become the default scientific figure theme: do not put a large figure title, curator watermark, article screenshot, or promotional footer inside a manuscript-ready plot.

## Distilled grammar from the additional source set

### Evidence-ladder plates

Many of the added figures are readable because their panels form an evidence ladder rather than a collection of attractive plots:

1. **Context or design:** sampling map, timeline, workflow, tissue/cell schematic, or model setup.
2. **Primary observation:** image, microscopy, cytometry, map, spectral field, or representative trace.
3. **Quantitative summary:** bars with raw replicates, distributions, point-range estimates, trajectories, or regional summaries.
4. **Validation or mechanism:** heatmap, enrichment/network, perturbation, pathway, correlation, or targeted assay.
5. **Generalization or outcome:** time horizon, scenario comparison, spatial transfer, survival/outcome, or application panel when the study supports it.

Use only the rungs supported by the data. The ordering is a planning device; a paper may begin with a hero result or omit a rung.

### Dense mechanistic and omics plates

The biomedical and materials examples repeatedly use a compact grammar: a schematic or experimental timeline anchors the top or left; image evidence and quantitative summaries sit adjacent; distributions expose replication; matrix, pathway, or interaction panels explain mechanism. Reusable decisions are:

- assign each panel one role and one guide owner before composing;
- keep the hero result visually dominant, with validation panels compact but readable;
- use raw points, interval definitions, and sample structure when a summary mark could hide them;
- reuse condition colours across bars, distributions, heatmap annotations, and schematic labels;
- keep local axes and legends when units differ; collect only genuinely shared guides;
- use panel tags and short in-panel descriptors, while leaving the figure title, caption, DOI, methods, and provenance outside the canvas.

### Spatial and environmental plates

The third album adds a distinct `map → regional summary → trajectory/model` pattern. When maps are comparable, hold projection, extent, aspect ratio, geographic boundaries, colour limits, and missing-value treatment constant. Pair a map with a distribution, trend, or uncertainty panel only when the relationship is explicit. Use sequential scales for magnitude, diverging scales around a declared midpoint, and a muted missing mask. Treat rainbow ramps, decorative basemaps, unlabelled 3D surfaces, and independently rescaled small multiples as review warnings.

### Study-area locator maps

The user-provided archive `「研究区位图」文件夹.zip` was reviewed on 2026-09-23 as a layout reference: all 139 raster entries were scanned in contact sheets and 17 representative maps were inspected full-size; the single SVG was inventoried but not visually reviewed. Recurrent useful grammar:

- **Separate location from evidence.** Distinguish a locator inset (where the study area sits in a broader region) from a detail inset (a larger view of a hard-to-read local feature). Keep the study map or thematic map group dominant. When multiple thematic panels share one footprint, use one shared locator for the group and repeat the same study-area cue across panels; repeat a locator only when different regions need separate orientation.
- **Make the study area easy to find.** Mark it on the overview and detail map with the same clear box, boundary outline, or restrained fill; use a short connector only when the spatial link is not self-evident. Keep this boundary cue distinct from the thematic data encoding. Avoid stacking competing fills, halos, arrows, and symbols for the same region.
- **Choose a quiet, purposeful basemap.** Use pale neutral land/water and fine contextual boundaries for ordinary locator or site maps. Add subdued hillshade/relief when terrain explains the sampling pattern; use satellite or land-cover imagery when its texture is evidence. Otherwise mute or desaturate imagery so the study boundary and data remain foremost. Avoid stacking prominent imagery, administrative borders, roads, labels, graticules, and points without a clear role.
- **Compose in a clear hierarchy.** Align locator, main map, and any related profile/statistics panels to a deliberate grid. Reserve a quiet corner or adjacent column for the locator and guides; do not cover study sites or key boundaries. For multi-map comparisons, keep projection, geographic extent, panel aspect, and thematic meaning consistent. Add photographs only when they document the mapped environment or sites, using matching panel/site labels rather than decorative callouts.
- **Keep map furniture selective.** Show coordinate ticks or a light graticule when geographic position matters, a scale bar when local distance matters, and a north arrow only when orientation is not already clear. A globe inset is optional, not a default ornament. Label only places needed to orient the reader; inspect label collisions and all inset edges at final size.

These are layout and visual-hierarchy cues, not new palette or basemap-source requirements. Preserve the selected EasyPlot palette and the applicable China/world data-source, boundary, CRS and licensing rules. The archive is a curated example set, not evidence that every shown map, basemap, projection, or decoration is suitable for a new study.

For time-series panels, show the noisy observations and the smooth/model summary as separate visual layers, state whether the smooth is a fit or a descriptive guide, preserve gaps, and keep reference periods or shaded windows explainable.

### Palette distillation

The source posters make palettes easy to copy, but their hex/RGB strips are attached to particular figures. Distil roles first: control/reference, active treatment, comparison group, observed image, continuous magnitude, midpoint, missing, and annotation. Select the final colours after the geometry and semantics are known, then check contrast, grayscale, and colour-vision readability. A source palette may seed a role mapping; it does not override journal typography, data semantics, or accessibility checks.

## What recurs across the full collection

The strongest commonality is a workflow for building a scientific figure, not one universal palette:

| Recurrent decision | How to apply it |
| --- | --- |
| Start with the scientific message | Write the claim and panel roles before selecting colours or chart types. |
| Use a figure as a sequence | Move from system/context or sampling, to quantitative evidence, to mechanism, validation, or application when the study requires it. |
| Build a visual vocabulary | Reuse colours, order, line types, symbols, scale direction, and terminology across panels. |
| Let evidence determine density | Use a simple single-panel chart for a simple comparison; reserve dense plates for studies with multiple evidence layers. |
| Align comparable quantities | Share axes, projections, colour limits, reference lines, and panel widths when readers must compare them. |
| Keep local decoding close to the data | Put a colour bar, legend, scale bar, or short descriptor beside the panel that needs it; collect guides only when their meaning is shared. |
| Use a final-size hierarchy | Panel labels, axes, data marks, annotations, and footnotes need deliberate size and weight differences. |

The early entries repeatedly present colour cards with RGB values. Treat these as palette references attached to a particular figure, not as a command to use the same colours for every experiment. The collection also contains high-saturation, low-saturation, strongly separated, weakly separated, colour-vision-friendly, and colour-vision-unfriendly examples; EasyPlot should audit the choice against the data meaning and audience.

## Reusable visual grammar

### Composition

1. Decide the figure question and the role of every panel before styling.
2. Align panel plot regions, not only their outer boxes. Keep shared x/y scales when comparison is the point.
3. Use a hero-support layout when one result is primary; use a balanced grid when panels are peers.
4. Collect a legend or colour bar only when the encoding and scale are genuinely shared. Otherwise keep guides local.
5. Keep citations, figure titles, captions, methods, and provenance outside the image by default.

### Lines, points, and intervals

- Make data marks visually stronger than structural lines: data lines and intervals may be slightly darker or heavier than axes.
- Use small, semi-transparent raw points to reveal replication without turning the panel into noise.
- Put significance labels above the supplied uncertainty extent with scale-aware clearance; do not let labels determine the scientific conclusion.
- Keep reference or zero lines distinct but quiet. A log axis, regression line, or mask must be explained by the data contract or caption.

### Typography

- Use the selected journal profile for Latin, Greek, mathematics, and non-Latin scripts; the curated figures are not a font specification.
- Keep panel tags short, lowercase, and easy to find. Use italic text for Latin species names explicitly.
- Put units and transformations in axis labels. Use superscripts, subscripts, and Greek glyphs with a verified font fallback.
- Inspect the rendered figure at final physical size. Small text that looks elegant in a large preview is still a failure if it cannot be read at submission size.

### Colour roles

Use role names rather than assigning colours by factor order:

```r
easyplot_roles <- c(
  ink = "#252A2E",
  frame = "#5E666D",
  control = "#D8DDE2",
  rose = "#D8898D",
  blue = "#6C9DC5",
  gold = "#D6A15A",
  heat_cold = "#4F8DBA",
  heat_mid = "#F7F3EE",
  heat_warm = "#C87973",
  missing = "#D9D9D9"
)
```

These are starting roles, not a mandatory palette. Select the colour family after identifying whether the variable is categorical, sequential, diverging, or cyclic. Prefer fewer related hues when categories are few; allow a broader palette only when the figure has a defensible semantic mapping. Check contrast and grayscale; add shape, linetype, direct labels, or panel separation when colour alone carries too much meaning.

## Template candidates

These are composition archetypes that can sit on top of an existing geometry template:

| Archetype | Use when | Visual signature |
| --- | --- | --- |
| `journal_plate` | Several peer panels form one manuscript figure | White canvas, aligned grid, lowercase tags, shared typography, outside caption |
| `hero_support` | One result is primary and the rest explain or validate it | Larger main panel, compact support panels, one restrained guide system |
| `map_matrix` | Spatial layers or map comparisons are the scientific argument | Same extent/projection, explicit missing mask, local colour bars, aligned map frames |
| `omics_plate` | Heatmaps, differential plots, distributions, and pathway summaries form one evidence chain | Reused condition colours, explicit row/column annotation, local scales, carefully limited density |
| `data_plus_mechanism` | Quantitative results need a mechanism schematic | Data panels keep evidence styling; schematic uses a separate neutral vocabulary |
| `dense_mechanistic_plate` | A study combines design, primary observations, quantification, and mechanism/validation | Evidence-ladder roles, hero-support hierarchy, repeated semantic encodings, local guide ownership |
| `spatial_evidence_plate` | Maps must be read together with regional summaries, trajectories, or model outputs | Fixed projection/extent contract, deliberate fixed-aspect exception, explicit colour limits and missing mask |
| `source_figure_card` | A teaching or presentation artifact needs a source figure with citation metadata | Optional outer wrapper with title/DOI/palette/source note; never the manuscript-ready default |

Do not choose an archetype only because it resembles a source image. The panel roles and data contract must justify it.

## Reject by default

- publisher logos, article screenshots, watermarks, and copied source assets;
- the phrase “Nature style” as a substitute for a specific journal profile or design rationale;
- large in-figure titles, captions, citations, or promotional text in manuscript figures;
- rainbow maps used as a default continuous scale, arbitrary gradients, excessive categorical hues, and decorative shadows;
- a pastel palette that reduces contrast or hides uncertainty;
- shrinking panels to make a caption fit inside the exported image.

## Preflight prompts

Before rendering, answer:

- What is the one-sentence message of the figure?
- What does each panel contribute to that message?
- Which visual variable is semantic: position, length, colour, shape, line type, or texture?
- Are controls, missing values, uncertainty, and raw replicates visually distinguishable?
- Are the final width, fonts, panel labels, legends, colour bars, and outside caption consistent with the selected journal profile?

## Style-extraction protocol

When the input is a reference image or an album post, record the following before writing R code:

1. **Source layer:** source journal figure, palette card, poster wrapper, or screenshot. Ignore wrapper branding when extracting scientific rules.
2. **Panel roles:** what question each panel answers and how the reader moves between panels.
3. **Data geometries:** bar, point, line, interval, map, matrix, network, image, schematic, or a combination.
4. **Encoding contract:** which variable controls position, size, colour, shape, line type, fill, or texture; verify that the same meaning persists across panels.
5. **Scale and reference:** linear/log axes, common limits, baselines, thresholds, projections, colour limits, and masks.
6. **Evidence layers:** raw data, summary/model, uncertainty, statistical result, annotation, and citation/provenance.
7. **Typography and output:** panel tags, scientific labels, font roles, final physical size, and what belongs outside the image.

Return a style/layout specification when the source data are absent. Do not infer values or claim to have recreated a paper figure from a screenshot alone.
