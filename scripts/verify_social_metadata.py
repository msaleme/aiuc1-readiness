#!/usr/bin/env python3
"""Verify the static social-preview contract for AIUC-1 Pages."""

from __future__ import annotations

import struct
from html.parser import HTMLParser
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
ASSETS = ROOT / "assets"
PUBLIC_BASE = "https://msaleme.github.io/aiuc1-readiness/"
IMAGE_URL = f"{PUBLIC_BASE}assets/aiuc1-evidence-share.png"
QUICKSTART_URL = (
    "https://github.com/msaleme/red-team-blue-team-agent-fabric/"
    "blob/main/docs/QUICKSTART.md"
)


class HeadMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.anchors: list[dict[str, str]] = []
        self._active_anchor: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            if key and attributes.get("content"):
                self.meta[key] = attributes["content"]
        if tag == "link" and attributes.get("rel") and attributes.get("href"):
            self.links[attributes["rel"]] = attributes["href"]
        if tag == "a":
            self._active_anchor = {
                "class": attributes.get("class") or "",
                "href": attributes.get("href") or "",
                "text": "",
            }

    def handle_data(self, data: str) -> None:
        if self._active_anchor is not None:
            self._active_anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_anchor is not None:
            self._active_anchor["text"] = self._active_anchor["text"].strip()
            self.anchors.append(self._active_anchor)
            self._active_anchor = None


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), f"{path} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def assert_primary_harness_action(anchors: list[dict[str, str]]) -> None:
    actions = [
        anchor
        for anchor in anchors
        if anchor["text"] == "Run the harness"
        and "button" in anchor["class"].split()
    ]
    assert len(actions) == 1, "expected exactly one primary Run the harness action"
    assert actions[0]["href"] == QUICKSTART_URL, (
        "Run the harness action must point directly to Quick Start"
    )


def assert_counts_name_their_artifact(html: str) -> None:
    """A test-count claim must say which artifact it counted.

    The page published "603 unique test IDs" under the heading "Repository
    snapshot" while the repository's main branch was at 606. The number was not
    wrong -- it was the v4.15.0 release figure -- but nothing on the page said
    so, and a count that does not name its artifact silently becomes false the
    next time the artifact moves.

    Correcting the number would only reset the clock. This asserts the property
    instead: any numeric test-ID claim must carry a version or an explicit
    release/main qualifier in the same fact block.
    """
    claims = re.findall(
        r"<strong>\s*(\d[\d,]*)\s*</strong>\s*<span>(.*?)</span>",
        html, flags=re.S | re.I)
    unqualified = []
    for value, text in claims:
        if not re.search(r"test\s*ID", text, re.I):
            continue
        if not re.search(r"v\d+\.\d+|release|\bmain\b|commit", text, re.I):
            unqualified.append(value)
    assert not unqualified, (
        "test-ID counts that do not name the artifact they counted: "
        f"{unqualified}. Say which release or revision produced the number."
    )


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

    html = INDEX.read_text(encoding="utf-8")
    assert "https://pubpoint.com/" in html, "brand pathway must link to PubPoint"
    assert_primary_harness_action(parser.anchors)
    assert "Not affiliated with or endorsed by AIUC-1." in html
    assert_counts_name_their_artifact(html)

    assert (ASSETS / "favicon.svg").is_file()
    for name, size in (("icon-180.png", (180, 180)), ("icon-192.png", (192, 192)),
                       ("icon-512.png", (512, 512)), ("aiuc1-evidence-share.png", (1200, 630))):
        assert png_dimensions(ASSETS / name) == size, f"{name} dimensions must be {size}"

    print("social metadata and assets verified")


if __name__ == "__main__":
    main()
