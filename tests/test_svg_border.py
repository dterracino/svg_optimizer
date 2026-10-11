"""Geometry and CLI regressions for vector-only SVG borders."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree as ET

import pytest
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from svg_optimizer.cli import parse_arguments
from svg_optimizer.svg_border import BorderGenerationError, SVG_NS, SVGBorderGenerator


def test_package_metadata_and_cli_version_match(capsys: pytest.CaptureFixture[str]) -> None:
    import tomllib

    from svg_optimizer import __version__

    metadata = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert metadata["project"]["version"] == __version__ == "0.2.0"
    with pytest.raises(SystemExit) as error:
        parse_arguments(["--version"])
    assert error.value.code == 0
    assert capsys.readouterr().out.strip().endswith("0.2.0")


def svg(body: str, attributes: str = 'viewBox="0 0 100 100"') -> str:
    """Wrap test artwork in an SVG document."""
    return f'<svg xmlns="{SVG_NS}" {attributes}>{body}</svg>'


def outline(document: str) -> Polygon:
    """Evaluate the saved cubic path independently of the generator's flattening."""
    curves = border_curves(document)
    points = [curves[0][0]]
    for curve in curves:
        points.extend(cubic_point(curve, i / 100) for i in range(1, 101))
    return Polygon(points)


def border_curves(document: str) -> list[tuple[tuple[float, float], ...]]:
    """Parse serialized controls and require real cubics, not line commands."""
    root = ET.fromstring(document)
    path = root.find(f"{{{SVG_NS}}}path[@id='svg-optimizer-border']")
    assert path is not None
    coordinates = [
        (float(x), float(y))
        for x, y in re.findall(r"([+\-\d.eE]+),([+\-\d.eE]+)", path.attrib["d"])
    ]
    assert re.findall(r"[A-DF-Za-df-z]", path.attrib["d"]) == (
        ["M"] + ["C"] * ((len(coordinates) - 1) // 3) + ["Z"]
    )
    assert len(coordinates) >= 37 and (len(coordinates) - 1) % 3 == 0
    curves = []
    start = coordinates[0]
    for i in range(1, len(coordinates), 3):
        controls = (start, coordinates[i], coordinates[i + 1], coordinates[i + 2])
        curves.append(controls)
        start = controls[-1]
    assert start == curves[0][0]
    return curves


def cubic_point(controls: tuple[tuple[float, float], ...], t: float) -> tuple[float, float]:
    """Evaluate a cubic with Bernstein weights without using production helpers."""
    weights = ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3)
    return (
        sum(w * p[0] for w, p in zip(weights, controls)),
        sum(w * p[1] for w, p in zip(weights, controls)),
    )


@pytest.mark.parametrize("smoothing", [0, 5, 25, 100])
def test_cubic_joins_are_c2_continuous_including_closing_seam(smoothing: float) -> None:
    """Inspect serialized derivatives: rounded stroke joins must not hide corners."""
    document = SVGBorderGenerator(3, smoothing=smoothing).add_to_svg(
        svg('<ellipse cx="50" cy="50" rx="35" ry="20"/>')
    )
    curves = border_curves(document)
    for current, following in zip(curves, curves[1:] + curves[:1]):
        assert current[-1] == following[0]
        incoming = tuple(3 * (current[3][i] - current[2][i]) for i in range(2))
        outgoing = tuple(3 * (following[1][i] - following[0][i]) for i in range(2))
        assert math.hypot(*incoming) > 0
        assert incoming == pytest.approx(outgoing, abs=1e-10)
        second_in = tuple(6 * (current[3][i] - 2 * current[2][i] + current[1][i]) for i in range(2))
        second_out = tuple(
            6 * (following[0][i] - 2 * following[1][i] + following[2][i]) for i in range(2)
        )
        assert second_in == pytest.approx(second_out, abs=1e-10)


def test_circular_border_has_curved_segments_and_uniform_radius() -> None:
    """A circular source must not acquire a faceted or wavy outline."""
    document = SVGBorderGenerator(5, smoothing=10, tolerance=0.02).add_to_svg(
        svg('<circle cx="50" cy="50" r="25"/>')
    )
    radii = []
    for curve in border_curves(document):
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            p = cubic_point(curve, t)
            radii.append(math.hypot(p[0] - 50, p[1] - 50))
            first = tuple(
                3
                * (
                    (1 - t) ** 2 * (curve[1][i] - curve[0][i])
                    + 2 * (1 - t) * t * (curve[2][i] - curve[1][i])
                    + t**2 * (curve[3][i] - curve[2][i])
                )
                for i in range(2)
            )
            second = tuple(
                6
                * (
                    (1 - t) * (curve[2][i] - 2 * curve[1][i] + curve[0][i])
                    + t * (curve[3][i] - 2 * curve[2][i] + curve[1][i])
                )
                for i in range(2)
            )
            assert abs(first[0] * second[1] - first[1] * second[0]) > 0.1
    assert min(radii) - 25 - 0.5 >= 5
    assert max(radii) - min(radii) < 0.04


def test_gaussian_weights_suppress_fine_details_more_than_broad_features() -> None:
    """Measure attenuation, symmetry, and seam wrapping on known periodic signals."""
    count = 256
    knots = [
        (math.cos(2 * math.pi * i / count), math.cos(24 * math.pi * i / count))
        for i in range(count)
    ]
    amplitudes = []
    for sigma in (1, 3, 6):
        generator = SVGBorderGenerator(1, smoothing=sigma)
        result = generator._gaussian_perimeter(knots, 1)
        amplitude = tuple(
            2
            / count
            * math.fsum(
                result[i][axis] * math.cos(frequency * 2 * math.pi * i / count)
                for i in range(count)
            )
            for axis, frequency in ((0, 1), (1, 12))
        )
        expected = tuple(
            math.exp(-0.5 * (sigma * frequency * 2 * math.pi / count) ** 2) for frequency in (1, 12)
        )
        assert amplitude == pytest.approx(expected, abs=0.0002)
        assert result[1] == pytest.approx(result[-1], abs=1e-12)
        amplitudes.append(amplitude)
    assert amplitudes[0][1] > amplitudes[1][1] > amplitudes[2][1]
    assert amplitudes[2][1] < 0.22
    assert amplitudes[2][0] > 0.98
    assert SVGBorderGenerator(1, smoothing=0)._gaussian_perimeter(knots, 1) == knots


