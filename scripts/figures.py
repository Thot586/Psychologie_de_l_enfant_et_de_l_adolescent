"""Génère les graphiques de données (SVG inline) depuis data/figures.json vers src/figures/gen/.
Types : hbar (barres horizontales avec intervalle), gbar (barres groupées, 2 à 4 séries), dots100 (100 points),
dumbbell (avant → après), dotplot (points avec ligne de référence à 1).
Règles (dataviz) : marques fines (≤ 24 px), extrémité arrondie, grille en filet, étiquettes directes sobres,
texte en encre (jamais en couleur de série), légende dès 2 séries, couleurs = variables CSS --d1…--d4.
Usage : python scripts/figures.py
"""
from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / 'figures' / 'gen'
OUT.mkdir(parents=True, exist_ok=True)
FIG = json.load(open(ROOT / 'data' / 'figures.json', encoding='utf-8'))

W = 640
LEFT = 250
RIGHT = 70
FONT = 13


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v, nd=1):
    s = f'{v:.{nd}f}'.replace('.', ',')
    return s.rstrip('0').rstrip(',') if ',' in s else s


def bar_path(x0, y0, w, h, r=4):
    """Barre horizontale carrée à gauche (ligne de base), arrondie à droite (extrémité de donnée)."""
    if w <= r:
        return f'M{x0},{y0} h{max(w, 0.5)} v{h} h{-max(w, 0.5)} z'
    return f'M{x0},{y0} h{w - r} a{r},{r} 0 0 1 {r},{r} v{h - 2 * r} a{r},{r} 0 0 1 {-r},{r} h{-(w - r)} z'


def wrap(label, width=32):
    words = label.split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines[:2]


CUR = {'name': 'fig'}


def svg_open(w, h, title, desc, cls=''):
    n = CUR['name']
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="{n}-t {n}-d" class="{cls}" font-family="Public Sans, Segoe UI, system-ui, sans-serif" font-size="{FONT}">'
            f'<title id="{n}-t">{esc(title)}</title><desc id="{n}-d">{esc(desc)}</desc>')


def grid(x_of, vmax, y0, y1, step):
    out = []
    v = 0
    while v <= vmax + 1e-9:
        x = x_of(v)
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}"/>')
        out.append(f'<text class="t-sm" x="{x:.1f}" y="{y1 + 16}" text-anchor="middle">{fmt(v)}</text>')
        v += step
    return out


def label_lines(x, y, label, anchor='end'):
    lines = wrap(label)
    dy = -(len(lines) - 1) * 7
    return ''.join(f'<text x="{x}" y="{y + dy + i * 15:.1f}" text-anchor="{anchor}" dominant-baseline="middle">{esc(l)}</text>' for i, l in enumerate(lines))


def render_hbar(d):
    items = d['items']
    rowh = 44 if len(items) < 8 else 34
    top = 18 if not d.get('refline') else 30
    h = top + rowh * len(items) + 34
    vmax = d.get('max', max(i.get('hi', i['value']) for i in items) * 1.15)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    step = 10 if vmax > 25 else 5 if vmax > 10 else 1
    out = [svg_open(W, h, d['title'], d['desc'])]
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), step)
    for i, it in enumerate(items):
        y = top + i * rowh + (10 if rowh > 40 else 6)
        out.append(f'<path class="f1" d="{bar_path(x_of(0), y, x_of(it["value"]) - x_of(0), 22)}"><title>{esc(it["label"])} : {fmt(it["value"])} {esc(d.get("unit", ""))}</title></path>')
        if 'lo' in it:
            out.append(f'<line class="line" x1="{x_of(it["lo"]):.1f}" y1="{y + 11}" x2="{x_of(it["hi"]):.1f}" y2="{y + 11}" stroke-width="1.5"/>')
            out.append(f'<line class="line" x1="{x_of(it["lo"]):.1f}" y1="{y + 5}" x2="{x_of(it["lo"]):.1f}" y2="{y + 17}"/><line class="line" x1="{x_of(it["hi"]):.1f}" y1="{y + 5}" x2="{x_of(it["hi"]):.1f}" y2="{y + 17}"/>')
        out.append(label_lines(LEFT - 10, y + 11, it['label']))
        xv = x_of(it.get('hi', it['value'])) + 8
        out.append(f'<text class="t-num" x="{xv:.1f}" y="{y + 11}" dominant-baseline="middle">{fmt(it["value"])} {esc(d.get("unit", ""))}</text>')
        if it.get('range_label'):
            out.append(f'<text class="t-sm" x="{LEFT - 10}" y="{y + 11 + 15 + (7 if len(wrap(it["label"])) > 1 else 0)}" text-anchor="end">{esc(it["range_label"])}</text>' if False else '')
    if d.get('refline'):
        rx = x_of(d['refline']['value'])
        out.append(f'<line class="ref" x1="{rx:.1f}" y1="{top - 6}" x2="{rx:.1f}" y2="{top + rowh * len(items)}" stroke-width="2"/>')
        out.append(f'<text class="t-sm" x="{rx + 4:.1f}" y="{top - 8}">{esc(d["refline"]["label"])}</text>')
    out.append('</svg>')
    return ''.join(out)


