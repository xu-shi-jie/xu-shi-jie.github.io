#!/usr/bin/env python3
"""
Static blog generator.

Reads Markdown files from posts/ and renders a small blog into blogs/:
  - blogs/index.html        — reverse-chronological list of posts
  - blogs/<slug>.html       — one page per post

Each post is a Markdown file with an optional YAML-ish front matter block
delimited by `---` lines at the very top, e.g.

    ---
    title: My first post
    date: 2026-06-08
    description: A short summary used for SEO and the index page.
    tags: bioinformatics, deep learning
    ---

    # Heading

    Body written in **Markdown**.

Front matter is optional: `title` falls back to the first `# H1` or the
file name; `date` falls back to the file's last git-commit date (or today).

The generated pages reuse the same theme system (fonts, colors, dark-mode
toggle, breadcrumb nav) as the site's index.html so the blog feels native.

Lives in data/ alongside the other update_*.py scripts; writes into blogs/
at the repository root. Run from anywhere (paths resolve via __file__):

    python3 data/build_blog.py
"""

import html
import json
import re
import subprocess
import datetime
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent  # repo root (script lives in data/)
POSTS_DIR = ROOT / "posts"
BLOGS_DIR = ROOT / "blogs"
BASE_URL = "https://xu-shi-jie.github.io"

MD_EXTENSIONS = [
    "fenced_code",   # ``` code blocks
    "tables",
    "sane_lists",
    "toc",
    "attr_list",
    "footnotes",
    "smarty",        # nice quotes/dashes
    "pymdownx.arithmatex",  # $...$, $$...$$ math -> MathJax delimiters
]

# arithmatex with generic=True emits \(...\) / \[...\] (wrapped in
# .arithmatex spans/divs) which MathJax renders; it also extracts math before
# the other extensions run, so smarty/emphasis can't mangle the LaTeX.
MD_EXTENSION_CONFIGS = {
    "pymdownx.arithmatex": {"generic": True},
}


