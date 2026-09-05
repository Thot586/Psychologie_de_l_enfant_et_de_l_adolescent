"""Construit data/references.json à partir de :
  - src/research/references-legacy.json (72 références de l'ancien outil) + src/research/audit-references.json (7 corrections)
  - src/research/sources.json (sources vérifiées des deux workflows de recherche)
  - data/references-overrides.json (corrections manuelles : auteurs_court, annee, url, etiquette, type, apa7)

Dédoublonne par DOI/URL ; conserve les clés de recherche comme alias de l'entrée retenue.
Écrit aussi src/research/references-report.md (entrées à relire).
Usage : python scripts/build_references.py
"""
from __future__ import annotations

import html as htmlmod
import json
import pathlib
import re
import unicodedata
from collections import OrderedDict

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / 'src' / 'research'
DATA = ROOT / 'data'
LEGACY_HTML = ROOT / '05-septembre-2026' / 'Psychologie_de_l_enfant.html'
VERIF_DATE = '2026-09-03'

legacy = json.load(open(R / 'references-legacy.json', encoding='utf-8'))
audit = {a['id']: a for a in json.load(open(R / 'audit-references.json', encoding='utf-8'))}
research = json.load(open(R / 'sources.json', encoding='utf-8'))
extra_path = DATA / 'references-extra.json'
if extra_path.exists():
    research = research + json.load(open(extra_path, encoding='utf-8'))
ovr_path = DATA / 'references-overrides.json'
overrides = json.load(open(ovr_path, encoding='utf-8')) if ovr_path.exists() else {}

report = []


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm_ident(u):
    u = (u or '').strip().lower()
    u = re.sub(r'^https?://(dx\.)?doi\.org/', '', u)
    u = re.sub(r'^https?://(www\.)?', '', u)
    u = u.split('?sfvrsn')[0]
    return u.rstrip('/').rstrip('.')


def strip_tags(s):
    return htmlmod.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()


YEAR_RE = re.compile(r'\((\d{4})([a-z])?(?:,[^)]*)?\)|\((s\. ?d\.)(?:-[a-z])?\)')
AUTHOR_RE = re.compile(r"([A-ZÀ-ÝÖÜ][\w'’\-À-ÿ]+(?: [A-ZÀ-Ý][\w'’\-À-ÿ]+)*(?:, Jr\.)?), ((?:[A-ZÀ-Ý]\.[\s\-]?)+)")


def parse_year(text):
    m = YEAR_RE.search(text)
    if not m:
        return '', ''
    if m.group(3):
        return 's. d.', ''
    return m.group(1), m.group(2) or ''


def parse_authors(text):
    """Renvoie (auteurs_court, nb_auteurs, sûr)."""
    head = YEAR_RE.split(text)[0].strip().rstrip('.').strip()
    if not head:
        return '', 0, False
    head = re.sub(r'\s*\(dir\.\)\s*$', '', head)
    names = AUTHOR_RE.findall(head)
    n = len(names)
    if n == 0:
        inst = head.split(',')[0].strip()
        inst = re.sub(r'\s*\[.*?\]\s*', '', inst)
        return inst, 0, len(inst) < 70
    first = names[0][0]
    if n == 1:
        return first, 1, True
    if n == 2:
        return f'{first} et {names[1][0]}', 2, True
    return f'{first} et al.', n, True


def classify(entry_type, url, tag, apa):
    et = (entry_type or '').lower()
    lab = ''
    if et in ('meta-analyse', 'revue systematique'):
        lab = 'Méta-analyse' if et == 'meta-analyse' else ''
    if et in ('rapport institutionnel', 'recommandation officielle', 'enquete', 'juridique'):
        lab = 'Institution'
    if et in ('prépublication', 'prepublication'):
        lab = 'Prépublication'
    if tag:
        lab = {'press': 'Presse', 'inst': 'Institution', 'pre': 'Prépublication', 'ong': 'ONG'}.get(tag, lab)
    if not lab and et == 'page web':
        host = norm_ident(url).split('/')[0]
        if any(k in host for k in ('allafrica', 'lexpress', 'newsmada', '2424.mg', 'midi-madagasikara', 'moov.mg', 'tribune', 'studiosifaka', 'theconversation', 'newhumanitarian')):
            lab = 'Presse'
        elif any(k in host for k in ('who.int', 'unicef', 'unesco', 'un.org', 'gouv', 'gov', 'education', 'has-sante', 'inserm', 'instat', 'ohchr', 'ilo.org')):
            lab = 'Institution'
    return lab


