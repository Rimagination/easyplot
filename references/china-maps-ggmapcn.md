# China maps with `ggmapcn`

Read this reference for China maps in R, especially national point maps, environmental overlays, nested national-boundary buffers, projected coordinates, or a South China Sea inset. It records the workflow tested in EasyPlot's 156-project aridity map and 5,864-site prediction map.

## Default decision: site map before generic spatial templates

When rows have longitude and latitude and represent projects, stations, samples or prediction sites, use the single-map `china_site_map` design implemented by [`easyplot_china_site_map()`](../scripts/easyplot_china_map.R). This is the default visual baseline distilled from the 5,864-site prediction figure.

- Keep the national map as one hero panel. Add more map panels only for an explicit comparison.
- Draw equal-sized points over neutral land. Use point fill for the requested class or value.
- Reserve province fills for genuine province-level estimates or totals.
- Never replace an available site table with a synthetic province index. If the real data path or required fields are unresolved, stop with the missing input. A user-requested demonstration belongs in a separate, visibly synthetic export.
- Do not route a single national result through `spatial_small_multiples` or `spatial_evidence_plate`.

The helper is a reusable implementation baseline. A manuscript deliverable should keep its consequential parameters visible; inline or adapt the helper when the recipient requires a fully self-contained script.

## Authority and version boundary

