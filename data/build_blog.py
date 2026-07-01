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
from urllib.parse import quote

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
      background-image: url('/docs/background-pkalm.webp');
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
      /* Fill the row (minus the toggle) and clip a long post title with an
         ellipsis instead of letting it collide with the theme button. */
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .breadcrumb-nav button { padding-right: max(1rem, calc((100vw - 800px) / 2 + 1rem)); flex: 0 0 auto; }
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
    article video { max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 6px; }
    article figure { margin: 1.5rem 0; }
    article figure img { display: block; margin: 0 auto; }
    article figcaption {
      font-size: 0.8rem; line-height: 1.5; color: var(--muted);
      margin-top: 0.6rem;
    }
    /* Footnotes / references — small, muted, Wikipedia-style endnotes. */
    article .footnote { font-size: 0.8rem; color: var(--muted); margin-top: 1rem; }
    article .footnote hr { display: none; }
    article .footnote ol { padding-left: 1.2rem; }
    article .footnote li { margin: 0.35rem 0; }
    article .footnote li::marker { color: var(--muted); }
    sup.footnote-ref a, .footnote-backref { border-bottom: none; }
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
    /* Collapsible byline: closed shows the summary line, open reveals the
       revision log. Multiple history entries are supported. */
    details.article-meta > summary {
      cursor: pointer; list-style: none; display: inline;
    }
    details.article-meta > summary::-webkit-details-marker { display: none; }
    details.article-meta > summary::after {
      content: "▾"; margin-left: 0.35rem; font-size: 0.75rem;
      display: inline-block; transition: transform 0.15s;
    }
    details.article-meta[open] > summary::after { transform: rotate(180deg); }
    .article-meta .rev-log {
      list-style: none; margin: 0.75rem 0 0; padding: 0.75rem 0 0 0;
      border-top: 1px solid rgba(128,128,128,0.2);
    }
    .article-meta .rev-log li { margin: 0 0 0.4rem; line-height: 1.5; }
    .article-meta .rev-log time { font-weight: 700; color: var(--text-color); opacity: 0.85; }
    /* Previous / next post navigation (older reads left, newer right). */
    .post-nav {
      display: flex; justify-content: space-between; gap: 1.5rem;
      margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
    }
    .post-nav-cell {
      display: flex; flex-direction: column; gap: 0.15rem;
      max-width: 48%; border-bottom: none;
    }
    .post-nav-right { margin-left: auto; text-align: right; align-items: flex-end; }
    .post-nav-label { font-size: 0.8rem; color: var(--muted); }
    .post-nav-title { font-size: 1.02rem; }
    @media (max-width: 480px) { .post-nav-title { font-size: 0.92rem; } }
    /* Floating action buttons (share + go-to-top), bottom-right. */
    .float-btn {
      position: fixed; right: 1.5rem; width: 2.75rem; height: 2.75rem;
      border-radius: 50%; border: 1px solid var(--border);
      background: var(--nav-bg); color: var(--text-color); cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.25rem; line-height: 1; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
      transition: opacity 0.25s ease, transform 0.15s ease; opacity: 0.85; z-index: 50;
    }
    .float-btn:hover { opacity: 1; transform: translateY(-2px); }
    #share-btn { bottom: 1.5rem; }
    #top-btn { bottom: 5rem; opacity: 0; pointer-events: none; }
    #top-btn.show { opacity: 0.85; pointer-events: auto; }
    #top-btn.show:hover { opacity: 1; }
    /* Share menu: a grid of platform icons that pops up to the left of the
       share button. */
    .share-menu {
      position: fixed; right: 5rem; bottom: 1.5rem; z-index: 50;
      display: grid; grid-template-columns: repeat(2, 2.6rem); gap: 0.5rem;
      padding: 0.6rem; border-radius: 14px;
      background: var(--nav-bg); border: 1px solid var(--border);
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
    }
    .share-menu[hidden] { display: none; }
    .share-opt {
      width: 2.6rem; height: 2.6rem; border-radius: 50%;
      border: 1px solid var(--border); background: var(--bg-color);
      color: var(--text-color); cursor: pointer; font-size: 1.05rem;
      display: flex; align-items: center; justify-content: center;
      text-decoration: none; opacity: 0.92;
      transition: transform 0.15s ease, opacity 0.2s ease;
    }
    .share-opt:hover { opacity: 1; transform: translateY(-2px); }
    #share-toast {
      position: fixed; right: 1.5rem; bottom: 8rem; z-index: 51;
      background: var(--text-color); color: var(--bg-color);
      padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.8rem;
      white-space: nowrap; opacity: 0; pointer-events: none;
      transition: opacity 0.25s ease;
    }
    #share-toast.show { opacity: 0.95; }
    /* WeChat QR modal. */
    .qr-modal {
      position: fixed; inset: 0; z-index: 60;
      display: flex; align-items: center; justify-content: center;
      background: rgba(0, 0, 0, 0.5);
    }
    .qr-modal[hidden] { display: none; }
    .qr-card {
      background: var(--bg-color); color: var(--text-color);
      padding: 1.25rem; border-radius: 14px; text-align: center;
      border: 1px solid var(--border); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }
    .qr-card img {
      display: block; width: 200px; height: 200px;
      background: #fff; padding: 8px; border-radius: 8px;
    }
    .qr-card p { margin: 0.75rem 0; font-size: 0.85rem; color: var(--muted); }
    .qr-close {
      border: 1px solid var(--border); background: var(--nav-bg);
      color: var(--text-color); border-radius: 6px; padding: 0.3rem 1rem;
      cursor: pointer; font-size: 0.85rem;
    }
    @media (max-width: 600px) {
      .float-btn { right: 1rem; }
      #share-btn { bottom: 1rem; }
      #top-btn { bottom: 4.5rem; }
      .share-menu { right: 4.5rem; bottom: 1rem; }
      #share-toast { right: 1rem; bottom: 7.5rem; }
    }
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
    // Apply the saved theme synchronously, before the browser paints. This
    // script sits in <head>, so setting data-theme here (rather than on
    // DOMContentLoaded, which fires after the first paint) avoids the
    // flash of light theme when navigating between pages in dark mode.
    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
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