# --------------------------------------------------------------------------- #
# Shared look & feel
# --------------------------------------------------------------------------- #
# Kept deliberately close to index.html's :root/[data-theme] variables and
# typography so the blog is visually continuous with the rest of the site.
SHARED_HEAD = """\
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <style>
    :root {
      --text-color: #222;
      --bg-color: #fff;
      --link-color: #0645ad;
      --nav-bg: #fafafa;
      --code-bg: #f5f5f5;
      --border: rgba(0, 0, 0, 0.1);
      --muted: #888;
    }
    [data-theme="dark"] {
      --text-color: #eee;
      --bg-color: #1a1a1a;
      --link-color: #6ea8fe;
      --nav-bg: #252525;
      --code-bg: #2a2a2a;
      --border: rgba(255, 255, 255, 0.1);
      --muted: #999;
    }
    html, body { overflow-x: hidden; }
    body {
      font-family: 'Roboto', -apple-system, BlinkMacSystemFont, segoe ui, Oxygen, Ubuntu, Cantarell, open sans, helvetica neue, sans-serif;
      font-size: 18px;
      margin: 0 auto;
      line-height: 1.6;
      color: var(--text-color);
      background: var(--bg-color);
      transition: color 0.3s, background-color 0.3s;
    }
    .hero {
      width: 100%;
      height: 120px;
      background-image: url('/docs/background-pkalm.jpg');
      background-size: cover;
      background-position: center;
    }
    .breadcrumb-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 0.25rem;
      margin-bottom: 1rem;
      padding: 0.25rem 0;
      font-size: 0.95rem;
      border-bottom: 1px solid var(--border);
      width: 100%;
      box-sizing: border-box;
    }
    .breadcrumb-content {
      padding-left: max(1rem, calc((100vw - 800px) / 2 + 1rem));
    }
    .breadcrumb-nav button { padding-right: max(1rem, calc((100vw - 800px) / 2 + 1rem)); }
    @media (max-width: 600px) {
      .breadcrumb-content { padding-left: 1rem; }
      .breadcrumb-nav button { padding-right: 1rem; }
    }
    .content { padding: 0 1rem 4rem; max-width: 800px; margin: 0 auto; }
    a {
      color: var(--text-color);
      text-decoration: none;
      border-bottom: 1px solid var(--text-color);
      opacity: 0.8;
      transition: opacity 0.2s ease;
    }
    a:hover { opacity: 1; }
    .theme-toggle {
      background: none; border: none; padding: 0; cursor: pointer;
      color: var(--text-color); width: 2rem; height: 2rem;
      display: flex; align-items: center; justify-content: center;
    }
    .theme-toggle img {
      width: 24px; height: 24px;
      transition: filter 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .theme-toggle .moon {
      display: block;
      filter: brightness(0) saturate(100%) invert(45%) sepia(90%) saturate(600%) hue-rotate(180deg) brightness(0.9);
    }
    .theme-toggle .sun { display: none; }
    .theme-toggle:hover .moon {
      filter: brightness(0) saturate(100%) invert(45%) sepia(90%) saturate(600%) hue-rotate(180deg) brightness(1.1) drop-shadow(0 0 4px #3399cc) drop-shadow(0 0 8px #3399cc);
      transform: scale(1.1);
    }
    [data-theme="dark"] .theme-toggle .moon { display: none; }
    [data-theme="dark"] .theme-toggle .sun {
      display: block;
      filter: brightness(0) saturate(100%) invert(55%) sepia(90%) saturate(600%) hue-rotate(360deg) brightness(0.95);
    }
    [data-theme="dark"] .theme-toggle:hover .sun {
      filter: brightness(0) saturate(100%) invert(55%) sepia(90%) saturate(600%) hue-rotate(360deg) brightness(1.1) drop-shadow(0 0 4px #dd8822) drop-shadow(0 0 8px #dd8822);
      transform: scale(1.1);
    }

    /* Post list (index) — simple date + title directory */
    .post-list { list-style: none; padding: 0; }
    .post-list li {
      display: flex; gap: 1rem; align-items: baseline;
      padding: 0.4rem 0; border-bottom: 1px solid var(--border);
    }
    .post-date {
      color: var(--muted); font-size: 0.9rem;
      font-variant-numeric: tabular-nums; white-space: nowrap;
      flex: 0 0 6.5rem;
    }
    .post-list a { border-bottom: none; font-size: 1.05rem; }
    @media (max-width: 480px) {
      .post-list li { flex-direction: column; gap: 0.1rem; }
    }

    /* Article body */
    article h1 { font-size: 2.4rem; margin: 0 0 0.25rem; line-height: 1.2; }
    article h2 { font-size: 1.7rem; margin-top: 2rem; }
    article h3 { font-size: 1.3rem; margin-top: 1.5rem; }
    article img { max-width: 100%; height: auto; }
    /* Left-aligned, not justified: with CJK text + inline formulas, justify
       stretches the spaces around math into large ugly gaps. */
    article p { text-align: left; }
    article blockquote {
      margin: 1rem 0; padding: 0.25rem 1rem;
      border-left: 3px solid var(--border); color: var(--muted);
    }
    article pre {
      background: var(--code-bg); padding: 1rem; border-radius: 6px;
      overflow-x: auto; font-size: 0.85rem;
    }
    article code {
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
      background: var(--code-bg); padding: 0.1rem 0.35rem; border-radius: 4px;
      font-size: 0.85em;
    }
    article pre code { background: none; padding: 0; }
    article table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    article th, article td { border: 1px solid var(--border); padding: 0.4rem 0.6rem; }
    article hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
    .article-meta { color: var(--muted); font-size: 0.9rem; margin-bottom: 2rem; }
  </style>
  <script>
    // Keep the Utterances comment widget (if present) in sync with the theme.
    function syncUtterancesTheme(theme) {
      const frame = document.querySelector('.utterances-frame');
      if (!frame) return;
      frame.contentWindow.postMessage(
        { type: 'set-theme', theme: theme === 'dark' ? 'github-dark' : 'github-light' },
        'https://utteranc.es');
    }
    function toggleTheme() {
      const el = document.documentElement;
      const next = el.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      el.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      syncUtterancesTheme(next);
    }
    document.addEventListener('DOMContentLoaded', () => {
      document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
    });
  </script>
"""

