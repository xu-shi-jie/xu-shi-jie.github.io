#!/usr/bin/env python3
"""
Generate blog posts HTML pages from markdown files.
Scans posts/*.md and generates:
1. posts.html - list of all posts
2. Individual HTML pages for each post
"""

import re
from pathlib import Path
from datetime import datetime
import markdown
import yaml

# Directory paths
POSTS_DIR = Path(__file__).parent
OUTPUT_DIR = POSTS_DIR / 'html'
MD_EXTENSIONS = ['extra', 'codehilite', 'toc', 'tables']

def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content."""
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)'
    match = re.match(pattern, content, re.DOTALL)

    if match:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    return {}, content

def read_post(filepath):
    """Read and parse a markdown post file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = parse_frontmatter(content)
    html_content = markdown.markdown(body, extensions=MD_EXTENSIONS)

    return {
        'filepath': filepath,
        'filename': filepath.stem,
        'title': frontmatter.get('title', 'Untitled'),
        'author': frontmatter.get('author', 'Unknown'),
        'date': frontmatter.get('date', datetime.now().strftime('%Y-%m-%d')),
        'tags': frontmatter.get('tags', []),
        'html_content': html_content,
        'frontmatter': frontmatter
    }

def get_html_template(title, content, is_post=False):
    """Generate HTML template with consistent styling."""
    if is_post:
        # Individual post page: Home is link, Posts is bold link
        breadcrumb = '<span style="margin-right: 0.75rem;">&gt;</span><a href="/">Home</a><span style="margin: 0 0.75rem;">&gt;</span><a href="/posts/html/posts.html" style="font-weight: 700;">Posts</a>'
    else:
        # Posts list page: Home is link, Posts is bold text (current page)
        breadcrumb = '<span style="margin-right: 0.75rem;">&gt;</span><a href="/">Home</a><span style="margin: 0 0.75rem;">&gt;</span><span style="font-weight: 700;">Posts</span>'

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Asul:wght@400;700&display=swap" rel="stylesheet">

  <title>{title} - Shijie Xu</title>
  <link rel="icon" type="image/x-icon" href="/favicon.ico">

  <style>
    :root {{
      --text-color: #222;
      --bg-color: #fff;
      --link-color: #0645ad;
      --code-bg: #f5f5f5;
    }}

    [data-theme="dark"] {{
      --text-color: #eee;
      --bg-color: #1a1a1a;
      --link-color: #6ea8fe;
      --code-bg: #2d2d2d;
    }}

    html, body {{
      overflow-x: hidden;
    }}

    body {{
      font-family: 'Asul', -apple-system, BlinkMacSystemFont, segoe ui, Roboto, Oxygen, Ubuntu, Cantarell, open sans, helvetica neue, sans-serif;
      font-size: 18px;
      max-width: 800px;
      margin: 0 auto;
      line-height: 1.6;
      color: var(--text-color);
      background: var(--bg-color);
      transition: color 0.3s, background-color 0.3s;
    }}

    @media (max-width: 600px) {{
      body {{
        max-width: 100vw;
        margin: 0;
      }}
    }}

    .hero {{
      position: relative;
      width: 100%;
      height: 200px;
      background-image: url('/docs/background-pkalm.jpg');
      background-size: cover;
      background-position: center;
    }}

    .content {{
      padding: 0 1rem;
    }}

    .breadcrumb-nav {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 0.5rem;
      margin-bottom: 1rem;
      padding: 0.4rem 0;
      font-size: 0.95rem;
      background: none;
      border-bottom: 0.5px solid #000;
    }}

    [data-theme="dark"] .breadcrumb-nav {{
      border-bottom: 0.5px solid #fff;
    }}

    h1 {{
      font-size: 3rem;
      margin: 0 0 0.5rem 0;
    }}

    h2 {{
      font-size: 2rem;
      margin-top: 2rem;
      margin-bottom: 0.5rem;
    }}

    h3 {{
      font-size: 1.5rem;
      margin-top: 1.5rem;
    }}

    a {{
      color: var(--text-color);
      text-decoration: none;
      border-bottom: 1px solid var(--text-color);
      opacity: 0.8;
      transition: opacity 0.2s ease;
    }}

    a:hover {{
      opacity: 1;
    }}

    .theme-toggle {{
      background: none;
      border: none;
      padding: 0;
      cursor: pointer;
      color: var(--text-color);
      width: 2rem;
      height: 2rem;
      transition: transform 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .theme-toggle img {{
      width: 24px;
      height: 24px;
      transition: filter 0.3s ease;
    }}

    .theme-toggle .moon {{
      display: block;
    }}

    .theme-toggle .sun {{
      display: none;
    }}

    [data-theme="dark"] .theme-toggle .moon {{
      display: none;
    }}

    [data-theme="dark"] .theme-toggle .sun {{
      display: block;
      filter: invert(1) brightness(1.1);
    }}

    .theme-toggle:hover {{
      transform: scale(1.1);
    }}

    .post-meta {{
      color: var(--text-color);
      opacity: 0.7;
      font-size: 0.9rem;
      margin-bottom: 2rem;
    }}

    .post-list {{
      list-style: none;
      padding: 0;
    }}

    .post-list li {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.75rem;
    }}

    .post-date {{
      opacity: 0.7;
      font-size: 0.9rem;
      white-space: nowrap;
      margin-left: auto;
      padding-left: 1rem;
    }}

    code {{
      background: var(--code-bg);
      padding: 0.2rem 0.4rem;
      border-radius: 3px;
      font-size: 0.9em;
    }}

    pre {{
      background: var(--code-bg);
      padding: 1rem;
      border-radius: 5px;
      overflow-x: auto;
    }}

    pre code {{
      background: none;
      padding: 0;
    }}

    blockquote {{
      border-left: 3px solid var(--text-color);
      margin-left: 0;
      padding-left: 1rem;
      opacity: 0.8;
    }}

    img {{
      max-width: 100%;
      height: auto;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }}

    th, td {{
      border: 1px solid rgba(128, 128, 128, 0.3);
      padding: 0.5rem;
      text-align: left;
    }}

    th {{
      background: var(--code-bg);
    }}

    footer {{
      margin-top: 3rem;
      margin-bottom: 2rem;
    }}

    footer p {{
      text-align: center;
      font-size: small;
    }}
  </style>

  <script>
    function toggleTheme() {{
      const body = document.documentElement;
      const currentTheme = body.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      body.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      const savedTheme = localStorage.getItem('theme') || 'light';
      document.documentElement.setAttribute('data-theme', savedTheme);
    }});
  </script>
