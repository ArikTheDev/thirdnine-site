#!/usr/bin/env python3
"""Site health check for thirdnine.dev.

Catches the things that quietly break small websites before they ship:
broken internal links, missing pages, duplicate or missing anchors, images
without alt text, inline code the security policy would block, missing
security headers, and malformed structured data.

Usage: python3 scripts/check_site.py   (exits 1 if anything fails)
Standard library only, so it runs anywhere Python 3.9+ is installed.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent / "site"  # the folder Cloudflare Pages publishes
PAGES = ["index.html", "404.html"]
SITE_URL = "https://thirdnine.dev/"
REQUIRED_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")


class PageScan(HTMLParser):
    """Collects what the checks need from one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[tuple[str, int]] = []
        self.images_without_alt: list[int] = []
        self.inline_styles: list[int] = []
        self.inline_scripts: list[int] = []
        self.external_assets: list[tuple[str, int]] = []
        self.json_ld: list[str] = []
        self.h1_count = 0
        self.has_lang = False
        self.has_title = False
        self.has_description = False
        self._in_json_ld = False
        self._json_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name: (value or "") for name, value in attrs}
        line = self.getpos()[0]
        if "id" in attr:
            self.ids.append(attr["id"])
        if "style" in attr:
            self.inline_styles.append(line)
        if tag == "html" and attr.get("lang"):
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "meta" and attr.get("name") == "description" and attr.get("content"):
            self.has_description = True
        if tag == "meta" and attr.get("property") == "og:image":
            image = attr.get("content", "")
            if image.startswith(SITE_URL):
                self.links.append(("/" + image[len(SITE_URL):], line))
        if tag == "img" and "alt" not in attr:
            self.images_without_alt.append(line)
        if tag == "a" and "href" in attr:
            self.links.append((attr["href"], line))
        if tag == "link" and "href" in attr:
            href = attr["href"]
            if attr.get("rel") == "canonical":
                pass
            elif href.startswith(("http://", "https://")):
                self.external_assets.append((href, line))
            else:
                self.links.append((href, line))
        if tag in ("script", "img", "iframe", "source") and attr.get("src"):
            src = attr["src"]
            if src.startswith(("http://", "https://")):
                self.external_assets.append((src, line))
            else:
                self.links.append((src, line))
        if tag == "script":
            if attr.get("type") == "application/ld+json":
                self._in_json_ld = True
                self._json_buffer = []
            elif "src" not in attr:
                self.inline_scripts.append(line)

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_buffer))
            self._in_json_ld = False


def resolve_local(href: str) -> Path | None:
    """Map a site-relative URL to a file in the repo, or None if it's an anchor only."""
    parts = urlsplit(href)
    path = unquote(parts.path)
    if not path:
        return None
    if path.endswith("/"):
        path += "index.html"
    return ROOT / path.lstrip("/")


def check_pages(failures: list[str]) -> None:
    scans: dict[str, PageScan] = {}
    for page in PAGES:
        file = ROOT / page
        if not file.exists():
            failures.append(f"{page}: file is missing")
            continue
        scan = PageScan()
        scan.feed(file.read_text(encoding="utf-8"))
        scans[page] = scan

    for page, scan in scans.items():
        if not scan.has_lang:
            failures.append(f"{page}: <html> needs a lang attribute")
        if not scan.has_title:
            failures.append(f"{page}: missing <title>")
        if page == "index.html" and not scan.has_description:
            failures.append(f"{page}: missing meta description")
        if scan.h1_count != 1:
            failures.append(f"{page}: expected exactly one <h1>, found {scan.h1_count}")
        seen: set[str] = set()
        for element_id in scan.ids:
            if element_id in seen:
                failures.append(f"{page}: duplicate id '{element_id}'")
            seen.add(element_id)
        for line in scan.images_without_alt:
            failures.append(f"{page}:{line}: image is missing alt text")
        for line in scan.inline_styles:
            failures.append(f"{page}:{line}: inline style attribute (blocked by the security policy)")
        for line in scan.inline_scripts:
            failures.append(f"{page}:{line}: inline script (blocked by the security policy)")
        for url, line in scan.external_assets:
            failures.append(f"{page}:{line}: loads {url} from another site (blocked by the security policy)")
        for raw in scan.json_ld:
            try:
                json.loads(raw)
            except json.JSONDecodeError as error:
                failures.append(f"{page}: structured data is not valid JSON ({error})")

        for href, line in scan.links:
            if href.startswith(EXTERNAL_SCHEMES):
                continue
            parts = urlsplit(href)
            target_page = page
            if parts.path:
                target = resolve_local(href)
                if target is None or not target.exists():
                    failures.append(f"{page}:{line}: link to missing file '{href}'")
                    continue
                target_page = target.relative_to(ROOT).as_posix()
            if parts.fragment:
                target_scan = scans.get(target_page)
                if target_scan is not None and parts.fragment not in target_scan.ids:
                    failures.append(f"{page}:{line}: link to missing anchor '#{parts.fragment}'")


def check_headers(failures: list[str]) -> None:
    file = ROOT / "_headers"
    if not file.exists():
        failures.append("_headers: file is missing")
        return
    text = file.read_text(encoding="utf-8")
    for header in REQUIRED_HEADERS:
        if f"{header}:" not in text:
            failures.append(f"_headers: missing {header}")


def check_sitemap(failures: list[str]) -> None:
    file = ROOT / "sitemap.xml"
    try:
        tree = ET.parse(file)
    except (ET.ParseError, FileNotFoundError) as error:
        failures.append(f"sitemap.xml: cannot be read ({error})")
        return
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locations = [element.text for element in tree.iter(f"{namespace}loc")]
    if SITE_URL not in locations:
        failures.append(f"sitemap.xml: does not list {SITE_URL}")


def main() -> int:
    failures: list[str] = []
    check_pages(failures)
    check_headers(failures)
    check_sitemap(failures)
    if failures:
        print(f"Site check failed ({len(failures)} problem(s)):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Site check passed: {len(PAGES)} pages, links, anchors, alt text, headers and sitemap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
