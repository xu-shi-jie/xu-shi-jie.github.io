#!/usr/bin/env python3
"""
Fetch is-referenced-by-count from Crossref for DOIs in data/pubs.json
and update the JSON file in-place. Creates a backup at data/pubs.json.bak.

Usage: python3 update_citations.py
Run in repository root.
"""
import json
import urllib.request
import urllib.parse
import time
import sys
import os
from datetime import datetime

PUBS_PATH = 'pubs.json'
BACKUP_PATH = PUBS_PATH + '.bak'

def load_pubs(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_pubs(path, pubs):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pubs, f, ensure_ascii=False, indent=2)

def normalize_doi(entry):
    doi = entry.get('doi')
    if doi:
        return doi.strip()
    links = entry.get('links') or {}
    doi_url = links.get('doi')
    if doi_url:
        try:
            p = urllib.parse.urlparse(doi_url)
            return p.path.lstrip('/')
        except Exception:
            parts = doi_url.rstrip('/').split('/')
            return parts[-1]
    return None

def fetch_crossref_count(doi, attempts=3):
    if not doi:
        return None
    api = 'https://api.crossref.org/works/' + urllib.parse.quote(doi)
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'xu-shi-jie.github.io (mailto:shijie.xu@ees.hokudai.ac.jp)'
    }
    for attempt in range(1, attempts+1):
        try:
            req = urllib.request.Request(api, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    raise Exception(f'HTTP {resp.status}')
                j = json.load(resp)
                return j.get('message', {}).get('is-referenced-by-count')
        except Exception as e:
            print(f'[warn] attempt {attempt} failed for {doi}: {e}', file=sys.stderr)
            if attempt < attempts:
                time.sleep(attempt * 2)
    return None

def main():
    if not os.path.exists(PUBS_PATH):
        print('data/pubs.json not found', file=sys.stderr)
        sys.exit(1)

    pubs = load_pubs(PUBS_PATH)

    # backup
    try:
        save_pubs(BACKUP_PATH, pubs)
        print(f'Backup written to {BACKUP_PATH}')
    except Exception as e:
        print('Failed to write backup:', e, file=sys.stderr)

    changed = False
    report = []
    for entry in pubs:
        doi = normalize_doi(entry)
        if not doi:
            report.append((None, 'no-doi'))
            continue
        count = fetch_crossref_count(doi)
        if count is None:
            report.append((doi, 'failed'))
            # leave existing value unchanged if any
            continue
        # update only if different
        old = entry.get('is_referenced_by_count')
        if old != count:
            entry['is_referenced_by_count'] = count
            changed = True
            report.append((doi, count))
        else:
            report.append((doi, count))
        # small pause between requests
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
