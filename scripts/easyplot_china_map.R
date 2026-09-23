# EasyPlot China-wide site and prediction map baseline.
# Source this file while building a project script, or inline/adapt the function
# when the final deliverable must be fully self-contained.

easyplot_require_china_packages <- function() {
  required <- c("ggplot2", "ggmapcn", "sf", "patchwork", "systemfonts")
  missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing)) {
    stop("Missing required R packages: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  invisible(TRUE)
}

easyplot_degree_labels <- function(values, positive, negative) {
  suffix <- ifelse(values < 0, negative, ifelse(values > 0, positive, ""))
  sprintf("%.1f\u00b0%s", abs(values), suffix)
}

easyplot_panel_range <- function(panel_parameters, axis = c("x", "y")) {
  axis <- match.arg(axis)
  for (name in c(paste0(axis, "_range"), paste0(axis, ".range"))) {
    value <- panel_parameters[[name]]
    if (is.numeric(value) && length(value) == 2L && all(is.finite(value))) {
      return(as.numeric(value))
    }
  }
  axis_parameters <- panel_parameters[[axis]]
  if (!is.null(axis_parameters)) {
    for (name in c("continuous_range", "range")) {
      value <- axis_parameters[[name]]
      if (is.numeric(value) && length(value) == 2L && all(is.finite(value))) {
        return(as.numeric(value))
      }
    }
  }
  stop("Could not read the rendered ", axis, " range.", call. = FALSE)
}

easyplot_panel_ratio <- function(plot_object) {
  built <- suppressWarnings(ggplot2::ggplot_build(plot_object))
  parameters <- built$layout$panel_params[[1]]
  diff(easyplot_panel_range(parameters, "x")) /
    diff(easyplot_panel_range(parameters, "y"))
}

easyplot_china_site_map <- function(
    data,
    lon,
    lat,
    value = NULL,
    mode = NULL,
    id = NULL,
    legend_title = NULL,
    categorical_palette = NULL,
    categorical_labels = NULL,
    continuous_option = "C",
    value_trans = "identity",
    value_breaks = NULL,
    value_limits = NULL,
    missing_colour = "grey85",
    location_fill = "#8D73B9",
    font_family = "Arial",
    text_pt = 8,
    point_size_main = 1.05,
    point_size_inset = 0.72,
    point_alpha = 0.82,
    point_stroke = 0.12,
    point_outline = "#24232B",
    main_xlim = c(72, 142),
    main_ylim = c(12, 56),
    inset_xlim = c(105, 125),
    inset_ylim = c(0, 25),
    inset_height = 0.29,
    inset_right = 0.995,
    inset_bottom = 0.012,
    graticule_lon = seq(80, 130, by = 10),
    graticule_lat = seq(20, 50, by = 10),
    buffer_outer_m = 40000,
    buffer_inner_m = 20000,
    buffer_outer_fill = "#D2D5EB",
    buffer_inner_fill = "#BBB3D8",
    land_boundary_colour = "#333333",
    coastline_colour = "#2F7F9F",
    boundary_halo_colour = "#D9D9D9",
    coastline_halo_colour = "#C7E0EA",
    inset_label = "NANHAI\nZHUDAO",
    alt = NULL) {
  easyplot_require_china_packages()

  if (!is.data.frame(data) || !nrow(data)) {
    stop("data must be a non-empty data frame.", call. = FALSE)
  }
  required_fields <- c(lon, lat, value, id)
  required_fields <- unique(required_fields[!is.null(required_fields) & nzchar(required_fields)])
  missing_fields <- setdiff(required_fields, names(data))
  if (length(missing_fields)) {
    stop("Missing required fields: ", paste(missing_fields, collapse = ", "), call. = FALSE)
  }
  if (!is.numeric(data[[lon]]) || !is.numeric(data[[lat]])) {
    stop("Longitude and latitude columns must be numeric WGS84 degrees.", call. = FALSE)
  }
  valid_coordinates <- is.finite(data[[lon]]) & is.finite(data[[lat]]) &
    data[[lon]] >= -180 & data[[lon]] <= 180 &
    data[[lat]] >= -90 & data[[lat]] <= 90
  if (!all(valid_coordinates)) {
    stop(sum(!valid_coordinates), " rows have missing, non-finite, or invalid coordinates.", call. = FALSE)
  }
  if (!is.null(id) && anyDuplicated(data[[id]])) {
    stop("Duplicate site identifiers in field: ", id, call. = FALSE)
  }
  if (buffer_outer_m <= buffer_inner_m || buffer_inner_m <= 0) {
    stop("Buffer distances must satisfy outer > inner > 0.", call. = FALSE)
  }
  if (length(main_xlim) != 2L || length(main_ylim) != 2L ||
      length(inset_xlim) != 2L || length(inset_ylim) != 2L) {
    stop("Each map extent must contain exactly two values.", call. = FALSE)
  }

  sites <- data
  if (is.null(mode)) {
    mode <- if (is.null(value)) {
      "location"
    } else if (is.numeric(sites[[value]])) {
      "continuous"
    } else {
      "categorical"
    }
  }
  mode <- match.arg(mode, c("continuous", "categorical", "location"))
  if (mode != "location" && is.null(value)) {
    stop("value is required for continuous or categorical maps.", call. = FALSE)
  }

  if (mode == "continuous") {
    if (!is.numeric(sites[[value]]) || any(!is.finite(sites[[value]]))) {
      stop("The continuous value field must contain only finite numeric values.", call. = FALSE)
    }
    if (identical(value_trans, "log10") && any(sites[[value]] <= 0)) {
      stop("log10 mapping requires strictly positive values.", call. = FALSE)
    }
    if (!is.null(value_limits)) {
      if (length(value_limits) != 2L || any(!is.finite(value_limits)) ||
          value_limits[1] >= value_limits[2]) {
        stop("value_limits must contain two increasing finite values.", call. = FALSE)
      }
      outside_limits <- sites[[value]] < value_limits[1] | sites[[value]] > value_limits[2]
      if (any(outside_limits)) {
        stop("value_limits would hide ", sum(outside_limits), " observed values.", call. = FALSE)
      }
    }
  }

  if (mode == "categorical") {
    if (anyNA(sites[[value]])) {
      stop("The categorical value field contains missing values; recode them explicitly.", call. = FALSE)
    }
    if (!is.factor(sites[[value]])) {
      sites[[value]] <- factor(sites[[value]], levels = unique(sites[[value]]))
    }
    levels_present <- levels(droplevels(sites[[value]]))
    if (is.null(categorical_palette) || is.null(names(categorical_palette))) {
      stop("categorical_palette must be a named colour vector.", call. = FALSE)
    }
    missing_colours <- setdiff(levels_present, names(categorical_palette))
    if (length(missing_colours)) {
      stop("Palette is missing levels: ", paste(missing_colours, collapse = ", "), call. = FALSE)
    }
    if (!is.null(categorical_labels)) {
      if (is.null(names(categorical_labels))) {
        stop("categorical_labels must be named by category level.", call. = FALSE)
      }
      missing_labels <- setdiff(levels_present, names(categorical_labels))
      if (length(missing_labels)) {
        stop("Category labels are missing levels: ", paste(missing_labels, collapse = ", "), call. = FALSE)
      }
    }
  }

  if (mode == "location") {
    sites$.easyplot_location <- factor("Sites", levels = "Sites")
    value <- ".easyplot_location"
  }

  in_main <- sites[[lon]] >= main_xlim[1] & sites[[lon]] <= main_xlim[2] &
    sites[[lat]] >= main_ylim[1] & sites[[lat]] <= main_ylim[2]
  in_inset <- sites[[lon]] >= inset_xlim[1] & sites[[lon]] <= inset_xlim[2] &
    sites[[lat]] >= inset_ylim[1] & sites[[lat]] <= inset_ylim[2]
  if (any(!(in_main | in_inset))) {
    stop(sum(!(in_main | in_inset)), " sites fall outside both the main map and inset.", call. = FALSE)
  }

  unique_coordinates <- nrow(unique(sites[c(lon, lat)]))
  n_sites <- nrow(sites)
  if (is.null(legend_title)) {
    legend_title <- if (mode == "location") "Locations" else value
  }
  legend_title <- paste0(legend_title, "\n(n = ", format(n_sites, big.mark = ","), ")")

  china_albers <- paste(
    "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105",
    "+datum=WGS84 +units=m +no_defs"
  )
  line_mm <- 25.4 / 72

  if (!font_family %in% unique(systemfonts::system_fonts()$family)) {
    stop("Font is unavailable: ", font_family, call. = FALSE)
  }

  geodata <- ggmapcn::check_geodata(files = "China_sheng.rda", quiet = TRUE)
  if (!length(geodata) || all(is.na(geodata)) || !any(file.exists(geodata), na.rm = TRUE)) {
    stop("ggmapcn could not resolve China_sheng.rda.", call. = FALSE)
  }

  sites_sf <- sf::st_as_sf(
    sites,
    coords = c(lon, lat),
    crs = 4326,
    remove = FALSE
  ) |>
    sf::st_transform(china_albers)

  publication_theme <-
    ggplot2::theme_classic(base_size = text_pt, base_family = font_family) +
    ggplot2::theme(
      text = ggplot2::element_text(family = font_family, size = text_pt, colour = "black"),
      axis.text = ggplot2::element_text(family = font_family, size = text_pt, colour = "black"),
      axis.title = ggplot2::element_blank(),
      legend.text = ggplot2::element_text(family = font_family, size = text_pt, colour = "black"),
      legend.title = ggplot2::element_text(family = font_family, size = text_pt, colour = "black"),
      panel.border = ggplot2::element_rect(colour = "black", fill = NA, linewidth = line_mm),
      axis.line = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_line(colour = "black", linewidth = line_mm),
      panel.grid = ggplot2::element_blank(),
      plot.background = ggplot2::element_rect(fill = "white", colour = NA),
      panel.background = ggplot2::element_rect(fill = "white", colour = NA),
      legend.background = ggplot2::element_rect(fill = NA, colour = NA),
      legend.box.background = ggplot2::element_blank(),
      legend.key = ggplot2::element_rect(fill = NA, colour = NA),
      plot.margin = ggplot2::margin(2, 2, 2, 2, "mm")
    )

  map_layers <- function() {
    list(
      ggmapcn::geom_buffer_cn(
        mainland_dist = buffer_outer_m, crs = china_albers,
        color = NA, fill = buffer_outer_fill
      ),
      ggmapcn::geom_buffer_cn(
        mainland_dist = buffer_inner_m, crs = china_albers,
        color = NA, fill = buffer_inner_fill
      ),
      ggmapcn::geom_mapcn(
        admin_level = "province", crs = china_albers,
        fill = "#F7F7F4", color = "#C7CCCF", linewidth = line_mm * 0.55
      ),
      ggmapcn::geom_boundary_cn(
        crs = china_albers,
        mainland_color = boundary_halo_colour, mainland_size = line_mm * 2.3,
        coastline_color = coastline_halo_colour, coastline_size = line_mm * 1.8,
        ten_segment_line_color = boundary_halo_colour, ten_segment_line_size = line_mm * 2,
        SAR_boundary_color = "transparent",
        undefined_boundary_color = boundary_halo_colour, undefined_boundary_size = line_mm * 2,
        province_color = "transparent"
      ),
      ggmapcn::geom_boundary_cn(
        crs = china_albers,
        mainland_color = land_boundary_colour, mainland_size = line_mm * 1.15,
        coastline_color = coastline_colour, coastline_size = line_mm * 0.8,
        ten_segment_line_color = land_boundary_colour, ten_segment_line_size = line_mm * 1.05,
        ten_segment_line_linetype = "longdash",
        SAR_boundary_color = "grey35", SAR_boundary_size = line_mm * 0.55,
        SAR_boundary_linetype = "dashed",
        undefined_boundary_color = land_boundary_colour, undefined_boundary_size = line_mm * 0.9,
        undefined_boundary_linetype = "dotdash",
        province_color = "transparent"
      )
    )
  }

  site_layer <- function(size, show_legend) {
    ggplot2::geom_sf(
      data = sites_sf,
      mapping = ggplot2::aes(fill = .data[[value]]),
      shape = 21,
      size = size,
      colour = point_outline,
      stroke = point_stroke,
      alpha = point_alpha,
      inherit.aes = FALSE,
      show.legend = show_legend
    )
  }

  fill_scale <- function(show_guide = TRUE) {
    guide <- if (show_guide) {
      if (mode == "continuous") {
        ggplot2::guide_colourbar(
          title.position = "top", title.hjust = 0,
          barheight = grid::unit(28, "mm"), barwidth = grid::unit(3.5, "mm"),
          ticks.colour = "black", frame.colour = "black"
        )
      } else {
        ggplot2::guide_legend(title.position = "top", title.hjust = 0)
      }
    } else {
      "none"
    }

    if (mode == "continuous") {
      ggplot2::scale_fill_viridis_c(
        option = continuous_option,
        trans = value_trans,
        breaks = value_breaks,
        limits = value_limits,
        na.value = missing_colour,
        name = legend_title,
        guide = guide
      )
    } else if (mode == "categorical") {
      counts <- table(sites[[value]], useNA = "no")
      levels_present <- names(counts)
      labels <- if (is.null(categorical_labels)) {
        sprintf("%s (n = %d)", levels_present, as.integer(counts))
      } else {
        unname(categorical_labels[levels_present])
      }
      ggplot2::scale_fill_manual(
        values = categorical_palette,
        breaks = levels_present,
        labels = labels,
        drop = FALSE,
        na.value = missing_colour,
        name = legend_title,
        guide = guide
      )
    } else {
      ggplot2::scale_fill_manual(
        values = c(Sites = location_fill),
        breaks = "Sites",
        labels = paste0("Sites (n = ", format(n_sites, big.mark = ","), ")"),
        name = NULL,
        guide = guide
      )
    }
  }

  if (is.null(alt)) {
    alt <- paste0(
      "Map of China showing ", format(n_sites, big.mark = ","),
      " sites at ", format(unique_coordinates, big.mark = ","),
      " unique coordinates. Equal-sized circles encode ",
      if (mode == "location") "site location" else value,
      " by fill. A South China Sea inset appears in the lower right."
    )
  }

  p_main <- ggplot2::ggplot() +
    map_layers() +
    site_layer(point_size_main, TRUE) +
    fill_scale(TRUE) +
    ggplot2::scale_x_continuous(
      breaks = graticule_lon,
      labels = function(x) easyplot_degree_labels(x, "E", "W")
    ) +
    ggplot2::scale_y_continuous(
      breaks = graticule_lat,
      labels = function(y) easyplot_degree_labels(y, "N", "S")
    ) +
    ggplot2::coord_sf(
      crs = china_albers,
      default_crs = sf::st_crs(4326),
      xlim = main_xlim,
      ylim = main_ylim,
      label_axes = "--EN",
      expand = FALSE
    ) +
    ggplot2::labs(x = NULL, y = NULL, alt = alt) +
    publication_theme +
    ggplot2::theme(
      panel.grid.major = ggplot2::element_line(colour = "grey88", linewidth = line_mm * 0.45),
      legend.position = "right",
      legend.direction = "vertical",
      legend.box = "vertical"
    )

  p_inset <- ggplot2::ggplot() +
    map_layers() +
    site_layer(point_size_inset, FALSE) +
    fill_scale(FALSE) +
    ggplot2::annotate(
      "text",
      x = inset_xlim[2] - 3.5,
      y = inset_ylim[1] + 2.5,
      label = inset_label,
      family = font_family,
      fontface = "plain",
      size = 6 / ggplot2::.pt,
      lineheight = 0.85,
      hjust = 1,
      vjust = 0,
      colour = "black"
    ) +
    ggplot2::coord_sf(
      crs = china_albers,
      default_crs = sf::st_crs(4326),
      xlim = inset_xlim,
      ylim = inset_ylim,
      expand = FALSE
    ) +
    publication_theme +
    ggplot2::theme(
      panel.border = ggplot2::element_blank(),
      panel.grid = ggplot2::element_blank(),
      axis.text = ggplot2::element_blank(),
      axis.title = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_blank(),
      legend.position = "none",
      plot.margin = ggplot2::margin(0, 0, 0, 0, "mm")
    )

  main_ratio <- easyplot_panel_ratio(p_main)
  inset_ratio <- easyplot_panel_ratio(p_inset)
  inset_width <- inset_height * inset_ratio / main_ratio
  inset_left <- inset_right - inset_width
  inset_top <- inset_bottom + inset_height
  if (!all(is.finite(c(main_ratio, inset_ratio, inset_width, inset_left, inset_top))) ||
      inset_left < 0 || inset_width <= 0 || inset_top > 1) {
    stop("Calculated inset geometry falls outside the main panel.", call. = FALSE)
  }

  inset_frame <- ggplot2::ggplot() +
    ggplot2::theme_void() +
    ggplot2::theme(
      plot.background = ggplot2::element_rect(fill = NA, colour = "black", linewidth = line_mm),
      plot.margin = ggplot2::margin(0, 0, 0, 0, "mm")
    )

  composite <- p_main +
    patchwork::inset_element(
      p_inset,
      left = inset_left, bottom = inset_bottom,
      right = inset_right, top = inset_top,
      align_to = "panel"
    ) +
    patchwork::inset_element(
      inset_frame,
      left = inset_left, bottom = inset_bottom,
      right = inset_right, top = inset_top,
      align_to = "panel"
    )

  attr(composite, "easyplot_china_map_audit") <- list(
    mode = mode,
    n_sites = n_sites,
    unique_coordinates = unique_coordinates,
    value = if (mode == "location") NULL else value,
    projection = china_albers,
    main_xlim = main_xlim,
    main_ylim = main_ylim,
    inset_xlim = inset_xlim,
    inset_ylim = inset_ylim,
    buffer_outer_m = buffer_outer_m,
    buffer_inner_m = buffer_inner_m,
    land_boundary_colour = land_boundary_colour,
    coastline_colour = coastline_colour
  )
  composite
}