def test_gaussian_wraps_multiple_turns_without_seam_or_coordinate_bias() -> None:
    generator = SVGBorderGenerator(1, smoothing=20)
    knots = [(math.cos(i * math.pi / 6), math.sin(i * math.pi / 6)) for i in range(12)]
    result = generator._gaussian_perimeter(knots, 1)
    assert max(math.hypot(x, y) for x, y in result) < 0.0001
    translated = generator._gaussian_perimeter([(x + 10000, y - 20000) for x, y in knots], 1)
    for a, b in zip(result, translated):
        assert b == pytest.approx((a[0] + 10000, a[1] - 20000), abs=1e-10)
    constant = [(12345.0, -34567.0)] * 12
    assert generator._gaussian_perimeter(constant, 1) == constant
    with pytest.raises(BorderGenerationError, match="averaging budget"):
        SVGBorderGenerator(1, smoothing=1e6)._gaussian_perimeter(knots, 1)


def test_gaussian_smoothing_simplifies_wavy_border_without_losing_clearance() -> None:
    """Stronger smoothing reduces excess turning on an enclosing wavy outline."""
    points = []
    for i in range(720):
        angle = 2 * math.pi * i / 720
        radius = 50 + 2 * math.cos(20 * angle) + 5 * math.cos(3 * angle)
        points.append((75 + radius * math.cos(angle), 75 + radius * math.sin(angle)))
    artwork = Polygon(points)
    source = svg('<polygon points="' + " ".join(f"{x},{y}" for x, y in points) + '"/>')
    turning = []
    for smoothing in (0, 2, 5):
        result = outline(
            SVGBorderGenerator(0.5, smoothing=smoothing, tolerance=0.02).add_to_svg(source)
        )
        assert result.is_valid and result.covers(artwork)
        assert result.boundary.distance(artwork) - 0.5 >= 0.5
        ring = list(result.exterior.coords)[:-1]
        edges = [
            (ring[(i + 1) % len(ring)][0] - p[0], ring[(i + 1) % len(ring)][1] - p[1])
            for i, p in enumerate(ring)
        ]
        turning.append(
            math.fsum(
                abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
                for a, b in zip(edges, edges[1:] + edges[:1])
            )
        )
    assert turning[0] > turning[1] > turning[2]
    assert turning[2] < turning[0] / 2


def test_curve_bounds_include_controls_and_stroke() -> None:
    """Canvas bounds must account for possible cubic bulges, not just endpoints."""
    document = SVGBorderGenerator(4, smoothing=20, stroke_width=3).add_to_svg(
        svg(
            '<ellipse cx="0" cy="0" rx="35" ry="15"/>',
            'viewBox="-35 -15 70 30" width="70" height="30"',
        )
    )
    x, y, width, height = map(float, ET.fromstring(document).attrib["viewBox"].split())
    for curve in border_curves(document):
        for px, py in curve:
            assert x + 1.5 <= px <= x + width - 1.5
            assert y + 1.5 <= py <= y + height - 1.5


def test_failed_curve_validation_does_not_fall_back_to_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsafe cubic fits must raise rather than silently emit a polygon."""
    generator = SVGBorderGenerator(4)
    curves = [((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 1.0))]
    monkeypatch.setattr(generator, "_periodic_spline", Mock(return_value=curves))
    with pytest.raises(BorderGenerationError, match="enclosure/clearance"):
        generator.add_to_svg(svg('<rect x="10" y="10" width="40" height="30"/>'))


@pytest.mark.parametrize("smoothing", [0, 2, 10, 30])
def test_clearance_is_to_inside_of_stroke(smoothing: float) -> None:
    """Smoothing must never eat into the requested clearance."""
    generator = SVGBorderGenerator(5, smoothing=smoothing, stroke_width=2)
    result = outline(generator.add_to_svg(svg('<rect x="10" y="10" width="40" height="30"/>')))
    artwork = box(10, 10, 50, 40)
    assert result.is_valid and result.covers(artwork)
    assert result.boundary.distance(artwork) - 1 >= 5


def test_disconnected_outlier_is_enclosed_by_one_border() -> None:
    """A small isolated piece must not disappear or become a separate border."""
    source = svg('<rect x="10" y="10" width="20" height="20"/>' '<circle cx="80" cy="70" r="1"/>')
    result = outline(SVGBorderGenerator(4, smoothing=8).add_to_svg(source))
    artwork = unary_union([box(10, 10, 30, 30), Point(80, 70).buffer(1, quad_segs=1000)])
    assert result.covers(artwork)
    assert result.boundary.distance(artwork) - 0.5 >= 4
    assert len(result.interiors) == 0


def test_smoothing_bridges_small_notch_but_preserves_large_recess() -> None:
    """The smoothing scale must not turn a concave shape into a convex hull."""
    body = '<path d="M0 0 H100 V100 H70 V30 H30 V100 H0 V60 H2 V58 H0 Z"/>'
    source = svg(body)
    sharp = outline(SVGBorderGenerator(0.5, smoothing=0, tolerance=0.02).add_to_svg(source))
    smooth = outline(SVGBorderGenerator(0.5, smoothing=5, tolerance=0.02).add_to_svg(source))
    assert not smooth.covers(Point(50, 90))
    assert smooth.covers(Point(1, 59))
    assert smooth.boundary.length < sharp.boundary.length


@pytest.mark.parametrize(
    "body",
    [
        '<circle cx="40" cy="40" r="20"/>',
        '<ellipse cx="40" cy="40" rx="20" ry="10" transform="rotate(25 40 40)"/>',
        '<rect x="20" y="20" width="40" height="40" rx="10"/>',
    ],
)
def test_arc_shapes_are_supported(body: str) -> None:
    assert outline(SVGBorderGenerator(3).add_to_svg(svg(body))).is_valid


def test_cubic_clearance_against_dense_original_curve() -> None:
    """Check actual curve samples, not the generator's flattened geometry."""
    points = []
    for i in range(5001):
        t = i / 5000
        points.append(
            (
                10 * (1 - t) ** 3 + 10 * 3 * (1 - t) ** 2 * t + 60 * 3 * (1 - t) * t**2 + 60 * t**3,
                10 * (1 - t) ** 3 + 70 * 3 * (1 - t) ** 2 * t + 70 * 3 * (1 - t) * t**2 + 10 * t**3,
            )
        )
    curve = LineString(points + [points[0]])
    result = outline(
        SVGBorderGenerator(3, tolerance=0.05).add_to_svg(
            svg('<path d="M10 10 C10 70 60 70 60 10 Z"/>')
        )
    )
    assert result.covers(curve)
    assert result.boundary.distance(curve) - 0.5 >= 3


