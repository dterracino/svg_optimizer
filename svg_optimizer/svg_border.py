"""Vector-only enclosing borders for filled SVG artwork."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import ImageColor
from rich.progress import TextColumn, TimeElapsedColumn
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union
from shapely.validation import make_valid
from svgelements import Arc, Close, CubicBezier, Line, Move, QuadraticBezier, SVG, Shape
from svgelements import Path as SVGPath
from svgelements import Point as SVGPoint

from . import log_info
from .utils import create_progress_bar

SVG_NS = "http://www.w3.org/2000/svg"
MAX_POINTS = 100_000
MAX_CURVES = 10_000
BORDER_UNITS = ("svg", "mm", "cm", "in", "px", "pt", "pc", "percent")
ABSOLUTE_UNIT_PX = {
    "": 1.0,
    "px": 1.0,
    "mm": 96 / 25.4,
    "cm": 96 / 2.54,
    "in": 96.0,
    "pt": 96 / 72,
    "pc": 16.0,
}
Coordinate = tuple[float, float]
Bezier = tuple[Coordinate, Coordinate, Coordinate, Coordinate]


class BorderGenerationError(ValueError):
    """An SVG cannot be safely converted into an enclosing border."""


class SVGBorderGenerator:
    """Enclose filled vector artwork without rasterization.

    Explicit distances use ``units`` and are converted to root SVG user units.
    Percent distances use the shorter viewport side. Curves are flattened to vector segments
    within ``tolerance``; conservative buffer margins compensate for flattening
    and circular-arc approximation. The border is a periodic cubic spline with
    continuous first and second derivatives, including at the closing seam.
    """

    def __init__(
        self,
        offset: float | None,
        smoothing: float | None = 5.0,
        tolerance: float | None = 0.1,
        stroke_width: float | None = 1.0,
        color: str = "black",
        show_progress: bool = False,
        units: str = "svg",
        border_type: str = "outline",
        corner_radius: float | None = None,
    ) -> None:
        if border_type not in ("outline", "frame"):
            raise BorderGenerationError("Border type must be outline or frame.")
        if corner_radius is not None and (not math.isfinite(corner_radius) or corner_radius < 0):
            raise BorderGenerationError("Corner radius must be finite and nonnegative.")
        if corner_radius is not None and border_type == "outline":
            raise BorderGenerationError("Corner radius requires a frame border.")
        self.border_type = border_type
        self._requested_corner_radius = corner_radius or 0.0
        if units not in BORDER_UNITS:
            raise BorderGenerationError(f"Border units must be one of: {', '.join(BORDER_UNITS)}.")
        for name, value, allow_zero in (
            ("offset", offset, False),
            ("smoothing", smoothing, True),
            ("tolerance", tolerance, False),
            ("stroke_width", stroke_width, False),
        ):
            if value is not None and (
                not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero)
            ):
                raise BorderGenerationError(
                    f"Border {name} must be finite and positive"
                    + (" or zero." if allow_zero else ".")
                )
        if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|[a-zA-Z]+", color):
            raise BorderGenerationError("Border color must be a named color or #RGB/#RRGGBB.")
        try:
            ImageColor.getrgb(color)
        except ValueError as error:
            raise BorderGenerationError("Border color must be a visible SVG color.") from error
        self._requested_distances = (offset, smoothing, tolerance, stroke_width)
        self.units = units
        self._unit_scale = 1.0
        self.offset = offset if offset is not None else 1.0
        self.smoothing = smoothing if smoothing is not None else 5.0
        self.tolerance = tolerance if tolerance is not None else 0.1
        self.stroke_width = stroke_width if stroke_width is not None else 1.0
        self.color = color
        self.show_progress = show_progress
        self._reporter: Callable[[str, int, int | None], None] | None = None

    @contextmanager
    def _progress(self) -> Iterator[None]:
        if not self.show_progress or self._reporter is not None:
            yield
            return
        progress = create_progress_bar("Vector border")
        progress.columns = (
            *progress.columns,
            TextColumn("{task.completed:.0f} processed"),
            TimeElapsedColumn(),
        )
        last_stage = ""

        def report(stage: str, completed: int, total: int | None) -> None:
            nonlocal last_stage
            if stage != last_stage:
                log_info(f"Border: {stage}")
                last_stage = stage
                progress.reset(task, total=total, completed=completed, description=stage)
            else:
                progress.update(task, completed=completed, total=total)

        with progress:
            task = progress.add_task("Starting vector border", total=None)
            self._reporter = report
            try:
                yield
            finally:
                self._reporter = None

    def _report(self, stage: str, completed: int = 0, total: int | None = None) -> None:
        if self._reporter is not None:
            self._reporter(stage, completed, total)

    def generate(self, input_svg: Path, output_svg: Path) -> None:
        """Save a bordered SVG; never overwrite the source file."""
        if input_svg.resolve() == output_svg.resolve():
            raise BorderGenerationError("Border output must differ from the input SVG.")
        log_info("Generating vector border")
        with self._progress():
            self._report("Reading SVG")
            try:
                source = input_svg.read_text(encoding="utf-8-sig")
            except UnicodeError as error:
                raise BorderGenerationError("SVG input must use UTF-8 encoding.") from error
            result = self.add_to_svg(source)
            self._report("Writing bordered SVG")
            output_svg.write_text(result, encoding="utf-8")
            self._report("Border saved", 1, 1)

    def add_to_svg(self, svg: str) -> str:
        """Return an SVG with preserved artwork and a new outer border path."""
        with self._progress():
            return self._add_to_svg(svg)

    def default_output(self, input_path: Path, svg: str) -> Path:
        """Name a border output using its offset in the selected distance units."""
        try:
            root = ET.fromstring(svg)
        except ET.ParseError as error:
            raise BorderGenerationError(f"Invalid SVG: {error}") from error
        viewport = self._viewport(root)
        factor = self._distance_scale(root, viewport)
        requested = self._requested_distances[0]
        size = requested if requested is not None else min(viewport[2:]) / 210 / factor
        return input_path.with_name(
            f"{input_path.stem}_border_{self.border_type}_{size:.12g}{self.units}.svg"
        )

    def _frame(self, artwork: BaseGeometry) -> tuple[ET.Element, BaseGeometry]:
        self._report("Building bounding-box frame")
        distance = self.offset + self.stroke_width / 2 + 2 * self.tolerance
        left, top, right, bottom = artwork.bounds
        left, top, right, bottom = (
            left - distance,
            top - distance,
            right + distance,
            bottom + distance,
        )
        radius = self._requested_corner_radius * self._unit_scale
        if not math.isfinite(radius):
            raise BorderGenerationError("Converted corner radius must be finite.")
        expansion = 0.0
        if radius > 0:
            error = self.tolerance / 4
            angle = math.acos(1 - min(1, error / radius))
            if angle == 0:
                raise BorderGenerationError(
                    "Corner radius exceeds numeric accuracy; increase tolerance."
                )
            segments = max(16, math.ceil(math.pi / (4 * angle)))
            if segments > 4096:
                raise BorderGenerationError(
                    "Corner radius exceeds accuracy budget; increase tolerance."
                )
            required = self.offset + self.stroke_width / 2 + self.tolerance

            def fits(extra: float) -> bool:
                x0, y0, x1, y1 = left - extra, top - extra, right + extra, bottom + extra
                if x1 - x0 < 2 * radius or y1 - y0 < 2 * radius:
                    return False
                inner_left, inner_top = x0 + radius, y0 + radius
                inner_right, inner_bottom = x1 - radius, y1 - radius
                if inner_left == inner_right and inner_top == inner_bottom:
                    core: BaseGeometry = Point(inner_left, inner_top)
                elif inner_left == inner_right or inner_top == inner_bottom:
                    core = LineString([(inner_left, inner_top), (inner_right, inner_bottom)])
                else:
                    core = box(inner_left, inner_top, inner_right, inner_bottom)
                # Inscribed arc chords make this check conservative for the native SVG arcs.
                candidate = core.buffer(radius, quad_segs=segments)
                return (
                    candidate.covers(artwork) and candidate.boundary.distance(artwork) >= required
                )

            self._report("Checking rounded frame against actual artwork")
            if not fits(0):
                low = 0.0
                high = radius + distance
                if not math.isfinite(high) or not fits(high):
                    raise BorderGenerationError(
                        "Cannot enclose artwork with the requested corner radius."
                    )
                self._report("Finding minimum rounded-frame expansion", 0, 64)
                for attempt in range(64):
                    if high - low <= error:
                        break
                    middle = (low + high) / 2
                    if fits(middle):
                        high = middle
                    else:
                        low = middle
                    self._report("Finding minimum rounded-frame expansion", attempt + 1, 64)
                else:
                    raise BorderGenerationError(
                        "Cannot resolve rounded-frame expansion within tolerance."
                    )
                expansion = high
                if self.show_progress:
                    log_info(
                        f"Rounded frame expanded by {expansion / self._unit_scale:.6g} "
                        f"{self.units} per side to preserve clearance; corner radius unchanged."
                    )
        left, top, right, bottom = (
            left - expansion,
            top - expansion,
            right + expansion,
            bottom + expansion,
        )
        width, height = right - left, bottom - top
        element = ET.Element(
            f"{{{SVG_NS}}}rect",
            {
                "x": f"{left:.17g}",
                "y": f"{top:.17g}",
                "width": f"{width:.17g}",
                "height": f"{height:.17g}",
                "rx": f"{radius:.17g}",
                "ry": f"{radius:.17g}",
            },
        )
        return element, box(left, top, right, bottom)

    def _add_to_svg(self, svg: str) -> str:
        self._report("Parsing SVG and resolving styles")
        if "<!ENTITY" in svg.upper() or "<?xml-stylesheet" in svg.lower():
            raise BorderGenerationError("Entities and external stylesheets are unsupported.")
        try:
            root = ET.fromstring(
                svg, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
            )
            if root.tag != f"{{{SVG_NS}}}svg":
                raise BorderGenerationError("Input must have an SVG-namespaced svg root.")
            if any(e.get("id") == "svg-optimizer-border" for e in root.iter()):
                raise BorderGenerationError("This SVG already contains an optimizer border.")
            normalized = copy.deepcopy(root)
            self._resolve_class_styles(normalized)
            self._validate_features(normalized)
            viewport = self._viewport(root)
            scale = min(viewport[2:]) / 210
            defaults = (scale, 2 * scale, 0.005 * scale, 0.1 * scale)
            self._unit_scale = self._distance_scale(root, viewport)
            self.offset, self.smoothing, self.tolerance, self.stroke_width = (
                default if requested is None else requested * self._unit_scale
                for requested, default in zip(self._requested_distances, defaults)
            )
            if any(
                not math.isfinite(value) or value <= 0
                for value in (self.offset, self.tolerance, self.stroke_width)
            ) or not math.isfinite(self.smoothing):
                raise BorderGenerationError(
                    "Converted border distances must be finite and positive."
                )
            if self.show_progress:
                log_info(
                    f"Border distances (SVG units): offset={self.offset:g}, "
                    f"smoothing={self.smoothing:g}, tolerance={self.tolerance:g}, "
                    f"width={self.stroke_width:g}"
                )
            artwork = self._artwork(normalized, viewport)
            if self.border_type == "frame":
                border_path, curve_bounds = self._frame(artwork)
            else:
                border = self._outline(artwork)
                curves = self._curved_outline(border, artwork)
                border_path = ET.Element(f"{{{SVG_NS}}}path", {"d": self._path_data(curves)})
                controls = [point for curve in curves for point in curve]
                curve_bounds = box(
                    min(p[0] for p in controls),
                    min(p[1] for p in controls),
                    max(p[0] for p in controls),
                    max(p[1] for p in controls),
                )
            border_path.attrib.update(
                {
                    "id": "svg-optimizer-border",
                    "fill": "none",
                    "stroke": self.color,
                    "stroke-width": str(self.stroke_width),
                    "stroke-opacity": "1",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
            root.append(border_path)
            self._expand_viewport(root, viewport, curve_bounds)
            self._report("Serializing bordered SVG")
            ET.register_namespace("", SVG_NS)
            result = ET.tostring(root, encoding="unicode", xml_declaration=True)
            self._report("Border geometry complete", 1, 1)
            return result
        except (ET.ParseError, GEOSException) as error:
            raise BorderGenerationError(f"Invalid SVG geometry: {error}") from error

    @staticmethod
    def _resolve_class_styles(root: ET.Element) -> None:
        """Resolve a deliberately limited CSS subset on the geometry-only copy."""
        rules: list[tuple[str, str]] = []
        for parent in root.iter():
            for element in list(parent):
                if element.tag != f"{{{SVG_NS}}}style":
                    continue
                if set(element.attrib) - {"type"} or element.get("type", "text/css") != "text/css":
                    raise BorderGenerationError("Conditional SVG stylesheets are unsupported.")
                css = re.sub(r"/\*.*?\*/", "", element.text or "", flags=re.DOTALL)
                while css.strip():
                    match = re.match(r"\s*\.([a-zA-Z_][a-zA-Z0-9_-]*)\s*\{([^{}]*)\}", css)
                    if match is None:
                        raise BorderGenerationError(
                            "Only simple .class SVG stylesheet selectors are supported."
                        )
                    rules.append((match[1], match[2]))
                    end = match.end()
                    css = css[end:]
                parent.remove(element)
        known_classes = {name for name, _ in rules}
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            classes = set(element.get("class", "").split())
            if classes - known_classes:
                raise BorderGenerationError("SVG contains an unresolved CSS class.")
            declarations = [value for name, value in rules if name in classes]
            if declarations:
                declarations.append(element.get("style", ""))
                element.set("style", ";".join(declarations))
            element.attrib.pop("class", None)
        # Validate unused rules too, rather than silently accepting unsafe CSS.
        for _, declarations in rules:
            probe = ET.Element(f"{{{SVG_NS}}}g", {"style": declarations})
            SVGBorderGenerator._validate_features(probe)

    @staticmethod
    def _validate_features(root: ET.Element) -> None:
        allowed = {"svg", "g", "path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}
        ignored = {"metadata", "title", "desc", "defs"}
        forbidden = {
            "clip-path",
            "mask",
            "filter",
            "marker-start",
            "marker-mid",
            "marker-end",
            "vector-effect",
            "stroke-dasharray",
            "stroke-dashoffset",
            "transform-origin",
            "transform-box",
            "class",
        }
        styles = {
            "fill",
            "fill-rule",
            "fill-opacity",
            "stroke",
            "stroke-width",
            "stroke-opacity",
            "opacity",
            "display",
            "visibility",
            "color",
            "shape-rendering",
            "text-rendering",
            "image-rendering",
            "clip-rule",
        }

        def visit(element: ET.Element) -> None:
            if not isinstance(element.tag, str):
                return
            tag = element.tag.removeprefix(f"{{{SVG_NS}}}")
            if tag in ignored:
                if any(
                    isinstance(child.tag, str) and child.tag == f"{{{SVG_NS}}}style"
                    for child in element.iter()
                ):
                    raise BorderGenerationError("SVG stylesheets are unsupported.")
                return
            if tag not in allowed or (tag == "svg" and element is not root):
                raise BorderGenerationError(f"Unsupported SVG element: {tag}.")
            if element is root and element.get("transform"):
                raise BorderGenerationError("Root transforms are unsupported; use a group.")
            if forbidden.intersection(element.attrib):
                raise BorderGenerationError(f"Unsupported SVG effect or CSS class on {tag}.")
            for declaration in element.get("style", "").split(";"):
                if not declaration.strip():
                    continue
                name, separator, value = declaration.partition(":")
                if not separator or name.strip() not in styles or "!important" in value:
                    raise BorderGenerationError(f"Unsupported inline SVG style: {declaration}.")
            if any("url(" in value.lower() for value in element.attrib.values()):
                raise BorderGenerationError("SVG paint servers and references are unsupported.")
            for child in element:
                visit(child)

        visit(root)

    @staticmethod
    def _length(value: str) -> tuple[float, str]:
        match = re.fullmatch(
            r"\s*([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)" r"(px|mm|cm|in|pt|pc)?\s*", value
        )
        if not match or not math.isfinite(float(match[1])) or float(match[1]) <= 0:
            raise BorderGenerationError("SVG dimensions must be positive absolute lengths.")
        return float(match[1]), match[2] or ""

    @classmethod
    def _viewport(cls, root: ET.Element) -> tuple[float, float, float, float]:
        for attribute in ("width", "height"):
            if root.get(attribute) is not None:
                cls._length(root.attrib[attribute])
        if root.get("viewBox"):
            try:
                values = tuple(
                    float(v) for v in re.split(r"[\s,]+", root.attrib["viewBox"].strip())
                )
            except ValueError as error:
                raise BorderGenerationError("Invalid SVG viewBox.") from error
            if len(values) != 4 or not all(math.isfinite(v) for v in values):
                raise BorderGenerationError("SVG viewBox must contain four finite numbers.")
            x, y, width, height = values
        else:
            if not root.get("width") or not root.get("height"):
                raise BorderGenerationError("SVG needs a viewBox or absolute width and height.")
            w, wu = cls._length(root.attrib["width"])
            h, hu = cls._length(root.attrib["height"])
            x, y, width, height = 0.0, 0.0, w * ABSOLUTE_UNIT_PX[wu], h * ABSOLUTE_UNIT_PX[hu]
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            raise BorderGenerationError("SVG viewBox dimensions must be positive.")
        return x, y, width, height

    def _distance_scale(
        self, root: ET.Element, viewport: tuple[float, float, float, float]
    ) -> float:
        """Convert one selected distance unit using the original root viewport."""
        if self.units == "svg":
            return 1.0
        if self.units == "percent":
            return min(viewport[2:]) / 100
        pixels_per_user_unit = 1.0
        if root.get("viewBox"):
            if not root.get("width") or not root.get("height"):
                raise BorderGenerationError(
                    f"--border-units {self.units} requires absolute SVG width and height "
                    "with a viewBox; use svg or percent units when physical scale is unknown."
                )
            width, width_unit = self._length(root.attrib["width"])
            height, height_unit = self._length(root.attrib["height"])
            sx = width * ABSOLUTE_UNIT_PX[width_unit] / viewport[2]
            sy = height * ABSOLUTE_UNIT_PX[height_unit] / viewport[3]
            aspect = root.get("preserveAspectRatio", "xMidYMid meet").split()
            if (
                not aspect
                or aspect[0]
                not in (
                    "none",
                    "xMinYMin",
                    "xMidYMin",
                    "xMaxYMin",
                    "xMinYMid",
                    "xMidYMid",
                    "xMaxYMid",
                    "xMinYMax",
                    "xMidYMax",
                    "xMaxYMax",
                )
                or len(aspect) > 2
                or (len(aspect) == 2 and aspect[1] not in ("meet", "slice"))
            ):
                raise BorderGenerationError(
                    "Unsupported SVG preserveAspectRatio for unit conversion."
                )
            if aspect[0] == "none":
                if not math.isclose(sx, sy, rel_tol=1e-9):
                    raise BorderGenerationError(
                        "Physical border units require uniform SVG scaling; "
                        "preserveAspectRatio='none' stretches the SVG differently along each axis. "
                        "Use svg or percent units instead."
                    )
                pixels_per_user_unit = sx
            else:
                pixels_per_user_unit = (
                    max(sx, sy) if len(aspect) == 2 and aspect[1] == "slice" else min(sx, sy)
                )
        if not math.isfinite(pixels_per_user_unit) or pixels_per_user_unit <= 0:
            raise BorderGenerationError("SVG physical scale must be finite and positive.")
        factor = ABSOLUTE_UNIT_PX[self.units] / pixels_per_user_unit
        if not math.isfinite(factor) or factor <= 0:
            raise BorderGenerationError("Border unit conversion exceeds numeric range.")
        return factor

    def _artwork(
        self, root: ET.Element, viewport: tuple[float, float, float, float]
    ) -> BaseGeometry:
        normalized = copy.deepcopy(root)
        self._prune_transparent(normalized)
        # Work in root user coordinates, not the scaled/translated display viewport.
        normalized.attrib.pop("viewBox", None)
        normalized.set("width", str(viewport[2]))
        normalized.set("height", str(viewport[3]))
        self._report("Resolving vector shapes and transforms")
        try:
            document = SVG.parse(
                StringIO(ET.tostring(normalized, encoding="unicode")), reify=True, on_error="raise"
            )
        except (ValueError, TypeError, IndexError, ZeroDivisionError) as error:
            raise BorderGenerationError(f"Cannot parse SVG shapes: {error}") from error
        if document is None:
            raise BorderGenerationError("Cannot parse SVG document.")
        self._report(
            "Preflight: checking curve budget before flattening"
            if self.border_type == "outline"
            else "Collecting artwork for frame bounds"
        )
        paths: list[SVGPath] = []
        endpoints: list[Coordinate] = []
        for element in document.elements():
            if not isinstance(element, Shape):
                continue
            if element.values and element.values.get("visibility") in ("hidden", "collapse"):
                continue
            if element.stroke.value is not None and element.stroke.alpha:
                raise BorderGenerationError(
                    "Stroked artwork is unsupported; convert strokes to paths."
                )
            if element.fill.value is None or not element.fill.alpha:
                continue
            path = SVGPath(element)
            path.reify()
            paths.append(path)
            if self.border_type == "outline":
                for subpath in path.as_subpaths():
                    vertices = [
                        self._coordinate(segment.end)
                        for segment in subpath
                        if not isinstance(segment, Move) and segment.end is not None
                    ]
                    if len(vertices) >= 3 and isinstance(LineString(vertices).convex_hull, Polygon):
                        endpoints.extend(vertices)
        if self.border_type == "outline" and len(endpoints) >= 3:
            hull = LineString(endpoints).convex_hull
            lower_bound = hull.length if isinstance(hull, Polygon) else 2 * hull.length
            # The enclosing curve cannot be shorter than this convex hull.
            minimum_count = math.ceil(
                max(0, lower_bound - 2 * math.pi * self.tolerance) / self._spline_spacing()
            )
            if minimum_count > MAX_CURVES:
                raise BorderGenerationError(
                    f"Preflight: at least {minimum_count:,} cubic segments are needed "
                    f"(limit {MAX_CURVES:,}) before offsetting or smoothing. "
                    f"Increase --border-smoothing to at least "
                    f"{2 * lower_bound / (MAX_CURVES - 1) / self._unit_scale:.6g} "
                    f"{self.units} units, or increase "
                    "--border-tolerance. Omit those options for scale-aware CLI defaults."
                )
        polygons: list[BaseGeometry] = []
        point_count = 0
        self._report("Flattening artwork curves")
        segment_count = 0
        for path in paths:
            for subpath in path.as_subpaths():
                points: list[Coordinate] = []
                for segment in subpath:
                    segment_count += 1
                    if segment_count % 100 == 1:
                        self._report("Flattening artwork curves", segment_count)
                    if isinstance(segment, Move):
                        points.append(self._coordinate(segment.end))
                    elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                        controls = [self._coordinate(segment.start)]
                        if isinstance(segment, CubicBezier):
                            controls.extend(
                                (
                                    self._coordinate(segment.control1),
                                    self._coordinate(segment.control2),
                                )
                            )
                        else:
                            controls.append(self._coordinate(segment.control))
                        controls.append(self._coordinate(segment.end))
                        points.extend(self._flatten_bezier(controls))
                    elif isinstance(segment, Arc):
                        points.extend(self._flatten_arc(segment))
                    elif isinstance(segment, (Line, Close)):
                        points.append(self._coordinate(segment.end))
                    else:
                        raise BorderGenerationError(
                            f"Unsupported SVG segment: {type(segment).__name__}."
                        )
                    if len(points) + point_count > MAX_POINTS:
                        raise BorderGenerationError(
                            "SVG exceeds the vector point budget; increase tolerance."
                        )
                point_count += len(points)
                if len(set(points)) < 3:
                    continue
                polygon = make_valid(Polygon(points))
                if not polygon.is_empty and polygon.area > 0:
                    polygons.append(polygon)
        if not polygons:
            raise BorderGenerationError("SVG contains no supported visible filled artwork.")
        self._report("Flattening artwork curves", segment_count)
        self._report(f"Unioning {len(polygons)} filled subpaths ({point_count} vector points)")
        return unary_union(polygons)

    @staticmethod
    def _prune_transparent(element: ET.Element) -> bool:
        if not isinstance(element.tag, str):
            return True
        if element.tag.removeprefix(f"{{{SVG_NS}}}") in ("metadata", "title", "desc", "defs"):
            return True
        declarations = dict(
            (name.strip(), value.strip())
            for declaration in element.get("style", "").split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        )
        opacity = declarations.get("opacity", element.get("opacity", "1"))
        try:
            alpha = float(opacity.removesuffix("%"))
        except ValueError as error:
            raise BorderGenerationError(f"Unsupported SVG opacity: {opacity}.") from error
        if not math.isfinite(alpha):
            raise BorderGenerationError("SVG opacity must be finite.")
        if alpha <= 0:
            element.clear()
            return False
        for child in list(element):
            if not SVGBorderGenerator._prune_transparent(child):
                element.remove(child)
        return True

    def _coordinate(self, point: SVGPoint | None) -> Coordinate:
        if point is None or point.x is None or point.y is None:
            raise BorderGenerationError("SVG segment has missing coordinates.")
        coordinate = float(point.x), float(point.y)
        if not all(math.isfinite(v) for v in coordinate):
            raise BorderGenerationError("SVG contains non-finite coordinates.")
        if any(math.ulp(v) * 64 > self.tolerance for v in coordinate):
            raise BorderGenerationError("Tolerance is below numeric precision at this SVG's scale.")
        return coordinate

    def _flatten_bezier(
        self, controls: list[Coordinate], depth: int = 0, tolerance: float | None = None
    ) -> list[Coordinate]:
        error = self.tolerance if tolerance is None else tolerance
        chord = LineString([controls[0], controls[-1]])
        if max(chord.distance(Point(p)) for p in controls[1:-1]) <= error:
            return [controls[-1]]
        if depth >= 24:
            raise BorderGenerationError("Curve cannot be flattened safely; increase tolerance.")
        levels = [controls]
        while len(levels[-1]) > 1:
            levels.append(
                [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(levels[-1], levels[-1][1:])]
            )
        left = [level[0] for level in levels]
        right = [level[-1] for level in reversed(levels)]
        result = self._flatten_bezier(left, depth + 1, error) + self._flatten_bezier(
            right, depth + 1, error
        )
        if len(result) > MAX_POINTS:
            raise BorderGenerationError("Curve exceeds the vector point budget.")
        return result

    def _flatten_arc(self, arc: Arc) -> list[Coordinate]:
        center = self._coordinate(arc.center)
        axes = (self._coordinate(arc.prx), self._coordinate(arc.pry))
        radius_bound = math.sqrt(
            sum((p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2 for p in axes)
        )
        if radius_bound == 0:
            return [self._coordinate(arc.end)]
        step = min(math.pi / 2, math.sqrt(8 * self.tolerance / radius_bound))
        if arc.sweep is None or not math.isfinite(arc.sweep):
            raise BorderGenerationError("SVG arc has no finite sweep.")
        count = max(1, math.ceil(abs(arc.sweep) / step))
        if count > MAX_POINTS:
            raise BorderGenerationError("Arc exceeds the vector point budget; increase tolerance.")
        return [self._coordinate(arc.point(i / count)) for i in range(1, count + 1)]

    def _buffer(self, geometry: BaseGeometry, distance: float) -> BaseGeometry:
        # GEOS inscribes round joins. Inflate positive radii to guarantee clearance.
        ratio = min(1.0, self.tolerance / (10 * abs(distance)))
        angle = math.acos(1 - ratio)
        if angle == 0:
            raise BorderGenerationError("Tolerance is too small for this SVG's scale.")
        segments = max(16, math.ceil(math.pi / (4 * angle)))
        if segments > 4096:
            raise BorderGenerationError("Buffer exceeds the accuracy budget; increase tolerance.")
        radius = distance / math.cos(math.pi / (4 * segments)) if distance > 0 else distance
        return geometry.buffer(radius, quad_segs=segments, join_style="round")

    def _outline(self, artwork: BaseGeometry) -> Polygon:
        # Include curve error and half the border stroke: clearance is to the ink,
        # not merely to the centerline of the new path.
        clearance = self.offset + self.stroke_width / 2 + 2 * self.tolerance
        self._report("Offsetting artwork for minimum clearance")
        protected = self._buffer(artwork, clearance)
        connected = protected
        if isinstance(connected, MultiPolygon):
            pieces = sorted(connected.geoms, key=lambda p: p.area, reverse=True)
            connected = pieces.pop(0)
            if len(pieces) > 1000:
                raise BorderGenerationError("Too many disconnected shapes to bridge safely.")
            total = len(pieces)
            while pieces:
                self._report("Connecting disconnected pieces", total - len(pieces), total)
                index = min(range(len(pieces)), key=lambda i: connected.distance(pieces[i]))
                piece = pieces.pop(index)
                a, b = nearest_points(connected, piece)
                bridge = self._buffer(
                    LineString([a.coords[0], b.coords[0]]), max(self.smoothing, clearance)
                )
                connected = unary_union([connected, piece, bridge])
            self._report("Connecting disconnected pieces", total, total)
        if self.smoothing > 0:
            self._report("Smoothing outline: outward buffer")
            outward = self._buffer(connected, self.smoothing)
            self._report("Smoothing outline: inward buffer")
            closed = self._buffer(outward, -self.smoothing)
            self._report("Combining smoothed and protected outlines")
            connected = unary_union([closed, connected])
            # Leave a numerical margin at coincident union edges before fitting.
            connected = self._buffer(connected, self.tolerance)
        if not isinstance(connected, Polygon):
            raise BorderGenerationError("Cannot produce one connected enclosing border.")
        border = Polygon(connected.exterior)
        self._report("Checking preliminary enclosure and clearance")
        if not border.is_valid or not border.covers(protected):
            raise BorderGenerationError("Smoothed border failed the enclosure check.")
        if border.boundary.distance(artwork) < clearance - self.tolerance:
            raise BorderGenerationError("Smoothed border failed the minimum-clearance check.")
        return border

    def _curved_outline(self, border: Polygon, artwork: BaseGeometry) -> list[Bezier]:
        """Fit and check the actual cubic border, compensating for inward drift."""
        clearance = self.offset + self.stroke_width / 2 + 2 * self.tolerance
        self._report("Preparing fitted-curve clearance check")
        protected = self._buffer(artwork, clearance)
        validation_error = self.tolerance / 4
        margin = 0.0
        for attempt in range(1, 7):
            self._report(f"Fitting cubic border: attempt {attempt}/6")
            expanded = border if margin == 0 else self._buffer(border, margin)
            if not isinstance(expanded, Polygon):
                raise BorderGenerationError("Cannot fit a connected cubic border.")
            curves = self._periodic_spline(expanded)
            points = [curves[0][0]]
            stage = f"Validating cubic curves: attempt {attempt}/6"
            self._report(stage, 0, len(curves))
            for index, curve in enumerate(curves, 1):
                points.extend(self._flatten_bezier(list(curve), tolerance=validation_error))
                if index % 25 == 0 or index == len(curves):
                    self._report(stage, index, len(curves))
                if len(points) > MAX_POINTS:
                    raise BorderGenerationError(
                        "Cubic border exceeds the vector point budget; increase tolerance."
                    )
            candidate = Polygon(points)
            self._report(f"Checking fitted enclosure and clearance: attempt {attempt}/6")
            if (
                candidate.is_valid
                and candidate.exterior.is_simple
                and candidate.covers(protected)
                and candidate.boundary.distance(artwork) >= clearance - validation_error
            ):
                return curves
            # Spline averaging can move either way. Expand the source outline,
            # then refit: moving individual handles would break smooth joins.
            self._report(f"Measuring outward correction: attempt {attempt}/6")
            deviation = expanded.boundary.hausdorff_distance(candidate.boundary)
            if not math.isfinite(deviation):
                raise BorderGenerationError("Cannot measure cubic border fitting error.")
            margin += max(self.tolerance, deviation + 2 * validation_error)
        raise BorderGenerationError(
            "Smooth cubic border failed enclosure/clearance checks; reduce smoothing."
        )

    def _spline_spacing(self) -> float:
        return max(
            self.smoothing / 2,
            math.sqrt(8 * self.tolerance * max(self.offset, self.tolerance)),
        )

    def _periodic_spline(self, border: Polygon) -> list[Bezier]:
        """Convert uniform perimeter samples into a closed C2 cubic B-spline."""
        ring = border.exterior
        spacing = self._spline_spacing()
        count = max(12, math.ceil(ring.length / spacing))
        if count > MAX_CURVES:
            raise BorderGenerationError(
                "Cubic border exceeds the curve budget; increase smoothing or tolerance."
            )
        stage = "Sampling outline for cubic spline"
        self._report(stage, 0, count)
        knots: list[Coordinate] = []
        for i in range(count):
            point = ring.interpolate(i / count, normalized=True)
            knots.append((float(point.x), float(point.y)))
            if (i + 1) % 100 == 0 or i + 1 == count:
                self._report(stage, i + 1, count)
        knots = self._gaussian_perimeter(knots, ring.length / count)
        endpoints = [
            (
                (knots[i - 1][0] + 4 * knots[i][0] + knots[(i + 1) % count][0]) / 6,
                (knots[i - 1][1] + 4 * knots[i][1] + knots[(i + 1) % count][1]) / 6,
            )
            for i in range(count)
        ]
        curves: list[Bezier] = []
        for i, current in enumerate(knots):
            following = knots[(i + 1) % count]
            start = endpoints[i]
            end = endpoints[(i + 1) % count]
            control1 = ((2 * current[0] + following[0]) / 3, (2 * current[1] + following[1]) / 3)
            control2 = ((current[0] + 2 * following[0]) / 3, (current[1] + 2 * following[1]) / 3)
            curves.append((start, control1, control2, end))
        return curves

    def _gaussian_perimeter(self, knots: list[Coordinate], spacing: float) -> list[Coordinate]:
        """Average a cyclic perimeter with Gaussian sigma in SVG distance units."""
        if self.smoothing == 0:
            return knots
        sigma = self.smoothing / spacing
        radius = math.ceil(4 * sigma)
        if radius > MAX_POINTS:
            raise BorderGenerationError(
                "Gaussian smoothing exceeds the averaging budget; reduce smoothing."
            )
        # Wrap each weight, including repeated turns when sigma spans the seam.
        weights = [0.0] * len(knots)
        for shift in range(-radius, radius + 1):
            weights[shift % len(knots)] += math.exp(-0.5 * (shift / sigma) ** 2)
        normalization = sum(weights)
        kernel = [(i, w / normalization) for i, w in enumerate(weights) if w > 0]
        origin = knots[0]
        centered = [(x - origin[0], y - origin[1]) for x, y in knots]
        stage = "Gaussian averaging of closed perimeter"
        self._report(stage, 0, len(knots))
        result: list[Coordinate] = []
        for i in range(len(knots)):
            result.append(
                (
                    origin[0]
                    + math.fsum(
                        weight * centered[(i + shift) % len(knots)][0] for shift, weight in kernel
                    ),
                    origin[1]
                    + math.fsum(
                        weight * centered[(i + shift) % len(knots)][1] for shift, weight in kernel
                    ),
                )
            )
            if (i + 1) % 100 == 0 or i + 1 == len(knots):
                self._report(stage, i + 1, len(knots))
        return result

    @staticmethod
    def _path_data(curves: list[Bezier]) -> str:
        commands = [f"M {curves[0][0][0]:.17g},{curves[0][0][1]:.17g}"]
        commands.extend(
            "C " + " ".join(f"{x:.17g},{y:.17g}" for x, y in curve[1:]) for curve in curves
        )
        return " ".join(commands) + " Z"

    def _expand_viewport(
        self, root: ET.Element, viewport: tuple[float, float, float, float], border: BaseGeometry
    ) -> None:
        x, y, width, height = viewport
        left, top, right, bottom = border.bounds
        padding = self.stroke_width / 2 + self.tolerance
        left, top = min(x, left - padding), min(y, top - padding)
        right, bottom = max(x + width, right + padding), max(y + height, bottom + padding)
        new_width, new_height = right - left, bottom - top
        root.set("viewBox", f"{left:.17g} {top:.17g} {new_width:.17g} {new_height:.17g}")
        for attribute, old_size, new_size in (
            ("width", width, new_width),
            ("height", height, new_height),
        ):
            length, unit = self._length(root.get(attribute, str(old_size)))
            root.set(attribute, f"{length * new_size / old_size:.17g}{unit}")