# Utterances comments (https://utteranc.es/), backed by GitHub Issues in the
# xu-shi-jie/comments repo. issue-term="pathname" gives each post its own
# thread.
#
# The script is written with document.write (during synchronous parse) rather
# than createElement/appendChild. utterances' client.js finds its own <script>
# via document.currentScript and only falls back when that is `undefined`; a
# dynamically-inserted script makes currentScript `null`, so the fallback is
# skipped and the widget silently fails. A parser-inserted script keeps
# currentScript valid. The initial theme is read from localStorage here; later
# theme toggles are pushed to the iframe by syncUtterancesTheme().
COMMENTS = """\
    <section id="comments" style="margin-top:3rem; padding-top:1.5rem; border-top:1px solid var(--border);">
      <h2 style="font-size:1.4rem; margin-bottom:1rem;">Comments</h2>
      <script>
        (function () {
          var dark = (localStorage.getItem('theme') || 'light') === 'dark';
          document.write(
            '<script src="https://utteranc.es/client.js" '
            + 'repo="xu-shi-jie/comments" issue-term="pathname" label="comment" '
            + 'theme="' + (dark ? 'github-dark' : 'github-light') + '" '
            + 'crossorigin="anonymous" async><' + '/script>'
          );
        })();
      </script>
    </section>
"""

# MathJax v3. Delimiters match arithmatex's generic output (\\(...\\), \\[...\\]).
# Loaded only on post pages (see render_post); the index needs no math.
MATHJAX = """\
  <script>
    window.MathJax = {
      tex: {
        inlineMath: [['\\\\(', '\\\\)']],
        displayMath: [['\\\\[', '\\\\]']]
      },
      options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] }
    };
  </script>
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
"""

NAV = """\
  <div class="hero" role="banner"></div>
  <nav class="breadcrumb-nav">
    <div class="breadcrumb-content">{breadcrumb}</div>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme" aria-label="Toggle theme">
      <img src="/docs/sun.svg" alt="Light mode" class="sun">
      <img src="/docs/moon.svg" alt="Dark mode" class="moon">
    </button>
  </nav>
"""

