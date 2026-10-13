# -*- coding: utf-8 -*-
"""Reconstruct the 38 figures of the Tencent 'Agent self-evolution flywheel'
article as portable, English-only inline SVG. Produces a dict of {key: svg}.
Run modes:
  python _flywheel_figs.py preview   -> write _preview.html (all figs stacked)
  python _flywheel_figs.py build     -> assemble the final illustrated MD
"""
import sys, math, io, os

FONT = 'system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif'
INK  = '#0f172a'
SUB  = '#64748b'
LINE = '#94a3b8'

# fill, stroke, text
PAL = {
    'blue':   ('#eff6ff', '#3b82f6', '#1d4ed8'),
    'green':  ('#ecfdf5', '#10b981', '#047857'),
    'amber':  ('#fffbeb', '#f59e0b', '#b45309'),
    'red':    ('#fef2f2', '#ef4444', '#b91c1c'),
    'purple': ('#faf5ff', '#a855f7', '#7e22ce'),
    'gray':   ('#f8fafc', '#94a3b8', '#475569'),
    'teal':   ('#f0fdfa', '#14b8a6', '#0f766e'),
    'emerald':('#ecfdf5', '#059669', '#047857'),
}

def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

def wrap_px(s, width, size, pad=20):
    maxc = max(4, int((width - pad) / (size * 0.53)))
    out, cur = [], ''
    for w in str(s).split():
        t = (cur + ' ' + w).strip()
        if len(t) <= maxc:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out or ['']

def txt(x, y, s, size=15, color=INK, weight='normal', anchor='start', italic=False):
    st = ' font-style="italic"' if italic else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family=\'{FONT}\' font-size="{size}" '
            f'fill="{color}" font-weight="{weight}" text-anchor="{anchor}"{st}>{esc(s)}</text>')

def block(x, y, lines, size, color=INK, lh=None, weight='normal', anchor='start'):
    lh = lh or size + 5
    out = []
    for i, ln in enumerate(lines):
        out.append(txt(x, y + i * lh, ln, size, color, weight, anchor))
    return ''.join(out), y + len(lines) * lh

def rrect(x, y, w, h, fill='#ffffff', stroke='#e2e8f0', rx=12, sw=1.5, extra=''):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{(" "+extra) if extra else ""}/>')

def arrow(x1, y1, x2, y2, color=LINE, w=2.6, hl=10, dash=False):
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - hl * math.cos(ang), y2 - hl * math.sin(ang)
    d = ' stroke-dasharray="6 5"' if dash else ''
    p2 = (x2 - hl * math.cos(ang - .45), y2 - hl * math.sin(ang - .45))
    p3 = (x2 - hl * math.cos(ang + .45), y2 - hl * math.sin(ang + .45))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" '
            f'stroke-width="{w}"{d}/>'
            f'<polygon points="{x2:.1f},{y2:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" fill="{color}"/>')

def chip(cx, y, label, fill, tcolor='#ffffff', size=12.5, pad=9):
    w = len(label) * size * 0.6 + pad * 2
    return (rrect(cx - w / 2, y, w, size + 9, fill, fill, rx=(size + 9) / 2, sw=0) +
            txt(cx, y + size + 2, label, size, tcolor, 'bold', 'middle')), w

def svg_open(w, h, title=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="100%" style="max-width:{w}px;height:auto;display:block;margin:1.4em auto" '
            f'role="img" aria-label="{esc(title)}">'
            + rrect(1, 1, w - 2, h - 2, '#ffffff', '#e2e8f0', rx=16, sw=1.5))

def header(w, title, subtitle=None, y=38):
    s = txt(w / 2, y, title, 21, INK, '700', 'middle')
    yy = y
    if subtitle:
        s += txt(w / 2, y + 24, subtitle, 13.5, SUB, 'normal', 'middle')
        yy = y + 24
    return s, yy + 22

# ---------------------------------------------------------------- card measure
def _card_h(c, w, pad=16):
    y = pad
    if c.get('num') or c.get('tag'):
        y += 30
    y += len(wrap_px(c['head'], w, 16)) * 22
    if c.get('sub'):
        y += len(wrap_px(c['sub'], w, 13)) * 18 + 3
    for b in c.get('bullets', []):
        y += len(wrap_px(b, w - 14, 13)) * 18 + 4
    if c.get('foot'):
        y += 6 + len(wrap_px(c['foot'], w, 12.5)) * 17
    return y + pad

