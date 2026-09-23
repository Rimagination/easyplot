"""Focused regression checks for EasyPlot metadata and palette audits."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
import sys
import tempfile

import matplotlib.pyplot as plt
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject,
    NameObject, NumberObject,
)


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from easyplot_metadata import inspect_file, main as metadata_main  # noqa: E402
from easyplot_palette_audit import (  # noqa: E402
    BUILTIN_PALETTES, audit_palette, contrast_ratio, grayscale_hex, parse_hex,
)
from easyplot_py import publication_context, save_figure  # noqa: E402


def check_raster_metadata(output_dir: Path) -> None:
    nominal = output_dir / "nominal_300.png"
    report = inspect_file(nominal, 300, 180, "forbid", target_height_mm=80, size_tolerance_mm=0)
    properties = report["properties"]
    assert not report["errors"] and not report["warnings"], report
    assert math.isclose(properties["width_mm"], 2125 * 25.4 / properties["dpi_x"])
    assert math.isclose(properties["height_mm"], 944 * 25.4 / properties["dpi_y"])
    assert 0 < properties["size_rounding_tolerance_mm"]["width"] < 0.1
    assert math.isclose(properties["effective_dpi_at_target_height"], 944 * 25.4 / 80)
    assert properties["dpi_check"]["source"] == "minimum_effective_axis"
    assert set(properties["dpi_check"]["axes"]) == {"x", "y"}
    enlarged = inspect_file(nominal, min_dpi=300, target_width_mm=180, target_height_mm=160)
    assert any("raster height" in warning for warning in enlarged["warnings"])
    assert any("DPI" in warning and "y axis" in warning for warning in enlarged["warnings"])
    assert not any("x axis" in warning for warning in enlarged["warnings"])
    height_only = inspect_file(nominal, min_dpi=300, target_height_mm=80)
    assert not height_only["warnings"]
    assert height_only["properties"]["dpi_check"]["source"] == "effective_at_target_height"

    for extension in ("png", "tiff", "jpg"):
        path = output_dir / f"physical_axes.{extension}"
        Image.new("RGB", (300, 300), "white").save(path, dpi=(300, 150))
        report = inspect_file(path, target_width_mm=25.4, target_height_mm=50.8)
        assert not report["errors"] and not report["warnings"], report
        assert abs(report["properties"]["width_mm"] - 25.4) < 0.01
        assert abs(report["properties"]["height_mm"] - 50.8) < 0.01

    missing = output_dir / "missing_dpi.png"
    Image.new("RGB", (300, 300), "white").save(missing)
    report = inspect_file(missing, min_dpi=300, target_width_mm=25.4, target_height_mm=25.4)
    assert report["properties"]["width_mm"] is None and report["properties"]["height_mm"] is None
    assert report["properties"]["effective_dpi_at_target_width"] == 300
    assert len(report["warnings"]) == 2 and all("raster" in warning for warning in report["warnings"])
    assert not inspect_file(missing)["warnings"]  # No size or resolution contract was requested.
    invalid_dpi = output_dir / "invalid_dpi.png"
    Image.new("RGB", (10, 10), "white").save(invalid_dpi, dpi=(0, 300))
    report = inspect_file(invalid_dpi, min_dpi=300)
    assert not report["errors"] and report["properties"]["dpi_x"] is None
    assert any("x axis is unavailable" in warning for warning in report["warnings"])

    opaque = output_dir / "opaque_alpha.png"
    translucent = output_dir / "translucent.png"
    Image.new("RGBA", (2, 2), (255, 255, 255, 255)).save(opaque)
    Image.new("RGBA", (2, 2), (255, 255, 255, 100)).save(translucent)
    assert not inspect_file(opaque, alpha_policy="forbid")["warnings"]
    assert inspect_file(translucent, alpha_policy="forbid")["properties"]["has_transparency"]
    assert inspect_file(translucent, alpha_policy="forbid")["warnings"]

    for option, values in (
        ("target_width_mm", (0, -1, float("nan"), float("inf"))),
        ("target_height_mm", (0, -1, float("nan"), float("inf"))),
        ("min_dpi", (0, -1, float("nan"), float("inf"))),
        ("size_tolerance_mm", (-1, float("nan"), float("inf"))),
        ("expected_svg_text", ("auto", "")),
        ("require_embedded_fonts", ("false", 1)),
    ):
        for value in values:
            report = inspect_file(nominal, **{option: value})
            assert any(option in error for error in report["errors"]), (option, value, report)


def write_svg(output_dir: Path, name: str, body: str = "", dimensions: str = 'width="180mm" height="80mm"') -> Path:
    path = output_dir / f"{name}.svg"
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" {dimensions}>{body}</svg>', encoding="utf-8")
    return path


def check_svg_metadata(output_dir: Path) -> None:
    editable = write_svg(output_dir, "editable", '<text x="1" y="12" style="font-family: Arial">中文 signal α</text>')
    report = inspect_file(editable, target_width_mm=180, target_height_mm=80, expected_svg_text="editable")
    assert not report["errors"] and not report["warnings"], report
    assert report["properties"]["text_mode_evidence"] == "editable-text-present"
    assert report["properties"]["font_families"] == ["Arial"]
    assert any("text elements remain" in warning for warning in inspect_file(editable, expected_svg_text="outline")["warnings"])

    path_data = '<path d="M0 0 L10 0 L10 10 Z"/>'
    outlined = write_svg(output_dir, "outline", path_data)
    report = inspect_file(outlined, expected_svg_text="outline")
    assert not report["warnings"] and report["properties"]["path_elements"] == 1
    assert report["properties"]["text_mode_evidence"] == "paths-without-text"
    assert any("ordinary diagram geometry" in limit for limit in report["properties"]["inspection_limits"])
    assert inspect_file(outlined, expected_svg_text="editable")["warnings"]

    definitions = '<defs><path id="glyph" d="M0 0 L10 0 L10 10 Z"/></defs>'
    via_use = write_svg(output_dir, "used_outline", definitions + '<use href="#glyph"/><use href="#glyph" x="20"/>')
    report = inspect_file(via_use, expected_svg_text="outline")
    assert not report["warnings"] and report["properties"]["visible_path_instances"] == 2
    cycle = write_svg(output_dir, "cyclic_use", '<defs><g id="cycle"><use href="#cycle"/></g></defs><use href="#cycle"/>')
    assert inspect_file(cycle, expected_svg_text="outline")["warnings"]

    # Cairo can expose all glyphs through a filter's local feImage group reference.
    cairo_definitions = (
        '<defs xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<symbol id="cairo-glyph">' + path_data + '</symbol>'
        '<g id="cairo-source"><use xlink:href="#cairo-glyph"/></g>'
        '<g id="cairo-group"><g><use xlink:href="#cairo-source"/></g></g>'
        '<g id="cairo-destination"><rect width="10" height="10"/></g>'
        '<g id="unused-source">' + path_data + '</g>'
        '<filter id="cairo-filter">'
        '<feImage xlink:href="#cairo-group" result="source"/>'
        '<feImage xlink:href="#cairo-destination" result="destination"/>'
        '<feComposite in="source" in2="destination" operator="over"/>'
        '</filter><filter id="unused-filter"><feImage href="#unused-source"/></filter></defs>'
    )
    for name, attributes in (("cairo_filter", 'filter="url(#cairo-filter)"'),
                             ("cairo_inline_filter", 'style="filter:url(\'#cairo-filter\')"')):
        body = cairo_definitions + f'<g {attributes}><rect width="10" height="10"/></g>'
        report = inspect_file(write_svg(output_dir, name, body), expected_svg_text="outline")
        assert not report["errors"] and not report["warnings"], report
        assert report["properties"]["path_elements"] == 2
        assert report["properties"]["visible_path_instances"] == 1  # Unused defs/filter stay excluded.
        assert report["properties"]["text_mode_evidence"] == "paths-without-text"
        assert any("filter effects" in limit for limit in report["properties"]["inspection_limits"])
    unused = write_svg(output_dir, "unused_cairo_filters", cairo_definitions +
                       '<filter id="unused-at-root"><feImage href="#unused-source"/></filter><rect width="10" height="10"/>')
    report = inspect_file(unused, expected_svg_text="outline")
    assert not report["errors"] and report["properties"]["visible_path_instances"] == 0
    assert any("no visible path evidence" in warning for warning in report["warnings"])
    for name, sibling, expected_paths in (("cyclic_filter", "", 0), ("cyclic_filter_with_path", path_data, 1)):
        body = ('<defs><filter id="loop-filter"><feImage href="#loop-group"/></filter>'
                '<g id="loop-group" filter="url(#loop-filter)"><rect width="10" height="10"/>' + sibling +
                '</g></defs><g filter="url(#loop-filter)"><rect width="10" height="10"/></g>')
        report = inspect_file(write_svg(output_dir, name, body), expected_svg_text="outline")
        assert not report["errors"] and report["properties"]["visible_path_instances"] == expected_paths, report
        assert bool(report["warnings"]) is (expected_paths == 0), report

    for name, body in (
        ("empty", ""), ("rect_only", '<rect width="5" height="5"/>'),
        ("image_only", '<image href="data:image/png;base64,"/>'),
        ("unused_definitions", definitions), ("empty_path", '<path d=""/>'),
        ("hidden", f'<g style="display:none">{path_data}</g>'),
        ("invisible", f'<g opacity="0">{path_data}</g>'),
        ("unpainted", f'<g fill="none" stroke="none">{path_data}</g>'),
    ):
        path = write_svg(output_dir, name, body)
        assert not inspect_file(path)["warnings"], name
        report = inspect_file(path, expected_svg_text="outline")
        assert not report["errors"] and report["properties"]["visible_path_instances"] == 0, report
        assert any("no visible path evidence" in warning for warning in report["warnings"]), name
    for name, body in (("empty_text", "<text/>"), ("hidden_text", '<g visibility="hidden"><text>label</text></g>')):
        report = inspect_file(write_svg(output_dir, name, body), expected_svg_text="editable")
        assert any("no visible nonempty text" in warning for warning in report["warnings"])

    for dimensions in ('width="100%" height="80mm"', 'width="10em" height="80mm"',
                       'width="12frogs" height="80mm"', 'width="0" height="80mm"',
                       'width="-1mm" height="80mm"', 'width="1e999mm" height="80mm"',
                       'height="80mm"', 'width="NaN" height="80mm"'):
        path = write_svg(output_dir, "bad_width", dimensions=dimensions)
        report = inspect_file(path, target_width_mm=180)
        assert not report["errors"] and report["properties"]["width_mm"] is None, report
        assert any("SVG width is missing or invalid" in warning for warning in report["warnings"])
    for dimensions in ('width="180mm" height="-1"', 'width="180mm" height="0mm"', 'width="180mm"', 'viewBox="0 0 180 80"'):
        report = inspect_file(write_svg(output_dir, "bad_height", dimensions=dimensions))
        assert report["properties"]["height_mm"] is None
        assert any("SVG height is missing or invalid" in warning for warning in report["warnings"])
    for unit, value in (("mm", "25.4"), ("cm", "2.54"), ("in", "1"), ("pt", "72"),
                        ("pc", "6"), ("px", "96"), ("", "96"), ("q", "101.6"), ("mm", "2.54e1")):
        path = write_svg(output_dir, "units", dimensions=f'width="{value}{unit}" height="{value}{unit}"')
        report = inspect_file(path, target_width_mm=25.4, target_height_mm=25.4, size_tolerance_mm=0)
        assert not report["warnings"] and not report["errors"], (unit, report)

    near = write_svg(output_dir, "near_size", dimensions='width="180.15mm" height="80.15mm"')
    assert not inspect_file(near, target_width_mm=180, target_height_mm=80)["warnings"]
    assert len(inspect_file(near, target_width_mm=180, target_height_mm=80, size_tolerance_mm=0.1)["warnings"]) == 2
    for name, body, alpha in (
        ("opaque_svg", '<g opacity="1" style="fill-opacity:1; stroke-opacity:100%">' + path_data + '</g>', False),
        ("override_opacity", '<g opacity="0.5" style="opacity:1">' + path_data + '</g>', False),
        ("unrelated_opacity_word", '<g data-note="opacity:0.5">' + path_data + '</g>', False),
        ("group_alpha", '<g opacity="0.5">' + path_data + '</g>', True),
        ("style_alpha", '<g style="fill-opacity:50%">' + path_data + '</g>', True),
        ("negative_alpha", '<g opacity="-0.2">' + path_data + '</g>', True),
    ):
        report = inspect_file(write_svg(output_dir, name, body), alpha_policy="forbid")
        assert report["properties"]["has_alpha_markers"] is alpha
        assert bool(report["warnings"]) is alpha, report
    for value, alpha in (("1", False), (".5", True)):
        css = write_svg(output_dir, "nested_css", '<style>@media print { .a { opacity:' + value + '; } }</style>' + path_data)
        report = inspect_file(css, alpha_policy="forbid")
        assert report["properties"]["stylesheet_has_alpha_markers"] is alpha
        assert bool(report["warnings"]) is alpha, report
        assert any("Nested CSS" in limit for limit in report["properties"]["inspection_limits"])
    unresolved = write_svg(output_dir, "css_variable", '<g style="opacity:var(--alpha)">' + path_data + '</g>')
    assert inspect_file(unresolved, alpha_policy="forbid")["warnings"]
    broken = output_dir / "broken.svg"
    broken.write_text("<svg", encoding="utf-8")
    assert inspect_file(broken)["errors"]
    broken.write_text('<document width="180mm" height="80mm"/>', encoding="utf-8")
    assert inspect_file(broken)["errors"]


def pdf_font(writer: PdfWriter, name: str, subtype: str = "Type1", font_file: str | None = None):
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject(f"/{subtype}"), NameObject("/BaseFont"): NameObject(f"/{name}")})
    if font_file:
        stream = DecodedStreamObject()
        # Deliberately not a real font program: these tests check resource evidence only.
        stream.set_data(b"metadata fixture font bytes")
        font[NameObject("/FontDescriptor")] = writer._add_object(DictionaryObject({NameObject(font_file): writer._add_object(stream)}))
    return writer._add_object(font)


def check_pdf_metadata(output_dir: Path) -> None:
    writer = PdfWriter()
    first = writer.add_blank_page(width=180 * 72 / 25.4, height=80 * 72 / 25.4)
    second = writer.add_blank_page(width=180 * 72 / 25.4, height=90 * 72 / 25.4)
    type1 = pdf_font(writer, "EmbeddedType1", font_file="/FontFile")
    cff = pdf_font(writer, "EmbeddedCFF", font_file="/FontFile3")
    cid = pdf_font(writer, "BilingualCID", "CIDFontType2", "/FontFile2")
    composite = pdf_font(writer, "BilingualComposite", "Type0")
    composite.get_object()[NameObject("/DescendantFonts")] = ArrayObject([cid])
    type3 = pdf_font(writer, "Type3Glyphs", "Type3")
    glyph = DecodedStreamObject()
    glyph.set_data(b"10 0 d0 0 0 m 10 0 l 10 10 l h f")
    type3.get_object()[NameObject("/CharProcs")] = DictionaryObject({NameObject("/A"): writer._add_object(glyph)})
    first[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({
        NameObject("/F1"): type1, NameObject("/FCFF"): cff,
        NameObject("/FCJK"): composite, NameObject("/FType3"): type3,
    })})

    missing = pdf_font(writer, "Helvetica")
    nested_missing = pdf_font(writer, "Courier")
    inner = DecodedStreamObject()
    inner.set_data(b"BT /Nested 10 Tf (nested) Tj ET")
    inner.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"), NameObject("/BBox"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(100), NumberObject(100)])})
    inner_ref = writer._add_object(inner)
    inner[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/Nested"): nested_missing}),
        NameObject("/XObject"): DictionaryObject({NameObject("/Self"): inner_ref}),
    })
    outer = DecodedStreamObject()
    outer.set_data(b"/Inner Do")
    outer.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"), NameObject("/BBox"): inner["/BBox"], NameObject("/Resources"): DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Inner"): inner_ref})})})
    second[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/Missing"): missing}),
        NameObject("/XObject"): DictionaryObject({NameObject("/Outer"): writer._add_object(outer)}),
    })
    path = output_dir / "all_pages_nested_fonts.pdf"
    writer.write(path)
    report = inspect_file(path, target_width_mm=180, target_height_mm=80, require_embedded_fonts=True)
    properties = report["properties"]
    assert not report["errors"], report
    assert properties["first_page_fonts"] == ["BilingualComposite", "EmbeddedCFF", "EmbeddedType1", "Type3Glyphs"]
    assert len(properties["page_sizes"]) == 2 and abs(properties["page_sizes"][1]["height_mm"] - 90) < 1e-6
    assert any("page 2 height" in warning for warning in report["warnings"])
    assert properties["all_fonts_embedded"] is False and not properties["font_scan_issues"]
    fonts = properties["pdf_fonts"]
    assert len(fonts) == 6, fonts  # Cyclic Form resources terminate without duplicate records.
    by_name = {font["base_font"]: font for font in fonts}
    assert by_name["EmbeddedType1"]["font_file_keys"] == ["/FontFile"]
    assert by_name["EmbeddedCFF"]["font_file_keys"] == ["/FontFile3"]
    assert by_name["BilingualComposite"]["descendant_fonts"][0]["font_file_keys"] == ["/FontFile2"]
    assert by_name["Type3Glyphs"]["font_file_keys"] == []
    assert by_name["Type3Glyphs"]["type3_charprocs"] == {"count": 1, "stream_count": 1}
    assert all(by_name[name]["embedded"] is True for name in properties["first_page_fonts"])
    assert by_name["Courier"]["page"] == 2 and "/Outer/Resources/XObject/Inner/Resources/Font/Nested" in by_name["Courier"]["resource_path"]
    font_warnings = [warning for warning in report["warnings"] if "font embedding" in warning]
    assert len(font_warnings) == 2 and all("page 2" in warning for warning in font_warnings)
    assert any("/Nested" in warning for warning in font_warnings)
    assert not inspect_file(path)["warnings"]  # Font enforcement is opt-in.

    embedded_writer = PdfWriter()
    embedded_writer.add_page(first)
    embedded_path = output_dir / "embedded_evidence.pdf"
    embedded_writer.write(embedded_path)
    report = inspect_file(embedded_path, require_embedded_fonts=True)
    assert not report["warnings"] and report["properties"]["all_fonts_embedded"] is True
    assert any("not certified" in limit for limit in report["properties"]["inspection_limits"])

    for case in ("no_fonts", "bad_stream", "empty_stream", "unknown_subtype", "descendant_cycle", "bad_charprocs", "bad_resources", "bad_font_dictionary"):
        bad_writer = PdfWriter()
        page = bad_writer.add_blank_page(width=72, height=36)
        if case != "no_fonts":
            font = pdf_font(bad_writer, "Uncertain", "Type0" if case == "descendant_cycle" else "Type1")
            if case in {"bad_stream", "empty_stream"}:
                value = NumberObject(42)
                if case == "empty_stream":
                    empty = DecodedStreamObject()
                    empty.set_data(b"")
                    value = bad_writer._add_object(empty)
                font.get_object()[NameObject("/FontDescriptor")] = DictionaryObject({NameObject("/FontFile2"): value})
            elif case == "unknown_subtype":
                del font.get_object()["/Subtype"]
            elif case == "descendant_cycle":
                font.get_object()[NameObject("/DescendantFonts")] = ArrayObject([font])
            elif case == "bad_charprocs":
                font.get_object()[NameObject("/Subtype")] = NameObject("/Type3")
                font.get_object()[NameObject("/CharProcs")] = DictionaryObject({NameObject("/A"): NumberObject(1)})
            page[NameObject("/Resources")] = (NumberObject(1) if case == "bad_resources" else DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}))
            if case == "bad_font_dictionary":
                form = DecodedStreamObject()
                form.set_data(b"")
                form.update({NameObject("/Subtype"): NameObject("/Form"), NameObject("/Resources"): DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/NestedValid"): pdf_font(bad_writer, "NestedValid", "TrueType", "/FontFile2")})})})
                page[NameObject("/Resources")][NameObject("/Font")] = NumberObject(1)
                page[NameObject("/Resources")][NameObject("/XObject")] = DictionaryObject({NameObject("/Form"): bad_writer._add_object(form)})
        invalid = output_dir / f"{case}.pdf"
        bad_writer.write(invalid)
        report = inspect_file(invalid, require_embedded_fonts=True)
        assert not report["errors"] and report["properties"]["all_fonts_embedded"] is None, (case, report)
        assert bool(report["warnings"]) is (case != "no_fonts"), (case, report)
        if case == "no_fonts":
            assert report["properties"]["pdf_fonts"] == [] and report["properties"]["first_page_fonts"] == []
        elif case == "bad_font_dictionary":
            assert report["properties"]["pdf_fonts"][0]["base_font"] == "NestedValid"
            assert report["properties"]["pdf_fonts"][0]["embedded"] is True

    for case, coordinates, unit in (
        ("negative_width", [0, 0, -72, 36], 1), ("zero_height", [0, 0, 72, 0], 1),
        ("negative_height", [0, 0, 72, -36], 1), ("missing_box", None, 1),
        ("invalid_unit", [0, 0, 72, 36], -1), ("scaled_unit", [0, 0, 72, 36], 2),
    ):
        size_writer = PdfWriter()
        page = size_writer.add_blank_page(width=72, height=36)
        if coordinates is None:
            del page["/MediaBox"]
        else:
            page[NameObject("/MediaBox")] = ArrayObject([FloatObject(value) for value in coordinates])
        page[NameObject("/UserUnit")] = FloatObject(unit)
        invalid = output_dir / f"{case}.pdf"
        size_writer.write(invalid)
        report = inspect_file(invalid)
        assert not report["errors"], report
        if case == "scaled_unit":
            assert not report["warnings"] and report["properties"]["page_width_mm"] == 50.8
            assert report["properties"]["page_height_mm"] == 25.4
        else:
            assert any("missing or invalid" in warning for warning in report["warnings"]), (case, report)


def check_metadata_cli(output_dir: Path) -> None:
    for name, extra, expected_status in (
        ("editable.svg", ["--expected-svg-text", "editable"], 0),
        ("empty.svg", ["--expected-svg-text", "outline"], 1),
        ("embedded_evidence.pdf", ["--require-embedded-fonts"], 0),
        ("all_pages_nested_fonts.pdf", ["--require-embedded-fonts"], 1),
        ("editable.svg", ["--target-height-mm", "-1"], 1),
    ):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = metadata_main([str(output_dir / name), "--json", "--fail-on-warning", "--target-width-mm", "180", "--target-height-mm", "80", "--size-tolerance-mm", "0.2", *extra])
        reports = json.loads(stdout.getvalue())
        assert status == expected_status, (name, reports)
        assert len(reports) == 1
        if expected_status == 0:
            assert not reports[0]["warnings"] and not reports[0]["errors"]
    assert inspect_file(output_dir / "absent.png")["errors"]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="easyplot-qa-") as temp_dir:
        output_dir = Path(temp_dir)
        with publication_context(font_family="Arial"):
            fig, ax = plt.subplots(figsize=(180 / 25.4, 80 / 25.4), dpi=160)
            ax.plot([0, 1, 2], [0, 1, 0], color="#252A2E")
            ax.set_xlabel("time")
            ax.set_ylabel("signal")
            outputs = [
                save_figure(fig, output_dir / "figure.png", dpi=160),
                save_figure(fig, output_dir / "figure.pdf", dpi=160),
                save_figure(fig, output_dir / "figure.svg", dpi=160),
            ]
        plt.close(fig)

        reports = [inspect_file(path, target_width_mm=180) for path in outputs]
        assert all(not report["errors"] for report in reports)
        assert reports[0]["properties"]["width_px"] > 1000
        assert abs(reports[1]["properties"]["page_width_mm"] - 180) < 0.2
        assert reports[2]["properties"]["font_families"]

        # PNG stores integer pixels/metre; canvas dimensions also round to pixels.
        nominal_png = output_dir / "nominal_300.png"
        Image.new("RGB", (2125, 944), "white").save(nominal_png, dpi=(300, 300))
        assert not inspect_file(nominal_png, min_dpi=300)["warnings"]
        assert not inspect_file(nominal_png, min_dpi=300, target_width_mm=180)["warnings"]
        # Enlarging a 300-dpi file must use the effective resolution at placement.
        assert inspect_file(nominal_png, min_dpi=300, target_width_mm=360)["warnings"]
        anisotropic_png = output_dir / "unequal_dpi.png"
        Image.new("RGB", (64, 64), "white").save(anisotropic_png, dpi=(300, 72))
        assert inspect_file(anisotropic_png, min_dpi=300)["warnings"]
        low_dpi_png = output_dir / "below_300.png"
        Image.new("RGB", (64, 64), "white").save(low_dpi_png, dpi=(299, 299))
        assert inspect_file(low_dpi_png, min_dpi=300)["warnings"]
        assert inspect_file(nominal_png, min_dpi=float("nan"))["errors"]
        assert inspect_file(nominal_png, target_width_mm=0)["errors"]

        check_raster_metadata(output_dir)
        check_svg_metadata(output_dir)
        check_pdf_metadata(output_dir)
        check_metadata_cli(output_dir)

        palette_report = audit_palette(
            {"steel": "#568FC3", "coral": "#F59092"},
            min_gray_delta=2,
        )
        assert palette_report["summary"]["passes_foreground_threshold"]
        assert palette_report["summary"]["passes_grayscale_screen"]

        # Numbers remain identical across plot contexts; only advice changes.
        palette = BUILTIN_PALETTES["easyplot_conditions"]
        generic = audit_palette(palette)
        bars = audit_palette(palette, geometry="bar", cues=("position-labels", "outline"))
        lines = audit_palette(palette, geometry="line", cues=("outline",))
        encoded_lines = audit_palette(palette, geometry="line", cues=("markers", "linestyles"))
        assert generic["pairs"] == bars["pairs"] == lines["pairs"] == encoded_lines["pairs"]
        assert len([pair for pair in generic["pairs"] if pair["below_heuristic"]]) == 3
        assert generic["gray_threshold_kind"] == "heuristic"
        assert not bars["warnings"] and bars["notes"]
        assert not bars["summary"]["passes_grayscale_screen"]
        assert any("heuristic" in warning for warning in lines["warnings"])
        assert not any("heuristic" in warning for warning in encoded_lines["warnings"])
        assert encoded_lines["warnings"]  # light strokes still need contrast review
        dark_scatter = {"A": "#333333", "B": "#444444"}
        for placement in (None, "on-marks"):
            options = {} if placement is None else {"foreground_placement": placement}
            report = audit_palette(dark_scatter, geometry="scatter", cues=("direct-labels",), **options)
            assert any("foreground" in warning for warning in report["warnings"])
        outside = audit_palette(dark_scatter, geometry="scatter", cues=("direct-labels",), foreground_placement="outside-marks")
        assert not outside["warnings"]
        invisible_outside = audit_palette(dark_scatter, foreground="#FFFFFF", geometry="scatter", cues=("direct-labels",), foreground_placement="outside-marks")
        assert any("foreground" in warning for warning in invisible_outside["warnings"])
        dark_lines = audit_palette(BUILTIN_PALETTES["easyplot_lines"], geometry="line", cues=("markers", "linestyles"), foreground_placement="outside-marks")
        assert not dark_lines["warnings"]
        assert abs(contrast_ratio(parse_hex("#000000"), parse_hex("#FFFFFF")) - 21) < 1e-12
        assert grayscale_hex("#000000") == "#000000"
        assert grayscale_hex("#FFFFFF") == "#FFFFFF"
        assert parse_hex("#FFFFFF00", (0, 0, 0)) == (0, 0, 0)
        try:
            audit_palette({}, geometry="line")
        except ValueError:
            pass
        else:
            raise AssertionError("empty palettes must fail with a useful validation error")

    print("EasyPlot metadata and palette QA checks passed")


if __name__ == "__main__":
    main()
