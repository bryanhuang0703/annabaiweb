#!/usr/bin/env python3
"""Export the Claude canvas design (design/Noir.dc.html) to the static site (index.html).

Usage:
    python3 tools/export_canvas.py            # writes index.html
    python3 tools/export_canvas.py --check    # exits 1 if index.html is out of date

The canvas file uses the Design Component format: markup inside <x-dc>, page CSS in
<helmet>, {{holes}} filled from a logic class, <sc-if> branches and onClick handlers.
This script turns it into plain HTML that GitHub Pages can serve:

  * head (SEO, Open Graph, JSON-LD, self-hosted @font-face) comes from tools/head.html
  * extra CSS rules written in the canvas <helmet> are inserted into that head
  * {{accent}} and other tweak props are replaced by their data-props defaults
  * canvas asset URLs (/_blob/...) are mapped to files in assets/
  * the phone menu (<sc-if> + handlers) becomes a hidden panel driven by tools/menu.js
  * small logos use resized WebP files (LOGO_SIZES); a skip link to <main> is added
  * the CSP meta tag in head.html gets the sha256 hash of the inlined menu script

It fails loudly if anything canvas-specific is left over, so a new canvas feature
shows up as an error instead of a broken page.
"""
import base64
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "design" / "Noir.dc.html"
TARGET = ROOT / "index.html"
HEAD = ROOT / "tools" / "head.html"
MENU_JS = ROOT / "tools" / "menu.js"

# Canvas upload id -> site asset, plus attributes to add on <img> tags that use it.
ASSETS = {
    "/_blob/33d543e911319cf0537e977326f07df9": "assets/logo.png",
}

# Displayed logo size (px) -> resized file. Sizes not listed keep the 512px PNG.
LOGO_SIZES = {
    "20": "assets/logo-64.webp",
    "32": "assets/logo-64.webp",
    "168": "assets/logo-336.webp",
}

SKIP_LINK = '<a class="ab-skip" href="#content">Skip to content</a>'

# CSS rules the static site needs on top of the canvas CSS, inserted right after
# the canvas rule whose text starts with the key.
EXTRA_CSS_AFTER = {
    ".ab-nav-toggle{": ".ab-nav-panel[hidden]{display:none !important}",
}


def fail(msg):
    sys.exit(f"export_canvas: {msg}")


def between(text, start, end, what):
    i = text.find(start)
    j = text.find(end, i + len(start)) if i >= 0 else -1
    if i < 0 or j < 0:
        fail(f"could not find {what}")
    return text[i + len(start):j]


def prop_defaults(src):
    m = re.search(r"data-props='([^']*)'", src)
    if not m:
        return {}
    props = json.loads(html.unescape(m.group(1)))
    return {k: v["default"] for k, v in props.items()
            if isinstance(v, dict) and "default" in v and not k.startswith("$")}


def canvas_css(helmet, head):
    style = between(helmet, "<style>", "</style>", "<style> in <helmet>")
    rules = [l.strip() for l in style.splitlines() if l.strip()]
    keep = []
    for rule in rules:
        selector = rule.split("{", 1)[0]
        # skip base rules (body, a, html) that head.html already defines,
        # including ones head.html wraps in a media query
        if re.search(r"(^|\n|\{)" + re.escape(selector) + r"\{", head):
            continue
        keep.append(rule)
        for prefix, extra in EXTRA_CSS_AFTER.items():
            if rule.startswith(prefix):
                keep.append(extra)
    return "\n".join(keep)


def img_size_attrs(tag):
    w = re.search(r"width:\s*(\d+)px", tag)
    h = re.search(r"height:\s*(\d+)px", tag)
    return (w.group(1), h.group(1)) if w and h else None