# Font Awesome 6 (free, solid set) for the floating-button icons. Loaded only
# on post pages, alongside FLOAT_UI.
FONTAWESOME = (
    '  <link rel="stylesheet" '
    'href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" '
    'crossorigin="anonymous" referrerpolicy="no-referrer">\n'
)

# Floating share + go-to-top buttons (post pages only). The share button opens
# a small menu of social platforms (links built per-post from the canonical URL
# + title); WeChat shows a scannable QR of the page; Copy falls back to the
# clipboard. The go-to-top button fades in once the reader scrolls past the
# fold. Platforms follow lilianweng.github.io's set (X, LinkedIn, Reddit,
# Facebook, WhatsApp, Telegram) plus Line, WeChat, Email and Copy.

# Social platforms: (label, Font Awesome icon class, intent-URL template with
# {u}=encoded URL and {t}=encoded title). WeChat/Copy are handled in JS, not
# here, because they don't have a simple share URL.
SHARE_PLATFORMS = [
    ("X", "fa-brands fa-x-twitter", "https://twitter.com/intent/tweet?url={u}&text={t}"),
    ("LinkedIn", "fa-brands fa-linkedin-in", "https://www.linkedin.com/sharing/share-offsite/?url={u}"),
    ("Reddit", "fa-brands fa-reddit-alien", "https://www.reddit.com/submit?url={u}&title={t}"),
    ("Facebook", "fa-brands fa-facebook-f", "https://www.facebook.com/sharer/sharer.php?u={u}"),
    ("WhatsApp", "fa-brands fa-whatsapp", "https://api.whatsapp.com/send?text={t}%20{u}"),
    ("Telegram", "fa-brands fa-telegram", "https://t.me/share/url?url={u}&text={t}"),
    ("Line", "fa-brands fa-line", "https://social-plugins.line.me/lineit/share?url={u}"),
    ("Email", "fa-solid fa-envelope", "mailto:?subject={t}&body={u}"),
]

# Plain string (not an f-string) so the JS braces need no escaping.
FLOAT_JS = """\
    <script>
      function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
      function closeShareMenu() { document.getElementById('share-menu').hidden = true; }
      function toggleShareMenu() {
        var m = document.getElementById('share-menu');
        m.hidden = !m.hidden;
      }
      function showShareToast(msg) {
        var t = document.getElementById('share-toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(function () { t.classList.remove('show'); }, 1800);
      }
      function copyLink() {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(location.href)
            .then(function () { showShareToast('Link copied'); })
            .catch(function () { showShareToast(location.href); });
        } else {
          showShareToast(location.href);
        }
        closeShareMenu();
      }
      function showWeChatQR() {
        var img = document.getElementById('wechat-qr-img');
        if (!img.getAttribute('src')) {
          img.src = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=10&data='
            + encodeURIComponent(location.href);
        }
        document.getElementById('wechat-qr').hidden = false;
        closeShareMenu();
      }
      function hideWeChatQR() { document.getElementById('wechat-qr').hidden = true; }
      (function () {
        var top = document.getElementById('top-btn');
        function onScroll() { top.classList.toggle('show', window.scrollY > 400); }
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
        // Close the share menu on outside click or Escape.
        document.addEventListener('click', function (e) {
          var wrap = document.getElementById('share-wrap');
          var menu = document.getElementById('share-menu');
          if (menu && !menu.hidden && wrap && !wrap.contains(e.target)) menu.hidden = true;
        });
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') { closeShareMenu(); hideWeChatQR(); }
        });
        // Clicking any share option (open a network, email) also dismisses the menu.
        document.getElementById('share-menu').addEventListener('click', function (e) {
          if (e.target.closest('a')) this.hidden = true;
        });
      })();
    </script>
"""


