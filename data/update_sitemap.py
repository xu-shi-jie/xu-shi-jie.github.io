#!/usr/bin/env python3
"""
Regenerate sitemap.xml so each deploy ships fresh SEO metadata.

<lastmod> for every URL is derived from git history (the date the page's
source files were last committed) rather than blindly stamping "today",
so the dates stay honest and search engines keep trusting them. Falls back
to the current UTC date when git history is unavailable.

Lives in data/ alongside the other update_*.py scripts; writes sitemap.xml
at the repository root. Run from anywhere (paths resolve via __file__).
"""

import re
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root (script lives in data/)
BASE_URL = "https://xu-shi-jie.github.io"

# Each entry: (URL path, <changefreq>, <priority>, [source files/dirs that
# determine its lastmod]). Paths are relative to the repo root.
PAGES = [
    ("/", "monthly", "1.0",
     ["index.html", "data/pubs.json", "data/presentations.json", "data/journals.json"]),
    ("/docs/resume.pdf", "monthly", "0.6",
     ["docs/resume.pdf", "cv-latex", "data/pubs.json", "data/presentations.json"]),
]


def today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def last_modified(sources) -> str:
    """Newest commit date (YYYY-MM-DD) across the given source paths."""
    newest = ""
    for src in sources:
        if not (ROOT / src).exists():
            continue
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%cs", "--", src],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return today()
        if out > newest:
            newest = out
    return newest or today()


def blog_pages():
    """Discover generated blog pages so each post is indexed.

    The blog index plus one entry per posts/*.md (its lastmod follows the
    Markdown source). Returns the same 4-tuple shape as PAGES.
    """
    pages = []
    posts_dir = ROOT / "posts"
    if (ROOT / "blogs" / "index.html").exists():
        sources = ["blogs/index.html"] + (
            [str(p.relative_to(ROOT)) for p in posts_dir.glob("*.md")]
            if posts_dir.exists() else [])
        pages.append(("/blogs/", "weekly", "0.7", sources))
    for src in sorted(posts_dir.glob("*.md")) if posts_dir.exists() else []:
        slug = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-") or "post"
        if (ROOT / "blogs" / f"{slug}.html").exists():
            pages.append((f"/blogs/{slug}.html", "monthly", "0.6",
                          [f"posts/{src.name}"]))
    return pages


def main() -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    all_pages = PAGES + blog_pages()
    for path, changefreq, priority, sources in all_pages:
        lines += [
            "  <url>",
            f"    <loc>{BASE_URL}{path}</loc>",
            f"    <lastmod>{last_modified(sources)}</lastmod>",
            f"    <changefreq>{changefreq}</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote sitemap.xml with {len(all_pages)} URLs.")


if __name__ == "__main__":
    main()
