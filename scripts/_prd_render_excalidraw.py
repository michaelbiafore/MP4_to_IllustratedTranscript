#!/usr/bin/env python
"""Render an entire Excalidraw scene to a single SVG (no slicing). Faithful
renderer: rects, arrows, lines, text with excalidraw highlights. Output is an
HTML wrapper rasterized to PNG by msedge --headless --screenshot."""
import json, sys, os, html, math

SRC, OUT_HTML = sys.argv[1], sys.argv[2]
d = json.load(open(SRC, encoding='utf-8'))
files = d.get('files', {})
els = [e for e in d['elements'] if not e.get('isDeleted')]

def esc(s): return html.escape(str(s), quote=True)

FONT = {
    1: '"Segoe Print","Bradley Hand","Comic Sans MS",cursive',
    2: '"Segoe UI",Helvetica,Arial,sans-serif',
    3: '"Cascadia Code",Consolas,monospace',
    5: '"Segoe Print","Bradley Hand","Comic Sans MS",cursive',
    6: '"Segoe UI",Helvetica,Arial,sans-serif',
    7: '"Cascadia Code",Consolas,monospace',
}

PAD = 32
x0 = min(e['x'] for e in els) - PAD
y0 = min(e['y'] for e in els) - PAD
x1 = max(e['x'] + e.get('width', 0) for e in els) + PAD
y1 = max(e['y'] + e.get('height', 0) for e in els) + PAD
W, H = x1 - x0, y1 - y0

def render_element(e):
    t = e['type']
    op = e.get('opacity', 100) / 100.0
    x, y = e['x'], e['y']
    w, h = e.get('width', 0), e.get('height', 0)
    stroke = e.get('strokeColor', '#1e1e1e')
    sw = e.get('strokeWidth', 1)
    bg = e.get('backgroundColor', 'transparent')
    ang = e.get('angle', 0) or 0
    cx, cy = x + w / 2, y + h / 2
    xf = '' if abs(ang) < 1e-6 else f' transform="rotate({math.degrees(ang):.3f} {cx:.2f} {cy:.2f})"'
    out = []
    if t == 'image':
        f = files.get(e.get('fileId'))
        if not f: return ''
        out.append(f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                   f'opacity="{op:.2f}" preserveAspectRatio="none" href="{f["dataURL"]}"{xf}/>')
    elif t == 'rectangle':
        rx = min(32, min(abs(w), abs(h)) / 4) if e.get('roundness') else 0
        fill = bg if bg and bg != 'transparent' else 'none'
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx:.1f}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op:.2f}"{xf}/>')
    elif t in ('line', 'freedraw'):
        pts = e.get('points', [])
        if len(pts) < 2: return ''
        dpts = ' '.join(f'{x+px:.2f},{y+py:.2f}' for px, py in pts)
        fill = bg if (t == 'freedraw' and bg and bg != 'transparent') else 'none'
        out.append(f'<polyline points="{dpts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round" opacity="{op:.2f}"{xf}/>')
    elif t == 'arrow':
        pts = e.get('points', [])
        if len(pts) < 2: return ''
        dpts = ' '.join(f'{x+px:.2f},{y+py:.2f}' for px, py in pts)
        mk = ' marker-end="url(#arrowhead)"' if e.get('endArrowhead') else ''
        mks = ' marker-start="url(#arrowtail)"' if e.get('startArrowhead') else ''
        out.append(f'<polyline points="{dpts}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round" opacity="{op:.2f}"{mk}{mks}{xf}/>')
    elif t == 'text':
        fs = e.get('fontSize', 20)
        lh = e.get('lineHeight', 1.25)
        fam = FONT.get(e.get('fontFamily', 5), FONT[5])
        align = e.get('textAlign', 'left')
        anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}.get(align, 'start')
        tx = {'left': x, 'center': x + w / 2, 'right': x + w}.get(align, x)
        if bg and bg != 'transparent':
            out.append(f'<rect x="{x-3:.2f}" y="{y:.2f}" width="{w+6:.2f}" height="{h:.2f}" '
                       f'fill="{bg}" opacity="{op:.2f}"/>')
        spans = []
        for i, ln in enumerate(e.get('text', '').split('\n')):
            by = y + i * lh * fs + fs * 0.82
            spans.append(f'<tspan x="{tx:.2f}" y="{by:.2f}">{esc(ln) if ln else "&#160;"}</tspan>')
        out.append(f'<text font-family={chr(34)}{fam}{chr(34)} font-size="{fs}" fill="{stroke}" '
                   f'text-anchor="{anchor}" opacity="{op:.2f}"{xf}>{"".join(spans)}</text>')
    return '\n'.join(out)

defs = ('<defs>'
        '<marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L8,3 L0,6 Z" fill="#1e1e1e"/></marker>'
        '<marker id="arrowtail" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto" markerUnits="strokeWidth">'
        '<path d="M8,0 L0,3 L8,6 Z" fill="#1e1e1e"/></marker>'
        '</defs>')
body = '\n'.join(s for s in (render_element(e) for e in els) if s.strip())
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
       f'viewBox="{x0:.2f} {y0:.2f} {W:.2f} {H:.2f}">'
       f'{defs}<rect x="{x0:.2f}" y="{y0:.2f}" width="{W:.2f}" height="{H:.2f}" fill="#ffffff"/>'
       f'{body}</svg>')
page = (f'<!doctype html><html><head><meta charset="utf-8">'
        f'<style>html,body{{margin:0;padding:0;background:#fff}}svg{{display:block}}</style></head>'
        f'<body>{svg}</body></html>')
open(OUT_HTML, 'w', encoding='utf-8').write(page)
print(f"wrote {OUT_HTML}  {W:.0f}x{H:.0f}")