def render_float_ui(share_url: str, title: str) -> str:
    """Floating share menu + go-to-top button for a post page."""
    u = quote(share_url, safe="")
    t = quote(title, safe="")
    links = "\n".join(
        f'        <a class="share-opt" href="{tmpl.format(u=u, t=t)}" target="_blank" '
        f'rel="noopener noreferrer" title="Share on {label}" aria-label="Share on {label}">'
        f'<i class="{icon}" aria-hidden="true"></i></a>'
        for label, icon, tmpl in SHARE_PLATFORMS
    )
    return f"""\
    <div id="share-wrap">
      <div id="share-menu" class="share-menu" hidden>
{links}
        <button class="share-opt" onclick="showWeChatQR()" title="Share on WeChat" aria-label="Share on WeChat"><i class="fa-brands fa-weixin" aria-hidden="true"></i></button>
        <button class="share-opt" onclick="copyLink()" title="Copy link" aria-label="Copy link"><i class="fa-solid fa-link" aria-hidden="true"></i></button>
      </div>
      <button id="share-btn" class="float-btn" onclick="toggleShareMenu()" title="Share" aria-label="Share this post" aria-haspopup="true">
        <i class="fa-solid fa-share-nodes" aria-hidden="true"></i>
      </button>
    </div>
    <button id="top-btn" class="float-btn" onclick="scrollToTop()" title="Go to top" aria-label="Go to top">
      <i class="fa-solid fa-arrow-up" aria-hidden="true"></i>
    </button>
    <span id="share-toast" role="status" aria-live="polite"></span>
    <div id="wechat-qr" class="qr-modal" hidden onclick="hideWeChatQR()">
      <div class="qr-card" onclick="event.stopPropagation()">
        <img id="wechat-qr-img" alt="WeChat QR code" width="200" height="200">
        <p>Scan with WeChat to open / share</p>
        <button class="qr-close" onclick="hideWeChatQR()">Close</button>
      </div>
    </div>
{FLOAT_JS}"""

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
    YAML dependency. The `update:` key is special: it may repeat, and each
    occurrence is collected (in order) into the list `meta["updates"]`. Each
    value is `YYYY-MM-DD | changelog text` (the `| text` part is optional).
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
                key = key.strip().lower()
                val = val.strip().strip('"\'')
                if key == "update":
                    meta.setdefault("updates", []).append(val)
                else:
                    meta[key] = val
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

    prot = re.compile(r"```.*?```|``.*?``|`[^`\n]*`|\$\$.*?\$\$|\$[^$\n]*\$|<[^>]+>", re.DOTALL)
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


def add_image_dimensions(html_body: str) -> str:
    """Add intrinsic width/height to local <img> tags that lack them.

    Browsers use the attributes to reserve space before the image loads,
    preventing layout shift (CLS). Reads sizes with Pillow; if Pillow is
    missing or the file can't be read, the tag is left unchanged.
    """
    try:
        from PIL import Image
    except ImportError:
        return html_body

    def repl(m):
        tag = m.group(0)
        if "width=" in tag or "height=" in tag:
            return tag
        src_m = re.search(r'src="([^"]+)"', tag)
        if not src_m:
            return tag
        src = src_m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            return tag
        try:
            with Image.open(ROOT / src.lstrip("/")) as im:
                w, h = im.size
        except Exception:
            return tag
        return tag[:-1] + f' width="{w}" height="{h}">'

    return re.sub(r"<img\b[^>]*>", repl, html_body)


def make_excerpt(html_body: str, limit: int = 200) -> str:
    """Plain-text excerpt from rendered HTML, for the index + meta tags."""
    text = re.sub(r"<[^>]+>", "", html_body)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return (text[:limit].rstrip() + "…") if len(text) > limit else text


def pretty_date(d: str) -> str:
    """'2026-06-16' -> 'June 16, 2026'; falls back to the raw string."""
    try:
        dt = datetime.datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return d
    return f'{dt.strftime("%B")} {dt.day}, {dt.year}'