TYPE_MAP = {'article': 'article', 'meta-analyse': 'méta-analyse', 'revue systematique': 'revue systématique', 'essai randomise': 'essai randomisé',
            'cohorte': 'cohorte', 'recommandation officielle': 'recommandation officielle', 'rapport institutionnel': 'rapport institutionnel',
            'livre': 'livre', 'chapitre': 'chapitre', 'page web': 'page web', 'enquete': 'enquête', 'these': 'thèse', 'autre': 'autre', 'rapport': 'rapport institutionnel'}

# ---------------------------------------------------------------- formes courtes de l'ancien HTML
legacy_short = {}
if LEGACY_HTML.exists():
    h = LEGACY_HTML.read_text(encoding='utf-8')
    for rid, txt in re.findall(r'<a class="cite" href="#(r-[^"]+)">([^<]+)</a>', h):
        txt = htmlmod.unescape(txt)
        m = re.match(r'(.+?), (\d{4}[a-z]?|s\. d\.(?:-[a-z])?)$', txt)
        if m and rid not in legacy_short:
            legacy_short[rid] = (m.group(1), m.group(2))

entries = OrderedDict()   # ident -> entry
key_index = {}


def add(entry, ident):
    if ident in entries:
        ex = entries[ident]
        for a in [entry['key']] + entry.get('aliases', []):
            if a != ex['key'] and a not in ex['aliases']:
                ex['aliases'].append(a)
        return ex
    entries[ident] = entry
    return entry


# ---------------------------------------------------------------- 1) legacy
for l in legacy:
    rid = l['id']
    key = rid[2:].replace('-', '')
    html_apa = l['html']
    text = l['text']
    urls = l['urls']
    a = audit.get(rid, {})
    corrected = a.get('corrected_apa7', '') or ''
    alt = a.get('alternative_url', '') or ''
    doi = next((u for u in urls if 'doi.org' in u), None)
    url = doi or (urls[0] if urls else '')
    url_secondaire = ''
    note = ''
    if a.get('status') == 'broken_link':
        if doi:
            url_secondaire = alt
        else:
            url = alt or url
        note = a['notes']
    elif a.get('status') in ('metadata_mismatch', 'unverifiable'):
        note = a['notes']
        if rid == 'r-eduscol':
            url = alt
    # nettoyage de la chaîne APA : sans ancres ni URL ; conserve <em>
    apa = re.sub(r'<a [^>]*>.*?</a>', '', html_apa)
    apa = re.sub(r'\((?:texte intégral|présentation|résumé en français)\s*:\s*\)', '', apa)
    apa = re.sub(r'\s+', ' ', apa).strip()
    apa = re.sub(r'\s*\.\s*$', '.', apa)
    if corrected and rid in ('r-eduscol', 'r-huang2022', 'r-scharpf2021', 'r-unicefmg-arozaza', 'r-saitis2022'):
        c = re.sub(r'\s*https?://\S+\s*$', '', corrected).strip()
        # réintroduit l'italique du titre de revue si présent dans l'ancienne chaîne
        em = re.search(r'<em>(.*?)</em>', apa)
        if em and em.group(1) and em.group(1) in c:
            c = c.replace(em.group(1), f'<em>{em.group(1)}</em>', 1)
        apa = c if c.endswith('.') else c + '.'
        note = (note + ' | corrigée d\'après l\'audit').strip(' |')
    short = legacy_short.get(rid)
    if short:
        auteurs_court, an = short
        m = re.match(r'(\d{4})([a-z])?', an)
        annee, suffixe = (m.group(1), m.group(2) or '') if m else (an, '')
    else:
        auteurs_court, _, _ = parse_authors(text)
        annee, suffixe = parse_year(text)
    entry = {
        'key': key, 'aliases': [], 'auteurs_court': auteurs_court, 'annee': annee, 'suffixe': suffixe,
        'apa7': apa, 'type': 'article' if doi else ('page web' if url else 'livre'),
        'doi': doi.replace('https://doi.org/', '') if doi else '', 'url': url, 'url_secondaire': url_secondaire,
        'etiquette': classify('', url, {'Presse': 'press', 'Institution': 'inst', 'ONG': 'ong', 'Prépublication': 'pre'}.get(l['etiquette'], ''), apa),
        'langue': 'fr' if re.search(r'\b(Dans|dir\.|éd\.|s\. d\.)\b', text) or any(k in url for k in ('.mg', 'gouv', 'unicef.org/madagascar/rapports')) else 'en',
        'verifie_le': VERIF_DATE, 'origine': 'legacy', 'note_verification': note,
    }
    if not url:
        report.append(f'- **{key}** : aucune URL (livre) → ajouter une URL d\'éditeur ou WorldCat dans references-overrides.json')
    add(entry, norm_ident(url) if url else 'legacy:' + key)