def _draw_card(x, y, w, h, c, pad=16):
    f, st, tc = PAL[c.get('color', 'blue')]
    out = [rrect(x, y, w, h, f, st, rx=12, sw=2)]
    cy = y + pad + 6
    if c.get('num') is not None:
        out.append(f'<circle cx="{x+pad+8}" cy="{cy+3}" r="13" fill="{st}"/>')
        out.append(txt(x + pad + 8, cy + 8, str(c['num']), 14, '#fff', '700', 'middle'))
        out.append(txt(x + pad + 28, cy + 8, c.get('tag', ''), 13, tc, '700'))
        cy += 30
    elif c.get('tag'):
        cw, ww = chip(x + pad + _tw(c['tag'], 12.5) / 2 + 2, y + pad, c['tag'], st)
        out.append(cw); cy = y + pad + 34
    for ln in wrap_px(c['head'], w, 16):
        out.append(txt(x + pad, cy, ln, 15.5, tc, '700')); cy += 22
    if c.get('sub'):
        for ln in wrap_px(c['sub'], w, 13):
            out.append(txt(x + pad, cy, ln, 13, INK, '600')); cy += 18
        cy += 3
    for b in c.get('bullets', []):
        lns = wrap_px(b, w - 14, 13)
        out.append(f'<circle cx="{x+pad+2}" cy="{cy-4}" r="2" fill="{st}"/>')
        for j, ln in enumerate(lns):
            out.append(txt(x + pad + 10, cy, ln, 12.8, '#334155')); cy += 18
        cy += 4
    if c.get('foot'):
        cy += 2
        for ln in wrap_px(c['foot'], w, 12.5):
            out.append(txt(x + pad, cy, ln, 12.3, SUB, 'italic' if False else 'normal')); cy += 17
    return ''.join(out)

def _tw(s, size):
    return len(s) * size * 0.6 + 18

# ---------------------------------------------------------------- flow
def fig_flow(title, subtitle, cards, orient='h', arrows=True, note=None,
             W=940, gap=44, acolor=None):
    n = len(cards)
    if orient == 'h':
        cw = (W - 80 - gap * (n - 1)) / n
        hs = [_card_h(c, cw) for c in cards]
        ch = max(hs)
        head, y0 = header(W, title, subtitle)
        H = y0 + ch + (60 if note else 30)
        body = [svg_open(W, H, title), head]
        x = 40
        for i, c in enumerate(cards):
            body.append(_draw_card(x, y0, cw, ch, c))
            if arrows and i < n - 1:
                ac = acolor or PAL[cards[i + 1].get('color', 'gray')][1]
                body.append(arrow(x + cw + 6, y0 + ch / 2, x + cw + gap - 6, y0 + ch / 2, ac))
            x += cw + gap
        if note:
            body.append(txt(W / 2, H - 22, note, 12.8, SUB, 'normal', 'middle'))
        body.append('</svg>')
        return ''.join(body)
    else:  # vertical
        cw = W - 80
        head, y0 = header(W, title, subtitle)
        hs = [_card_h(c, cw) for c in cards]
        H = y0 + sum(hs) + gap * (n - 1) + (50 if note else 24)
        body = [svg_open(W, H, title), head]
        y = y0
        for i, c in enumerate(cards):
            body.append(_draw_card(40, y, cw, hs[i], c))
            if arrows and i < n - 1:
                ac = acolor or PAL[cards[i + 1].get('color', 'gray')][1]
                body.append(arrow(W / 2, y + hs[i] + 4, W / 2, y + hs[i] + gap - 4, ac, w=3))
            y += hs[i] + gap
        if note:
            body.append(txt(W / 2, H - 18, note, 12.8, SUB, 'normal', 'middle'))
        body.append('</svg>')
        return ''.join(body)

# ---------------------------------------------------------------- table
def _sev_color(s):
    s = s.lower()
    if 'high' in s: return PAL['red'][1], '#fff'
    if 'medium' in s or 'mid' in s and 'low' not in s: return PAL['amber'][1], '#fff'
    if 'fatal' in s: return PAL['red'][1], '#fff'
    return '#eab308', '#fff'