FOOTER = """\
  <footer style="text-align:center; font-size:small; color:var(--muted); padding:2rem 1rem;">
    &copy; 2022-<span id="y"></span> Shijie Xu. Hosted via
    <a href="https://docs.github.com/en/pages">GitHub Pages</a>.
    <span id="page-counter"></span>
  </footer>
  <script>document.getElementById('y').textContent = new Date().getFullYear();</script>
  <!-- Visitor counter (shared with index.html) -->
  <script>
    window.COUNTER_API_URL = 'https://page-counter-eight.vercel.app/api/counter-neon';
    window.COUNTER_PREFIX = 'Visitors: ';
  </script>
  <script src="https://page-counter-eight.vercel.app/counter.js"></script>
"""


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def git_date(path: Path) -> str:
    """Last commit date (YYYY-MM-DD) for a file, or today() if unavailable."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or today()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return today()


def parse_front_matter(text: str):
    """Split an optional `---`-delimited front matter block from the body.

    Returns (meta: dict, body: str). The mini-parser handles `key: value`
    lines only — enough for title/date/description/tags without pulling in a
    YAML dependency.
    """
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip("\n")
            body = text[end + 4:].lstrip("\n")
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, val = line.split(":", 1)
                meta[key.strip().lower()] = val.strip().strip('"\'')
            return meta, body
    return meta, text


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "post"


def first_heading(body: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return m.group(1).strip() if m else ""


# CJK characters + ideographic/full-width punctuation. A space between one of
# these and an inline $...$ formula renders as an ugly gap (CJK text has no
# inter-word spaces), so we strip it.
_CJK = r"㐀-䶿一-鿿豈-﫿　-〿＀-￯"


def tidy_quotes(text: str) -> str:
    """Pair straight ASCII quotes into curly quotes (“” / ‘’).

    smarty leaves a straight quote alone when it sits between CJK characters
    (no whitespace boundary to detect open vs close), so Chinese quotes stay
    straight. We pair them ourselves. Code spans, fenced code and math are
    masked first so their quotes are never touched.
    """
    masked = []

    def _mask(m):
        masked.append(m.group(0))
        return f"\x00{len(masked) - 1}\x00"

    prot = re.compile(r"```.*?```|``.*?``|`[^`\n]*`|\$\$.*?\$\$|\$[^$\n]*\$", re.DOTALL)
    text = prot.sub(_mask, text)
    text = re.sub(r'"([^"\n]*)"', "\u201c\\1\u201d", text)
    text = re.sub(r"'([^'\n]*)'", "\u2018\\1\u2019", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: masked[int(m.group(1))], text)
    return text


def tidy_cjk_math(text: str) -> str:
    """Strip spaces between CJK characters and adjacent inline math / brackets.

    A space between Chinese text and a `$...$` formula or a parenthesised label
    like `(b)` renders as an ugly gap (CJK has no inter-word spaces). We only
    target math delimiters and brackets `$ ( [ {` — spaces between CJK and a
    Latin word (e.g. `使用 Python`) are left alone, since those read fine.
    """
    text = re.sub(rf"([{_CJK}])[ \t]+(?=[(\[{{])", r"\1", text)   # 件 (b) -> 件(b)
    text = re.sub(rf"(?<=[)\]}}])[ \t]+([{_CJK}])", r"\1", text)  # (b) 时 -> (b)时
    return text


# Chinese 破折号 ("——") is two em dashes meant to read as one continuous long
# dash. Roboto (the body font) has U+2014, so the browser draws them as two
# short Latin em dashes with a gap. Forcing a CJK font on em dashes that touch
# CJK text makes them full-width and connect, matching the surrounding glyphs.
# Pangu spacing: exactly one ASCII space between a Han character and an
# inline formula, regardless of how the source was spaced. Runs on rendered
# HTML, where arithmatex wraps each formula in <span class="arithmatex">.
_HAN = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_INLINE_MATH = r'<span class="arithmatex">.*?</span>'


def space_han_math(html_text: str) -> str:
    html_text = re.sub(rf"([{_HAN}])[ \t]*({_INLINE_MATH})", r"\1 \2", html_text)
    html_text = re.sub(rf"({_INLINE_MATH})[ \t]*([{_HAN}])", r"\1 \2", html_text)
    return html_text


_CJK_DASH_FONT = ("'Noto Sans CJK SC', 'Source Han Sans SC', 'PingFang SC', "
                  "'Microsoft YaHei', 'Heiti SC', sans-serif")
_CJK_DASH_RE = re.compile(rf"(?:(?<=[{_CJK}])—+|—+(?=[{_CJK}]))")


def wrap_cjk_dash(html_text: str) -> str:
    return _CJK_DASH_RE.sub(
        lambda m: f'<span style="font-family:{_CJK_DASH_FONT}">{m.group()}</span>',
        html_text)


def make_excerpt(html_body: str, limit: int = 200) -> str:
    """Plain-text excerpt from rendered HTML, for the index + meta tags."""
    text = re.sub(r"<[^>]+>", "", html_body)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return (text[:limit].rstrip() + "…") if len(text) > limit else text


class Post:
    def __init__(self, path: Path):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        body = tidy_quotes(body)
        body = tidy_cjk_math(body)
        md = markdown.Markdown(extensions=MD_EXTENSIONS,
                               extension_configs=MD_EXTENSION_CONFIGS,
                               output_format="html5")
        self.path = path
        # The page template renders the title as its own <h1>, so drop a
        # leading <h1> from the body to avoid showing the title twice.
        self.html = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "",
                           md.convert(body), count=1, flags=re.DOTALL)
        self.html = space_han_math(self.html)
        self.html = wrap_cjk_dash(self.html)
        self.slug = slugify(meta.get("slug") or path.stem)
        self.title = meta.get("title") or first_heading(body) or path.stem
        self.date = meta.get("date") or git_date(path)
        self.updated = max(self.date, git_date(path))  # for dateModified
        self.description = meta.get("description") or make_excerpt(self.html)
        self.lang = meta.get("lang", "en")        # content language (SEO)
        self.keywords = meta.get("keywords", "")  # optional <meta keywords>
        self.url = f"/blogs/{self.slug}.html"


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
_OG_LOCALE = {"en": "en_US", "zh": "zh_CN", "zh-cn": "zh_CN", "zh-CN": "zh_CN",
              "ja": "ja_JP"}
_OG_IMAGE = f"{BASE_URL}/docs/background-pkalm.jpg"


def jsonld_script(obj: dict) -> str:
    """Serialize a Schema.org object to a safe <script type=ld+json> block."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f'  <script type="application/ld+json">{s.replace("</", "<\\/")}</script>\n'