# ---------------------------------------------------------------- 2) recherche
for s in research:
    text = s['apa7']
    url = s.get('doi_or_url') or ''
    if not url:
        m = re.search(r'https?://\S+', text)
        url = m.group(0).rstrip('.),') if m else ''
    apa = re.sub(r'\s*https?://\S+\s*$', '', text).strip()
    apa = re.sub(r'\s*\(https?://[^)]*\)\s*$', '', apa).strip()
    apa = htmlmod.escape(apa, quote=False)
    if not apa.endswith('.'):
        apa += '.'
    auteurs_court, n, sure = parse_authors(text)
    annee, suffixe = parse_year(text)
    if not sure or not annee:
        report.append(f'- **{s["key"]}** : forme courte à vérifier → « {auteurs_court}, {annee}{suffixe} » ({text[:90]}…)')
    doi = ''
    if 'doi.org/' in url:
        doi = url.split('doi.org/')[1]
    entry = {
        'key': s['key'], 'aliases': [], 'auteurs_court': auteurs_court, 'annee': annee, 'suffixe': suffixe, 'apa7': apa,
        'type': TYPE_MAP.get((s.get('type') or 'autre').lower(), s.get('type', 'autre')), 'doi': doi, 'url': url, 'url_secondaire': '',
        'etiquette': classify(s.get('type', ''), url, '', apa), 'langue': (s.get('language') or '')[:2].lower().replace('fr', 'fr').replace('an', 'en'),
        'verifie_le': VERIF_DATE, 'origine': ','.join(s.get('origins', [])), 'note_verification': s.get('verification_notes', '')[:300],
        'discipline': s.get('discipline', ''), 'apport': s.get('what_it_teaches', ''), 'modules_cibles': s.get('modules_cibles', []),
    }
    if not url:
        report.append(f'- **{s["key"]}** : aucune URL → à compléter')
    add(entry, norm_ident(url) if url else 'src:' + s['key'])

# ---------------------------------------------------------------- 3) doublons de clés et overrides
seen = {}
for e in entries.values():
    k = e['key']
    if k in seen:
        n = 2
        while f'{k}-{n}' in seen:
            n += 1
        report.append(f'- clé dupliquée « {k} » renommée « {k}-{n} »')
        e['key'] = f'{k}-{n}'
    seen[e['key']] = e
for k, o in overrides.items():
    target = seen.get(k) or next((e for e in entries.values() if k in e['aliases']), None)
    if not target:
        report.append(f'- override sans cible : {k}')
        continue
    if o.get('merge_into'):
        dest = seen.get(o['merge_into']) or next((e for e in entries.values() if o['merge_into'] in e['aliases']), None)
        if dest and dest is not target:
            for a in [target['key']] + target['aliases']:
                if a not in dest['aliases'] and a != dest['key']:
                    dest['aliases'].append(a)
            for ident, e in list(entries.items()):
                if e is target:
                    del entries[ident]
        continue
    if o.get('rename'):
        if target['key'] not in target['aliases']:
            target['aliases'].append(target['key'])
        target['key'] = o['rename']
    target.update({kk: vv for kk, vv in o.items() if kk not in ('key', 'rename', 'merge_into')})

# ---------------------------------------------------------------- 4) tri, écriture
out = sorted(entries.values(), key=lambda e: strip_accents(strip_tags(e['apa7'])).lower())
DATA.mkdir(exist_ok=True)
with open(DATA / 'references.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
(R / 'references-report.md').write_text('# Références : points à relire\n\n' + '\n'.join(report) + '\n', encoding='utf-8')
n_alias = sum(len(e['aliases']) for e in out)
print(f'{len(out)} références écrites ({n_alias} alias) ; {len(report)} points à relire dans src/research/references-report.md')