def convert_body(body, props):
    # 1. tweak props -> literal values
    for name, value in props.items():
        body = body.replace("{{" + name + "}}", str(value))

    # 2. assets: map url, add width/height, lazy-load images that are not in the header
    header_end = body.find("</header>")

    def fix_img(m):
        tag = m.group(0)
        for blob, path in ASSETS.items():
            tag = tag.replace(blob, path)
        size = img_size_attrs(tag)
        if size and size[0] in LOGO_SIZES and 'src="assets/logo.png"' in tag:
            tag = tag.replace('src="assets/logo.png"', f'src="{LOGO_SIZES[size[0]]}"')
        extra = ""
        if size and " width=" not in tag:
            extra += f' width="{size[0]}" height="{size[1]}"'
        if m.start() > header_end and "loading=" not in tag:
            extra += ' loading="lazy"'
        if extra:
            tag = re.sub(r'(alt="[^"]*")', r"\1" + extra, tag, count=1)
        return tag

    body = re.sub(r"<img\b[^>]*>", fix_img, body)

    # 3. phone menu: button
    body = re.sub(
        r'aria-label="\{\{menuLabel\}\}" aria-expanded="\{\{menuOpen\}\}" onClick="\{\{toggleMenu\}\}"',
        'id="ab-nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="ab-nav-panel"',
        body,
    )
    # icons: closed state shows the bars, open state shows the X
    def icon(m):
        state, svg = m.group(1), m.group(2).strip()
        cls = "ab-icon-close" if state == "menuOpen" else "ab-icon-open"
        svg = svg.replace("<svg ", f'<svg class="{cls}" ', 1)
        if cls == "ab-icon-close":
            svg = svg.replace('aria-hidden="true">', 'aria-hidden="true" style="display: none">', 1)
        return re.sub(r"></path>", "/>", svg)

    body = re.sub(
        r'<sc-if value="\{\{(menuOpen|menuClosed)\}\}"[^>]*>\s*(<svg\b.*?</svg>)\s*</sc-if>',
        icon, body, flags=re.S)
    # panel: rendered hidden, opened by menu.js
    body = re.sub(
        r'<sc-if value="\{\{menuOpen\}\}"[^>]*>\s*<div class="ab-nav-panel"(.*?)</div>\s*</sc-if>',
        lambda m: '<div class="ab-nav-panel" id="ab-nav-panel" hidden' + m.group(1) + "</div>",
        body, flags=re.S)
    body = body.replace(' onClick="{{closeMenu}}"', "")

    # skip link target: first <main>
    if body.count("<main>") != 1:
        fail("expected exactly one <main> for the skip link")
    body = body.replace("<main>", '<main id="content" tabindex="-1">')

    # 4. nothing canvas-specific may remain
    leftovers = [p for p in ("{{", "<sc-", "<dc-import", "onClick=", "/_blob/") if p in body]
    if leftovers:
        fail("canvas-only syntax left in the page: " + ", ".join(leftovers)
             + " (update tools/export_canvas.py for the new canvas feature)")
    return body.strip("\n")


def build():
    src = SOURCE.read_text(encoding="utf-8")
    head = HEAD.read_text(encoding="utf-8")
    xdc = between(src, "<x-dc>", "</x-dc>", "<x-dc> block")
    helmet = between(xdc, "<helmet>", "</helmet>", "<helmet> block")
    body = xdc.replace("<helmet>" + helmet + "</helmet>", "")
    head = head.replace("/*CANVAS_CSS*/", canvas_css(helmet, head))
    if "/*CANVAS_CSS*/" in head:
        fail("tools/head.html: the /*CANVAS_CSS*/ slot was not filled")
    body = convert_body(body, prop_defaults(src))
    menu = MENU_JS.read_text(encoding="utf-8").strip("\n")
    script = f"\n{menu}\n"
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    if "/*MENU_HASH*/" not in head:
        fail("tools/head.html: the /*MENU_HASH*/ slot in the CSP meta tag is missing")
    head = head.replace("/*MENU_HASH*/", "sha256-" + digest)
    return (f"{head.rstrip()}\n<body>\n{SKIP_LINK}\n{body}\n"
            f"<script>{script}</script>\n</body>\n</html>\n")


def main():
    page = build()
    if "--check" in sys.argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != page:
            print("index.html is out of date; run python3 tools/export_canvas.py")
            sys.exit(1)
        print("index.html is up to date")
        return
    TARGET.write_text(page, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)} ({len(page.encode())} bytes)")


if __name__ == "__main__":
    main()
