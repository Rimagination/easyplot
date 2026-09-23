# Global maps and area-preserving projections

Use this reference for world-scale site maps, global rasters/choropleths, graticules, and projection choice. Choose the projection from the quantity the map must communicate; projection choice is part of the analytical design, not a decorative afterthought.

## Select the projection by purpose

- Use **Equal Earth** when visual comparison of continental, country, or other regional areas matters. It is a global equal-area pseudocylindrical projection (`+proj=eqearth`; EPSG:8857 is WGS 84 / Equal Earth Greenwich). It preserves relative area, not every local shape, distance, or direction.
- Use **Robinson** when a balanced, familiar world overview is wanted and neither area nor another geometric property is the primary measure. It is a compromise projection, not equal-area.
- **Equal Earth and Robinson can look quite similar without a projection error.** Both are pseudocylindrical, and Equal Earth was inspired by Robinson; their global silhouettes are related, while their geometric properties differ. Do not diagnose a wrong projection from outline similarity alone. For a side-by-side comparison, keep the source data, geographic extent, central meridian, graticule and panel dimensions consistent, but let each projection use its own projected bounds. Compare high-latitude graticule/shape changes and relative areas (for example Greenland versus Africa), not only the outer silhouette.
- If the projection is in doubt, inspect the CRS on the geometries actually plotted and the plot's target CRS—not just labels or variable names. Confirm coordinates are transformed by the intended operation (for example `sf::st_transform()` or `coord_sf(crs = ...)`), not merely reassigned a CRS with `st_crs<-`. Sanity-check the same WGS 84 control points in both targets, including `(0°, 0°)`, `(90°, 0°)`, `(0°, 60°)` and `(90°, 60°)`; the projected coordinates should reflect the declared Equal Earth or Robinson operation. For Greenwich-centered targets, these points also expose accidental central-meridian changes. Fix a demonstrated CRS/transform mismatch before changing the map styling.
- Use another projection when the scientific task requires it; explain the choice when distortion could affect interpretation. A world map is always a transformed view of the globe.
- The UN General Assembly's 4 September 2026 resolution A/RES/80/307 encourages Equal Earth and other equal-area representations when relative area matters and promotes map literacy. It does not require one projection for every map, endorse Equal Earth exclusively, ban Mercator, or change UN authoritative-boundary policy. Select a projection for the map's purpose, not as a claim of UN certification.
- Treat the projection and boundary dataset as separate decisions. State the geographic-data source and date; preserve its stated CRS and the source's treatment of disputed/undefined boundaries. Equal Earth does not make a boundary source authoritative.
- For maps where China's boundary depiction matters, follow this user's source preference: use the `world` polygons and China linework from [ggmapcn-data](https://github.com/Rimagination/ggmapcn-data), transforming the `boundary` layer from CGCS2000 as declared. Do not substitute Natural Earth Admin-0 political boundaries for this requested depiction. This is a user-directed source choice, not a claim that the repository is a UN boundary authority; record its commit and inspect the relevant boundary classes.

## Global-map visual contract

- Keep all spatial layers in a declared CRS. Exchange raw positions as longitude/latitude only when their datum is known; do not silently interpret projected x/y as degrees.
- For a global locator/site map, keep land quiet, use a common point shape and size, map the scientific class/value to colour, and keep the graticule thin and low contrast. Increase legend key size rather than inflating dense map points. For a raster or choropleth, choose sequential/diverging colour from the variable's meaning and state units, limits, centre and missing-data treatment.
- Use a deliberate graticule interval (often 30° for lines and 60° for labels); omit labels that collide with the frame or each other. The tutorial's sparse edge labels are useful, but the interval and sides should fit the final panel size.
- Decide explicitly whether graticules sit below land, over land, or between the background and analytical marks. A graticule drawn below opaque land will be hidden on land; this can be intentional. Remove automatic panel grids when drawing an explicit graticule so two systems do not overlap.
- Set a global extent explicitly. Do not rely on the observed data extent to define the world frame: clustered sites can otherwise crop the map or change the graticule. Inspect the antimeridian, both polar edges, small islands, and labels at the final aspect ratio.
- For comparisons, hold projection, extent, panel geometry, colour limits and missing-data mask constant unless a difference is part of the analysis.

## R with `sf` / ggplot2

`sf::st_crs(8857)` resolves to Equal Earth Greenwich. `coord_sf()` reprojects `sf` layers to a shared target CRS; when a layer uses plain longitude/latitude columns, declare `default_crs` rather than letting those values be read as already projected coordinates. Draw one explicit graticule and suppress the panel's automatic grid.

```r
target_crs <- sf::st_crs(8857)
graticule <- sf::st_graticule(
  lon = seq(-180, 150, by = 30),
  lat = seq(-60, 60, by = 30)
)

# Optional global frame: build the full geographic perimeter and project it
# as one continuous path. Include both meridian seams and both polar edges.
edge_lat <- seq(-90, 90, length.out = 721)
edge_lon <- seq(-180, 180, length.out = 1441)
frame_lonlat <- rbind(
  cbind(rep(-180, length(edge_lat)), edge_lat),
  cbind(edge_lon[-1], rep(90, length(edge_lon) - 1)),
  cbind(rep(180, length(edge_lat) - 1), rev(edge_lat)[-1]),
  cbind(rev(edge_lon)[-1], rep(-90, length(edge_lon) - 1))
)
frame_projected <- sf::st_sfc(sf::st_linestring(frame_lonlat), crs = 4326) |>
  sf::st_transform(target_crs)
frame_xy <- as.data.frame(sf::st_coordinates(frame_projected))
frame_xy$path_id <- 1L

ggplot2::ggplot() +
  ggplot2::geom_sf(data = world, fill = "#E9ECEF", colour = "white", linewidth = 0.15) +
  ggplot2::geom_sf(data = graticule, colour = "#D5D9DC", linewidth = 0.25) +
  ggplot2::geom_sf(data = sites, ggplot2::aes(colour = group), size = 1.1) +
  ggplot2::geom_path(
    data = frame_xy,
    ggplot2::aes(x = X, y = Y, group = path_id),
    inherit.aes = FALSE,
    colour = "#AAB0B5",
    linewidth = 0.3,
    linejoin = "round"
  ) +
  ggplot2::coord_sf(
    crs = target_crs,
    default_crs = target_crs,
    expand = FALSE,
    clip = "off"
  ) +
  ggplot2::theme_minimal() +
  ggplot2::theme(panel.grid = ggplot2::element_blank())
```

The frame is a plotting stroke, not a land or political boundary. Project its geographic perimeter once, extract the target-CRS coordinates, then draw it as one independent `geom_path()` after thematic layers. This makes its rendering path explicit and keeps one `linewidth` across all four edges; avoid also stroking country polygons along the antimeridian, which can double the sides. If a frame coincides with the panel limits, the default panel clipping cuts off half of the stroke. Set `clip = "off"` and retain sufficient white plot margin so the entire border is visible. Inspect the complete border at the final displayed size. Check both polar edges and the antimeridian for the selected projection. For Robinson, use the corresponding CRS definition (for example `+proj=robin +lon_0=0`) while retaining the same extent and data contract.

For a longitude/latitude `geom_point()` layer, `default_crs = sf::st_crs(4326)` is essential; preferably convert points to `sf` first. `coord_sf()` can otherwise interpret plain x/y columns in the projected map CRS, producing misplaced points. Refer to the installed ggplot2 and `sf` documentation for version-specific arguments.

## Python

When Python is explicitly requested, keep the same projection and data contracts. With Cartopy available, use `cartopy.crs.EqualEarth(central_longitude=0)` for equal-area mapping or `cartopy.crs.Robinson(central_longitude=0)` for a compromise overview; declare source coordinates with `transform=cartopy.crs.PlateCarree()`, set a global extent, and draw a deliberately spaced graticule. Confirm that Cartopy and the required Natural Earth/boundary data are installed before promising a runnable script. This reference does not claim a bundled EasyPlot Python world-map helper.

## Source adoption and scope

The user-provided R tutorial is a practical rendering example, not a projection standard. Its useful ideas are explicit global extent and graticules, sparse edge labels, quiet land styling, map-scale legend keys, raster and point-map variants, and a deliberately constructed outer frame. Its example data and `RdBu` choice are not defaults: choose colours from the variable semantics and never present tutorial/demo values as study data. Grid order is an aesthetic choice, not a universal rule.

Primary references:

- [UN General Assembly resolution A/RES/80/307](https://www.un.org/zh/ga/80/resolutions.shtml) and [114th plenary-meeting record](https://transcripts.un.org/en/ga/80/114?t=3519).
- [PROJ Equal Earth documentation](https://proj.org/en/stable/operations/projections/eqearth.html) and [EPSG:8857](https://epsg.org/crs/gml/id/8857).
- [ggplot2 `coord_sf()` reference](https://ggplot2.tidyverse.org/reference/ggsf.html).
- User-provided [R tutorial on Robinson world maps](https://mp.weixin.qq.com/s/5mr4BBrzgjdALivO9Nv6lw).
