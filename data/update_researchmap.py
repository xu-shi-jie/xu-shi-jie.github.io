#!/usr/bin/env python3
"""
Sync achievements to researchmap.jp by simulating the normal browser login
(no API application needed).

researchmap runs on NetCommons3 / CakePHP. We:
  1. log in through the real /auth/login form (CSRF + SecurityComponent tokens),
  2. read existing achievements from the public read API (no auth) to avoid
     adding duplicates,
  3. add missing achievements by submitting the same edit form a browser does.

data/presentations.json and data/pubs.json use researchmap's own field names
(presentation_title{en,ja}, presenters{en:[{name}]}, event{en,ja},
from/to_event_date, presentation_type, address_country, ...), so each entry
maps almost 1:1 onto the add form.

Handled achievement types (dedup avoids duplicates):
  * presentations    -> data/presentations.json,  dedup by title + event
  * published_papers -> data/pubs.json,            dedup by DOI

Credentials come from data/../.env (git-ignored) or environment variables:
    RESEARCHMAP_ID         researchmap login id           (e.g. xushijie)
    RESEARCHMAP_PASSWORD   researchmap password
    RESEARCHMAP_PERMALINK  profile permalink, default = RESEARCHMAP_ID
.env may be two bare lines (id, then password) or KEY=VALUE lines.

Usage:
    pip install requests
    python3 data/update_researchmap.py                 # add missing presentations; report papers
    python3 data/update_researchmap.py --check          # report missing presentations AND papers, never write
    python3 data/update_researchmap.py --add-papers      # also actually add missing papers
    python3 data/update_researchmap.py --limit 1         # add at most N (handy for a test run)

Both runs always check papers (dedup by DOI); papers are only *added* with --add-papers.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / '.env'
PRES_JSON = ROOT / 'data' / 'presentations.json'
PUBS_JSON = ROOT / 'data' / 'pubs.json'

SITE = 'https://researchmap.jp'
API = 'https://api.researchmap.jp'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


# --------------------------------------------------------------------------- helpers
def load_credentials():
    env_id = os.environ.get('RESEARCHMAP_ID')
    env_pw = os.environ.get('RESEARCHMAP_PASSWORD')
    if env_id and env_pw:
        perm = os.environ.get('RESEARCHMAP_PERMALINK', env_id)
        return env_id, env_pw, perm
    if ENV_PATH.exists():
        lines = [l.strip() for l in ENV_PATH.read_text(encoding='utf-8').splitlines()
                 if l.strip() and not l.lstrip().startswith('#')]
        kv = {}
        for l in lines:
            if '=' in l:
                k, v = l.split('=', 1)
                kv[k.strip()] = v.strip().strip('"').strip("'")
        if kv.get('RESEARCHMAP_ID') and kv.get('RESEARCHMAP_PASSWORD'):
            return (kv['RESEARCHMAP_ID'], kv['RESEARCHMAP_PASSWORD'],
                    kv.get('RESEARCHMAP_PERMALINK', kv['RESEARCHMAP_ID']))
        if len(lines) >= 2:  # bare format: id, password
            return lines[0], lines[1], os.environ.get('RESEARCHMAP_PERMALINK', lines[0])
    sys.exit('[error] no credentials. Set RESEARCHMAP_ID / RESEARCHMAP_PASSWORD '
             '(env or .env), or put id on line 1 and password on line 2 of .env.')


def strip_html(text):
    return html.unescape(re.sub(r'<[^>]+>', '', text or '')).strip()


def en(field):
    """English value of a researchmap multilingual {en, ja} field."""
    if isinstance(field, dict):
        return field.get('en') or field.get('ja') or ''
    return field or ''


def names_csv(people):
    """[{'name': 'A'}, {'name': 'B'}] -> 'A, B' for the author/presenter box."""
    if isinstance(people, dict):  # {'en': [...], 'ja': [...]}
        people = people.get('en') or people.get('ja') or []
    return ', '.join(p['name'] if isinstance(p, dict) else str(p) for p in (people or []))


def date_parts(iso):
    """'2026-05-14' -> ('2026', '05', '14'); partial dates are tolerated."""
    if not iso:
        return '', '', ''
    bits = (str(iso).split('-') + ['', '', ''])[:3]
    return bits[0], bits[1], bits[2]


# --------------------------------------------------------------------------- session
def login(session, account, password):
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ja,en;q=0.9'})
    session.get(f'{SITE}/', timeout=30)
    page = session.get(f'{SITE}/auth/login', timeout=30).text
    m = re.search(r'<form[^>]*id="AuthGeneral".*?</form>', page, re.DOTALL)
    if not m:
        sys.exit('[error] login form not found (site layout changed).')
    fields, _files = scrape_form_fields(m.group(0))
    fields['data[User][username]'] = account
    fields['data[User][password]'] = password
    r = session.post(f'{SITE}/auth/auth/login', data=fields,
                     headers={'Referer': f'{SITE}/auth/login', 'Origin': SITE}, timeout=30)
    if 'ログアウト' not in r.text and 'logout' not in r.text.lower():
        sys.exit('[error] login failed — check RESEARCHMAP_ID / RESEARCHMAP_PASSWORD.')
    print(f'  logged in as {account}')


def scrape_form_fields(form_html):
    """Replicate what a browser submits: every named field with its current
    value. Radios contribute only the checked value; checkboxes/files are
    omitted unless checked (their hidden CakePHP companion carries the default).
    File inputs are returned separately so they can be sent as empty multipart
    parts (the form is multipart/form-data and the SecurityComponent token
    requires every non-unlocked field, including the file input, to be present).
    Returns (fields, file_field_names)."""
    fields = {}
    file_names = []
    for tag in re.findall(r'<input\b[^>]*>', form_html):
        nm = re.search(r'name="([^"]*)"', tag)
        if not nm:
            continue
        name = html.unescape(nm.group(1))
        typ = (re.search(r'type="([^"]*)"', tag) or [None, 'text'])[1]
        val = re.search(r'value="([^"]*)"', tag)
        val = html.unescape(val.group(1)) if val else ''
        if typ in ('radio', 'checkbox'):
            if 'checked' in tag:
                fields[name] = val
        elif typ == 'file':
            file_names.append(name)
        else:
            fields.setdefault(name, val)
    for sm in re.finditer(r'<select\b[^>]*name="([^"]*)"[^>]*>(.*?)</select>', form_html, re.DOTALL):
        name = html.unescape(sm.group(1))
        opt = re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', sm.group(2)) \
            or re.search(r'<option[^>]*value="([^"]*)"[^>]*selected', sm.group(2))
        fields.setdefault(name, html.unescape(opt.group(1)) if opt else '')
    for tm in re.finditer(r'<textarea\b[^>]*name="([^"]*)"[^>]*>(.*?)</textarea>', form_html, re.DOTALL):
        fields.setdefault(html.unescape(tm.group(1)), html.unescape(tm.group(2)).strip())
    return fields, file_names


def get_add_form(session, permalink, achievement_type):
    url = f'{SITE}/{permalink}/{achievement_type}/add'
    page = session.get(url, timeout=30).text
    m = re.search(r'<form[^>]*action="[^"]*' + re.escape(achievement_type) + r'/add"[^>]*>.*?</form>',
                  page, re.DOTALL)
    if not m:
        sys.exit(f'[error] add form for {achievement_type} not found.')
    return scrape_form_fields(m.group(0))


def submit_add(session, permalink, achievement_type, fields, file_names):
    url = f'{SITE}/{permalink}/{achievement_type}/add'
    # multipart/form-data: file inputs are sent as empty parts so the
    # SecurityComponent's field set matches the rendered form.
    files = {name: ('', b'') for name in file_names} or None
    r = session.post(url, data=fields, files=files,
                     headers={'Referer': url, 'Origin': SITE},
                     timeout=60, allow_redirects=True)
    ok = r.status_code == 200 and f'/{achievement_type}/add' not in r.url
    return ok, r


# --------------------------------------------------------------------------- existing data (public API, no auth)
def norm(text):
    return re.sub(r'\s+', ' ', strip_html(text)).strip().lower()


def multilang_values(field):
    if isinstance(field, dict):
        return [v for v in field.values() if v]
    return [field] if field else []


def fetch_existing_keys(permalink, achievement_type, api_keys_fn):
    """Return a set of dedup keys for items already on researchmap (public API)."""
    keys = set()
    try:
        j = requests.get(f'{API}/{permalink}/{achievement_type}',
                         headers={'Accept': 'application/json'}, timeout=30).json()
    except Exception as e:
        print(f'  [warn] could not read existing {achievement_type}: {e}', file=sys.stderr)
        return keys, 0
    items = j.get('items', [])
    for it in items:
        keys.update(api_keys_fn(it))
    return keys, len(items)


# dedup keys: presentations by title+event, papers by DOI
def pres_api_keys(item):
    out = set()
    for t in multilang_values(item.get('presentation_title')):
        for e in multilang_values(item.get('event')):
            out.add(f'{norm(t)}||{norm(e)}')
    return out


def pres_local_key(p):
    return f"{norm(en(p['presentation_title']))}||{norm(en(p.get('event', '')))}"


def paper_api_keys(item):
    ident = item.get('identifiers') or {}
    dois = ident.get('doi') if isinstance(ident, dict) else None
    return {d.strip().lower() for d in (dois or []) if d}


def paper_local_key(p):
    dois = (p.get('identifiers') or {}).get('doi') or []
    return dois[0].strip().lower() if dois else ''


# --------------------------------------------------------------------------- field mappers
def _dates(o, prefix, iso):
    y, m, d = date_parts(iso)
    if y:
        o[f'{prefix}[year]'] = y
    if m:
        o[f'{prefix}[month]'] = m
    if d:
        o[f'{prefix}[day]'] = d


def presentation_overrides(p):
    """Map a researchmap-schema presentations.json entry to add-form fields."""
    P = 'data[PresentationsIndex][_source]'
    title = en(p['presentation_title'])
    presenters = names_csv(p.get('presenters'))
    o = {
        f'{P}[presentation_title][en]': title,
        f'{P}[presentation_title][ja]': p['presentation_title'].get('ja', ''),
        f'{P}[event][en]': en(p['event']),
        f'{P}[event][ja]': p['event'].get('ja', ''),
        f'{P}[presentation_type]': p.get('presentation_type', 'oral_presentation'),
        f'{P}[invited]': '1' if p.get('invited') else '0',
        f'{P}[location][en]': en(p.get('location')),
        f'{P}[location][ja]': (p.get('location') or {}).get('ja', ''),
        f'{P}[address_country]': p.get('address_country', ''),
        f'{P}[languages][0]': (p.get('languages') or ['eng'])[0],
        f'{P}[display]': '2',
        # researchmap auto-splits the author box into individual presenters.
        f'{P}[presenters][en]': presenters,
        f'{P}[presenters][ja]': presenters if p['presentation_title'].get('ja') else '',
        'data[use_ai_split_author][presenters][en]': '1',
        'data[use_ai_split_author][presenters][ja]': '1',
    }
    _dates(o, f'{P}[from_event_date]', p.get('from_event_date'))
    _dates(o, f'{P}[to_event_date]', p.get('to_event_date'))
    _dates(o, f'{P}[publication_date]', p.get('from_event_date'))
    return title, o


# --------------------------------------------------------------------------- main
def add_missing(session, permalink, achievement_type, items, make_overrides,
                api_keys_fn, local_key_fn, check, limit, allow_write):
    existing, n = fetch_existing_keys(permalink, achievement_type, api_keys_fn)
    print(f'{achievement_type}: {n} already on researchmap, {len(items)} in local data')
    added = attempts = 0
    for it in items:
        key = local_key_fn(it)
        title, overrides = make_overrides(it)
        if key and key in existing:
            print(f'  = exists, skip: {title}')
            continue
        if check or not allow_write:
            print(f'  + MISSING (would add): {title}')
            continue
        if limit is not None and attempts >= limit:
            print(f'  … limit {limit} reached, stopping')
            break
        attempts += 1
        fields, file_names = get_add_form(session, permalink, achievement_type)
        fields.update(overrides)
        ok, resp = submit_add(session, permalink, achievement_type, fields, file_names)
        if ok:
            print(f'  + added: {title}  (-> {resp.url})')
            added += 1
            existing.add(key)
        else:
            errs = re.findall(r'class="[^"]*error-message[^"]*"[^>]*>([^<]+)<', resp.text)[:5]
            print(f'  ! FAILED: {title}  status={resp.status_code} url={resp.url}', file=sys.stderr)
            if errs:
                print('    errors:', errs, file=sys.stderr)
    return added


def main():
    ap = argparse.ArgumentParser(description='Sync presentations/papers to researchmap.jp via browser login')
    ap.add_argument('--check', action='store_true', help='report missing items only; never write')
    ap.add_argument('--add-papers', action='store_true',
                    help='also ADD missing published_papers (otherwise papers are only reported)')
    ap.add_argument('--limit', type=int, default=None, help='add at most N items (e.g. --limit 1 for a test)')
    args = ap.parse_args()

    account, password, permalink = load_credentials()
    presentations = json.loads(PRES_JSON.read_text(encoding='utf-8'))
    pubs = json.loads(PUBS_JSON.read_text(encoding='utf-8'))

    session = requests.Session()
    print(f'Logging in to researchmap ({permalink}) ...')
    login(session, account, password)

    # presentations: add missing (unless --check). papers: always reported,
    # added only with --add-papers (papers usually come from a DOI import).
    total = add_missing(session, permalink, 'presentations', presentations,
                        presentation_overrides, pres_api_keys, pres_local_key,
                        args.check, args.limit, allow_write=True)
    add_missing(session, permalink, 'published_papers', pubs,
                paper_overrides, paper_api_keys, paper_local_key,
                args.check, args.limit, allow_write=args.add_papers)

    print('Done (check only, nothing written).' if args.check
          else f'Done. {total} presentation(s) added.')


def paper_overrides(p):
    """Map a researchmap-schema pubs.json entry to published_papers add-form fields."""
    P = 'data[PublishedPapersIndex][_source]'
    title = en(p['paper_title'])
    authors = names_csv(p.get('authors'))
    o = {
        f'{P}[paper_title][en]': title,
        f'{P}[paper_title][ja]': p['paper_title'].get('ja', ''),
        f'{P}[authors][en]': authors,
        f'{P}[authors][ja]': authors if p['paper_title'].get('ja') else '',
        'data[use_ai_split_author][authors][en]': '1',
        'data[use_ai_split_author][authors][ja]': '1',
        f'{P}[publication_name][en]': en(p['publication_name']),
        f'{P}[publication_name][ja]': p['publication_name'].get('ja', ''),
        f'{P}[volume]': str(p.get('volume') or ''),
        f'{P}[number]': str(p.get('number') or ''),
        f'{P}[starting_page]': str(p.get('starting_page') or ''),
        f'{P}[ending_page]': str(p.get('ending_page') or ''),
        f'{P}[published_paper_type]': p.get('published_paper_type', 'scientific_journal'),
        f'{P}[referee]': '1' if p.get('referee') else '0',
        f'{P}[languages][0]': (p.get('languages') or ['eng'])[0],
        f'{P}[display]': '2',
    }
    _dates(o, f'{P}[publication_date]', p.get('publication_date'))
    dois = (p.get('identifiers') or {}).get('doi') or []
    if dois:
        o[f'{P}[identifiers][doi][0]'] = dois[0]
    return title, o


if __name__ == '__main__':
    main()