def page(title: str, description: str, nav_breadcrumb: str, body: str,
         canonical: str, *, lang: str = "en", og_type: str = "website",
         keywords: str = "", published: str = "", jsonld: dict = None,
         extra_head: str = "") -> str:
    t, d = html.escape(title), html.escape(description)
    locale = _OG_LOCALE.get(lang, "en_US")
    head = [
        f'  <title>{t}</title>',
        f'  <meta name="description" content="{d}">',
        '  <meta name="author" content="Shijie Xu">',
        '  <meta name="robots" content="index, follow, max-image-preview:large">',
        f'  <link rel="canonical" href="{canonical}">',
        '  <link rel="alternate" type="application/atom+xml" '
        f'title="Shijie Xu — Blog" href="{BASE_URL}/blogs/feed.xml">',
        f'  <meta property="og:type" content="{og_type}">',
        '  <meta property="og:site_name" content="Shijie Xu">',
        f'  <meta property="og:locale" content="{locale}">',
        f'  <meta property="og:title" content="{t}">',
        f'  <meta property="og:description" content="{d}">',
        f'  <meta property="og:url" content="{canonical}">',
        f'  <meta property="og:image" content="{_OG_IMAGE}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{t}">',
        f'  <meta name="twitter:description" content="{d}">',
        f'  <meta name="twitter:image" content="{_OG_IMAGE}">',
    ]
    if keywords:
        head.insert(3, f'  <meta name="keywords" content="{html.escape(keywords)}">')
    if published:
        head.append(f'  <meta property="article:published_time" content="{published}">')
        head.append('  <meta property="article:author" content="Shijie Xu">')
    head_str = "\n".join(head) + "\n"
    if jsonld:
        head_str += jsonld_script(jsonld)
    return f"""\
<!doctype html>
<html lang="{lang}">
<head>
{head_str}{SHARED_HEAD}{extra_head}</head>
<body>
{NAV.format(breadcrumb=nav_breadcrumb)}  <div class="content">
{body}
  </div>
{FOOTER}</body>
</html>
"""


def render_index(posts) -> str:
    items = []
    for p in posts:
        items.append(f"""\
      <li>
        <time class="post-date" datetime="{p.date}">{p.date}</time>
        <a href="{p.url}">{html.escape(p.title)}</a>
      </li>""")
    listing = "\n".join(items) if items else (
        '<p style="color:var(--muted)">No posts yet.</p>')
    body = f"""\
    <header><h1 style="font-size:2.6rem; margin:0.5rem 0 1.5rem;">Blog</h1></header>
    <ul class="post-list">
{listing}
    </ul>"""
    breadcrumb = (
        '<span style="margin-right:0.75rem;">&gt;</span>'
        '<a href="/">Home</a>'
        '<span style="margin:0 0.75rem;">&gt;</span>'
        '<span style="font-weight:700;">Blog</span>'
    )
    blog_ld = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Shijie Xu — Blog",
        "url": f"{BASE_URL}/blogs/",
        "author": {"@type": "Person", "name": "Shijie Xu", "url": f"{BASE_URL}/"},
        "blogPost": [
            {"@type": "BlogPosting", "headline": p.title,
             "url": f"{BASE_URL}{p.url}", "datePublished": p.date,
             "inLanguage": p.lang}
            for p in posts
        ],
    }
    return page("Blog — Shijie Xu",
                "Posts by Shijie Xu on bioinformatics, computational chemistry, "
                "deep learning, and mathematics.",
                breadcrumb, body, f"{BASE_URL}/blogs/",
                og_type="website", jsonld=blog_ld)


