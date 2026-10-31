#!/usr/bin/env python3
"""Checks the gallery's items and builds index.json (standard library only).

    python tools/gallery.py check    # what CI runs: every item is valid and index.json is up to date
    python tools/gallery.py index    # rewrite index.json after adding or changing an item
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items"
INDEX = ROOT / "index.json"

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
LICENSES = {"MIT", "CC-BY-4.0", "CC0-1.0"}
KINDS = {"overlay", "widget"}
PACKAGE = "package.cuebot-overlay"
PREVIEWS = {"preview.png", "preview.jpg", "preview.webp"}
MAX_PACKAGE = 25 * 1024 * 1024
MAX_UNPACKED = 100 * 1024 * 1024
MAX_PREVIEW = 2 * 1024 * 1024
PANES = {"widget.html", "widget.css", "widget.js", "fields.json", "data.json", "override.css"}
ASSET = re.compile(r"^assets/([0-9a-f]{64})\.([a-z0-9]{1,8})$")
WIDGET_FILE = re.compile(r"^widgets/(w[0-9]{1,5})/([a-z.]+)$")
ASSET_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "apng", "mp4", "webm", "mov", "mp3", "ogg", "oga",
                    "wav", "m4a", "flac", "opus", "woff", "woff2", "ttf", "otf"}


def text(value, limit):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def check_package(path, kind, original_code, errors):
    data = path.read_bytes()
    if len(data) > MAX_PACKAGE:
        errors.append(f"{path}: larger than 25 MB")
        return
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        errors.append(f"{path}: not a zip file")
        return
    with archive:
        infos = archive.infolist()
        if sum(i.file_size for i in infos) > MAX_UNPACKED:
            errors.append(f"{path}: unpacks to more than 100 MB")
            return
        names = {i.filename for i in infos}
        for name in names:
            if name == "package.json" or ASSET.match(name):
                continue
            m = WIDGET_FILE.match(name)
            if not m or m.group(2) not in PANES:
                errors.append(f"{path}: unexpected file '{name}'")
        if "package.json" not in names:
            errors.append(f"{path}: no package.json")
            return
        try:
            manifest = json.loads(archive.read("package.json").decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            errors.append(f"{path}: package.json is not valid JSON")
            return
        if manifest.get("format") != "cuebot-overlay" or manifest.get("version") != 1:
            errors.append(f"{path}: not a version 1 Cuebot overlay package")
        if manifest.get("kind") != kind:
            errors.append(f"{path}: the package is a '{manifest.get('kind')}' but item.json says '{kind}'")
        if manifest.get("leftOut"):
            errors.append(f"{path}: widgets were left out ({', '.join(manifest['leftOut'])}); share only complete packages")
        if any(layer.get("leftOut") for layer in manifest.get("layers", []) if isinstance(layer, dict)):
            errors.append(f"{path}: a layer was shared without its code")
        widgets = manifest.get("widgets") or {}
        for wid, info in widgets.items():
            if not isinstance(info, dict) or not re.match(r"^w[0-9]{1,5}$", wid):
                errors.append(f"{path}: bad widget entry '{wid}'")
            elif not info.get("cuebot") and not original_code:
                errors.append(f"{path}: widget '{info.get('name', wid)}' is not one of Cuebot's own; only code you wrote may be "
                              "shared, and item.json must say \"originalCode\": true")
        for name in names:
            m = ASSET.match(name)
            if not m:
                continue
            if m.group(2) not in ASSET_EXTENSIONS:
                errors.append(f"{path}: '{name}' is not a file type overlays use")
            elif hashlib.sha256(archive.read(name)).hexdigest() != m.group(1):
                errors.append(f"{path}: '{name}' does not match its content")
        listed = set(manifest.get("assets") or [])
        packed = {n[len("assets/"):] for n in names if n.startswith("assets/")}
        if listed != packed:
            errors.append(f"{path}: package.json's assets do not match the files in assets/")


def load_items(errors):
    items = []
    if not ITEMS.is_dir():
        return items
    for folder in sorted(p for p in ITEMS.iterdir()):
        if not folder.is_dir():
            errors.append(f"{folder}: only item folders belong in items/")
            continue
        slug = folder.name
        if not SLUG.match(slug):
            errors.append(f"{folder}: folder names are lower-case letters, digits and dashes (2 to 49)")
        files = {p.name for p in folder.iterdir()}
        previews = sorted(files & PREVIEWS)
        extra = files - {"item.json", PACKAGE} - PREVIEWS
        if extra:
            errors.append(f"{folder}: unexpected files {sorted(extra)}")
        if "item.json" not in files or PACKAGE not in files or len(previews) != 1:
            errors.append(f"{folder}: needs item.json, {PACKAGE} and one preview (png, jpg or webp)")
            continue
        try:
            meta = json.loads((folder / "item.json").read_text("utf-8"))
        except ValueError:
            errors.append(f"{folder}/item.json: not valid JSON")
            continue
        for key, limit in (("name", 80), ("author", 60), ("description", 500)):
            if not text(meta.get(key), limit):
                errors.append(f"{folder}/item.json: '{key}' is needed (at most {limit} characters)")
        if meta.get("kind") not in KINDS:
            errors.append(f"{folder}/item.json: 'kind' is overlay or widget")
        if meta.get("license") not in LICENSES:
            errors.append(f"{folder}/item.json: 'license' is one of {sorted(LICENSES)}")
        tags = meta.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 8 or not all(text(t, 24) for t in tags):
            errors.append(f"{folder}/item.json: 'tags' is a list of up to 8 short words")
        preview = folder / previews[0]
        if preview.stat().st_size > MAX_PREVIEW:
            errors.append(f"{preview}: larger than 2 MB")
        package = folder / PACKAGE
        check_package(package, meta.get("kind"), meta.get("originalCode") is True, errors)
        data = package.read_bytes()
        items.append({
            "id": slug,
            "name": meta.get("name"),
            "author": meta.get("author"),
            "description": meta.get("description"),
            "kind": meta.get("kind"),
            "license": meta.get("license"),
            "tags": tags,
            "originalCode": meta.get("originalCode") is True,
            "package": f"items/{slug}/{PACKAGE}",
            "preview": f"items/{slug}/{previews[0]}",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return items


def index_text(items):
    return json.dumps({"format": "cuebot-gallery", "version": 1, "items": items}, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    command = argv[1] if len(argv) > 1 else "check"
    errors = []
    items = load_items(errors)
    if command == "index":
        if errors:
            print("\n".join(e.replace(str(ROOT) + "/", "") for e in errors))
            return 1
        INDEX.write_text(index_text(items), "utf-8")
        print(f"index.json: {len(items)} items")
        return 0
    if not INDEX.exists() or INDEX.read_text("utf-8") != index_text(items):
        errors.append("index.json is out of date: run python tools/gallery.py index and commit it")
    for error in errors:
        print("error:", error.replace(str(ROOT) + "/", ""))
    print(f"{len(items)} items, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