def render_gbar(d):
    items = d['items']
    series = d['series']
    n = len(series)
    barh = 14
    gap = 3
    rowh = n * (barh + gap) + 18
    top = 34
    h = top + rowh * len(items) + 34
    vmax = d.get('max', max(v for i in items for v in i['values']) * 1.15)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    step = 10 if vmax > 25 else 5
    out = [svg_open(W, h, d['title'], d['desc'])]
    # légende
    lx = LEFT
    for k, s in enumerate(series):
        out.append(f'<rect class="f{k + 1}" x="{lx}" y="6" width="12" height="12" rx="2"/><text x="{lx + 17}" y="12.5" dominant-baseline="middle">{esc(s)}</text>')
        lx += 17 + len(s) * 7.5 + 18
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), step)
    for i, it in enumerate(items):
        y0 = top + i * rowh + 6
        for k, v in enumerate(it['values']):
            y = y0 + k * (barh + gap)
            out.append(f'<path class="f{k + 1}" d="{bar_path(x_of(0), y, x_of(v) - x_of(0), barh, 3)}"><title>{esc(it["label"])} · {esc(series[k])} : {fmt(v)} %</title></path>')
            out.append(f'<text class="t-sm t-num" x="{x_of(v) + 6:.1f}" y="{y + barh / 2:.1f}" dominant-baseline="middle">{fmt(v)}</text>')
        out.append(label_lines(LEFT - 10, y0 + (n * (barh + gap) - gap) / 2, it['label']))
    out.append('</svg>')
    return ''.join(out)


def render_dots100(d):
    cols = 10
    r = 9
    step = 26
    pad = 14
    w = pad * 2 + step * cols
    h = pad * 2 + step * 10 + 30
    out = [svg_open(w, h, d['title'], d['desc'], 'narrow')]
    for i in range(100):
        cx = pad + step * (i % cols) + step / 2
        cy = pad + step * (i // cols) + step / 2
        on = ' on' if i < d['value'] else ''
        out.append(f'<circle class="dot{on}" cx="{cx}" cy="{cy}" r="{r}"/>')
    out.append(f'<text class="t-b" x="{pad}" y="{h - 12}"><tspan class="t-num" font-size="18">{d["value"]}</tspan> sur 100 · {esc(d["src"])}</text>')
    out.append('</svg>')
    return ''.join(out)


def render_dumbbell(d):
    items = d['items']
    rowh = 52
    top = 20
    h = top + rowh * len(items) + 34
    vmax = d.get('max', 100)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    out = [svg_open(W, h, d['title'], d['desc'])]
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), 10)
    for i, it in enumerate(items):
        y = top + i * rowh + 18
        x1, x2 = x_of(it['from']), x_of(it['to'])
        out.append(f'<line class="line" x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" stroke-width="3"/>')
        out.append(f'<circle class="halo" cx="{x1:.1f}" cy="{y}" r="9"/><circle class="dot" cx="{x1:.1f}" cy="{y}" r="7"><title>Avant : {fmt(it["from"])} %</title></circle>')
        out.append(f'<circle class="halo" cx="{x2:.1f}" cy="{y}" r="9"/><circle class="f1" cx="{x2:.1f}" cy="{y}" r="7"><title>Après : {fmt(it["to"])} %</title></circle>')
        out.append(f'<text class="t-num" x="{x1:.1f}" y="{y - 14}" text-anchor="middle">{fmt(it["from"])} %</text>')
        out.append(f'<text class="t-num" x="{x2:.1f}" y="{y - 14}" text-anchor="middle">{fmt(it["to"])} %</text>')
        out.append(label_lines(LEFT - 10, y, it['label']))
    out.append('</svg>')
    return ''.join(out)


def render_dotplot(d):
    items = d['items']
    rowh = 34
    top = 18
    h = top + rowh * len(items) + 34
    vmax = d.get('max', 4)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    out = [svg_open(W, h, d['title'], d['desc'])]
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), 1)
    out.append(f'<line class="ref" x1="{x_of(1):.1f}" y1="{top - 6}" x2="{x_of(1):.1f}" y2="{top + rowh * len(items)}" stroke-width="2"/>')
    out.append(f'<text class="t-sm" x="{x_of(1) + 4:.1f}" y="{top - 8}">1 = aucune différence</text>')
    for i, it in enumerate(items):
        y = top + i * rowh + 14
        out.append(f'<line class="line-soft" x1="{x_of(1):.1f}" y1="{y}" x2="{x_of(it["value"]):.1f}" y2="{y}"/>')
        out.append(f'<circle class="halo" cx="{x_of(it["value"]):.1f}" cy="{y}" r="8"/><circle class="f1" cx="{x_of(it["value"]):.1f}" cy="{y}" r="6"><title>{esc(it["label"])} : {fmt(it["value"], 2)}</title></circle>')
        out.append(f'<text class="t-num" x="{x_of(it["value"]) + 12:.1f}" y="{y}" dominant-baseline="middle">{fmt(it["value"], 2)}</text>')
        out.append(label_lines(LEFT - 10, y, it['label']))
    out.append('</svg>')
    return ''.join(out)


RENDER = {'hbar': render_hbar, 'gbar': render_gbar, 'dots100': render_dots100, 'dumbbell': render_dumbbell, 'dotplot': render_dotplot}

n = 0
for name, d in FIG.items():
    CUR['name'] = name
    svg = RENDER[d['type']](d)
    (OUT / f'{name}.svg').write_text(svg, encoding='utf-8')
    # la note de figure (sources, mises en garde) n'est plus dessinée : troisième ligne du jumeau, rendue sous la figure
    (OUT / f'{name}.txt').write_text(d['title'] + '\n' + d['desc'] + '\n' + (d.get('note') or '') + chr(10), encoding='utf-8')
    n += 1
print(f'{n} figures générées dans {OUT.relative_to(ROOT)}')