def parse_revisions(raw, write_date: str):
    """Turn raw `update:` values into a newest-first list of (date, log) pairs.

    Each raw entry is `YYYY-MM-DD | changelog text` (the log is optional).
    Entries without a valid date, or dated on/before the write date, are
    dropped so the history reflects genuine post-publication edits.
    """
    revisions = []
    for entry in (raw or []):
        date_part, _, log = entry.partition("|")
        date_part = date_part.strip()
        try:
            datetime.datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue
        if date_part <= write_date:
            continue
        revisions.append((date_part, log.strip()))
    revisions.sort(key=lambda r: r[0], reverse=True)
    return revisions


def reading_minutes(html_body: str) -> int:
    """Rough reading time: Latin words + CJK characters at ~200 units/min."""
    text = html.unescape(re.sub(r"<[^>]+>", "", html_body))
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    cjk = len(re.findall(rf"[{_CJK}]", text))
    return max(1, round((words + cjk) / 200))


def crumb_title(title: str, limit: int = 48) -> str:
    """Shorten a long title for the breadcrumb, breaking on a word boundary.

    The full title still appears in the page <h1> and <title>; only the
    breadcrumb is clipped so it never crowds the theme toggle.
    """
    t = title.strip()
    if len(t) <= limit:
        return html.escape(t)
    cut = t[:limit].rstrip()
    sp = cut.rfind(" ")
    if sp > limit // 2:
        cut = cut[:sp].rstrip()
    return html.escape(cut) + "…"


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
        self.html = add_image_dimensions(self.html)
        self.slug = slugify(meta.get("slug") or path.stem)
        self.title = meta.get("title") or first_heading(body) or path.stem
        self.date = meta.get("date") or git_date(path)
        # Revision history: repeated `update:` lines, each `DATE | log`. Parsed
        # into (date, log) pairs, sorted newest-first, and only kept when dated
        # after the write date (editorial intent, not git noise).
        self.revisions = parse_revisions(meta.get("updates"), self.date)
        # `updated` (SEO dateModified): newest declared revision, else the file's
        # last git-commit date; never earlier than the write date.
        newest_rev = self.revisions[0][0] if self.revisions else ""
        self.updated = max(self.date, newest_rev or git_date(path))
        self.description = meta.get("description") or make_excerpt(self.html)
        self.lang = meta.get("lang", "en")        # content language (SEO)
        self.keywords = meta.get("keywords", "")  # optional <meta keywords>
        self.url = f"/blogs/{self.slug}.html"
        # Optional per-post social-share cover (frontmatter `image:`,
        # site-root-relative e.g. /docs/foo.jpg). Use a raster (JPEG/PNG) for
        # broad scraper support (WeChat/Line dislike WebP). Falls back to the
        # site default background. `image_alt:` overrides the alt text.
        img = meta.get("image")
        if img:
            self.image = (img if img.startswith(("http://", "https://"))
                          else f"{BASE_URL}/{img.lstrip('/')}")
            self.image_alt = meta.get("image_alt") or self.title
            self.image_w, self.image_h = og_image_dims(img)
        else:
            self.image = _OG_IMAGE
            self.image_alt = _OG_IMAGE_ALT
            self.image_w, self.image_h = _OG_IMAGE_W, _OG_IMAGE_H


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
_OG_LOCALE = {"en": "en_US", "zh": "zh_CN", "zh-cn": "zh_CN", "zh-CN": "zh_CN",
              "ja": "ja_JP"}
_OG_IMAGE = f"{BASE_URL}/docs/background-pkalm.jpg"
_OG_IMAGE_W, _OG_IMAGE_H = "1188", "904"
_OG_IMAGE_ALT = "Shijie Xu — research background"


def og_image_dims(site_path: str):
    """(width, height) strings for a local site-root image, ('','') if unknown."""
    try:
        from PIL import Image
        with Image.open(ROOT / site_path.lstrip("/")) as im:
            return str(im.size[0]), str(im.size[1])
    except Exception:
        return "", ""


