# Updating the site from the canvas

The page is designed on a Claude canvas and exported to `index.html` with a script.
The canvas source is kept in `design/Noir.dc.html`; do not edit `index.html` by hand,
because the next export overwrites it.

## Steps

1. Edit the "Home, amber noir" artboard on the canvas.
2. Copy the canvas file `project/Noir.dc.html` over `design/Noir.dc.html`.
3. Run `python3 tools/export_canvas.py`. It writes `index.html` and stops with an
   error if the canvas uses something it does not know how to convert.
4. Check the page at desktop and phone widths, then commit both files and push to
   `master`. GitHub Pages republishes annabai.com within a minute or two.

`python3 tools/export_canvas.py --check` reports whether `index.html` matches the
current design file without writing anything.

## What lives where

- `design/Noir.dc.html`: canvas source (copied, not edited here)
- `tools/head.html`: everything in `<head>` (title, description, Open Graph, JSON-LD,
  fonts, base CSS). Edit this file directly for SEO or metadata changes; the
  `/*CANVAS_CSS*/` slot receives the CSS written in the canvas.
- `tools/menu.js`: the phone menu script
- `tools/export_canvas.py`: the converter, including the map from canvas uploads
  (`/_blob/...`) to files in `assets/`. A new image on the canvas needs a matching
  file in `assets/` and an entry in `ASSETS`.
