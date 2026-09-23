# Maintainer helper: export already-installed, versioned R palette data.
# Input contains parsed colour literals only. No remote R source is evaluated.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Usage: build_palette_sources.R ggsci-input.json output.json")
if (file.exists(args[[2L]])) stop("Refusing to overwrite R source export")
ggsci <- jsonlite::read_json(args[[1L]], simplifyVector = FALSE)
records <- list()
add <- function(x) records[[length(records) + 1L]] <<- x
for (p in ggsci) {
  if (p$kind != "qualitative") {
    # Matches the declared ggsci RGB generator: Lab spline, 512 fixed samples.
    mat <- grDevices::colorRamp(unlist(p$colours), space = "Lab", interpolate = "spline")(
      seq(0, 1, length.out = 512L))
    p$anchors <- p$colours
    p$colours <- unname(grDevices::rgb(mat[, 1], mat[, 2], mat[, 3], maxColorValue = 255))
    p$colour_names <- NULL
    p$notes <- "Original ggsci anchors retained; frozen 512-step Lab/spline table follows ggsci's scale generator. Arbitrary n samples this table."
  }
  add(p)
}
info <- RColorBrewer::brewer.pal.info
for (name in rownames(info)) {
  max_n <- info[name, "maxcolors"]
  variants <- setNames(lapply(3:max_n, function(n) RColorBrewer::brewer.pal(n, name)), as.character(3:max_n))
  kind <- c(qual = "qualitative", seq = "sequential", div = "diverging")[[info[name, "category"]]]
  add(list(id = paste0("brewer.", name), label = name, family = "brewer", kind = kind,
      colours = RColorBrewer::brewer.pal(max_n, name), native_sizes = variants,
      selection = "native", tags = c("classic", "native-size-schemes"),
      cvd = list(status = if (info[name, "colorblind"]) "conditional" else "not_assessed",
                 evidence = "https://colorbrewer2.org/",
                 note = "RColorBrewer family-level colorblind metadata; suitability varies with class count, geometry and background."),
      source = list(url = "https://colorbrewer2.org/", version = as.character(packageVersion("RColorBrewer")),
                    license = "ColorBrewer Apache-style license; see assets/colorbrewer-LICENSE.txt"),
      notes = "Exact native n-class schemes for n >= 3; n=1/2 uses the first n of the 3-class scheme. No automatic continuous interpolation."))
}
for (name in c("magma", "inferno", "plasma", "viridis", "cividis", "rocket", "mako", "turbo")) {
  # Keep the exact installed viridisLite output; don't recompute it in Python.
  values <- toupper(substr(getExportedValue("viridisLite", name)(256L), 1L, 7L))
  add(list(id = paste0("viridis.", name), label = name, family = "viridis", kind = "sequential",
      colours = values, selection = "lut", tags = c("classic", "continuous"),
      cvd = list(status = if (name == "turbo") "not_recommended" else "reported",
                 targets = if (name == "turbo") NULL else c("protan", "deutan"),
                 evidence = "https://sjmgarnier.github.io/viridisLite/",
                 note = if (name == "turbo") "Rainbow-like convenience option; excluded from the CVD-friendly shortlist; lightness is nonmonotonic."
                        else "Upstream describes the viridis family as robust for common red-green deficiencies and grayscale. Tritanopia performance is weaker; inspect the actual figure and retain redundant cues."),
      source = list(url = "https://sjmgarnier.github.io/viridisLite/", version = as.character(packageVersion("viridisLite")), license = "MIT")))
}

# Named HCL palettes are sourced from colorspace's actual palette constructors;
# the native-size tables are frozen so both runtime backends share exact HEX.
hcl_specs <- list(
  list(id = "blues3", label = "Blues 3", kind = "sequential", constructor = colorspace::sequential_hcl),
  list(id = "ylgnbu", label = "YlGnBu", kind = "sequential", constructor = colorspace::sequential_hcl),
  list(id = "green_brown", label = "Green-Brown", kind = "diverging", constructor = colorspace::diverging_hcl),
  list(id = "blue_red3", label = "Blue-Red 3", kind = "diverging", constructor = colorspace::diverging_hcl),
  list(id = "set2", label = "Set 2", kind = "qualitative", constructor = colorspace::qualitative_hcl),
  list(id = "dark3", label = "Dark 3", kind = "qualitative", constructor = colorspace::qualitative_hcl)
)
for (spec in hcl_specs) {
  sizes <- if (spec$kind == "qualitative") 3:8 else 3:12
  native <- setNames(lapply(sizes, function(n) {
    spec$constructor(n, palette = spec$label)
  }), as.character(sizes))
  cvd <- if (spec$id %in% c("green_brown", "blue_red3")) {
    list(status = "reported",
         evidence = "https://stat.ethz.ch/R-manual/R-devel/library/grDevices/html/palettes.html",
         note = "Base R identifies this diverging scheme as colourblind-safe; choose a meaningful centre and inspect the rendered figure.")
  } else if (spec$id == "dark3") {
    list(status = "conditional",
         evidence = "https://colorspace.r-forge.r-project.org/articles/hcl_palettes.html",
         note = "colorspace recommends Dark 3 for up to five groups; HCL construction is not itself a CVD validation. Prefer n <= 5 and inspect the rendered marks.")
  } else {
    list(status = "not_assessed",
         evidence = "https://colorspace.r-forge.r-project.org/articles/hcl_palettes.html",
         note = "HCL construction balances perceptual weight for its data type; this named palette has no scheme-specific CVD validation. Inspect the rendered marks.")
  }
  scheme_tags <- c("hcl", "candidate")
  if (spec$id %in% c("green_brown", "blue_red3", "dark3")) scheme_tags <- c(scheme_tags, "cvd-shortlist")
  add(list(id = paste0("colorspace.", spec$id), label = paste0(spec$label, " / HCL"),
      family = "colorspace", kind = spec$kind, colours = native[[as.character(max(sizes))]],
      native_sizes = native, selection = "native", tags = scheme_tags, cvd = cvd,
      source = list(url = "https://colorspace.r-forge.r-project.org/articles/hcl_palettes.html",
                    version = as.character(packageVersion("colorspace")), license = "BSD-3-Clause"),
      notes = "Generated by colorspace's named HCL constructor; exact HEX for n = 3 through the listed native maximum is frozen."))
}
jsonlite::write_json(records, args[[2L]], pretty = TRUE, auto_unbox = TRUE)
cat("Exported", length(records), "core R records\n")