def fig_table(title, subtitle, headers, rows, weights, W=980, sev_idx=None,
              first_color=None, note=None):
    pad = 26
    tw = W - 2 * pad
    tot = sum(weights)
    xs, acc = [], pad
    for wt in weights:
        xs.append(acc); acc += tw * wt / tot
    xs.append(W - pad)
    head, y0 = header(W, title, subtitle)
    # measure rows
    def cell_lines(txt_, ci):
        cwid = xs[ci + 1] - xs[ci] - 16
        return wrap_px(txt_, cwid, 12.8)
    rh = []
    for r in rows:
        m = 1
        for ci, cell in enumerate(r):
            if sev_idx is not None and ci == sev_idx:
                continue
            m = max(m, len(cell_lines(cell, ci)))
        rh.append(m * 18 + 16)
    hh = 30
    H = y0 + hh + sum(rh) + (44 if note else 22)
    body = [svg_open(W, H, title), head]
    # header row
    body.append(rrect(pad, y0, tw, hh, '#f1f5f9', '#e2e8f0', rx=8, sw=1))
    for ci, h in enumerate(headers):
        body.append(txt(xs[ci] + 8, y0 + 20, h, 13, '#334155', '700'))
    y = y0 + hh
    for ri, r in enumerate(rows):
        if ri % 2 == 1:
            body.append(f'<rect x="{pad}" y="{y:.1f}" width="{tw:.1f}" height="{rh[ri]:.1f}" fill="#fafbfc"/>')
        for ci, cell in enumerate(r):
            cx = xs[ci] + 8
            if sev_idx is not None and ci == sev_idx:
                col, tcol = _sev_color(cell)
                cwd = min(_tw(cell, 12) + 6, xs[ci + 1] - xs[ci] - 12)
                body.append(rrect(xs[ci] + 8, y + rh[ri] / 2 - 11, cwd, 22, col, col, rx=11, sw=0))
                body.append(txt(xs[ci] + 8 + cwd / 2, y + rh[ri] / 2 + 4, cell, 11.5, tcol, '700', 'middle'))
                continue
            lns = cell_lines(cell, ci)
            ty = y + rh[ri] / 2 - (len(lns) - 1) * 9 + 4
            bold = (ci == 0)
            col = (first_color or '#0f172a') if ci == 0 else '#334155'
            for ln in lns:
                body.append(txt(cx, ty, ln, 12.6, col, '700' if bold else 'normal'))
                ty += 18
        body.append(f'<line x1="{pad}" y1="{y+rh[ri]:.1f}" x2="{W-pad}" y2="{y+rh[ri]:.1f}" stroke="#eef2f6" stroke-width="1"/>')
        y += rh[ri]
    if note:
        body.append(txt(W / 2, H - 18, note, 12.8, SUB, 'normal', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- pyramid
def fig_pyramid(title, subtitle, layers, left_labels, W=940):
    # layers top->bottom: dict head, sub(list), color ; right label list
    head, y0 = header(W, title, subtitle)
    n = len(layers)
    lh = 96
    gap = 6
    H = y0 + n * lh + n * gap + 26
    cx = W / 2 - 40
    topw, botw = 150, 620
    body = [svg_open(W, H, title), head]
    y = y0
    for i, L in enumerate(layers):
        f, st, tc = PAL[L['color']]
        wtop = topw + (botw - topw) * (i) / n
        wbot = topw + (botw - topw) * (i + 1) / n
        x1t, x2t = cx - wtop / 2, cx + wtop / 2
        x1b, x2b = cx - wbot / 2, cx + wbot / 2
        body.append(f'<polygon points="{x1t:.1f},{y:.1f} {x2t:.1f},{y:.1f} {x2b:.1f},{y+lh:.1f} {x1b:.1f},{y+lh:.1f}" fill="{f}" stroke="{st}" stroke-width="2"/>')
        cyt = y + lh / 2
        body.append(txt(cx, cyt - 6, L['head'], 16, tc, '700', 'middle'))
        if L.get('sub'):
            body.append(txt(cx, cyt + 15, L['sub'], 12.3, '#475569', 'normal', 'middle'))
        # right label
        body.append(txt(x2b + 18, cyt - 4, L['rlabel'][0], 12.8, tc, '700'))
        if len(L['rlabel']) > 1:
            body.append(txt(x2b + 18, cyt + 14, L['rlabel'][1], 12, SUB))
        # left freq label
        body.append(txt(x1b - 18, cyt + 4, left_labels[i], 12, SUB, 'normal', 'end'))
        y += lh + gap
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- trilemma
def fig_trilemma(title, subtitle, top, bl, br, edges, center, W=880):
    head, y0 = header(W, title, subtitle)
    H = y0 + 400
    ax, ay = W / 2, y0 + 20            # apex
    bx1, by1 = W / 2 - 250, y0 + 300   # bottom-left
    bx2, by2 = W / 2 + 250, y0 + 300   # bottom-right
    body = [svg_open(W, H, title), head]
    body.append(f'<polygon points="{ax},{ay} {bx1},{by1} {bx2},{by2}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>')
    # edge labels
    body.append(txt((ax + bx1) / 2 - 8, (ay + by1) / 2, edges[0], 12.5, SUB, 'normal', 'end'))
    body.append(txt((ax + bx2) / 2 + 8, (ay + by2) / 2, edges[1], 12.5, SUB, 'normal', 'start'))
    body.append(txt(W / 2, by1 + 26, edges[2], 12.5, SUB, 'normal', 'middle'))
    # vertices
    for (vx, vy, v, col, anch) in [(ax, ay, top, 'red', 'middle'),
                                   (bx1, by1, bl, 'green', 'middle'),
                                   (bx2, by2, br, 'blue', 'middle')]:
        f, st, tc = PAL[col]
        body.append(f'<circle cx="{vx}" cy="{vy}" r="46" fill="{f}" stroke="{st}" stroke-width="3"/>')
        body.append(txt(vx, vy - 4, v[0], 15, tc, '700', 'middle'))
        body.append(txt(vx, vy + 15, v[1], 11.5, '#475569', 'normal', 'middle'))
    # center box
    cw, chh = 300, 74
    body.append(rrect(W / 2 - cw / 2, y0 + 150, cw, chh, '#ecfdf5', '#059669', rx=10, sw=2))
    body.append(txt(W / 2, y0 + 176, center[0], 13.5, '#047857', '700', 'middle'))
    for i, ln in enumerate(center[1:]):
        body.append(txt(W / 2, y0 + 176 + 20 + i * 17, ln, 12, '#334155', 'normal', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- attribution tree
def fig_tree(title, subtitle, root, mid, branches, note, W=980):
    head, y0 = header(W, title, subtitle)
    n = len(branches)
    rowh, rgap = 62, 14
    H = y0 + n * (rowh + rgap) + (46 if note else 20)
    rx0, midx = 40, 250
    condx, actx = 470, 730
    body = [svg_open(W, H, title), head]
    cy_mid = y0 + (n * (rowh + rgap)) / 2
    # root
    body.append(rrect(rx0, cy_mid - 30, 150, 60, '#eef2ff', '#6366f1', rx=12, sw=2))
    body.append(txt(rx0 + 75, cy_mid + 4, root, 14, '#4338ca', '700', 'middle'))
    body.append(arrow(rx0 + 150, cy_mid, midx - 6, cy_mid, LINE))
    # mid
    body.append(rrect(midx, cy_mid - 34, 175, 68, '#f8fafc', '#64748b', rx=12, sw=2))
    for i, ln in enumerate(wrap_px(mid, 165, 13.5)):
        body.append(txt(midx + 87, cy_mid - 6 + i * 18, ln, 13.5, '#334155', '700', 'middle'))
    y = y0
    for b in branches:
        f, st, tc = PAL[b['color']]
        body.append(arrow(midx + 175, cy_mid, condx - 6, y + rowh / 2, st, w=2))
        body.append(rrect(condx, y, 235, rowh, f, st, rx=10, sw=2))
        cy = y + 22
        for ln in wrap_px(b['cond'], 225, 13.5):
            body.append(txt(condx + 12, cy, ln, 13.5, tc, '700')); cy += 17
        for ln in wrap_px(b.get('csub', ''), 225, 12):
            if ln:
                body.append(txt(condx + 12, cy, ln, 11.8, '#475569')); cy += 15
        body.append(arrow(condx + 235, y + rowh / 2, actx - 6, y + rowh / 2, st, w=2))
        ay = y + rowh / 2 - (len(wrap_px(b['act'], 220, 13)) - 1) * 8
        for ln in wrap_px(b['act'], 220, 13):
            body.append(txt(actx, ay, ln, 13, INK, '600')); ay += 16
        y += rowh + rgap
    if note:
        body.append(txt(W / 2, H - 16, note, 12.6, SUB, 'normal', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- snake pipeline
def fig_snake(title, subtitle, steps, note, W=980, cols=4):
    head, y0 = header(W, title, subtitle)
    pad, gapx, gapy = 30, 30, 46
    n = len(steps)
    rows = math.ceil(n / cols)
    cw = (W - 2 * pad - gapx * (cols - 1)) / cols
    ch = 118
    H = y0 + rows * ch + (rows - 1) * gapy + (44 if note else 20)
    body = [svg_open(W, H, title), head]
    pos = []
    for i in range(n):
        r = i // cols
        c = i % cols if r % 2 == 0 else (cols - 1 - i % cols)
        x = pad + c * (cw + gapx)
        y = y0 + r * (ch + gapy)
        pos.append((x, y, c, r))
    for i, s in enumerate(steps):
        x, y, c, r = pos[i]
        f, st, tc = PAL[s['color']]
        body.append(rrect(x, y, cw, ch, f, st, rx=12, sw=2))
        body.append(f'<circle cx="{x+20}" cy="{y+22}" r="13" fill="{st}"/>')
        body.append(txt(x + 20, y + 27, str(i + 1), 13, '#fff', '700', 'middle'))
        cy = y + 26
        for ln in wrap_px(s['head'], cw - 44, 14):
            body.append(txt(x + 40, cy, ln, 13.8, tc, '700')); cy += 17
        cy += 3
        for ln in wrap_px(s['body'], cw - 20, 12.3):
            body.append(txt(x + 12, cy, ln, 12.1, '#334155')); cy += 15
        # arrow to next
        if i < n - 1:
            nx, ny, nc, nr = pos[i + 1]
            if nr == r:
                if nc > c:
                    body.append(arrow(x + cw + 4, y + ch / 2, x + cw + gapx - 4, y + ch / 2, LINE))
                else:
                    body.append(arrow(x - 4, y + ch / 2, x - gapx + 4, y + ch / 2, LINE))
            else:  # drop down
                body.append(arrow(x + cw / 2, y + ch + 4, x + cw / 2, y + ch + gapy - 4, LINE, w=3))
    if note:
        body.append(txt(W / 2, H - 16, note, 12.6, SUB, 'normal', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- panorama
def fig_panorama(title, subtitle, bands, footer, W=980):
    """bands: list of rows. Each row is dict:
        {'full': {...box}} single full-width box, or
        {'cols': [box,...]}  a row of equal columns.
       box: {head, color, bullets(list) or text}"""
    head, y0 = header(W, title, subtitle)
    pad, gy, gx = 30, 16, 16
    # measure
    def box_h(b, w):
        h = 14
        h += len(wrap_px(b['head'], w - 24, 14.5)) * 20
        for t in b.get('bullets', []):
            h += len(wrap_px(t, w - 30, 12)) * 15 + 3
        if b.get('text'):
            h += len(wrap_px(b['text'], w - 24, 12)) * 16
        return h + 14
    rowh = []
    for row in bands:
        if 'full' in row:
            rowh.append(box_h(row['full'], W - 2 * pad))
        else:
            cols = row['cols']
            cw = (W - 2 * pad - gx * (len(cols) - 1)) / len(cols)
            rowh.append(max(box_h(b, cw) for b in cols))
    H = y0 + sum(rowh) + gy * (len(bands)) + (footer and 34 or 10)
    body = [svg_open(W, H, title), head]
    y = y0
    def draw_box(x, yy, w, h, b):
        f, st, tc = PAL[b['color']]
        o = [rrect(x, yy, w, h, f, st, rx=11, sw=1.8)]
        cy = yy + 22
        for ln in wrap_px(b['head'], w - 24, 14.5):
            o.append(txt(x + 12, cy, ln, 14, tc, '700')); cy += 19
        cy += 2
        if b.get('text'):
            for ln in wrap_px(b['text'], w - 24, 12):
                o.append(txt(x + 12, cy, ln, 12, '#334155')); cy += 16
        for t in b.get('bullets', []):
            lns = wrap_px(t, w - 30, 12)
            o.append(f'<circle cx="{x+15}" cy="{cy-4}" r="1.8" fill="{st}"/>')
            for ln in lns:
                o.append(txt(x + 22, cy, ln, 12, '#334155')); cy += 15
            cy += 3
        return ''.join(o)
    for i, row in enumerate(bands):
        if 'full' in row:
            body.append(draw_box(pad, y, W - 2 * pad, rowh[i], row['full']))
        else:
            cols = row['cols']
            cw = (W - 2 * pad - gx * (len(cols) - 1)) / len(cols)
            x = pad
            for b in cols:
                body.append(draw_box(x, y, cw, rowh[i], b))
                x += cw + gx
        y += rowh[i] + gy
    if footer:
        body.append(rrect(pad, H - 30, W - 2 * pad, 22, '#f1f5f9', '#e2e8f0', rx=8, sw=1))
        body.append(txt(W / 2, H - 14, footer, 12.3, '#475569', '600', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- flywheel (circle)
def fig_flywheel(title, subtitle, center, nodes, edge_labels, footer, W=940):
    head, y0 = header(W, title, subtitle)
    H = y0 + 560
    cx, cy = W / 2, y0 + 250
    R = 210
    body = [svg_open(W, H, title), head]
    # center
    body.append(f'<circle cx="{cx}" cy="{cy}" r="58" fill="#eef2ff" stroke="#6366f1" stroke-width="3"/>')
    body.append(txt(cx, cy - 4, center[0], 17, '#4338ca', '700', 'middle'))
    body.append(txt(cx, cy + 16, center[1], 12, '#475569', 'normal', 'middle'))
    # four nodes at top,right,bottom,left
    ang = [-90, 0, 90, 180]
    npos = []
    for a in ang:
        rad = math.radians(a)
        npos.append((cx + R * math.cos(rad), cy + R * math.sin(rad)))
    bw, bh = 250, 96
    # curved arrows between nodes (clockwise): top->right->bottom->left->top
    order = [0, 1, 2, 3, 0]
    for i in range(4):
        (x1, y1), (x2, y2) = npos[order[i]], npos[order[i + 1]]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # control point pushed outward
        ox, oy = mx - cx, my - cy
        d = math.hypot(ox, oy) or 1
        ctrlx, ctrly = cx + ox / d * (R + 70), cy + oy / d * (R + 70)
        # arrow along quad curve, approximate direction at end
        body.append(f'<path d="M {x1:.1f} {y1:.1f} Q {ctrlx:.1f} {ctrly:.1f} {x2:.1f} {y2:.1f}" '
                    f'fill="none" stroke="#cbd5e1" stroke-width="3"/>')
        # small arrowhead near end
        ex, ey = x2, y2
        body.append(f'<circle cx="{ctrlx:.1f}" cy="{ctrly:.1f}" r="0"/>')
        body.append(txt(ctrlx, ctrly + 4, edge_labels[i], 11.5, SUB, 'normal', 'middle'))
    for i, node in enumerate(nodes):
        x, y = npos[i]
        f, st, tc = PAL[node['color']]
        body.append(rrect(x - bw / 2, y - bh / 2, bw, bh, f, st, rx=12, sw=2.4))
        cyy = y - bh / 2 + 24
        for ln in wrap_px(node['head'], bw - 24, 14.5):
            body.append(txt(x, cyy, ln, 14.3, tc, '700', 'middle')); cyy += 18
        cyy += 2
        for ln in wrap_px(node['sub'], bw - 20, 12):
            body.append(txt(x, cyy, ln, 12, '#334155', 'normal', 'middle')); cyy += 15
    if footer:
        body.append(rrect(40, H - 34, W - 80, 24, '#f1f5f9', '#e2e8f0', rx=8, sw=1))
        body.append(txt(W / 2, H - 17, footer, 12, '#475569', '600', 'middle'))
    body.append('</svg>')
    return ''.join(body)

# ---------------------------------------------------------------- data flow (vertical, branches)
def fig_dataflow(title, subtitle, footer, W=960):
    head, y0 = header(W, title, subtitle)
    H = y0 + 640
    body = [svg_open(W, H, title), head]
    cx = W / 2
    def node(x, y, w, h, head_, sub, color):
        f, st, tc = PAL[color]
        o = [rrect(x - w / 2, y, w, h, f, st, rx=11, sw=2)]
        cyy = y + 24
        for ln in wrap_px(head_, w - 20, 13.5):
            o.append(txt(x, cyy, ln, 13.3, tc, '700', 'middle')); cyy += 17
        for ln in wrap_px(sub, w - 16, 11.8):
            o.append(txt(x, cyy, ln, 11.6, '#334155', 'normal', 'middle')); cyy += 14
        return ''.join(o)
    y = y0
    body.append(node(cx, y, 320, 56, 'Agent executes task', 'produces execution trace + final output', 'blue'));
    body.append(arrow(cx, y + 56, cx, y + 84, LINE, w=3)); y += 84
    body.append(node(cx, y, 360, 60, 'Evaluation: scoring + diagnostic attribution', 'identify good experience & locate problems', 'red'))
    ytop = y + 60
    y += 60
    # two branches
    lx, rx = cx - 250, cx + 250
    body.append(arrow(cx - 60, ytop, lx, ytop + 40, PAL['green'][1], w=2.6))
    body.append(txt(cx - 190, ytop + 20, 'good experience', 11.5, '#047857', '700', 'middle'))
    body.append(arrow(cx + 60, ytop, rx, ytop + 40, PAL['amber'][1], w=2.6))
    body.append(txt(cx + 190, ytop + 20, 'problem / gap', 11.5, '#b45309', '700', 'middle'))
    by = ytop + 40
    body.append(node(lx, by, 300, 62, 'Memory: write + promote', 'precipitate into reusable experience / Skill', 'green'))
    body.append(node(rx, by, 300, 62, 'Deployment: generate fix', 'three-way signal aggregation -> N candidates', 'amber'))
    body.append(arrow(lx, by + 62, lx, by + 92, LINE, w=2.6))
    body.append(arrow(rx, by + 62, rx, by + 92, LINE, w=2.6))
    by2 = by + 92
    body.append(node(lx, by2, 300, 56, 'Agent performs better', 'experience recalled next round', 'blue'))
    body.append(node(rx, by2, 300, 74, 'Control: review - canary - full', '5 gates + human confirm + rollback', 'purple'))
    body.append(arrow(rx, by2 + 74, rx, by2 + 104, LINE, w=2.6))
    body.append(txt(rx + 8, by2 + 92, 'Skill/Prompt update takes effect', 11.3, SUB, 'normal', 'start'))
    by3 = by2 + 104
    body.append(node(rx, by3, 300, 52, 'Agent performs better', 'update in effect', 'blue'))
    # merge to next-round loop
    body.append(arrow(lx, by2 + 56, lx, by3 + 40, LINE, w=2.4))
    myy = by3 + 40
    body.append(node(cx, myy, 360, 54, 'Next-round evaluation is higher', 'lower failure rate -> enter the next loop', 'red'))
    # loop arrow up the right side
    body.append(f'<path d="M {cx+180} {myy+27} Q {W-30} {myy+27} {W-30} {(ytop+30):.1f} Q {W-30} {y0+8} {cx+180} {y0+8}" fill="none" stroke="#cbd5e1" stroke-width="2.4" stroke-dasharray="7 5"/>')
    body.append(arrow(cx + 181, y0 + 8, cx + 160, y0 + 8, '#cbd5e1', w=2.4))
    body.append(txt(W - 20, (myy + ytop) / 2, 'loop', 12, SUB, 'normal', 'middle'))
    if footer:
        body.append(txt(cx, H - 16, footer, 12.6, SUB, 'normal', 'middle'))
    body.append('</svg>')
    return ''.join(body)
