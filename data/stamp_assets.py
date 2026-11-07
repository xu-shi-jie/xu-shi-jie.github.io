#!/usr/bin/env python3
"""
Stamp shared assets with a content hash so pages and assets never mismatch.

GitHub Pages serves everything with Cache-Control: max-age=600. A page that
loads /docs/hero-dna.js under a fixed URL can, for ten minutes after a deploy,
run the browser's cached old script against the new markup (the hero then shows
its no-JS fallback nav over the canvas). Rewriting the reference to
/docs/hero-dna.js?v=<hash of the file> makes every change a new URL.

Idempotent: re-running replaces an existing ?v=. Run after build_blog.py, which
writes the blog pages with a bare URL. Paths resolve relative to this file.

Usage: python3 stamp_assets.py
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ["docs/hero-dna.js"]


def pages():
    yield from ROOT.glob("*.html")
    yield from (ROOT / "blogs").glob("*.html")


def main() -> None:
    for asset in ASSETS:
        version = hashlib.sha1((ROOT / asset).read_bytes()).hexdigest()[:10]
        ref = re.compile(r'(["\'])/' + re.escape(asset) + r'(?:\?v=[0-9a-f]*)?\1')
        for page in pages():
            text = page.read_text(encoding="utf-8")
            new = ref.sub(lambda m: f"{m[1]}/{asset}?v={version}{m[1]}", text)
            if new != text:
                page.write_text(new, encoding="utf-8")
                print(f"{page.relative_to(ROOT)}: /{asset}?v={version}")


if __name__ == "__main__":
    main()
