"""Inspect PNG/PDF/SVG properties for an EasyPlot export preflight.

This checker reports machine-readable properties and warnings. It does not
prove scientific validity, journal acceptance, or the integrity of every
embedded raster inside a vector container.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import StreamObject


SUPPORTED = {"png", "pdf", "svg", "jpg", "jpeg", "tif", "tiff"}
UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "in": 25.4,
    "pt": 25.4 / 72.0,
    "pc": 25.4 / 6.0,
    "px": 25.4 / 96.0,
    "q": 0.25,
}


def _positive_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _length_to_mm(value: str | None) -> float | None:
    if not value:
        return None
    match = re.fullmatch(r"\s*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\s*([a-zA-Z]*)\s*", value)
    if not match:
        return None
    number = _positive_number(match.group(1))
    unit = match.group(2).lower() or "px"
    if number is None or unit not in UNIT_TO_MM:
        return None
    return _positive_number(number * UNIT_TO_MM[unit])


def _resolve(value):
    return value.get_object() if hasattr(value, "get_object") else value


def _all_embedded(states: list[bool | None]) -> bool | None:
    if False in states:
        return False
    return True if states and all(state is True for state in states) else None


def _pdf_font_evidence(value, ancestors: frozenset[int] = frozenset()) -> dict:
    evidence = {
        "base_font": None, "subtype": None, "embedded": None,
        "font_file_keys": [], "descendant_fonts": [],
        "type3_charprocs": None, "issues": [],
    }
    try:
        font = _resolve(value)
        if not isinstance(font, dict):
            raise ValueError("font resource is not a dictionary")
        if id(font) in ancestors:
            raise ValueError("cyclic DescendantFonts reference")
        ancestors = ancestors | {id(font)}
        evidence["base_font"] = str(font["/BaseFont"]).lstrip("/") if "/BaseFont" in font else None
        evidence["subtype"] = str(font.get("/Subtype", "")).lstrip("/") or None
        descriptor = _resolve(font.get("/FontDescriptor"))
        if descriptor is not None:
            if not isinstance(descriptor, dict):
                raise ValueError("FontDescriptor is not a dictionary")
            for key in ("/FontFile", "/FontFile2", "/FontFile3"):
                if key in descriptor:
                    stream = _resolve(descriptor[key])
                    if isinstance(stream, StreamObject) and stream.get_data():
                        evidence["font_file_keys"].append(key)
                    else:
                        evidence["issues"].append(f"{key} is not a nonempty font stream")
        if "/DescendantFonts" in font:
            descendants = _resolve(font["/DescendantFonts"])
            if not isinstance(descendants, (list, tuple)):
                raise ValueError("DescendantFonts is not an array")
            evidence["descendant_fonts"] = [_pdf_font_evidence(child, ancestors) for child in descendants]

        subtype = evidence["subtype"]
        if subtype == "Type3":
            charprocs = _resolve(font.get("/CharProcs"))
            if charprocs is None:
                evidence["embedded"] = False
            elif not isinstance(charprocs, dict):
                raise ValueError("Type3 CharProcs is not a dictionary")
            else:
                streams = sum(isinstance(_resolve(proc), StreamObject) for proc in charprocs.values())
                evidence["type3_charprocs"] = {"count": len(charprocs), "stream_count": streams}
                if not charprocs or streams != len(charprocs):
                    evidence["issues"].append("Type3 CharProcs is empty or contains non-stream entries")
                else:
                    evidence["embedded"] = True
        elif subtype == "Type0":
            evidence["embedded"] = _all_embedded([child["embedded"] for child in evidence["descendant_fonts"]])
            if not evidence["descendant_fonts"]:
                evidence["issues"].append("Type0 font has no DescendantFonts")
        elif subtype in {"Type1", "MMType1", "TrueType", "CIDFontType0", "CIDFontType2"}:
            if not evidence["issues"]:
                evidence["embedded"] = bool(evidence["font_file_keys"])
        else:
            evidence["issues"].append("missing or unsupported font subtype")
    except Exception as error:
        evidence["issues"].append(str(error))
    return evidence


def _pdf_fonts(page, page_number: int) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    issues: list[str] = []
    seen: set[int] = set()

    def visit(value, resource_path: str) -> None:
        if value is None:
            return
        try:
            resources = _resolve(value)
            if not isinstance(resources, dict):
                raise ValueError("resources are not a dictionary")
            if id(resources) in seen:
                return
            seen.add(id(resources))
            try:
                fonts = _resolve(resources.get("/Font", {}))
                if not isinstance(fonts, dict):
                    raise ValueError("Font resources are not a dictionary")
            except Exception as error:
                issues.append(f"page {page_number} {resource_path}/Font: {error}")
                fonts = {}
            for key, font in fonts.items():
                records.append({
                    "page": page_number, "resource_name": str(key),
                    "resource_path": f"{resource_path}/Font{key}",
                    **_pdf_font_evidence(font),
                })
            xobjects = _resolve(resources.get("/XObject", {}))
            if not isinstance(xobjects, dict):
                raise ValueError("XObject resources are not a dictionary")
            for key, value in xobjects.items():
                try:
                    xobject = _resolve(value)
                    if xobject.get("/Subtype") == "/Form":
                        visit(xobject.get("/Resources"), f"{resource_path}/XObject{key}/Resources")
                except Exception as error:
                    issues.append(f"page {page_number} {resource_path}/XObject{key}: {error}")
        except Exception as error:
            issues.append(f"page {page_number} {resource_path}: {error}")

    visit(page.get("/Resources"), "/Resources")
    return records, issues


def _inspect_raster(path: Path) -> dict:
    with Image.open(path) as image:
        dpi = image.info.get("dpi")
        if isinstance(dpi, (tuple, list)):
            dpi_x = _positive_number(dpi[0]) if dpi else None
            dpi_y = _positive_number(dpi[1]) if len(dpi) > 1 else dpi_x
        elif dpi is None:
            dpi_x = dpi_y = None
        else:
            dpi_x = dpi_y = _positive_number(dpi)
        # PNG stores pixels/metre; JPEG JFIF density may be dots/inch or dots/cm.
        dpi_rounding = 0.0127 if image.format == "PNG" else 0.0
        if image.format == "JPEG":
            dpi_rounding = {1: 0.5, 2: 1.27}.get(image.info.get("jfif_unit"), 0.0)
        dimensions = {}
        rounding = {}
        for axis, pixels, resolution in (("width", image.width, dpi_x), ("height", image.height, dpi_y)):
            dimensions[f"{axis}_mm"] = pixels * 25.4 / resolution if resolution else None
            # Allow one quantized canvas pixel plus the embedded-DPI uncertainty.
            rounding[axis] = (
                25.4 / resolution + dimensions[f"{axis}_mm"] * dpi_rounding / (resolution - dpi_rounding)
                if resolution and resolution > dpi_rounding else None
            )
        has_alpha_channel = "A" in image.getbands()
        if has_alpha_channel:
            alpha_min, alpha_max = image.getchannel("A").getextrema()
            has_transparency = alpha_min < 255
        else:
            has_transparency = "transparency" in image.info
        return {
            "format": image.format,
            "width_px": int(image.width),
            "height_px": int(image.height),
            "mode": image.mode,
            "dpi_x": dpi_x,
            "dpi_y": dpi_y,
            **dimensions,
            "embedded_dpi_rounding_tolerance": dpi_rounding,
            "size_rounding_tolerance_mm": rounding,
            "compression": image.info.get("compression"),
            "has_alpha_channel": has_alpha_channel,
            "has_transparency": has_transparency,
            "has_alpha": has_transparency,
            "has_icc_profile": bool(image.info.get("icc_profile")),
        }


def _inspect_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    if not reader.pages:
        raise ValueError("PDF contains no pages")
    page_sizes = []
    fonts = []
    scan_issues = []
    for number, page in enumerate(reader.pages, 1):
        width = height = None
        try:
            box = _resolve(page.get("/MediaBox"))
            unit = _positive_number(page.get("/UserUnit", 1))
            if box is not None and len(box) == 4 and unit is not None:
                coordinates = [float(_resolve(value)) for value in box]
                if all(math.isfinite(value) for value in coordinates):
                    width = _positive_number((coordinates[2] - coordinates[0]) * unit * 25.4 / 72.0)
                    height = _positive_number((coordinates[3] - coordinates[1]) * unit * 25.4 / 72.0)
        except (TypeError, ValueError, OverflowError):
            pass
        page_sizes.append({"page": number, "width_mm": width, "height_mm": height})
        page_fonts, issues = _pdf_fonts(page, number)
        fonts.extend(page_fonts)
        scan_issues.extend(issues)
    metadata = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "page_width_mm": page_sizes[0]["width_mm"],
        "page_height_mm": page_sizes[0]["height_mm"],
        "page_sizes": page_sizes,
        "first_page_fonts": sorted({
            font["base_font"] or font["resource_name"].lstrip("/") for font in fonts
            if font["page"] == 1 and font["resource_path"] == f"/Resources/Font{font['resource_name']}"
        }),
        "pdf_fonts": fonts,
        "all_fonts_embedded": _all_embedded([font["embedded"] for font in fonts] + ([None] if scan_issues else [])),
        "font_scan_issues": scan_issues,
        "inspection_limits": [
            "FontFile/FontFile2/FontFile3 and Type3 CharProcs are resource evidence only; font programs, glyph coverage and rendering are not certified.",
            "Fonts are inventoried in all page and nested Form XObject resources, including unused resources; other resource contexts are not scanned.",
            "Page dimensions use the unrotated MediaBox and UserUnit; crop boxes and rendered bounds are not checked.",
        ],
        "document_metadata_keys": sorted(str(key) for key in metadata.keys()),
    }


def _svg_style(element) -> dict[str, str]:
    style = {key.rsplit("}", 1)[-1]: value for key, value in element.attrib.items()}
    for declaration in element.get("style", "").split(";"):
        key, separator, value = declaration.partition(":")
        if separator:
            style[key.strip().lower()] = re.sub(r"\s*!important\s*$", "", value.strip(), flags=re.I)
    return style


def _opacity(value: str) -> float | None:
    try:
        number = float(value.rstrip("%")) / (100 if value.endswith("%") else 1)
        return max(0.0, min(1.0, number)) if math.isfinite(number) else None
    except ValueError:
        return None


def _svg_visible_evidence(root) -> tuple[int, int]:
    ids = {element.get("id"): element for element in root.iter() if element.get("id")}
    paths = texts = 0

    def visit(element, inherited: dict, ancestors: frozenset[int], referenced: bool = False) -> None:
        nonlocal paths, texts
        if id(element) in ancestors:
            return
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in {"defs", "filter", "clipPath", "mask", "pattern", "marker"} or (tag == "symbol" and not referenced):
            return
        own = _svg_style(element)
        if own.get("display") == "none" or _opacity(own.get("opacity", "1")) == 0:
            return
        inherited_keys = ("visibility", "fill", "stroke", "fill-opacity", "stroke-opacity")
        style = {**inherited, **{key: own[key] for key in inherited_keys if key in own and own[key] != "inherit"}}
        visible = style.get("visibility") not in {"hidden", "collapse"}
        painted = (
            style.get("fill", "black") != "none" and _opacity(style.get("fill-opacity", "1")) != 0
        ) or (
            style.get("stroke", "none") != "none" and _opacity(style.get("stroke-opacity", "1")) != 0
        )
        if visible and painted:
            if tag == "path" and element.get("d", "").strip():
                paths += 1
            if tag == "text" and "".join(element.itertext()).strip():
                texts += 1
        ancestors = ancestors | {id(element)}
        if visible:
            filter_reference = re.fullmatch(r"url\(\s*(['\"]?)#([^'\"\s()]+)\1\s*\)", own.get("filter", "").strip())
            if filter_reference:
                used_filter = ids.get(filter_reference.group(2))
                if used_filter is not None and used_filter.tag.rsplit("}", 1)[-1] == "filter" and id(used_filter) not in ancestors:
                    filter_ancestors = ancestors | {id(used_filter)}
                    for primitive in used_filter:
                        if primitive.tag.rsplit("}", 1)[-1] != "feImage":
                            continue
                        href = primitive.get("href", primitive.get("{http://www.w3.org/1999/xlink}href", ""))
                        if href.startswith("#") and href[1:] in ids:
                            visit(ids[href[1:]], {}, filter_ancestors | {id(primitive)}, referenced=True)
        if tag == "use":
            href = element.get("href", element.get("{http://www.w3.org/1999/xlink}href", ""))
            if href.startswith("#") and href[1:] in ids:
                visit(ids[href[1:]], style, ancestors, referenced=True)
        for child in element:
            visit(child, style, ancestors)

    # ponytail: inline/presentation styles, local use and used-filter feImage targets only; use a renderer for CSS/filter effects.
    visit(root, {}, frozenset())
    return paths, texts


def _inspect_svg(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("XML root is not an SVG element")
    width_mm = _length_to_mm(root.attrib.get("width"))
    height_mm = _length_to_mm(root.attrib.get("height"))
    view_box = root.attrib.get("viewBox")
    text_count = 0
    image_count = 0
    path_count = 0
    stylesheet_count = 0
    font_families: set[str] = set()
    alpha_markers = 0
    unresolved_opacity: set[str] = set()
    css_alpha_markers = 0
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "text":
            text_count += 1
        elif tag == "image":
            image_count += 1
        elif tag == "path":
            path_count += 1
        elif tag == "style":
            stylesheet_count += 1
            css = re.sub(r"/\*.*?\*/", "", "".join(element.itertext()), flags=re.S)
            for value in re.findall(r"(?:^|[;{])\s*(?:fill-|stroke-|stop-)?opacity\s*:\s*([^;}]+)", css, re.I):
                opacity = _opacity(re.sub(r"\s*!important\s*$", "", value.strip(), flags=re.I))
                if opacity is None:
                    unresolved_opacity.add(value.strip())
                elif opacity < 1:
                    css_alpha_markers += 1
        for key, value in _svg_style(element).items():
            if key in {"opacity", "fill-opacity", "stroke-opacity", "stop-opacity"}:
                opacity = _opacity(value.strip())
                if opacity is None:
                    unresolved_opacity.add(value)
                elif opacity < 1:
                    alpha_markers += 1
        for key, value in element.attrib.items():
            if key.endswith("font-family"):
                font_families.add(value)
        font_families.update(
            match.strip().strip("'\"")
            for match in re.findall(r"font-family\s*:\s*([^;]+)", element.get("style", ""))
        )
    visible_paths, visible_texts = _svg_visible_evidence(root)
    return {
        "width_mm": width_mm,
        "height_mm": height_mm,
        "viewBox": view_box,
        "text_elements": text_count,
        "image_elements": image_count,
        "path_elements": path_count,
        "visible_path_instances": visible_paths,
        "visible_text_instances": visible_texts,
        "text_mode_evidence": (
            "editable-text-present" if visible_texts else
            "paths-without-text" if visible_paths and not text_count else
            "no-visible-text-or-outline-evidence"
        ),
        "font_families": sorted(font_families),
        "has_alpha_markers": alpha_markers > 0,
        "stylesheet_elements": stylesheet_count,
        "stylesheet_has_alpha_markers": css_alpha_markers > 0,
        "unresolved_opacity_values": sorted(unresolved_opacity),
        "inspection_limits": [
            "Visible instances are structural candidates using presentation/inline styles, local use references and local feImage targets of used filters; path data, transforms, clipping and occlusion are not rendered.",
            "Nested CSS rules, selector matching, cascading, external stylesheets, animation, filter effects and color alpha are not resolved; stylesheet opacity markers may be unused.",
            "Paths without text are outline evidence only; paths may be ordinary diagram geometry and do not certify outlined glyphs.",
        ],
    }


def _check_dimension(warnings: list[str], actual: float | None, target: float | None, label: str, tolerance: float) -> None:
    if actual is None:
        warnings.append(f"{label} is missing or invalid (physical units/DPI may be unavailable or unsupported)")
    elif target is not None and abs(actual - target) > tolerance + 1e-9:
        warnings.append(f"{label} {actual:.3f} mm differs from target {target:.3f} mm (tolerance {tolerance:.3f} mm)")


def inspect_file(
    filename: str | Path,
    min_dpi: float | None = None,
    target_width_mm: float | None = None,
    alpha_policy: str = "allow",
    *,
    target_height_mm: float | None = None,
    size_tolerance_mm: float = 0.2,
    expected_svg_text: str | None = None,
    require_embedded_fonts: bool = False,
) -> dict:
    """Audit export metadata; embedding/text-mode flags describe evidence, not glyph certification.

    Existing positional arguments are unchanged. Size tolerance is in millimetres;
    raster comparisons also allow pixel/DPI quantization. Supplied raster target
    axes determine effective-DPI checks; with no targets both embedded axes apply.
    Font requirements apply to PDFs; text expectations apply to SVGs.
    """
    path = Path(filename)
    report = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "format": path.suffix.lower().lstrip("."),
        "properties": {},
        "warnings": [],
        "errors": [],
    }
    if not path.exists():
        report["errors"].append("file does not exist")
        return report
    if report["format"] not in SUPPORTED:
        report["warnings"].append("unsupported extension; no format-specific inspection performed")
        return report

    try:
        for name, value in (("min_dpi", min_dpi), ("target_width_mm", target_width_mm), ("target_height_mm", target_height_mm)):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(size_tolerance_mm) or size_tolerance_mm < 0:
            raise ValueError("size_tolerance_mm must be finite and nonnegative")
        if expected_svg_text not in (None, "editable", "outline"):
            raise ValueError("expected_svg_text must be None, 'editable', or 'outline'")
        if alpha_policy not in ("allow", "forbid"):
            raise ValueError("alpha_policy must be 'allow' or 'forbid'")
        if not isinstance(require_embedded_fonts, bool):
            raise ValueError("require_embedded_fonts must be a bool")
        targets = {"width": target_width_mm, "height": target_height_mm}
        if report["format"] in {"png", "jpg", "jpeg", "tif", "tiff"}:
            report["properties"] = _inspect_raster(path)
            properties = report["properties"]
            for axis, target in targets.items():
                if target is not None:
                    properties[f"effective_dpi_at_target_{axis}"] = properties[f"{axis}_px"] / (target / 25.4)
                    _check_dimension(
                        report["warnings"], properties[f"{axis}_mm"], target, f"raster {axis}",
                        size_tolerance_mm + (properties["size_rounding_tolerance_mm"][axis] or 0),
                    )
            if min_dpi is not None:
                axis_checks = {}
                has_targets = any(target is not None for target in targets.values())
                for axis, letter in (("width", "x"), ("height", "y")):
                    target = targets[axis]
                    if has_targets and target is None:
                        continue
                    available = properties[f"effective_dpi_at_target_{axis}"] if target else properties[f"dpi_{letter}"]
                    tolerance = (25.4 / target if target else properties["embedded_dpi_rounding_tolerance"]) + 1e-9
                    axis_checks[letter] = {
                        "source": f"effective_at_target_{axis}" if target else "embedded",
                        "value": available, "minimum": min_dpi, "rounding_tolerance": tolerance,
                    }
                    if available is None:
                        report["warnings"].append(f"DPI on {letter} axis is unavailable; provide --target-{axis}-mm for an effective DPI")
                    elif available + tolerance < min_dpi:
                        report["warnings"].append(f"DPI {available:.2f} on {letter} axis is below requested minimum {min_dpi:.2f}")
                minimum = min(axis_checks.values(), key=lambda check: check["value"] if check["value"] is not None else -1)
                source = "minimum_embedded_axis" if not has_targets else (
                    minimum["source"] if len(axis_checks) == 1 else "minimum_effective_axis"
                )
                properties["dpi_check"] = {
                    **minimum, "source": source, "axes": axis_checks,
                }
            if alpha_policy == "forbid" and properties.get("has_transparency"):
                report["warnings"].append("alpha/transparency is present but alpha policy is forbid")
        elif report["format"] == "pdf":
            report["properties"] = _inspect_pdf(path)
            properties = report["properties"]
            for page in properties["page_sizes"]:
                for axis, target in targets.items():
                    _check_dimension(report["warnings"], page[f"{axis}_mm"], target, f"page {page['page']} {axis}", size_tolerance_mm)
            report["warnings"].extend(properties["font_scan_issues"])
            if require_embedded_fonts:
                for font in properties["pdf_fonts"]:
                    if font["embedded"] is not True:
                        status = "missing" if font["embedded"] is False else "unknown"
                        report["warnings"].append(f"PDF font embedding evidence is {status}: page {font['page']} {font['resource_path']} ({font['base_font'] or font['resource_name']})")
        elif report["format"] == "svg":
            report["properties"] = _inspect_svg(path)
            properties = report["properties"]
            for axis, target in targets.items():
                _check_dimension(report["warnings"], properties[f"{axis}_mm"], target, f"SVG {axis}", size_tolerance_mm)
            if expected_svg_text == "editable" and not properties["visible_text_instances"]:
                report["warnings"].append("expected editable SVG text, but no visible nonempty text evidence was found")
            elif expected_svg_text == "outline":
                if properties["text_elements"]:
                    report["warnings"].append("expected outlined SVG text, but text elements remain")
                if not properties["visible_path_instances"]:
                    report["warnings"].append("expected outlined SVG text, but no visible path evidence was found; zero text elements does not prove outlines")
            if alpha_policy == "forbid":
                if properties["has_alpha_markers"]:
                    report["warnings"].append("SVG opacity below 1 is declared but alpha policy is forbid")
                if properties["stylesheet_has_alpha_markers"]:
                    report["warnings"].append("SVG stylesheet declares opacity below 1; selector applicability is unresolved")
                if properties["unresolved_opacity_values"]:
                    report["warnings"].append("SVG opacity values could not be resolved under alpha policy forbid")
    except Exception as error:
        report["errors"].append(f"inspection failed: {error}")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="PNG, PDF, or SVG files to inspect")
    parser.add_argument("--min-dpi", type=float, default=None, help="minimum embedded/effective raster DPI")
    parser.add_argument("--target-width-mm", type=float, default=None, help="target physical width for size/DPI checks")
    parser.add_argument("--target-height-mm", type=float, default=None, help="target physical height for size/DPI checks")
    parser.add_argument("--size-tolerance-mm", type=float, default=0.2, help="nonnegative size tolerance; raster rounding is additional")
    parser.add_argument("--expected-svg-text", choices=("editable", "outline"), default=None, help="expected SVG text representation (evidence only)")
    parser.add_argument("--require-embedded-fonts", action="store_true", help="warn for missing/unknown PDF font embedding evidence")
    parser.add_argument("--alpha-policy", choices=("allow", "forbid"), default="allow")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a human-readable report")
    parser.add_argument("--fail-on-warning", action="store_true", help="return exit code 1 when warnings exist")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    reports = [
        inspect_file(
            filename,
            min_dpi=args.min_dpi,
            target_width_mm=args.target_width_mm,
            alpha_policy=args.alpha_policy,
            target_height_mm=args.target_height_mm,
            size_tolerance_mm=args.size_tolerance_mm,
            expected_svg_text=args.expected_svg_text,
            require_embedded_fonts=args.require_embedded_fonts,
        )
        for filename in args.files
    ]
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        for report in reports:
            status = "OK" if not report["errors"] else "ERROR"
            print(f"[{status}] {report['path']} ({report['size_bytes']} bytes)")
            print(json.dumps(report["properties"], indent=2, ensure_ascii=False))
            for warning in report["warnings"]:
                print(f"  WARNING: {warning}")
            for error in report["errors"]:
                print(f"  ERROR: {error}")
    has_errors = any(report["errors"] for report in reports)
    has_warnings = any(report["warnings"] for report in reports)
    return 1 if has_errors or (args.fail_on_warning and has_warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
