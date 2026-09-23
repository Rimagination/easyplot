"""Audit EasyPlot palettes for WCAG contrast and grayscale separation."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys

from easyplot_py import EASYPLOT_INK, EASYPLOT_PALETTE, EASYPLOT_LINE_PALETTE


BUILTIN_PALETTES = {
    "easyplot_conditions": {name: EASYPLOT_PALETTE[name] for name in ("CK", "Rh", "Ps", "RP")},
    "easyplot_lines": EASYPLOT_LINE_PALETTE,
    "easyplot_pastel": {
        name: EASYPLOT_PALETTE[name]
        for name in ("mist", "blush", "coral", "sand", "rose", "powder_blue", "steel_blue")
    },
}
THRESHOLDS = {"normal_text": 4.5, "large_text": 3.0, "graphical": 3.0}
GEOMETRIES = ("unspecified", "bar", "box", "line", "scatter")
CUES = ("position-labels", "direct-labels", "markers", "linestyles", "outline", "facets", "hatching")
FOREGROUND_PLACEMENTS = ("unspecified", "on-marks", "outside-marks")


def parse_hex(value: str, background: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> tuple[float, float, float]:
    token = value.strip().lstrip("#")
    if len(token) == 3:
        token = "".join(char * 2 for char in token)
    if len(token) not in {6, 8}:
        raise ValueError(f"invalid hex colour: {value}")
    channels = [int(token[index : index + 2], 16) / 255 for index in range(0, 6, 2)]
    if len(token) == 8:
        alpha = int(token[6:8], 16) / 255
        channels = [channel * alpha + base * (1 - alpha) for channel, base in zip(channels, background)]
    return tuple(channels)


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    linear = [_linear(channel) for channel in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    first_l = relative_luminance(first)
    second_l = relative_luminance(second)
    lighter, darker = max(first_l, second_l), min(first_l, second_l)
    return (lighter + 0.05) / (darker + 0.05)


def cie_lstar(rgb: tuple[float, float, float]) -> float:
    red, green, blue = [_linear(channel) for channel in rgb]
    x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
    y = (0.2126729 * red + 0.7151522 * green + 0.0721750 * blue) / 1.00000
    z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

    def f(value: float) -> float:
        epsilon = 216 / 24389
        kappa = 24389 / 27
        return value ** (1 / 3) if value > epsilon else (kappa * value + 16) / 116

    return 116 * f(y) - 16


def grayscale_hex(value: str, background: str = "#FFFFFF") -> str:
    """Equal-luminance sRGB gray; screening view, not a print/CVD simulation."""
    luminance = relative_luminance(parse_hex(value, parse_hex(background)))
    channel = 12.92 * luminance if luminance <= 0.0031308 else 1.055 * luminance ** (1 / 2.4) - 0.055
    byte = round(255 * channel)
    return f"#{byte:02X}{byte:02X}{byte:02X}"


def audit_palette(
    colours: dict[str, str],
    background: str = "#FFFFFF",
    foreground: str = EASYPLOT_INK,
    role: str = "graphical",
    min_gray_delta: float = 10.0,
    geometry: str = "unspecified",
    cues: tuple[str, ...] = (),
    foreground_placement: str = "unspecified",
) -> dict:
    if role not in THRESHOLDS:
        raise ValueError(f"unknown role: {role}")
    if not colours or not math.isfinite(min_gray_delta) or min_gray_delta < 0:
        raise ValueError("supply a non-empty palette and a finite, non-negative grayscale threshold")
    if geometry not in GEOMETRIES or set(cues) - set(CUES):
        raise ValueError("unknown geometry or cue")
    if foreground_placement not in FOREGROUND_PLACEMENTS:
        raise ValueError("unknown foreground placement")
    background_rgb = parse_hex(background)
    foreground_rgb = parse_hex(foreground, background_rgb)
    parsed = {name: parse_hex(value, background_rgb) for name, value in colours.items()}
    threshold = THRESHOLDS[role]
    entries = []
    for name, value in colours.items():
        rgb = parsed[name]
        entries.append(
            {
                "name": name,
                "hex": value,
                "contrast_vs_background": round(contrast_ratio(rgb, background_rgb), 4),
                "contrast_vs_foreground": round(contrast_ratio(rgb, foreground_rgb), 4),
                "cie_lstar": round(cie_lstar(rgb), 4),
            }
        )
    pairs = []
    for first, second in itertools.combinations(colours, 2):
        delta = abs(cie_lstar(parsed[first]) - cie_lstar(parsed[second]))
        pairs.append({"first": first, "second": second, "delta_cie_lstar": round(delta, 4), "below_heuristic": delta < min_gray_delta})
    warnings = []
    notes = []
    recommendations = []
    low_background = [entry["name"] for entry in entries if entry["contrast_vs_background"] < threshold]
    low_foreground = [entry["name"] for entry in entries if entry["contrast_vs_foreground"] < threshold]
    low_gray = [pair for pair in pairs if pair["below_heuristic"]]
    identity_cues = {"direct-labels", "facets"}
    if geometry in {"bar", "box"}:
        identity_cues.update({"position-labels", "hatching"})
    elif geometry == "line":
        identity_cues.update({"markers", "linestyles"})
    elif geometry == "scatter":
        identity_cues.add("markers")
    identity_supported = geometry != "unspecified" and bool(set(cues) & identity_cues)
    outline_supported = (
        role == "graphical" and geometry in {"bar", "box"} and "outline" in cues
        and contrast_ratio(foreground_rgb, background_rgb) >= threshold and not low_foreground
    )
    if low_background:
        message = (
            f"{len(low_background)} colour(s) are below {threshold}:1 against the background: "
            + ", ".join(low_background)
        )
        if outline_supported:
            notes.append(message + "; declared outlines provide boundaries; verify their actual width and visibility")
        else:
            warnings.append(message)
    if low_foreground:
        message = (
            f"{len(low_foreground)} colour(s) are below {threshold}:1 against the declared foreground: "
            + ", ".join(low_foreground)
        )
        if (role == "graphical" and geometry in {"line", "scatter"}
                and "outline" not in cues and foreground_placement == "outside-marks"):
            notes.append(message + "; foreground is explicitly declared outside the marks; verify placement at final size")
        else:
            warnings.append(message)
    foreground_background_contrast = contrast_ratio(foreground_rgb, background_rgb)
    label_threshold = THRESHOLDS["large_text" if role == "large_text" else "normal_text"]
    if foreground_placement == "outside-marks" and foreground_background_contrast < label_threshold:
        warnings.append(
            f"Outside foreground text has {foreground_background_contrast:.2f}:1 contrast against "
            f"the background, below {label_threshold}:1"
        )
    if low_gray:
        message = (
            f"{len(low_gray)} pair(s) have CIE L* separation below {min_gray_delta:.1f} "
            "(EasyPlot heuristic, not a WCAG criterion)"
        )
        if identity_supported:
            notes.append(message + "; declared identity cues may cover this; confirm at final size")
        else:
            warnings.append(message + "; inspect how group identity is encoded in the actual plot")
    if geometry in {"bar", "box"}:
        recommendations.append(
            "Keep pastel fills. With readable category labels, fixed positions and visible boundaries, "
            "extra hatching/markers are usually unnecessary. Repeated or stacked groups need a separate review."
        )
    elif geometry == "line":
        recommendations.append(
            "Trace lines through crossings. Use named group-specific markers/linestyles or direct end labels "
            "when identity is colour-only; keep existing adequate cues. Consider easyplot_lines for thin strokes."
        )
    elif geometry == "scatter":
        recommendations.append(
            "For overlapping groups, use group-specific marker shapes or facets and check occlusion; "
            "a shared dark outline alone does not identify groups."
        )
    else:
        recommendations.append("Declare --geometry and existing --cue values before choosing a styling change.")
    return {
        "role": role,
        "threshold": threshold,
        "background": background,
        "foreground": foreground,
        "foreground_contrast_vs_background": round(foreground_background_contrast, 4),
        "min_gray_delta": min_gray_delta,
        "gray_threshold_kind": "heuristic",
        "context": {
            "geometry": geometry, "declared_cues": sorted(set(cues)),
            "foreground_placement": foreground_placement,
            "source": "caller declaration; not image detection",
        },
        "colours": entries,
        "pairs": pairs,
        "summary": {
            "min_contrast_vs_background": min(entry["contrast_vs_background"] for entry in entries),
            "min_contrast_vs_foreground": min(entry["contrast_vs_foreground"] for entry in entries),
            "min_pairwise_cie_lstar_delta": min((pair["delta_cie_lstar"] for pair in pairs), default=None),
            "passes_foreground_threshold": not low_foreground,
            "passes_grayscale_screen": not low_gray,
        },
        "warnings": warnings,
        "notes": notes,
        "recommendations": recommendations,
    }


def _parse_custom_colours(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"custom colour must use NAME=HEX: {value}")
        name, hex_value = value.split("=", 1)
        if not name.strip():
            raise ValueError(f"custom colour name is empty: {value}")
        result[name.strip()] = hex_value.strip()
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", choices=sorted(BUILTIN_PALETTES), default="easyplot_conditions")
    parser.add_argument("--color", action="append", default=[], help="custom NAME=HEX colour; repeat as needed")
    parser.add_argument("--background", default="#FFFFFF")
    parser.add_argument("--foreground", default=EASYPLOT_INK)
    parser.add_argument("--role", choices=sorted(THRESHOLDS), default="graphical")
    parser.add_argument("--min-gray-delta", type=float, default=10.0)
    parser.add_argument("--geometry", choices=GEOMETRIES, default="unspecified")
    parser.add_argument("--cue", action="append", choices=CUES, default=[], help="existing group-specific cue; repeat as needed")
    parser.add_argument("--foreground-placement", choices=FOREGROUND_PLACEMENTS, default="unspecified",
                        help="declare whether foreground labels are on or outside the coloured marks")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        colours = dict(BUILTIN_PALETTES[args.palette])
        colours.update(_parse_custom_colours(args.color))
        report = audit_palette(
            colours,
            background=args.background,
            foreground=args.foreground,
            role=args.role,
            min_gray_delta=args.min_gray_delta,
            geometry=args.geometry,
            cues=tuple(args.cue),
            foreground_placement=args.foreground_placement,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Palette role: {report['role']} (threshold {report['threshold']}:1)")
        for entry in report["colours"]:
            print(
                f"{entry['name']}: bg={entry['contrast_vs_background']:.2f}:1 "
                f"fg={entry['contrast_vs_foreground']:.2f}:1 L*={entry['cie_lstar']:.2f}"
            )
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for note in report["notes"]:
            print(f"NOTE: {note}")
        for recommendation in report["recommendations"]:
            print(f"SUGGESTION: {recommendation}")
    return 1 if args.fail_on_warning and report["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
