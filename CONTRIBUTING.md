# Sharing an overlay or widget

The [wiki](../../wiki) has the detailed guide (including doing it all in the browser). The short version:

1. In Cuebot, open **Overlays & Widgets**, and on the overlay (or one widget, such as an alert box) choose
   **Share → Export package…**. Use **Export with custom widget code** only for code you wrote yourself.
2. Fork this repository and add a folder `items/<name>/` (lower-case letters, digits and dashes) with:
   - `package.cuebot-overlay`: the file Cuebot saved (at most 25 MB).
   - `preview.png` (or `.jpg` / `.webp`, at most 2 MB): what it looks like on stream, ideally 1280 × 720.
   - `item.json`:
     ```json
     {
       "name": "Neon starter scene",
       "author": "Your name",
       "description": "A chat box and alert box in neon colours.",
       "kind": "overlay",
       "license": "CC-BY-4.0",
       "tags": ["neon", "chat", "alerts"]
     }
     ```
     `kind` is `overlay` or `widget` (a single widget, such as an alert box). `license` is `MIT`, `CC-BY-4.0` or
     `CC0-1.0`. If the package contains widget code that is not Cuebot's own, add `"originalCode": true` to say you
     wrote it.
3. Run `python tools/gallery.py index` (Python 3, nothing to install) and commit the updated `index.json`.
4. Open a pull request and tick the boxes in its template. The check runs `python tools/gallery.py check`.

A maintainer looks at every item before merging: that it imports and works, that the preview is honest, and that
nothing in it is someone else's work. Items that load code or files from other sites may be asked to bundle them
instead.

## Taking an item down

Authors can remove their own item with a pull request. Anyone can [report an item](../../issues/new?template=report.yml);
copyright reports take the item down while they are looked at.