- Prefer the installed function signatures and the current [official documentation](https://rimagination.github.io/ggmapcn/) over historical examples. The package and documentation were both version 0.3.0 when checked on 2026-09-23.
- `geom_mapcn()` supplies province, city or county polygons; `geom_boundary_cn()` supplies independently styled mainland, coastline, ten-segment, SAR, undefined and optional province boundaries; `geom_buffer_cn()` builds projected buffers; `coord_proj()` accepts longitude/latitude limits for a target projection; `geom_loc()` transforms point coordinates.
- Large geodata files may be external. `check_geodata()` searches `local_dirs`, package `extdata`, then the per-user cache and can return `NA` when retrieval fails. For reproducible work, preflight the exact file, keep a local cached copy when needed, and stop with the unresolved path rather than drawing a partial map.
- The package describes its China administrative boundaries as derived from Tianditu data. A rendered research map does not by itself establish regulatory approval, an examination number, or compliance for public dissemination. Check the current official standard-map and map-review requirements for the actual publication context.

## Data contract before drawing

Keep one row per analytical site with a stable identifier, longitude, latitude, displayed class/value, coordinate source, and geolocation grade. Treat WGS84 longitude/latitude as the exchange format unless the source explicitly declares another CRS.

Audit and report:

- total records, valid-coordinate records, unique project IDs and unique coordinate pairs;
- missing, non-finite and out-of-range coordinates;
- duplicate IDs separately from colocated projects;
- the number of points covered by the main viewport and by the inset;
- any imputation or fallback location. Province/city centroids may support exploratory mapping only when disclosed; do not present them as measured station coordinates.

The legend's `n` should describe the plotted analytical units. If several projects share coordinates, also record the unique-coordinate count in the sidecar; overlapping symbols must not silently change the sample size.

## Projection and extent contract

Use one visible CRS parameter for polygons, boundaries, buffers, points and coordinates. EasyPlot's national equal-area default is:

```r
CHINA_ALBERS <- paste(
  "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105",
  "+datum=WGS84 +units=m +no_defs"
)
```

Use Albers when area comparison or an environmental surface matters. The package's azimuthal-equidistant default remains reasonable for general national locator maps. Never mix layers transformed to different CRSs.

With projected layers, retain longitude/latitude view limits through either:

```r
coord_sf(
  crs = CHINA_ALBERS,
  default_crs = sf::st_crs(4326),
  xlim = c(72, 142), ylim = c(12, 56),
  label_axes = "--EN", expand = FALSE
)
```

or `ggmapcn::coord_proj(crs = CHINA_ALBERS, xlim = ..., ylim = ...)`. Use one method per panel and inspect the rendered extent.

For the established vertical national layout, start with:

- main map: 72–142°E, 12–56°N;
- South China Sea inset: 105–125°E, 0–25°N;
- inset: lower right, about 29% of the composition height.

These are working viewports, not universal crop rules. Before export, assert that every coordinate of the complete China geometry and every plotted site lies in the main viewport or inset. This catches silent loss of islands, segment lines or southern observations.

## Layer order and boundary treatment

The stable order is outer buffer, inner buffer, administrative fill, authoritative boundary layers, then research data:

```r
ggplot2::ggplot() +
  ggmapcn::geom_buffer_cn(
    mainland_dist = 40000, crs = CHINA_ALBERS,
    color = NA, fill = "#D2D5EB"
  ) +
  ggmapcn::geom_buffer_cn(
    mainland_dist = 20000, crs = CHINA_ALBERS,
    color = NA, fill = "#BBB3D8"
  ) +
  ggmapcn::geom_mapcn(
    admin_level = "province", crs = CHINA_ALBERS,
    fill = "white", color = "grey80", linewidth = 0.2
  ) +
  ggmapcn::geom_boundary_cn(crs = CHINA_ALBERS)
```

Buffer distances are metres only when the selected projected CRS uses metres. The common `sf` warning that attributes are assumed spatially constant can occur during buffering; inspect the geometry rather than suppressing an unfamiliar warning. Buffer polygons surround irregular geometry, so draw the filled China polygon above them to mask the inward portion. The historical package notes also describe different visual behaviour for the ten-segment-line buffer; always inspect both mainland and inset.

For a restrained publication outline, use conventional map semantics: dark grey for land and administrative boundaries, blue for coastlines, and pale neutral/blue halos only to improve edge separation. The lavender colours belong to the nested buffer fills and should not replace the actual boundary colours. Keep coastline, ten-segment, SAR and undefined-boundary line types distinct, and do not let a halo erase legally or scientifically meaningful line categories.

## South China Sea inset

Build the inset from the same `map_layers()` and data layer as the main map, changing only viewport, point size, guides and furniture. This prevents mismatched coastlines, colours or projections.

EasyPlot's established presentation is:

- lower-right inset with its own fine frame;
- no duplicated legend, graticule labels or axis titles;
- plain, uppercase `NANHAI\nZHUDAO` near the lower-right whitespace;
- label placement checked against the actual coastline and point layer;
- the inset included in full-geometry and full-site coverage assertions.

The label is a presentation convention requested for this workflow. Preserve a different project or journal convention when one is already established.

## Graticules and map furniture

For a national research map, use light projected graticules and decimal-degree labels on the left and bottom edges when they help read geographic position. Derive hemisphere suffixes from signs when a viewport crosses zero.

In ggmapcn 0.3.0, `annotation_graticule(xlim, ylim)` uses those ranges both to choose which meridians/parallels exist and to build their full line geometries. They are geographic generation bounds, not an independent list of tick labels. Match them to the panel's complete unprojected viewport; use `lon_step` and `lat_step` for spacing:

```r
main_xlim <- c(72, 142)
main_ylim <- c(12, 56)

ggmapcn::annotation_graticule(
  xlim = main_xlim, ylim = main_ylim, crs = CHINA_ALBERS,
  lon_step = 10, lat_step = 10,
  sides = c("left", "bottom")
)
```

This creates meridians at 80–140°E and parallels at 20–50°N, with each line spanning the full opposite viewport dimension before projection. Do not pass `c(80, 130)` and `c(20, 50)` when the intent is merely to choose those tick values: that clips every graticule to an inner rectangle, leaving partial lines. If a custom sparse set of graticule values is needed, filter the generated geometry or build the desired full-extent lines explicitly; keep the map viewport unchanged.

Do not add a title, north arrow or scale bar by default. The figure title and methodological explanation belong in the external caption, and labelled graticules already carry orientation. When the user or venue requires map furniture, current ggmapcn provides `annotation_compass()` and `annotation_scalebar()`; for a projected China map use `which_north = "true"` when true north is intended. Inspect placement after adding either element. The 2025 tutorial notes that a north arrow and graticules are usually redundant and were combined there for demonstration.

## Thematic-map panels distilled from research figures

Selected figure sets in the National Science Review drought-threshold paper (Figs. 1–4) and the Nature Communications land-carbon paper (Figs. 1–4) support these context-specific patterns:

- For comparisons across datasets, scenarios or periods, hold projection, geographic extent, raster resolution, missing-data mask and colour limits constant wherever the mapped quantity is comparable. Use one shared legend for a genuinely common scale.
- Match the colour scale to the variable: sequential for ordered thresholds, diverging with a clear zero midpoint for signed change, and a labelled two-dimensional key only when two variables are jointly encoded.
- Add map stippling or dots only for a stated analytical criterion (for example, a significance or multi-source agreement rule); describe the criterion in the caption. Keep missing cells visually distinct from valid low values.
- Pair maps with small distributions or response profiles only when those panels answer a related question. Align them consistently, and move them outside the map when the inset becomes unreadable at final size.
- The reviewed global thematic maps omit graticules and rely on coast outlines and repeated map frames for orientation. Treat that as a useful low-clutter option for global raster comparisons, not a rule for locator or navigation maps.

These papers are design references, not authority for EasyPlot's projection or map-data choices. Their exact projections and colour specifications were not inferred from appearance; preserve the study's own data contract and cite the source of the basemap.

## Research points, values and legends

- For a location map, use equal-sized solid circles. Encode only the requested classification or continuous value; do not add capacity, source quality or model status as size/shape merely because those columns exist.
- Project point `sf` objects to the same CRS before plotting, or use `geom_loc()` with declared longitude and latitude columns.
- Keep the inset point size slightly smaller while preserving the same scale and colour meaning.
- Put total `n` in the legend title or a compact in-panel label. For categorical maps, include per-class `n`; for continuous predictions, state transformation and complete untrimmed range in the sidecar.
- Use a stable, named palette. Keep missing values visually distinct from zero and from values outside the model domain.
- A model-prediction map should record training `n`, prediction-frame `n`, extrapolation count and whether extrapolation status is visually encoded. Equal symbols can remain appropriate when the map's question is spatial pattern rather than model-domain diagnostics.

## Optional Global Aridity Index workflow

When using the Global-AI_ET0 annual v3 raster used in the photovoltaic workflow, keep the raster path, scale factor and extraction rule visible. The tested raster stores values requiring multiplication by `0.0001`. If the study has adopted the common five-class scheme, declare the exact intervals:

```text
Hyper-arid       AI < 0.03
Arid             0.03 <= AI < 0.20
Semi-arid        0.20 <= AI < 0.50
Dry sub-humid    0.50 <= AI <= 0.65
Humid            AI > 0.65
```

Do not silently replace zero or missing raster cells. A nearest-positive fallback within a declared maximum distance can be used only as an audited extraction rule; retain original cell value, fallback distance and method for every affected site.

## Export and final checks

A useful national-map starting size is 200 × 125 mm at 600 dpi, exported to PNG plus a verified vector format. Keep title and long notes outside the image. Write a UTF-8 caption/manifest containing package version, boundary source, projection string, viewports, buffer distances, input counts, unique coordinates, exclusions/fallbacks, palette or colour transform, physical dimensions and alt text.

Before delivery, inspect the final raster and verify:

1. complete China geometry is represented by the main map plus inset;
2. all plotted sites fall in at least one viewport and the displayed `n` matches the audited rows;
3. province lines do not obscure national, coastline, ten-segment, SAR or undefined boundaries;
4. buffers are visible outside the filled land geometry and do not cover evidence;
5. inset frame, `NANHAI ZHUDAO` label and points do not collide;
6. longitude/latitude labels are present, correctly suffixed and unclipped;
7. legends describe only displayed encodings and do not cover sites;
8. no title, north arrow, scale bar, capacity encoding or duplicated legend remains unless explicitly requested;
9. PNG/PDF dimensions, fonts, file sizes and sidecars are valid.
10. a site-level input remains a point map; no `Synthetic index (illustrative)` label or invented province fill appears in a data-backed result.

## Sources reviewed

Accessed 2026-09-23:

- [`ggmapcn` repository](https://github.com/Rimagination/ggmapcn) and [official 0.3.0 documentation](https://rimagination.github.io/ggmapcn/), including current references for `check_geodata()`, `geom_mapcn()`, `geom_boundary_cn()` and `geom_buffer_cn()`.
- [National Science Review: “Global variations in critical drought thresholds that impact vegetation”](https://academic.oup.com/nsr/article/10/5/nwad049/7057875?login=false), full text and Figs. 1–4 via [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC10103823/); [Nature Communications: “Increased maximum carbon release offsets half of the growth trend in annual land carbon sink”](https://www.nature.com/articles/s41467-026-77462-8), publisher PDF pp. 3–6, Figs. 1–4 and captions. Accessed 2026-09-23.
- WeChat: [“ggmapcn | 一款绘制中国标准地图的R包”](https://mp.weixin.qq.com/s/3NVZ6mksJktiWUS0DEeU7Q), 2024-11-09.
- WeChat: [“ggmapcn | R包更新与答疑（一）”](https://mp.weixin.qq.com/s/ZpaBHjo8mPUxVMX5wwc0Qg), 2024-11-25.
- WeChat: [“ggmapcn | 新增指北针与比例尺元素”](https://mp.weixin.qq.com/s/1m3l8iG5e2QGE23ITMAzgg), 2025-09-27.

The official current documentation and installed signatures govern code. The historical posts contribute design rationale, version history and known cartographic pitfalls.
