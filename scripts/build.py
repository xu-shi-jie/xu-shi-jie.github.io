from pathlib import Path
import datetime, re

class MarkdownParser:
    def __init__(self):
        self.html = ""
    
    def parse_title(self, line):
        """Parse title (lines starting with # )."""
        return f"<h1>{line[2:].strip()}</h1>\n"

    def parse_heading(self, line):
        """Parse headings (lines starting with ## or ###)."""
        level = line.count("#", 0, 6)  # Count number of #
        return f"<h{level}>{line[level + 1:].strip()}</h{level}>\n"

    def parse_image(self, line):
        """Parse images: ![alt text](image_url)."""
        alt_start = line.find("[") + 1
        alt_end = line.find("]")
        url_start = line.find("(") + 1
        url_end = line.find(")")
        alt_text = line[alt_start:alt_end]
        url = line[url_start:url_end]
        return f'<img src="{url}" alt="{alt_text}" />\n'

    def parse_table(self, lines):
        """Parse tables."""
        html_table = "<table>\n"
        headers = lines[0].split("|")
        html_table += "<tr>" + "".join([f"<th>{header.strip()}</th>" for header in headers]) + "</tr>\n"
        for row in lines[2:]:  # Skip the separator line
            cells = row.split("|")
            html_table += "<tr>" + "".join([f"<td>{cell.strip()}</td>" for cell in cells]) + "</tr>\n"
        html_table += "</table>\n"
        return html_table

    def parse_figure_caption(self, line):
        """Parse figure captions: `![Caption](image_url)`."""
        alt_start = line.find("[") + 1
        alt_end = line.find("]")
        url_start = line.find("(") + 1
        url_end = line.find(")")
        caption = line[alt_start:alt_end]
        url = line[url_start:url_end]
        return f'<figure><img src="{url}" alt="{caption}" /><figcaption>{caption}</figcaption></figure>\n'

    def parse_preamble(self, lines):
        """Parse preamble block starting and ending with ---."""
        self.meta_data = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                self.meta_data[key.strip()] = value.strip()

    def parse_mathjax(self, content):
        content = re.sub(r'\$\$(.*?)\$\$', r'\[ \1 \]', content)
        content = re.sub(r'\$(.*?)\$', r'\( \1 \)', content)
        content = re.sub(r'\\', r'\\\\', content)
        return content
    
    def parse(self, markdown):
        """Parse markdown text."""
        markdown = self.parse_mathjax(markdown)

        lines = markdown.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            if line.startswith("# "):
                self.html += self.parse_title(line)
            elif line.startswith("#"):
                self.html += self.parse_heading(line)
            elif line.startswith("![") and line.find("(") > -1:
                if i + 1 < len(lines) and lines[i + 1].strip() == "---":
                    table_lines = []
                    while i < len(lines) and lines[i].strip():
                        table_lines.append(lines[i].strip())
                        i += 1
                    self.html += self.parse_table(table_lines)
                else:
                    self.html += self.parse_figure_caption(line)
            elif line.startswith("|") and "---" in lines[i + 1]:
                table_lines = []
                while i < len(lines) and lines[i].strip():
                    table_lines.append(lines[i].strip())
                    i += 1
                self.html += self.parse_table(table_lines)
            elif line.startswith("!"):
                self.html += self.parse_image(line)
            elif line.startswith("---"):
                preamble_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "---":
                    preamble_lines.append(lines[i])
                    i += 1
                self.parse_preamble(preamble_lines)
            else:
                self.html += f"<p>{line.strip()}</p>\n"
            
            i += 1

        return self.meta_data, self.html



if __name__ == '__main__':
    Path('blogs').mkdir(exist_ok=True, parents=True)
    links = []
    for md in Path('docs').rglob('*.md'):
        content = md.read_text()
        tmpl = Path('docs/tmpl.html').read_text()

        parser = MarkdownParser()
        meta, html = parser.parse(content)
        html = re.sub(r'{\s*content\s*}', html, tmpl)

        # update meta data
        if 'date' not in meta:
            meta['date'] = datetime.datetime.now().strftime("%Y/%m/%d")
        if 'author' not in meta:
            meta['author'] = 'Shijie Xu'
        for key, value in meta.items():
            html = re.sub(r'{\s*' + key + r'\s*}', value, html)

        Path(f'blogs/{md.stem}.html').write_text(html)
        links.append((meta['date'], f'<a href="/blogs/{md.stem}.html">{meta["title"]}</a>', meta['author']))

    # sort by date
    links.sort(key=lambda x: x[0], reverse=True)
    links = "<p>"+"<br>".join([f'[{date}] {link}' for date, link, author in links])+ "</p>"
    html = Path('docs/tmpl.html').read_text()
    html = re.sub(r'{\s*content\s*}', links, html)
    html = re.sub(r'{\s*title\s*}', 'Blogs', html)
    html = re.sub(r'{\s*author\s*}', '', html)
    html = re.sub(r'{\s*copyright\s*}', '', html)
    html = re.sub(r'{\s*date\s*}', datetime.datetime.now().strftime("%Y/%m/%d"), html)
    Path('blogs.html').write_text(html)
