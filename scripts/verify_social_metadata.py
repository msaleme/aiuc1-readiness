#!/usr/bin/env python3
"""Verify the static social-preview contract for AIUC-1 Pages."""

from __future__ import annotations

import struct
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
ASSETS = ROOT / "assets"
PUBLIC_BASE = "https://msaleme.github.io/aiuc1-readiness/"
IMAGE_URL = f"{PUBLIC_BASE}assets/aiuc1-evidence-share.png"


class HeadMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            if key and attributes.get("content"):
                self.meta[key] = attributes["content"]
        if tag == "link" and attributes.get("rel") and attributes.get("href"):
            self.links[attributes["rel"]] = attributes["href"]


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), f"{path} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def main() -> None:
    parser = HeadMetadata()
    parser.feed(INDEX.read_text(encoding="utf-8"))

    expected_meta = {
        "og:title",
        "og:description",
        "og:type",
        "og:url",
        "og:site_name",
        "og:image",
        "og:image:secure_url",
        "og:image:type",
        "og:image:width",
        "og:image:height",
        "og:image:alt",
        "twitter:card",
        "twitter:title",
        "twitter:description",
        "twitter:image",
        "twitter:image:alt",
    }
    missing = expected_meta - parser.meta.keys()
    assert not missing, f"missing social metadata: {sorted(missing)}"
    assert parser.links.get("canonical") == PUBLIC_BASE
    assert parser.links.get("icon") == "assets/favicon.svg"
    assert parser.links.get("apple-touch-icon") == "assets/icon-180.png"
    assert parser.links.get("manifest") == "site.webmanifest"
    assert parser.meta["og:url"] == PUBLIC_BASE
    assert parser.meta["og:image"] == IMAGE_URL
    assert parser.meta["og:image:secure_url"] == IMAGE_URL
    assert parser.meta["twitter:image"] == IMAGE_URL
    assert parser.meta["og:image:type"] == "image/png"
    assert parser.meta["og:image:width"] == "1200"
    assert parser.meta["og:image:height"] == "630"
    assert parser.meta["twitter:card"] == "summary_large_image"

    assert (ASSETS / "favicon.svg").is_file()
    for name, size in (("icon-180.png", (180, 180)), ("icon-192.png", (192, 192)),
                       ("icon-512.png", (512, 512)), ("aiuc1-evidence-share.png", (1200, 630))):
        assert png_dimensions(ASSETS / name) == size, f"{name} dimensions must be {size}"

    print("social metadata and assets verified")


if __name__ == "__main__":
    main()