def test_quadratic_and_relative_paths() -> None:
    result = outline(
        SVGBorderGenerator(2).add_to_svg(svg('<path d="m10 10 q20 50 40 0 t40 0 l0 70 h-80z"/>'))
    )
    assert result.is_valid


def test_group_transforms_and_nonzero_viewbox_stay_in_user_coordinates() -> None:
    source = svg(
        '<g transform="translate(100 200)"><g transform="scale(2 3)">'
        '<rect x="0" y="0" width="10" height="10"/></g></g>',
        'viewBox="100 200 100 100" width="50mm" height="50mm"',
    )
    result = SVGBorderGenerator(5, smoothing=0).add_to_svg(source)
    border = outline(result)
    artwork = box(100, 200, 120, 230)
    assert border.covers(artwork)
    assert border.boundary.distance(artwork) - 0.5 >= 5
    root = ET.fromstring(result)
    group = root.find(f"{{{SVG_NS}}}g")
    assert group is not None
    assert group.get("transform") == "translate(100 200)"
    width = float(root.attrib["width"].removesuffix("mm"))
    view_width = float(root.attrib["viewBox"].split()[2])
    assert width / view_width == pytest.approx(0.5)


def test_viewport_expands_for_entire_border_stroke() -> None:
    source = svg(
        '<rect width="100" height="100"/>', 'viewBox="0 0 100 100" width="100" height="100"'
    )
    result = SVGBorderGenerator(10, stroke_width=2).add_to_svg(source)
    border = outline(result)
    root = ET.fromstring(result)
    x, y, w, h = map(float, root.attrib["viewBox"].split())
    assert box(x, y, x + w, y + h).covers(border.buffer(1))
    assert float(root.attrib["width"]) / w == pytest.approx(1)
    assert float(root.attrib["height"]) / h == pytest.approx(1)
    rectangle = root.find(f"{{{SVG_NS}}}rect")
    assert rectangle is not None
    assert rectangle.attrib == {"width": "100", "height": "100"}


def test_absolute_dimensions_without_viewbox() -> None:
    result = SVGBorderGenerator(2).add_to_svg(
        svg('<rect width="10" height="10"/>', 'width="25.4mm" height="1in"')
    )
    root = ET.fromstring(result)
    assert root.attrib["width"].endswith("mm")
    assert root.attrib["height"].endswith("in")
    assert outline(result).covers(box(0, 0, 10, 10))


def test_holes_do_not_get_inner_borders() -> None:
    source = svg('<path fill-rule="evenodd" d="M10 10H90V90H10Z M30 30H70V70H30Z"/>')
    result = outline(SVGBorderGenerator(2).add_to_svg(source))
    assert result.covers(box(10, 10, 90, 90))
    assert not result.interiors


def test_hidden_and_unfilled_shapes_do_not_affect_border() -> None:
    source = svg(
        '<rect x="30" y="30" width="10" height="10"/>'
        '<g display="none"><rect width="100" height="100"/></g>'
        '<g opacity="0"><rect opacity="1" width="100" height="100"/></g>'
        '<rect fill-opacity="0" width="100" height="100"/>'
        '<rect fill="none" width="100" height="100"/>'
    )
    result = outline(SVGBorderGenerator(2, smoothing=0).add_to_svg(source))
    assert result.bounds[0] > 20 and result.bounds[2] < 50


def test_coreldraw_rendering_hints_and_class_fill_are_preserved() -> None:
    source = svg(
        '<defs><style type="text/css"><![CDATA[.fil0 {fill:black}]]></style></defs>'
        '<path class="fil0" d="M30 30H40V40H30Z"/>',
        'viewBox="0 0 100 100" style="shape-rendering:geometricPrecision;'
        "text-rendering:geometricPrecision;image-rendering:optimizeQuality;"
        'fill-rule:evenodd;clip-rule:evenodd"',
    )
    result = SVGBorderGenerator(2).add_to_svg(source)
    original, saved = ET.fromstring(source), ET.fromstring(result)
    assert original.attrib["style"] == saved.attrib["style"]
    assert ET.tostring(original[0]) == ET.tostring(saved[0])
    assert original[1].attrib == saved[1].attrib
    assert outline(result).covers(box(30, 30, 40, 40))


def test_class_styles_resolve_before_transparency_and_inline_overrides() -> None:
    source = svg(
        "<style>.hidden {opacity:0}.paint {fill:none}.paint {fill:black}</style>"
        '<g class="hidden"><rect width="100" height="100"/></g>'
        '<rect class="paint" x="30" y="30" width="10" height="10"/>'
        '<rect class="paint" width="100" height="100" style="fill:none"/>'
    )
    result = outline(SVGBorderGenerator(2, smoothing=0).add_to_svg(source))
    assert result.covers(box(30, 30, 40, 40))
    assert result.bounds[0] > 20 and result.bounds[2] < 50


@pytest.mark.parametrize(
    "css",
    [
        ".artwork {transform:scale(2)}",
        ".artwork {fill:black!important}",
        ".artwork {fill:url(#paint)}",
        ".artwork:hover {fill:black}",
        "@import 'artwork.css';",
        ".artwork rect {fill:black}",
        ".artwork {fill:black} invalid",
    ],
)
def test_unsupported_class_styles_fail_explicitly(css: str) -> None:
    with pytest.raises(BorderGenerationError):
        SVGBorderGenerator(2).add_to_svg(
            svg(f'<style>{css}</style><rect class="artwork" width="10" height="10"/>')
        )


