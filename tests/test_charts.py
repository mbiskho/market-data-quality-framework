from __future__ import annotations

import struct
import unittest
import zlib
from pathlib import Path

from mdq.charts import render_reports
from mdq.validation import validate_csv

ROOT = Path(__file__).resolve().parents[1]


class ChartTests(unittest.TestCase):
    def test_reports_create_valid_svg_and_png_artifacts(self) -> None:
        report = validate_csv(ROOT / "data" / "sample_ohlcv.csv")
        outputs = render_reports(report, ROOT / "reports")
        self.assertEqual(len(outputs), 4)
        for path in outputs:
            self.assertGreater(path.stat().st_size, 100)
        for path in ROOT.joinpath("reports").glob("*.png"):
            image = path.read_bytes()
            self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", image[16:24]), (1200, 760))
            offset = 8
            compressed = bytearray()
            while offset < len(image):
                length = struct.unpack(">I", image[offset:offset + 4])[0]
                kind = image[offset + 4:offset + 8]
                data = image[offset + 8:offset + 8 + length]
                crc = struct.unpack(">I", image[offset + 8 + length:offset + 12 + length])[0]
                self.assertEqual(crc, zlib.crc32(kind + data) & 0xFFFFFFFF)
                if kind == b"IDAT":
                    compressed.extend(data)
                offset += length + 12
            self.assertEqual(len(zlib.decompress(compressed)), (1200 * 3 + 1) * 760)
        svg = (ROOT / "reports" / "market-data-quality-overview.svg").read_text()
        self.assertIn("<polyline", svg)
        self.assertIn("CLOSE PRICE SERIES", svg)


if __name__ == "__main__":
    unittest.main()