def jsonld_script(obj: dict) -> str:
    """Serialize a Schema.org object to a safe <script type=ld+json> block."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f'  <script type="application/ld+json">{s.replace("</", "<\\/")}</script>\n'


def page(title: str, description: str, nav_breadcrumb: str, body: str,
         canonical: str, *, lang: str = "en", og_type: str = "website",
         keywords: str = "", published: str = "", jsonld: dict = None,
         extra_head: str = "", image: str = _OG_IMAGE,
         image_w: str = _OG_IMAGE_W, image_h: str = _OG_IMAGE_H,
         image_alt: str = _OG_IMAGE_ALT) -> str:
    t, d = html.escape(title), html.escape(description)
    img, img_alt = html.escape(image), html.escape(image_alt)
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
        f'  <meta property="og:image" content="{img}">',
        *([f'  <meta property="og:image:width" content="{image_w}">',
           f'  <meta property="og:image:height" content="{image_h}">'] if image_w and image_h else []),
        f'  <meta property="og:image:alt" content="{img_alt}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{t}">',
        f'  <meta name="twitter:description" content="{d}">',
        f'  <meta name="twitter:image" content="{img}">',
        f'  <meta name="twitter:image:alt" content="{img_alt}">',
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


def post_nav(older, newer) -> str:
    """Bottom-of-post links to the chronologically adjacent posts.

    Posts are ordered newest-first, so `older` reads left (back in time) and
    `newer` reads right. Either side may be absent (first/last post); the
    empty cell still anchors the present one to its edge via space-between.
    """
    if not older and not newer:
        return ""

    def cell(post, side, label):
        if not post:
            return '<span class="post-nav-cell"></span>'
        arrow = "←" if side == "left" else "→"
        lbl = f"{arrow} {label}" if side == "left" else f"{label} {arrow}"
        return (f'<a class="post-nav-cell post-nav-{side}" href="{post.url}">'
                f'<span class="post-nav-label">{lbl}</span>'
                f'<span class="post-nav-title">{html.escape(post.title)}</span></a>')

    return (f'    <nav class="post-nav" aria-label="Adjacent posts">'
            f'{cell(older, "left", "Older post")}'
            f'{cell(newer, "right", "Newer post")}'
            f'</nav>\n')


def render_article_meta(p: Post, meta_line: str) -> str:
    """The byline block. Plain when the post has no revisions; a collapsible
    `<details>` (summary = byline, body = revision log) when it does."""
    if not p.revisions:
        return f'      <div class="article-meta">{meta_line}</div>'
    items = "\n".join(
        f'          <li><time datetime="{d}">{pretty_date(d)}</time>'
        f'{(" — " + html.escape(log)) if log else ""}</li>'
        for d, log in p.revisions
    )
    return f"""\
      <details class="article-meta revisions">
        <summary title="Revision history">{meta_line}</summary>
        <ul class="rev-log">
{items}
        </ul>
      </details>"""


def render_post(p: Post, older: "Post" = None, newer: "Post" = None) -> str:
    meta_line = (
        f'Date: <time datetime="{p.date}">{pretty_date(p.date)}</time>'
        f' | Estimated Reading Time: {reading_minutes(p.html)} min'
        ' | Author: Shijie Xu'
    )
    meta_html = render_article_meta(p, meta_line)
    body = f"""\
    <article>
      <h1>{html.escape(p.title)}</h1>
{meta_html}
{p.html}
    </article>
{post_nav(older, newer)}    <p style="margin-top:2rem;"><a href="/blogs/">← All posts</a></p>
{COMMENTS}{render_float_ui(f"{BASE_URL}{p.url}", p.title)}"""
    breadcrumb = (
        '<span style="margin-right:0.75rem;">&gt;</span>'
        '<a href="/">Home</a>'
        '<span style="margin:0 0.75rem;">&gt;</span>'
        '<a href="/blogs/">Blog</a>'
        '<span style="margin:0 0.75rem;">&gt;</span>'
        f'<span style="font-weight:700;" title="{html.escape(p.title)}">{crumb_title(p.title)}</span>'
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
        "image": p.image,
        "url": f"{BASE_URL}{p.url}",
    }
    return page(f"{p.title} — Shijie Xu", p.description, breadcrumb, body,
                f"{BASE_URL}{p.url}", lang=p.lang, og_type="article",
                keywords=p.keywords, published=p.date, jsonld=post_ld,
                extra_head=MATHJAX + FONTAWESOME,
                image=p.image, image_w=p.image_w, image_h=p.image_h,
                image_alt=p.image_alt)


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

    # posts is newest-first: index i-1 is newer, i+1 is older.
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        (BLOGS_DIR / f"{p.slug}.html").write_text(
            render_post(p, older=older, newer=newer), encoding="utf-8")
    (BLOGS_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    (BLOGS_DIR / "feed.xml").write_text(render_feed(posts), encoding="utf-8")

    print(f"Built {len(posts)} post(s) into blogs/.")
    for p in posts:
        print(f"  {p.date}  {p.slug}.html  — {p.title}")


if __name__ == "__main__":
    main()