@pytest.mark.parametrize(
    "body",
    [
        '<text x="10" y="20">Text</text>',
        '<image href="test.png"/>',
        '<use href="#shape"/>',
        '<svg><rect width="10" height="10"/></svg>',
        "<style>path {stroke-width:20}</style>",
        "<defs><style>path {fill:none}</style></defs>",
        '<rect width="10" height="10" clip-path="url(#clip)"/>',
        '<rect width="10" height="10" filter="url(#blur)"/>',
        '<rect width="10" height="10" stroke="red"/>',
        '<rect width="10" height="10" class="artwork"/>',
        '<rect width="10" height="10" style="transform:scale(2)"/>',
        '<rect width="10" height="10" fill="url(#gradient)"/>',
        '<rect width="10" height="10" stroke-dasharray="1 1"/>',
        '<rect width="10" height="10" transform-origin="50% 50%"/>',
    ],
)
def test_unsupported_features_fail_explicitly(body: str) -> None:
    with pytest.raises(BorderGenerationError):
        SVGBorderGenerator(2).add_to_svg(svg(body))


@pytest.mark.parametrize(
    "attributes",
    [
        'viewBox="0 0 0 100"',
        'viewBox="0 0 nan 100"',
        'width="100%" height="100%"',
        'viewBox="bad"',
        'viewBox="0 0 100 100" transform="scale(2)"',
    ],
)
def test_invalid_viewport_is_rejected(attributes: str) -> None:
    with pytest.raises(BorderGenerationError):
        SVGBorderGenerator(2).add_to_svg(svg('<rect width="10" height="10"/>', attributes))


@pytest.mark.parametrize(
    "options",
    [
        {"offset": -1},
        {"offset": 0},
        {"offset": math.nan},
        {"offset": math.inf},
        {"offset": 1, "smoothing": -1},
        {"offset": 1, "tolerance": 0},
        {"offset": 1, "stroke_width": 0},
        {"offset": 1, "color": "invalidcolor"},
        {"offset": 1, "color": "none"},
        {"offset": 1, "color": "url(#paint)"},
    ],
)
def test_invalid_options_are_rejected(options: dict) -> None:
    with pytest.raises(BorderGenerationError):
        SVGBorderGenerator(**options)


def test_existing_border_and_empty_artwork_are_rejected() -> None:
    generator = SVGBorderGenerator(2)
    with pytest.raises(BorderGenerationError, match="no supported"):
        generator.add_to_svg(svg(""))
    document = generator.add_to_svg(svg('<rect width="10" height="10"/>'))
    with pytest.raises(BorderGenerationError):
        generator.add_to_svg(document)


def test_source_is_unchanged_and_in_place_write_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.svg"
    destination = tmp_path / "border.svg"
    content = svg('<rect width="10" height="10"/>')
    source.write_text(content, encoding="utf-8")
    generator = SVGBorderGenerator(2)
    generator.generate(source, destination)
    assert source.read_text(encoding="utf-8") == content
    assert destination.is_file()
    with pytest.raises(BorderGenerationError, match="differ"):
        generator.generate(source, source)


def test_progress_reports_stages_counts_retries_and_only_saves_after_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Progress covers the file workflow and measurable curve-validation work."""
    from svg_optimizer import svg_border

    progress = Mock(columns=())
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task.return_value = 0
    monkeypatch.setattr(svg_border, "create_progress_bar", Mock(return_value=progress))
    messages = Mock()
    monkeypatch.setattr(svg_border, "log_info", messages)
    source = tmp_path / "source.svg"
    output = tmp_path / "border.svg"
    source.write_text(svg('<circle cx="50" cy="50" r="25"/>'), encoding="utf-8")
    generator = SVGBorderGenerator(5, smoothing=10, show_progress=True)
    generator.generate(source, output)
    descriptions = [call.kwargs["description"] for call in progress.reset.call_args_list]
    assert descriptions[0] == "Reading SVG"
    assert "Flattening artwork curves" in descriptions
    assert "Sampling outline for cubic spline" in descriptions
    assert any(stage.startswith("Validating cubic curves: attempt") for stage in descriptions)
    assert descriptions[-2:] == ["Writing bordered SVG", "Border saved"]
    assert any(
        call.kwargs.get("completed", 0) > 0 and call.kwargs.get("total") is not None
        for call in progress.update.call_args_list
    )
    assert output.is_file()
    assert generator._reporter is None
    assert progress.__exit__.call_count == 1
    assert messages.call_args_list[-1].args == ("Border: Border saved",)


def test_failed_border_progress_is_closed_without_reporting_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error must stop the live display without claiming completion."""
    from svg_optimizer import svg_border

    progress = Mock(columns=())
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(svg_border, "create_progress_bar", Mock(return_value=progress))
    monkeypatch.setattr(svg_border, "log_info", Mock())
    generator = SVGBorderGenerator(2, show_progress=True)
    with pytest.raises(BorderGenerationError):
        generator.add_to_svg(svg("<text>Unsupported</text>"))
    descriptions = [call.kwargs["description"] for call in progress.reset.call_args_list]
    assert not any("complete" in stage or "saved" in stage for stage in descriptions)
    assert generator._reporter is None
    assert progress.__exit__.call_count == 1


def test_library_border_generation_is_quiet_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from svg_optimizer import svg_border

    progress = Mock()
    monkeypatch.setattr(svg_border, "create_progress_bar", progress)
    SVGBorderGenerator(2).add_to_svg(svg('<rect width="10" height="10"/>'))
    progress.assert_not_called()


def test_progress_does_not_change_border_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    from svg_optimizer import svg_border

    progress = Mock(columns=())
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(svg_border, "create_progress_bar", Mock(return_value=progress))
    monkeypatch.setattr(svg_border, "log_info", Mock())
    source = svg('<circle cx="50" cy="50" r="25"/>')
    assert SVGBorderGenerator(2, show_progress=True).add_to_svg(source) == SVGBorderGenerator(
        2
    ).add_to_svg(source)


def test_write_failure_does_not_report_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from svg_optimizer import svg_border

    progress = Mock(columns=())
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(svg_border, "create_progress_bar", Mock(return_value=progress))
    monkeypatch.setattr(svg_border, "log_info", Mock())
    source = tmp_path / "source.svg"
    source.write_text(svg('<rect width="10" height="10"/>'), encoding="utf-8")
    generator = SVGBorderGenerator(2, show_progress=True)
    with pytest.raises(OSError):
        generator.generate(source, tmp_path)
    descriptions = [call.kwargs["description"] for call in progress.reset.call_args_list]
    assert descriptions[-1] == "Writing bordered SVG"
    assert "Border saved" not in descriptions
    assert generator._reporter is None