def render_post(p: Post) -> str:
    body = f"""\
    <article>
      <h1>{html.escape(p.title)}</h1>
      <div class="article-meta"><time datetime="{p.date}">{p.date}</time></div>
{p.html}
    </article>
    <p style="margin-top:3rem;"><a href="/blogs/">← All posts</a></p>
{COMMENTS}"""
    breadcrumb = (
        '<span style="margin-right:0.75rem;">&gt;</span>'
        '<a href="/">Home</a>'
        '<span style="margin:0 0.75rem;">&gt;</span>'
        '<a href="/blogs/">Blog</a>'
        '<span style="margin:0 0.75rem;">&gt;</span>'
        f'<span style="font-weight:700;">{html.escape(p.title)}</span>'
    )
    post_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p.title,
        "description": p.description,
        "datePublished": p.date,
        "dateModified": p.updated,
        "inLanguage": p.lang,
        "author": {"@type": "Person", "name": "Shijie Xu", "url": f"{BASE_URL}/"},
        "publisher": {"@type": "Person", "name": "Shijie Xu", "url": f"{BASE_URL}/"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{BASE_URL}{p.url}"},
        "image": _OG_IMAGE,
        "url": f"{BASE_URL}{p.url}",
    }
    return page(f"{p.title} — Shijie Xu", p.description, breadcrumb, body,
                f"{BASE_URL}{p.url}", lang=p.lang, og_type="article",
                keywords=p.keywords, published=p.date, jsonld=post_ld,
                extra_head=MATHJAX)


def render_feed(posts) -> str:
    """Minimal Atom feed for the blog — aids discovery and SEO."""
    updated = (posts[0].updated if posts else today()) + "T00:00:00Z"
    entries = []
    for p in posts:
        entries.append(f"""  <entry>
    <title>{html.escape(p.title)}</title>
    <link href="{BASE_URL}{p.url}"/>
    <id>{BASE_URL}{p.url}</id>
    <published>{p.date}T00:00:00Z</published>
    <updated>{p.updated}T00:00:00Z</updated>
    <summary>{html.escape(p.description)}</summary>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Shijie Xu — Blog</title>
  <subtitle>Bioinformatics, computational chemistry, deep learning, and mathematics.</subtitle>
  <link href="{BASE_URL}/blogs/feed.xml" rel="self"/>
  <link href="{BASE_URL}/blogs/"/>
  <id>{BASE_URL}/blogs/</id>
  <updated>{updated}</updated>
  <author><name>Shijie Xu</name></author>
{chr(10).join(entries)}
</feed>
"""


# --------------------------------------------------------------------------- #
def main() -> None:
    BLOGS_DIR.mkdir(exist_ok=True)
    files = sorted(POSTS_DIR.glob("*.md")) if POSTS_DIR.exists() else []
    posts = [Post(f) for f in files]
    # newest first; ties broken by title for a stable order
    posts.sort(key=lambda p: (p.date, p.title), reverse=True)

    # Remove stale generated pages whose source post no longer exists.
    keep = {f"{p.slug}.html" for p in posts} | {"index.html"}
    for old in BLOGS_DIR.glob("*.html"):
        if old.name not in keep:
            old.unlink()

    for p in posts:
        (BLOGS_DIR / f"{p.slug}.html").write_text(render_post(p), encoding="utf-8")
    (BLOGS_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    (BLOGS_DIR / "feed.xml").write_text(render_feed(posts), encoding="utf-8")

    print(f"Built {len(posts)} post(s) into blogs/.")
    for p in posts:
        print(f"  {p.date}  {p.slug}.html  — {p.title}")


if __name__ == "__main__":
    main()