</head>
<body>
  <div class="hero" role="banner"></div>
  <div class="content">
    <nav class="breadcrumb-nav">
      <div>
        {breadcrumb}
      </div>
      <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">
        <img src="/docs/moon.svg" alt="Dark mode" class="moon">
        <img src="/docs/sun.svg" alt="Light mode" class="sun">
      </button>
    </nav>

    {content}

    <footer>
      <p>&copy; 2022-2025 Shijie Xu. Hosted via <a href="https://docs.github.com/en/pages">GitHub Pages</a>.</p>
    </footer>
  </div>
</body>
</html>'''

def generate_post_page(post):
    """Generate individual HTML page for a post."""
    content = f'''
  <article>
    <h1>{post['title']}</h1>
    <div class="post-meta">
      <span>By {post['author']}</span> • <span>{post['date']}</span>
    </div>
    <div class="post-content">
      {post['html_content']}
    </div>
  </article>
'''

    html = get_html_template(post['title'], content, is_post=True)
    output_file = OUTPUT_DIR / f"{post['filename']}.html"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated: {output_file}")

def generate_posts_list(posts):
    """Generate the main posts list page."""
    # Sort posts by date (newest first)
    posts_sorted = sorted(posts, key=lambda x: x['date'], reverse=True)

    posts_html = '<ul class="post-list">'
    for post in posts_sorted:
        posts_html += f'''
    <li>
      <a href="{post['filename']}.html">{post['title']}</a>
      <span class="post-date">{post['date']}</span>
    </li>'''

    posts_html += '\n  </ul>'

    content = f'''
  <h2>Posts</h2>
  {posts_html}
'''

    html = get_html_template('Posts', content, is_post=False)
    output_file = OUTPUT_DIR / 'posts.html'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated: {output_file}")

def main():
    """Main function to generate all pages."""
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Scanning for markdown files...")

    # Find all .md files in posts directory
    md_files = list(POSTS_DIR.glob('*.md'))

    if not md_files:
        print("No markdown files found in posts/")
        return

    print(f"Found {len(md_files)} markdown file(s)")

    # Parse all posts
    posts = []
    for md_file in md_files:
        print(f"Processing: {md_file.name}")
        post = read_post(md_file)
        posts.append(post)
        generate_post_page(post)

    # Generate posts list page
    generate_posts_list(posts)

    print(f"\nDone! Generated {len(posts)} post page(s) + 1 list page")

if __name__ == '__main__':
    main()
