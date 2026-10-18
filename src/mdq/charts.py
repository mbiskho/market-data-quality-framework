"""Small stdlib-only SVG and PNG report renderer."""

from __future__ import annotations

import math
import struct
import zlib
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from .models import QualityReport

WIDTH = 1200
HEIGHT = 760
NAVY = "#14243a"
INK = "#26364a"
MUTED = "#68798d"
GRID = "#e7edf3"
BLUE = "#3979d6"
TEAL = "#1b9a8a"
AMBER = "#e2a338"
RED = "#d65b58"
PALE = "#f4f7fb"
WHITE = "#ffffff"

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000",) * 7,
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00110", "00100"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
}


class Canvas:
    """Shared shape list rendered to editable SVG and dependency-free PNG."""

    def __init__(self) -> None:
        self.shapes: list[tuple] = []

    def rect(self, x: int, y: int, width: int, height: int, fill: str, radius: int = 0) -> None:
        self.shapes.append(("rect", x, y, width, height, fill, radius))

    def line(self, x1: int, y1: int, x2: int, y2: int, color: str, width: int = 1) -> None:
        self.shapes.append(("line", x1, y1, x2, y2, color, width))

    def circle(self, x: int, y: int, radius: int, fill: str) -> None:
        self.shapes.append(("circle", x, y, radius, fill))

    def text(self, x: int, y: int, value: str, size: int = 14, color: str = INK, bold: bool = False) -> None:
        self.shapes.append(("text", x, y, value.upper(), size, color, bold))

    def polyline(self, points: list[tuple[int, int]], color: str, width: int = 3) -> None:
        self.shapes.append(("polyline", points, color, width))

    def svg(self) -> str:
        items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">']
        items.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{WHITE}"/>')
        for shape in self.shapes:
            if shape[0] == "rect":
                _, x, y, width, height, fill, radius = shape
                items.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"/>')
            elif shape[0] == "line":
                _, x1, y1, x2, y2, color, width = shape
                items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
            elif shape[0] == "circle":
                _, x, y, radius, fill = shape
                items.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}"/>')
            elif shape[0] == "polyline":
                _, points, color, width = shape
                point_text = " ".join(f"{x},{y}" for x, y in points)
                items.append(f'<polyline points="{point_text}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
            else:
                _, x, y, value, size, color, bold = shape
                items.append(
                    f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial, sans-serif" '
                    f'font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>'
                )
        items.append("</svg>")
        return "\n".join(items)

    def png(self) -> bytes:
        pixels = bytearray([255, 255, 255] * WIDTH * HEIGHT)

        def color_tuple(color: str) -> tuple[int, int, int]:
            return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))

        def pixel(x: int, y: int, color: str) -> None:
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                offset = (y * WIDTH + x) * 3
                pixels[offset:offset + 3] = bytes(color_tuple(color))

        def fill_rect(x: int, y: int, width: int, height: int, color: str) -> None:
            for row in range(max(0, y), min(HEIGHT, y + height)):
                start = (row * WIDTH + max(0, x)) * 3
                end = (row * WIDTH + min(WIDTH, x + width)) * 3
                if end > start:
                    pixels[start:end] = bytes(color_tuple(color)) * ((end - start) // 3)

        def draw_line(x1: int, y1: int, x2: int, y2: int, color: str, thickness: int = 1) -> None:
            dx, dy = abs(x2 - x1), abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            error = dx - dy
            while True:
                fill_rect(x1 - thickness // 2, y1 - thickness // 2, thickness, thickness, color)
                if x1 == x2 and y1 == y2:
                    break
                twice = 2 * error
                if twice > -dy:
                    error -= dy
                    x1 += sx
                if twice < dx:
                    error += dx
                    y1 += sy

        for shape in self.shapes:
            if shape[0] == "rect":
                _, x, y, width, height, fill, radius = shape
                fill_rect(x, y, width, height, fill)
            elif shape[0] == "line":
                _, x1, y1, x2, y2, color, width = shape
                draw_line(x1, y1, x2, y2, color, width)
            elif shape[0] == "circle":
                _, cx, cy, radius, fill = shape
                color = color_tuple(fill)
                for y in range(cy - radius, cy + radius + 1):
                    for x in range(cx - radius, cx + radius + 1):
                        if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                            pixel(x, y, fill)
            elif shape[0] == "polyline":
                _, points, color, width = shape
                for start, end in zip(points, points[1:]):
                    draw_line(*start, *end, color, width)
            else:
                _, x, y, value, size, color, bold = shape
                scale = max(1, size // 9)
                cursor = x
                for character in value:
                    glyph = FONT.get(character, FONT[" "])
                    for row, bitmap_row in enumerate(glyph):
                        for column, active in enumerate(bitmap_row):
                            if active == "1":
                                fill_rect(cursor + column * scale, y - 7 * scale + row * scale, scale, scale, color)
                    cursor += 6 * scale

        raw = bytearray()
        row_bytes = WIDTH * 3
        for row in range(HEIGHT):
            raw.append(0)
            raw.extend(pixels[row * row_bytes:(row + 1) * row_bytes])
        return b"\x89PNG\r\n\x1a\n" + _png_chunk(
            b"IHDR", struct.pack(">2I5B", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
        ) + _png_chunk(
            b"IDAT", zlib.compress(bytes(raw), 9)
        ) + _png_chunk(b"IEND", b"")


def render_reports(report: QualityReport, output_dir: str | Path) -> tuple[Path, ...]:
    """Render overview and pipeline flow charts based on this validation report."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []
    for name, canvas in (
        ("market-data-quality-overview", _overview(report)),
        ("market-data-quality-flow", _flow(report)),
    ):
        svg_path = output / f"{name}.svg"
        png_path = output / f"{name}.png"
        svg_path.write_text(canvas.svg(), encoding="utf-8")
        png_path.write_bytes(canvas.png())
        artifacts.extend((svg_path, png_path))
    return tuple(artifacts)


def _frame(title: str, subtitle: str, report: QualityReport) -> Canvas:
    canvas = Canvas()
    canvas.rect(0, 0, WIDTH, HEIGHT, WHITE)
    canvas.rect(0, 0, WIDTH, 10, BLUE)
    canvas.text(64, 77, title, 34, NAVY, True)
    canvas.text(66, 112, subtitle, 14, MUTED)
    canvas.text(66, 145, f"SYNTHETIC SAMPLE  /  {report.record_count} SOURCE ROWS  /  {report.expected_interval_minutes} MIN INTERVAL", 11, BLUE, True)
    return canvas


def _overview(report: QualityReport) -> Canvas:
    canvas = _frame("MARKET DATA QUALITY", "OHLCV validation snapshot  |  deterministic checks  |  no external dependencies", report)
    cards = [
        (64, "QUALITY SCORE", f"{report.quality_score:.1f}%", BLUE),
        (426, "VALID ROWS", f"{report.valid_row_count}/{report.record_count}", TEAL),
        (788, "FINDINGS", f"{report.error_count} ERR  {report.warning_count} WARN", RED if report.error_count else AMBER),
    ]
    for x, label, value, accent in cards:
        canvas.rect(x, 176, 330, 112, PALE, 10)
        canvas.rect(x, 176, 7, 112, accent, 3)
        canvas.text(x + 24, 211, label, 12, MUTED, True)
        canvas.text(x + 24, 258, value, 24, NAVY, True)

    canvas.text(66, 341, "CLOSE PRICE SERIES", 16, NAVY, True)
    canvas.text(66, 365, "Parsed observations in source order (synthetic price units)", 12, MUTED)
    plot_x, plot_y, plot_w, plot_h = 96, 399, 1010, 194
    canvas.rect(70, 382, 1060, 235, WHITE)
    values = [bar.close for bar in report.bars]
    if values:
        low, high = min(values), max(values)
        span = max(high - low, max(abs(high), 1.0) * 0.005)
        points = [
            (plot_x + round(index * plot_w / max(len(values) - 1, 1)),
             plot_y + plot_h - round((value - low) * plot_h / span))
            for index, value in enumerate(values)
        ]
        for fraction in (0, 0.5, 1):
            y = plot_y + round(plot_h * fraction)
            canvas.line(plot_x, y, plot_x + plot_w, y, GRID)
        canvas.polyline(points, BLUE, 4)
        for x, y in points:
            canvas.circle(x, y, 5, TEAL)
        canvas.text(73, plot_y + 5, f"{high:.2f}", 10, MUTED)
        canvas.text(73, plot_y + plot_h, f"{low:.2f}", 10, MUTED)
    else:
        canvas.text(420, 490, "NO FULLY PARSED OBSERVATIONS", 16, MUTED, True)

    canvas.text(66, 664, "FINDINGS BY CHECK", 14, NAVY, True)
    counts = Counter(issue.code for issue in report.issues)
    selected = counts.most_common(5)
    if not selected:
        selected = [("no findings", 0)]
    for index, (code, count) in enumerate(selected):
        x = 66 + index * 222
        canvas.text(x, 699, code.replace("_", " "), 10, MUTED, True)
        bar_width = 150 if not counts else max(8, round(150 * count / max(1, selected[0][1])))
        canvas.rect(x, 715, 150, 10, GRID, 4)
        canvas.rect(x, 715, bar_width, 10, RED if code not in ("timestamp_gap", "out_of_order") else AMBER, 4)
        canvas.text(x + 158, 725, str(count), 11, INK, True)
    canvas.text(66, 749, "Score = 40% completeness + 40% validity + 20% timestamp uniqueness", 10, MUTED)
    return canvas


def _flow(report: QualityReport) -> Canvas:
    canvas = _frame("VALIDATION FLOW", "One input file, explicit checks, inspectable output  |  counts below come from this run", report)
    stages = [
        ("01  INGEST", report.record_count, "CSV ROWS", BLUE),
        ("02  PARSE", report.parsed_count, "FULL OHLCV", TEAL),
        ("03  CHECK", report.valid_row_count, "VALID ROWS", AMBER),
        ("04  REPORT", len(report.issues), "FINDINGS", RED),
    ]
    card_xs = [64, 354, 644, 934]
    for index, (title, value, caption, color) in enumerate(stages):
        x = card_xs[index]
        canvas.rect(x, 190, 230, 140, PALE, 10)
        canvas.rect(x, 190, 230, 7, color, 4)
        canvas.text(x + 20, 229, title, 13, MUTED, True)
        canvas.text(x + 20, 278, str(value), 27, NAVY, True)
        canvas.text(x + 20, 307, caption, 11, color, True)
        if index < len(stages) - 1:
            canvas.line(x + 238, 260, x + 277, 260, MUTED, 2)
            canvas.polyline([(x + 268, 253), (x + 277, 260), (x + 268, 267)], MUTED, 2)

    canvas.text(66, 395, "ROW FUNNEL", 16, NAVY, True)
    canvas.text(66, 419, "Every bar is calculated from the same source file", 12, MUTED)
    labels = [
        ("Rows read", report.record_count, BLUE),
        ("Complete rows", report.complete_row_count, TEAL),
        ("Fully parsed", report.parsed_count, AMBER),
        ("Valid rows", report.valid_row_count, RED),
    ]
    max_value = max([value for _, value, _ in labels] + [1])
    for index, (label, value, color) in enumerate(labels):
        y = 464 + index * 54
        canvas.text(68, y + 17, label, 13, INK, True)
        canvas.rect(270, y, 730, 26, GRID, 5)
        width = round(730 * value / max_value)
        canvas.rect(270, y, width, 26, color, 5)
        canvas.text(1020, y + 19, str(value), 13, NAVY, True)

    canvas.rect(64, 696, 1066, 38, PALE, 6)
    canvas.text(82, 721, "CONTRACT", 11, BLUE, True)
    canvas.text(198, 721, "ISO-8601 UTC  |  FINITE NUMBERS  |  POSITIVE OHLC  |  NON-NEGATIVE VOLUME  |  EXPECTED BAR SPACING", 10, INK)
    return canvas


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
