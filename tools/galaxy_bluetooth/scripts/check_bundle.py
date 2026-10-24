#!/usr/bin/env python3
"""Check that bundled Galaxy's module, HTML and CSS references resolve locally."""
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / "ios/GalaxyBluetooth/Resources/Web"
missing = []
checked = 0


def check(source, reference):
    global checked
    if reference == "vue":
        reference = "/assets/vendor/vue/vue.esm-browser.js"
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("#", "data:", "blob:")):
        return
    path = parsed.path
    if "${" in reference:
        return
    if path == "/manifest.json":
        path = "/assets/manifest.json"
    if not path or not (path.startswith(("/", ".")) or "." in Path(path).name):
        return
    target = (ROOT / path.lstrip("/") if path.startswith("/") else source.parent / path).resolve()
    checked += 1
    if not target.is_file():
        missing.append((str(source.relative_to(ROOT)), reference))


for source in ROOT.rglob("*"):
    if source.suffix not in (".js", ".mjs", ".css", ".html"):
        continue
    text = source.read_text()
    if source.suffix in (".js", ".mjs"):
        for _, reference in re.findall(r'(?:\bfrom\s*|\bimport\s*\(|\bimport\s*)([\"\x27])([^\"\x27]+)\1', text):
            if reference != "vue" and not reference.startswith(("/", "./", "../")):
                continue
            check(source, reference)
    elif source.suffix == ".css":
        for reference in re.findall(r'url\(\s*[\"\x27]?([^\"\x27\)\s]+)', text):
            check(source, reference)
    else:
        for reference in re.findall(r'(?:src|href)=[\"\x27]([^\"\x27]+)', text):
            check(source, reference)

if missing:
    for source, reference in missing:
        print(f"Missing: {source} → {reference}")
    raise SystemExit(1)
print(f"All {checked} bundled Galaxy module/asset references resolve")
