"""Vérifie les DOI et URL de data/references.json et data/glossaire.json.
  - DOI : interrogation de l'API Crossref (https://api.crossref.org/works/<doi>) ; un DOI qui résout est « ok ».
  - URL : requête HTTP HEAD puis GET ; 2xx/3xx = ok ; 403/429 sur un domaine de la liste blanche = « manuel »
    (domaines qui bloquent les robots : vérifiés à la main dans un navigateur, date consignée dans le rapport).
Écrit src/research/liens-rapport.md et affiche un résumé. Usage : python scripts/check_links.py [--fast]
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import json
import time
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAST = '--fast' in sys.argv
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 (verification de liens, site pedagogique)'
HAND = json.load(open(ROOT / 'src' / 'research' / 'liens-verifies-main.json', encoding='utf-8')) if (ROOT / 'src' / 'research' / 'liens-verifies-main.json').exists() else {}
MANUAL_DOMAINS = ('ibcr.org', 'unicef.org', 'instat.mg', 'arozaza.mg', 'allafrica.com', 'who.int', 'unesco.org', 'unesdoc.unesco.org', 'education.gouv.fr', 'eduscol.education.gouv.fr',
                  'sciencedirect.com', 'wiley.com', 'onlinelibrary.wiley.com', 'tandfonline.com', 'cairn.info', 'shs.cairn.info', 'facebook.com', 'researchgate.net', 'jstor.org', 'academia.edu', 'lexpress.mg', 'midi-madagasikara.mg')


def fetch(url, method='HEAD', timeout=25):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'fr,en;q=0.8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, url
    except Exception as e:  # noqa: BLE001
        return -1, str(e)[:80]


def check_doi(doi):
    if doi in HAND:  # DOI dont la résolution a été vérifiée à la main
        return 'ok', f'vérifié à la main le {HAND[doi]}'
    s, _ = fetch('https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='/()'), 'GET')
    if s == 429:  # limitation de débit Crossref : une seule nouvelle tentative après une pause
        time.sleep(4)
        s, _ = fetch('https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='/()'), 'GET')
    if s == 200:
        return 'ok', 'crossref'
    s2, _ = fetch('https://doi.org/' + doi, 'HEAD')
    return ('ok', 'doi.org') if s2 in (200, 301, 302, 303) else ('KO', f'crossref {s} / doi.org {s2}')


def check_url(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if url in HAND:  # vérifié à la main dans un navigateur (src/research/liens-verifies-main.json)
        return 'ok', f'vérifié à la main le {HAND[url]}'
    s, final = fetch(url, 'HEAD')
    if s in (405, 403, 404, -1, 429, 400):
        s, final = fetch(url, 'GET')
    if 200 <= s < 400:
        return 'ok', str(s)
    if any(host.endswith(d) for d in MANUAL_DOMAINS):
        return 'manuel', f'{s} (domaine à vérifier à la main)'
    return 'KO', str(s)


def main():
    refs = json.load(open(ROOT / 'data' / 'references.json', encoding='utf-8'))
    gloss_path = ROOT / 'data' / 'glossaire.json'
    gloss = json.load(open(gloss_path, encoding='utf-8')) if gloss_path.exists() else []
    jobs = []
    for r in refs:
        if r.get('doi'):
            jobs.append(('ref', r['key'], 'doi', r['doi']))
        elif r.get('url'):
            jobs.append(('ref', r['key'], 'url', r['url']))
        if r.get('url_secondaire'):
            jobs.append(('ref', r['key'] + ' (secondaire)', 'url', r['url_secondaire']))
    for g in gloss:
        for l in g.get('liens', []):
            jobs.append(('gloss', g['id'], 'url', l['url']))
    if FAST:
        jobs = jobs[:40]
    results = []

    def run(j):
        kind, key, t, target = j
        st, note = check_doi(target) if t == 'doi' else check_url(target)
        return (kind, key, t, target, st, note)

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(run, jobs):
            results.append(res)
            print(f'  [{res[4]:6s}] {res[1]:32s} {res[3][:80]}  {res[5]}')
    ok = sum(1 for r in results if r[4] == 'ok')
    man = [r for r in results if r[4] == 'manuel']
    ko = [r for r in results if r[4] == 'KO']
    today = dt.date.today().isoformat()
    lines = [f'# Vérification des liens ({today})', '', f'{len(results)} liens vérifiés : {ok} ok, {len(man)} à vérifier à la main (domaines bloquant les robots), {len(ko)} en échec.', '']
    if ko:
        lines += ['## En échec', ''] + [f'- {r[0]} **{r[1]}** : {r[3]} ({r[5]})' for r in ko] + ['']
    if man:
        lines += ['## À vérifier à la main dans un navigateur', ''] + [f'- {r[0]} **{r[1]}** : {r[3]} ({r[5]})' for r in man] + ['']
    (ROOT / 'src' / 'research' / 'liens-rapport.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'\n{len(results)} liens : {ok} ok, {len(man)} manuels, {len(ko)} KO → src/research/liens-rapport.md')


if __name__ == '__main__':
    main()