def test_non_utf8_input_fails_with_explicit_error(tmp_path: Path) -> None:
    source = tmp_path / "utf16.svg"
    source.write_bytes(svg('<rect width="10" height="10"/>').encode("utf-16"))
    with pytest.raises(BorderGenerationError, match="UTF-8"):
        SVGBorderGenerator(2).generate(source, tmp_path / "result.svg")


def test_numeric_precision_failure_is_explicit() -> None:
    with pytest.raises(BorderGenerationError, match="precision"):
        SVGBorderGenerator(2).add_to_svg(
            svg('<rect x="1e20" y="0" width="1e6" height="1e6"/>', 'viewBox="0 0 1e21 1e21"')
        )


@pytest.mark.parametrize("offset", ["0", "-1", "nan", "inf"])
def test_cli_rejects_invalid_offset(offset: str) -> None:
    with pytest.raises(SystemExit) as error:
        parse_arguments(["input.svg", "--border-offset", offset])
    assert error.value.code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["input.svg"],
        ["input.png", "--border-smoothing", "10"],
        ["input.png", "--border-smoo", "10"],
        ["input.svg", "--border-offset", "2", "--upscale"],
        ["input.svg", "--border-offset", "2", "--threshold", "0.5"],
        ["input.svg", "--border-offset", "2", "-ccomparison.png"],
        ["input.svg", "--border-offset", "2", "--output", "bad.png"],
    ],
)
def test_cli_rejects_incompatible_modes(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        parse_arguments(arguments)
    assert error.value.code == 2


def test_cli_keeps_raster_defaults_and_accepts_border_options() -> None:
    normal = parse_arguments(["input.png"])
    assert normal.border_offset is None
    assert normal.upscale is False
    args = parse_arguments(
        [
            "input.svg",
            "--border-offset",
            "4",
            "--border-smoothing",
            "0",
            "--border-width",
            "2",
            "--border-color",
            "#ff0000",
        ]
    )
    assert args.border_offset == 4 and args.border_smoothing == 0 and args.border_width == 2


def test_cli_border_enables_automatic_distances() -> None:
    args = parse_arguments(["input.svg", "--border"])
    assert args.border is True
    assert args.border_offset is None
    assert args.border_smoothing is None
    assert args.border_tolerance is None
    assert args.border_width is None
    explicit = parse_arguments(["input.svg", "--border", "--border-offset", "5"])
    assert explicit.border_offset == 5
    assert not parse_arguments(["input.png"]).border


@pytest.mark.parametrize("radius", [0, 2, 5])
def test_frame_bounds_corners_clearance_and_artwork_preservation(radius: float) -> None:
    source = svg(
        '<g transform="translate(10 20)"><rect width="40" height="30"/></g>'
        '<rect x="70" y="60" width="2" height="2"/>'
        '<rect width="100" height="100" fill="none"/>'
    )
    generator = SVGBorderGenerator(5, stroke_width=2, border_type="frame", corner_radius=radius)
    output = generator.add_to_svg(source)
    original, saved = ET.fromstring(source), ET.fromstring(output)
    for before, after in zip(original, saved):
        assert ET.tostring(before) == ET.tostring(after)
    frame = saved.find(f"{{{SVG_NS}}}rect[@id='svg-optimizer-border']")
    assert frame is not None
    x, y, width, height, rx = (
        float(frame.attrib[name]) for name in ("x", "y", "width", "height", "rx")
    )
    assert (x, y, width, height, rx) == pytest.approx((3.8, 13.8, 74.4, 54.4, radius))
    if radius:
        polygon = box(x + rx, y + rx, x + width - rx, y + height - rx).buffer(rx, quad_segs=1000)
    else:
        polygon = box(x, y, x + width, y + height)
    artwork = unary_union([box(10, 20, 50, 50), box(70, 60, 72, 62)])
    assert polygon.covers(artwork)
    assert polygon.boundary.distance(artwork) - 1 >= 5
    vx, vy, vw, vh = map(float, saved.attrib["viewBox"].split())
    assert vx <= x - 1 and vy <= y - 1
    assert vx + vw >= x + width + 1 and vy + vh >= y + height + 1


def test_frame_avoids_outline_fitting_and_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    generator = SVGBorderGenerator(5, border_type="frame")
    for name in ("_outline", "_curved_outline", "_periodic_spline", "_gaussian_perimeter"):
        monkeypatch.setattr(generator, name, Mock(side_effect=AssertionError("No outline work")))
    result = generator.add_to_svg(
        svg('<rect width="30000" height="30000"/>', 'viewBox="0 0 30000 30000"')
    )
    assert ET.fromstring(result)[-1].tag == f"{{{SVG_NS}}}rect"


@pytest.mark.parametrize("units,expected", [("mm", 200), ("percent", 420)])
def test_frame_corner_radius_uses_selected_units(units: str, expected: float) -> None:
    generator = SVGBorderGenerator(
        5,
        stroke_width=None,
        smoothing=None,
        tolerance=None,
        units=units,
        border_type="frame",
        corner_radius=2,
    )
    result = generator.add_to_svg(
        svg(
            '<rect width="1000" height="2000"/>',
            'viewBox="0 0 21000 29700" width="210mm" height="297mm"',
        )
    )
    assert float(ET.fromstring(result)[-1].attrib["rx"]) == pytest.approx(expected)


@pytest.mark.parametrize("radius", [math.nan, math.inf, -1])
def test_invalid_frame_corner_radius(radius: float) -> None:
    with pytest.raises(BorderGenerationError, match="Corner radius"):
        SVGBorderGenerator(5, border_type="frame", corner_radius=radius)


@pytest.mark.parametrize("radius", [15, 50, 100])
def test_frame_expands_minimally_for_actual_clearance(radius: float) -> None:
    generator = SVGBorderGenerator(5, border_type="frame", corner_radius=radius, tolerance=0.02)
    result = generator.add_to_svg(svg('<rect width="50" height="50"/>'))
    frame = ET.fromstring(result)[-1]
    x, y, w, h, r = (float(frame.attrib[key]) for key in ("x", "y", "width", "height", "rx"))
    assert r == radius and w >= 2 * radius and h >= 2 * radius
    polygon = box(x + r, y + r, x + w - r, y + h - r).buffer(r, quad_segs=2000)
    artwork = box(0, 0, 50, 50)
    assert polygon.covers(artwork)
    assert polygon.boundary.distance(artwork) - 0.5 >= 5
    # Shrinking the frame just beyond the search/geometry margins must violate clearance.
    shrink = 0.1
    if w - 2 * shrink >= 2 * r:
        smaller = box(
            x + r + shrink, y + r + shrink, x + w - r - shrink, y + h - r - shrink
        ).buffer(r, quad_segs=2000)
        assert smaller.boundary.distance(artwork) - 0.5 < 5
    else:
        assert w - 2 * shrink < 2 * r


def test_frame_allows_large_radius_in_empty_bounding_box_corners() -> None:
    result = SVGBorderGenerator(5, border_type="frame", corner_radius=20).add_to_svg(
        svg('<circle cx="50" cy="50" r="25"/>')
    )
    frame = ET.fromstring(result)[-1]
    assert float(frame.attrib["x"]) == pytest.approx(19.3, abs=0.15)
    assert float(frame.attrib["width"]) < 62
    assert float(frame.attrib["rx"]) == 20


def test_frame_rejects_invalid_mode_and_duplicate_border() -> None:
    with pytest.raises(BorderGenerationError, match="requires"):
        SVGBorderGenerator(5, corner_radius=2)
    with pytest.raises(BorderGenerationError, match="already contains"):
        generator = SVGBorderGenerator(5, border_type="frame")
        generator.add_to_svg(generator.add_to_svg(svg('<rect width="50" height="50"/>')))


@pytest.mark.parametrize("flag", ["--border-type", "--border-style"])
@pytest.mark.parametrize("kind", ["outline", "frame"])
def test_cli_border_type_aliases(flag: str, kind: str) -> None:
    args = parse_arguments(["input.svg", "--border", flag, kind])
    assert args.border_type == kind


@pytest.mark.parametrize("flag", ["--border-type", "--border-style"])
def test_cli_rejects_removed_box_border_type(flag: str) -> None:
    with pytest.raises(SystemExit) as error:
        parse_arguments(["input.svg", "--border", flag, "box"])
    assert error.value.code == 2


def test_library_rejects_removed_box_border_type() -> None:
    with pytest.raises(BorderGenerationError, match="Border type must be outline or frame"):
        SVGBorderGenerator(5, border_type="box")


@pytest.mark.parametrize(
    "options",
    [
        ["--corner-radius", "2"],
        ["--border-type", "frame", "--border-smoothing", "2"],
    ],
)
def test_cli_rejects_incompatible_frame_options(options: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["input.svg", "--border", *options])


@pytest.mark.parametrize(
    "unit,size", [("svg", "100svg"), ("mm", "1mm"), ("percent", "0.47619047619percent")]
)
def test_default_border_filename_uses_resolved_automatic_offset(unit: str, size: str) -> None:
    source = svg("", 'viewBox="0 0 21000 29700" width="210mm" height="297mm"')
    generator = SVGBorderGenerator(None, units=unit, border_type="frame")
    assert (
        generator.default_output(Path("jack.svg"), source).name == f"jack_border_frame_{size}.svg"
    )
    explicit = SVGBorderGenerator(2.5, units=unit)
    assert (
        explicit.default_output(Path("jack.svg"), source).name
        == f"jack_border_outline_2.5{unit}.svg"
    )


def test_frame_cli_default_filename_and_explicit_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from svg_optimizer import __main__ as application

    source = tmp_path / "art.svg"
    source.write_text(
        svg(
            '<rect width="1000" height="2000"/>',
            'viewBox="0 0 21000 29700" width="210mm" height="297mm"',
        ),
        encoding="utf-8",
    )
    args = [
        "svg-optimizer",
        str(source),
        "--border-type",
        "frame",
        "--border-offset",
        "5",
        "--border-units",
        "mm",
        "--corner-radius",
        "2",
        "--log-file",
        str(tmp_path / "run.log"),
    ]
    monkeypatch.setattr(sys, "argv", args)
    assert application.main() == 0
    assert (tmp_path / "art_border_frame_5mm.svg").is_file()
    output = tmp_path / "custom.svg"
    monkeypatch.setattr(sys, "argv", [*args, "--output", str(output)])
    assert application.main() == 0
    assert output.is_file()


@pytest.mark.parametrize("unit", ["svg", "mm", "cm", "in", "px", "pt", "pc", "percent"])
def test_cli_border_units(unit: str) -> None:
    args = parse_arguments(["input.svg", "--border-offset", "5", "--border-units", unit])
    assert args.border_units == unit and args.border_offset == 5
    assert args.border_smoothing is None
    assert parse_arguments(["input.svg", "--border"]).border_units == "svg"


@pytest.mark.parametrize(
    "arguments",
    [
        ["input.png", "--border-units", "mm"],
        ["input.svg", "--border", "--border-units", "unknown"],
        ["input.svg", "--border", "--border-offset", "5%"],
    ],
)
def test_invalid_border_units_are_rejected(arguments: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(arguments)


@pytest.mark.parametrize(
    "unit,factor",
    [
        ("svg", 1),
        ("mm", 100),
        ("cm", 1000),
        ("in", 2540),
        ("px", 25.4 / 96 * 100),
        ("pt", 25.4 / 72 * 100),
        ("pc", 25.4 / 6 * 100),
        ("percent", 210),
    ],
)
def test_unit_conversion_uses_original_physical_canvas(unit: str, factor: float) -> None:
    root = ET.fromstring(svg("", 'viewBox="0 0 21000 29700" width="210mm" height="297mm"'))
    generator = SVGBorderGenerator(5, units=unit)
    assert generator._distance_scale(root, generator._viewport(root)) == pytest.approx(factor)


@pytest.mark.parametrize("unit,factor", [("mm", 100), ("percent", 210)])
def test_selected_units_match_explicit_svg_distances(unit: str, factor: float) -> None:
    source = svg(
        '<rect x="3000" y="3000" width="4000" height="4000"/>',
        'viewBox="-10 -20 21000 29700" width="210mm" height="297mm"',
    )
    generator = SVGBorderGenerator(5, smoothing=10, tolerance=0.01, stroke_width=0.2, units=unit)
    actual = generator.add_to_svg(source)
    expected = SVGBorderGenerator(
        5 * factor, smoothing=10 * factor, tolerance=0.01 * factor, stroke_width=0.2 * factor
    ).add_to_svg(source)
    assert actual == expected
    artwork = box(3000, 3000, 7000, 7000)
    assert outline(actual).boundary.distance(artwork) - 0.1 * factor >= 5 * factor
    assert generator.offset == pytest.approx(5 * factor)


@pytest.mark.parametrize("unit", ["mm", "percent"])
def test_units_leave_omitted_defaults_in_svg_scale(unit: str) -> None:
    generator = SVGBorderGenerator(5, smoothing=None, tolerance=None, stroke_width=None, units=unit)
    generator.add_to_svg(
        svg(
            '<rect width="1000" height="1000"/>',
            'viewBox="0 0 21000 29700" width="210mm" height="297mm"',
        )
    )
    assert generator.offset == pytest.approx(500 if unit == "mm" else 1050)
    assert (generator.smoothing, generator.tolerance, generator.stroke_width) == (200, 0.5, 10)


@pytest.mark.parametrize(
    "attributes,unit,factor",
    [
        ('width="25.4mm" height="1in"', "mm", 96 / 25.4),
        ('viewBox="0 0 100 50" width="200px" height="200px"', "px", 0.5),
        (
            'viewBox="0 0 100 50" width="200px" height="200px" '
            'preserveAspectRatio="xMidYMid slice"',
            "px",
            0.25,
        ),
        (
            'viewBox="0 0 100 50" width="200px" height="100px" ' 'preserveAspectRatio="none"',
            "px",
            0.5,
        ),
        ('viewBox="0 0 100 50"', "percent", 0.5),
        ('viewBox="0 0 100 50" width="1in" height="36pt"', "in", 100),
    ],
)
def test_units_respect_viewport_scaling(attributes: str, unit: str, factor: float) -> None:
    root = ET.fromstring(svg("", attributes))
    generator = SVGBorderGenerator(1, units=unit)
    assert generator._distance_scale(root, generator._viewport(root)) == pytest.approx(factor)


@pytest.mark.parametrize(
    "attributes",
    [
        'viewBox="0 0 100 50"',
        'viewBox="0 0 100 50" width="100px"',
        'viewBox="0 0 100 50" width="100px" height="100px" preserveAspectRatio="none"',
        'viewBox="0 0 100 50" width="100px" height="100px" preserveAspectRatio="bad"',
    ],
)
def test_unknown_or_nonuniform_physical_scale_fails_before_geometry(
    attributes: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    generator = SVGBorderGenerator(5, units="mm")
    geometry = Mock(side_effect=AssertionError("Do not start geometry with unknown units"))
    monkeypatch.setattr(generator, "_artwork", geometry)
    with pytest.raises(BorderGenerationError):
        generator.add_to_svg(svg('<rect width="10" height="10"/>', attributes))
    geometry.assert_not_called()


def test_unit_conversion_resolves_fresh_for_each_document() -> None:
    generator = SVGBorderGenerator(5, smoothing=None, tolerance=None, stroke_width=None, units="mm")
    for width, expected_offset in ((210, 500), (420, 250)):
        generator.add_to_svg(
            svg(
                '<rect width="1000" height="1000"/>',
                f'viewBox="0 0 21000 29700" width="{width}mm" height="{width * 297 / 210}mm"',
            )
        )
        assert generator.offset == pytest.approx(expected_offset)


def test_invalid_library_units_and_conversion_overflow_are_rejected() -> None:
    with pytest.raises(BorderGenerationError, match="Border units"):
        SVGBorderGenerator(5, units="unknown")
    with pytest.raises(BorderGenerationError, match="Converted border distances"):
        SVGBorderGenerator(1e308, units="percent").add_to_svg(
            svg('<rect width="10" height="10"/>', 'viewBox="0 0 21000 29700"')
        )


@pytest.mark.parametrize("size", [21, 210, 21000])
def test_automatic_distances_follow_svg_scale(size: float) -> None:
    generator = SVGBorderGenerator(None, smoothing=None, tolerance=None, stroke_width=None)
    source = svg(
        f'<rect x="{size/4}" y="{size/4}" width="{size/2}" height="{size/2}"/>',
        f'viewBox="0 0 {size} {size}"',
    )
    result = generator.add_to_svg(source)
    scale = size / 210
    assert (
        generator.offset,
        generator.smoothing,
        generator.tolerance,
        generator.stroke_width,
    ) == pytest.approx((scale, 2 * scale, 0.005 * scale, 0.1 * scale))
    artwork = box(size / 4, size / 4, 3 * size / 4, 3 * size / 4)
    assert outline(result).boundary.distance(artwork) - generator.stroke_width / 2 >= scale


def test_automatic_defaults_resolve_again_for_each_document() -> None:
    generator = SVGBorderGenerator(5, smoothing=None, tolerance=None, stroke_width=1)
    for size in (21000, 210):
        generator.add_to_svg(svg('<rect width="10" height="10"/>', f'viewBox="0 0 {size} {size}"'))
        assert generator.offset == 5 and generator.stroke_width == 1
        assert generator.smoothing == pytest.approx(2 * size / 210)


def test_preflight_rejects_excessive_detail_before_expensive_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = SVGBorderGenerator(5, smoothing=10)
    flatten = Mock(side_effect=AssertionError("Preflight must precede flattening"))
    buffer = Mock(side_effect=AssertionError("Preflight must precede buffering"))
    monkeypatch.setattr(generator, "_flatten_bezier", flatten)
    monkeypatch.setattr(generator, "_buffer", buffer)
    with pytest.raises(BorderGenerationError, match="Preflight: at least"):
        generator.add_to_svg(svg('<path d="M0 0H30000V30000H0Z"/>', 'viewBox="0 0 30000 30000"'))
    flatten.assert_not_called()
    buffer.assert_not_called()


def test_preflight_ignores_invisible_and_unfilled_outliers() -> None:
    result = SVGBorderGenerator(5, smoothing=10).add_to_svg(
        svg(
            '<rect width="10" height="10"/>'
            '<rect fill="none" width="30000" height="30000"/>'
            '<g opacity="0"><rect width="30000" height="30000"/></g>'
            '<path d="M50000 50000L60000 60000L70000 70000Z"/>'
        )
    )
    assert outline(result).bounds[2] < 30


def test_svg_cli_does_not_load_raster_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SVG border generation must not depend on rasterization or tracing."""
    from svg_optimizer import __main__ as application

    source = tmp_path / "art.svg"
    source.write_text(svg('<rect width="10" height="10"/>'), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "svg-optimizer",
            str(source),
            "--border-offset",
            "2",
            "--log-file",
            str(tmp_path / "run.log"),
        ],
    )
    modules = [
        "svg_optimizer.image_analysis",
        "svg_optimizer.potrace_tracer",
        "svg_optimizer.inkscape_wrapper",
        "svg_optimizer.image_comparer",
    ]
    for module in modules:
        monkeypatch.setitem(sys.modules, module, None)
    assert application.main() == 0
    assert (tmp_path / "art_border_outline_2svg.svg").is_file()


def test_svg_cli_automatic_border(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from svg_optimizer import __main__ as application

    source = tmp_path / "art.svg"
    source.write_text(
        svg('<rect width="100" height="100"/>', 'viewBox="0 0 210 297"'), encoding="utf-8"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "svg-optimizer",
            str(source),
            "--border",
            "--log-file",
            str(tmp_path / "run.log"),
        ],
    )
    assert application.main() == 0
    output = source.with_name("art_border_outline_1svg.svg").read_text(encoding="utf-8")
    path = ET.fromstring(output).find(f"{{{SVG_NS}}}path[@id='svg-optimizer-border']")
    assert path is not None and float(path.attrib["stroke-width"]) == pytest.approx(0.1)
    assert outline(output).boundary.distance(box(0, 0, 100, 100)) - 0.05 >= 1


@pytest.mark.parametrize("unit,offset", [("mm", 500), ("percent", 1050)])
def test_svg_cli_selected_border_units(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unit: str, offset: float
) -> None:
    from svg_optimizer import __main__ as application

    source = tmp_path / "art.svg"
    source.write_text(
        svg(
            '<rect x="3000" y="3000" width="4000" height="4000"/>',
            'viewBox="0 0 21000 29700" width="210mm" height="297mm"',
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "svg-optimizer",
            str(source),
            "--border-offset",
            "5",
            "--border-units",
            unit,
            "--log-file",
            str(tmp_path / "run.log"),
        ],
    )
    assert application.main() == 0
    output = source.with_name(f"art_border_outline_5{unit}.svg").read_text(encoding="utf-8")
    assert outline(output).boundary.distance(box(3000, 3000, 7000, 7000)) - 5 >= offset


def test_cli_border_failure_returns_nonzero_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from svg_optimizer import __main__ as application

    source = tmp_path / "bad.svg"
    source.write_text(svg("<text>unsupported</text>"), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "svg-optimizer",
            str(source),
            "--border-offset",
            "2",
            "--log-file",
            str(tmp_path / "run.log"),
        ],
    )
    assert application.main() == 1
    assert not (tmp_path / "bad_border_outline_2svg.svg").exists()


def test_traced_output_helper_applies_border_only_when_enabled(tmp_path: Path) -> None:
    from svg_optimizer.__main__ import _save_svg_content

    content = svg('<rect width="10" height="10"/>')
    destination = tmp_path / "trace.svg"
    _save_svg_content(content, destination, None)
    assert destination.read_text(encoding="utf-8") == content
    _save_svg_content(content, destination, SVGBorderGenerator(2))
    assert outline(destination.read_text(encoding="utf-8")).covers(box(0, 0, 10, 10))


@pytest.mark.parametrize("skip_optimization", [True, False])
@pytest.mark.parametrize("border_enabled", [True, False])
@pytest.mark.parametrize("border_units", ["svg", "percent", "mm"])
@pytest.mark.parametrize("border_type", ["outline", "frame"])
def test_raster_cli_final_output_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    skip_optimization: bool,
    border_enabled: bool,
    border_units: str,
    border_type: str,
) -> None:
    """Exercise real tracing in both CLI branches; bypass only SSIM and search."""
    from PIL import Image

    from svg_optimizer import __main__ as application
    from svg_optimizer.image_comparer import ImageComparer
    from svg_optimizer.inkscape_wrapper import InkscapeWrapper
    from svg_optimizer.parameter_optimizer import OptimizationResult, ParameterOptimizer

    source = tmp_path / "bitmap.png"
    Image.new("L", (32, 32), 0).save(source)
    original_bytes = source.read_bytes()
    monkeypatch.setattr(InkscapeWrapper, "validate", Mock(return_value=True))
    scored_svg: list[str] = []

    def score(original_path: Path, svg_content: str) -> float:
        assert original_path == source
        scored_svg.append(svg_content)
        return 0.5

    monkeypatch.setattr(ImageComparer, "compare_svg_string_to_original", Mock(side_effect=score))
    result = OptimizationResult(
        best_threshold=0.45,
        best_smooth=1.0,
        turdsize=2,
        opttolerance=0.2,
        turnpolicy="minority",
        best_score=0.9,
        threshold_iterations=1,
        smooth_iterations=1,
        total_evaluations=2,
    )
    monkeypatch.setattr(ParameterOptimizer, "optimize", Mock(return_value=result))
    arguments = [
        "svg-optimizer",
        str(source),
        "--no-comparison",
        "--log-file",
        str(tmp_path / "run.log"),
    ]
    if skip_optimization:
        arguments.append("--skip-optimization")
    if border_enabled:
        arguments.extend(
            ["--border-offset", "3", "--border-units", border_units, "--border-type", border_type]
        )
    monkeypatch.setattr(sys, "argv", arguments)
    assert application.main() == 0
    output_path = (
        source.with_name(f"bitmap_border_{border_type}_3{border_units}.svg")
        if border_enabled
        else source.with_suffix(".svg")
    )
    output = output_path.read_text(encoding="utf-8")
    assert (
        any(element.get("id") == "svg-optimizer-border" for element in ET.fromstring(output))
        == border_enabled
    )
    assert scored_svg and all("svg-optimizer-border" not in document for document in scored_svg)
    assert source.read_bytes() == original_bytes
    if border_enabled:
        path = next(
            element
            for element in ET.fromstring(output)
            if element.get("id") == "svg-optimizer-border"
        )
        assert path is not None
        half_stroke = float(path.attrib["stroke-width"]) / 2
        factor = {"svg": 1, "percent": 32 / 100, "mm": 96 / 25.4}[border_units]
        if border_type == "outline":
            boundary = outline(output).boundary
        else:
            x, y, w, h = (float(path.attrib[name]) for name in ("x", "y", "width", "height"))
            boundary = box(x, y, x + w, y + h).boundary
        assert boundary.distance(box(0, 0, 32, 32)) - half_stroke >= 3 * factor
