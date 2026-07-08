#!/usr/bin/env python3
"""
Fetch citation data from OpenAlex for the DOIs in data/pubs.json and update
the JSON file in-place.

For each publication we store two fields:
  - is_referenced_by_count : total citations (OpenAlex `cited_by_count`)
  - citations_by_year      : {"<year>": <count>, ...} from `counts_by_year`,
                             used to draw the hover bar chart on the homepage.

OpenAlex is free and needs no API key; we join its "polite pool" by sending a
mailto. Compared with Crossref's is-referenced-by-count, OpenAlex has broader
coverage and, crucially, exposes the per-year breakdown.

Usage: python3 update_citations.py   (run in repository root, i.e. from data/'s
parent so that pubs.json resolves — kept identical to the previous script).
"""
import json
import urllib.request
import urllib.parse
import time
import sys
import os

PUBS_PATH = 'pubs.json'
MAILTO = 'shijie.xu@ees.hokudai.ac.jp'


def load_pubs(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_pubs(path, pubs):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pubs, f, ensure_ascii=False, indent=2)


def normalize_doi(entry):
    # researchmap schema: identifiers.doi is a list of DOI strings.
    dois = (entry.get('identifiers') or {}).get('doi') or []
    if dois:
        return dois[0].strip()
    return None


def fetch_openalex(doi, attempts=3):
    """Return (total_citations, {year: count}) for a DOI, or (None, None) on failure."""
    if not doi:
        return None, None
    # OpenAlex accepts the DOI URL directly in the path; slashes stay literal.
    url = ('https://api.openalex.org/works/https://doi.org/' + doi
           + '?mailto=' + urllib.parse.quote(MAILTO)
           + '&select=cited_by_count,counts_by_year')
    headers = {
        'Accept': 'application/json',
        'User-Agent': f'xu-shi-jie.github.io citation updater (mailto:{MAILTO})',
    }
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    raise Exception(f'HTTP {resp.status}')
                j = json.load(resp)
            total = j.get('cited_by_count')
            by_year = {}
            for row in j.get('counts_by_year') or []:
                year = row.get('year')
                count = row.get('cited_by_count')
                if year is not None and count:
                    by_year[str(year)] = count
            return total, by_year
        except Exception as e:
            print(f'[warn] attempt {attempt} failed for {doi}: {e}', file=sys.stderr)
            if attempt < attempts:
                time.sleep(attempt * 2)
    return None, None


def main():
    if not os.path.exists(PUBS_PATH):
        print('data/pubs.json not found (run from the repository root)', file=sys.stderr)
        sys.exit(1)

    pubs = load_pubs(PUBS_PATH)

    changed = False
    report = []
    for entry in pubs:
        doi = normalize_doi(entry)
        if not doi:
            report.append((None, 'no-doi'))
            continue
        total, by_year = fetch_openalex(doi)
        if total is None:
            report.append((doi, 'failed'))
            # leave existing values unchanged
            continue

        if entry.get('is_referenced_by_count') != total:
            entry['is_referenced_by_count'] = total
            changed = True
        if entry.get('citations_by_year') != by_year:
            entry['citations_by_year'] = by_year
            changed = True
        report.append((doi, f'{total} ({len(by_year)} yr)'))
        # be polite between requests
        time.sleep(1)

    if changed:
        save_pubs(PUBS_PATH, pubs)
        print('Updated', PUBS_PATH)
    else:
        print('No changes')

    print('\nReport:')
    for doi, status in report:
        print('-', doi, status)


if __name__ == '__main__':
    main()
