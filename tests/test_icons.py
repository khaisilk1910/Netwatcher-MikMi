"""Brand icon pack static validation; no HA environment required."""
from pathlib import Path
from xml.etree import ElementTree
import struct
import json

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "custom_components" / "netwatcher_mikmi"


def _png_dimensions(path):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])


def test_integration_brand_images():
    for basename in ("icon.png", "dark_icon.png", "icon@2x.png", "dark_icon@2x.png"):
        dims = _png_dimensions(DOMAIN / "brand" / basename)
        assert dims == ((512, 512) if "@2x" in basename else (256, 256))
    for basename in ("logo.png", "dark_logo.png", "logo@2x.png", "dark_logo@2x.png"):
        width, height = _png_dimensions(DOMAIN / "brand" / basename)
        assert width > height


def test_all_icons_are_static_self_contained_svg():
    files = sorted((DOMAIN / "frontend" / "icons").glob("*.svg"))
    assert len(files) == 33
    for svg in files:
        src = svg.read_text()
        assert "<script" not in src.lower()
        assert "javascript:" not in src.lower()
        assert "http://" not in src.replace('xmlns="http://www.w3.org/2000/svg"', '')
        assert "https://" not in src
        parsed = ElementTree.fromstring(src)
        assert parsed.tag.endswith("svg")


def test_version_matches_manifest_card():
    m = json.loads((DOMAIN / "manifest.json").read_text())
    assert m["version"] == "0.4.1-beta.1"
    card = (DOMAIN / "frontend" / "netwatcher-mikmi-card.js").read_text()
    assert "ICON_PATHS" in card and "icon_style" in card
    assert "document.createElementNS" in card
    assert "innerHTML" not in card.replace('never innerHTML','')
