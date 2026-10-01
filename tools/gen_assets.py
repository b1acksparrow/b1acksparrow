#!/usr/bin/env python3
"""Generate the profile assets (banner, typing line, terminal, research card, divider).

Text in the SVGs is converted to outlines, so the look does not depend on fonts installed on the viewer's machine.
Run: python3 tools/gen_assets.py  (writes assets/ next to this folder)
"""
import os
import random
from xml.sax.saxutils import escape
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, 'assets')
LOGO = os.path.join(ROOT, "source", "logo.png")   # original logo, kept locally (not in the repository)
FC = '/usr/share/fonts/truetype/firacode/FiraCode-{}.ttf'
DJ = '/usr/share/fonts/truetype/dejavu/{}.ttf'
DROID = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'

RED = '#ff2b2b'
RED_DEEP = '#b80f0f'
RED_DIM = '#5a0d0d'
INK = '#0b0b0b'
TEXT = '#d6d6d6'
MUTED = '#8a8a8a'


class Font:
    def __init__(self, path, fallbacks=()):
        self.tt = TTFont(path, fontNumber=0)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt['head'].unitsPerEm
        self.fallbacks = list(fallbacks)

    def lookup(self, ch):
        for f in [self] + self.fallbacks:
            if ord(ch) in f.cmap:
                return f, f.cmap[ord(ch)]
        return self, self.cmap[ord('?')]

    def advance(self, ch, size):
        f, g = self.lookup(ch)
        return f.gs[g].width * size / f.upm


def outline(font, text, size, x, y, cell=None, wide=()):
    """SVG path data for text starting at baseline (x, y); returns (d, end_x, per-char x positions)."""
    parts, xs, cx = [], [], x
    for ch in text:
        xs.append(cx)
        f, g = font.lookup(ch)
        s = size / f.upm
        adv = (cell * (2 if ch in wide else 1)) if cell else f.gs[g].width * s
        glyph_w = f.gs[g].width * s
        dx = cx + (adv - glyph_w) / 2 if cell else cx   # centre fallback glyphs in their cells
        pen = SVGPathPen(f.gs, ntos=lambda v: ('%.1f' % v).rstrip('0').rstrip('.'))
        f.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, dx, y)))
        cmd = pen.getCommands()
        if cmd:
            parts.append(cmd)
        cx += adv
    xs.append(cx)
    return ' '.join(parts), cx, xs


def r(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


# ----------------------------------------------------------------------------------------------- banner
def banner(path_out, W=1500, H=500):
    random.seed(7)
    canvas = Image.new('RGB', (W, H), (4, 2, 2))

    # faint binary rain on the right, echoing the logo
    rain = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(rain)
    small = ImageFont.truetype(FC.format('Regular'), 15)
    for col in range(760, W, 26):
        y = random.randint(-200, 0)
        while y < H:
            bits = ''.join(random.choice('01') for _ in range(8))
            dr.text((col, y), '\n'.join(bits), font=small, fill=random.randint(18, 60), spacing=2)
            y += random.randint(190, 320)
    red_layer = Image.new('RGB', (W, H), (190, 20, 20))
    canvas.paste(red_layer, (0, 0), rain)

    # hex mesh glow behind the text block
    mesh = Image.new('L', (W, H), 0)
    dm = ImageDraw.Draw(mesh)
    s = 9
    for row in range(0, H // int(s * 1.5) + 2):
        for col in range(0, W // int(s * 1.732) + 2):
            cx = col * s * 1.732 + (s * 0.866 if row % 2 else 0)
            cy = row * s * 1.5
            if cx < 700:
                continue
            d = ((cx - 1150) / 520) ** 2 + ((cy - 250) / 300) ** 2
            a = int(max(0, 1 - d) * 26)
            if a:
                pts = [(cx + s * 0.95 * dx, cy + s * 0.95 * dy) for dx, dy in
                       ((0, -1), (0.866, -0.5), (0.866, 0.5), (0, 1), (-0.866, 0.5), (-0.866, -0.5))]
                dm.polygon(pts, outline=a)
    canvas.paste(Image.new('RGB', (W, H), (255, 40, 40)), (0, 0), mesh)

    # the logo, faded into the dark on its right edge
    logo = Image.open(LOGO).convert('RGB')
    lw = int(logo.width * H / logo.height)
    logo = logo.resize((lw, H), Image.LANCZOS)
    mask = Image.new('L', (lw, H), 255)
    md = ImageDraw.Draw(mask)
    fade0, fade1 = int(lw * 0.62), lw
    for x in range(fade0, fade1):
        md.line([(x, 0), (x, H)], fill=int(255 * (1 - (x - fade0) / (fade1 - fade0)) ** 1.6))
    canvas.paste(logo, (-40, 0), mask)

    # text block, measured so that it ends 70 px before the right edge
    name = 'B1ACKSPARROW'
    name_font = ImageFont.truetype(FC.format('Bold'), 82)
    sub_font = ImageFont.truetype(DJ.format('DejaVuSans'), 28)
    role_font = ImageFont.truetype(FC.format('SemiBold'), 22)
    tag_font = ImageFont.truetype(FC.format('Regular'), 17)
    foot_font = ImageFont.truetype(FC.format('Medium'), 16)
    motto_font = ImageFont.truetype(FC.format('Light'), 16)
    sub = 'Sergey Mkrtchyan  ·  Սերգեյ Մկրտչյան'
    role = 'PENETRATION TESTER  //  SECURITY RESEARCHER'
    tag = 'post-quantum migration · ai security · verifiable audit'
    foot, motto = '[ yerevan, armenia ]', 'trust nothing · verify everything'
    block_w = max(name_font.getlength(name), sub_font.getlength(sub), role_font.getlength(role),
                  tag_font.getlength(tag), foot_font.getlength(foot) + 40 + motto_font.getlength(motto))
    x0 = int(W - 70 - block_w)

    glow = Image.new('RGB', (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).text((x0, 108), name, font=name_font, fill=(255, 30, 30))
    canvas = ImageChops.add(canvas, glow.filter(ImageFilter.GaussianBlur(14)))

    d = ImageDraw.Draw(canvas)
    d.text((x0 + 3, 111), name, font=name_font, fill=(70, 0, 0))          # offset shadow
    d.text((x0, 108), name, font=name_font, fill=(255, 43, 43))
    d.text((x0 + 2, 210), sub, font=sub_font, fill=(232, 232, 232))
    d.rectangle([x0 + 2, 264, x0 + block_w - 10, 266], fill=(200, 20, 20))
    d.rectangle([x0 + block_w - 10, 260, x0 + block_w, 270], fill=(255, 43, 43))
    d.text((x0 + 2, 290), role, font=role_font, fill=(245, 245, 245))
    d.text((x0 + 2, 330), tag, font=tag_font, fill=(255, 92, 92))
    d.text((x0 + 2, 408), foot, font=foot_font, fill=(140, 140, 140))
    d.text((x0 + block_w - motto_font.getlength(motto), 408), motto, font=motto_font, fill=(160, 64, 64))

    # scanlines and vignette
    over = Image.new('L', (W, H), 0)
    do = ImageDraw.Draw(over)
    for y in range(0, H, 4):
        do.line([(0, y), (W, y)], fill=34)
    canvas.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), over)
    vig = Image.new('L', (W, H), 0)
    dv = ImageDraw.Draw(vig)
    for i in range(60):
        dv.rectangle([i, i, W - 1 - i, H - 1 - i], outline=int(150 * (1 - i / 60) ** 2))
    canvas.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), vig)
    canvas.save(path_out, 'JPEG', quality=90, optimize=True, progressive=True)


def avatar(path_out, size=800):
    logo = Image.open(LOGO).convert('RGB')
    cx, cy, half = 836, 455, 430
    logo.crop((cx - half, cy - half, cx + half, cy + half)).resize((size, size), Image.LANCZOS).save(path_out)


# ----------------------------------------------------------------------------------------------- typing line
def typing(path_out, lines, W=900, H=56, size=27):
    font = Font(FC.format('Medium'))
    cell = font.advance('M', size)
    type_t, del_t, hold, gap = 0.065, 0.028, 1.7, 0.35
    spans = []
    t = 0.0
    for ln in lines:
        n = len(ln)
        spans.append((t, n))
        t += n * type_t + hold + n * del_t + gap
    total = t
    base = H / 2 + size * 0.36
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
           '<title>' + escape(' · '.join(lines)) + '</title>',
           '<defs><filter id="g" x="-10%" y="-60%" width="120%" height="220%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    for i, (ln, (t0, n)) in enumerate(zip(lines, spans)):
        width = n * cell
        x = (W - width) / 2
        d, _, _ = outline(font, ln, size, x, base, cell=cell)
        # discrete keyframes: type in, hold, delete, stay hidden
        times, widths = [0.0], [0.0]
        for k in range(1, n + 1):
            times.append(t0 + k * type_t); widths.append(k * cell)
        t_del = t0 + n * type_t + hold
        for k in range(1, n + 1):
            times.append(t_del + k * del_t); widths.append((n - k) * cell)
        times.append(total); widths.append(0.0)
        kt = ';'.join(r(min(1, tt / total)) for tt in times)
        vals = ';'.join(r(w) for w in widths)
        xs = ';'.join(r(x + w) for w in widths)
        out.append(f'<clipPath id="c{i}"><rect x="{r(x)}" y="0" height="{H}" width="0">'
                   f'<animate attributeName="width" values="{vals}" keyTimes="{kt}" dur="{r(total)}s" '
                   f'calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>')
        out.append(f'<path d="{d}" fill="{RED}" filter="url(#g)" clip-path="url(#c{i})"/>')
        vis = ';'.join('1' if (t0 <= tt < times[-2] and tt < total) else '0' for tt in times)
        out.append(f'<rect y="{r(base - size * 0.78)}" width="{r(cell * 0.55)}" height="{r(size * 0.95)}" fill="{RED}" opacity="0">'
                   f'<animate attributeName="x" values="{xs}" keyTimes="{kt}" dur="{r(total)}s" calcMode="discrete" repeatCount="indefinite"/>'
                   f'<animate attributeName="opacity" values="{vis}" keyTimes="{kt}" dur="{r(total)}s" calcMode="discrete" repeatCount="indefinite"/>'
                   '</rect>')
    out.append('</svg>')
    open(path_out, 'w').write('\n'.join(out))


# ----------------------------------------------------------------------------------------------- terminal
def terminal(path_out, script, W=900, size=15, lh=23):
    mono = Font(FC.format('Regular'), fallbacks=[Font(DJ.format('DejaVuSansMono')), Font(DROID)])
    bold = Font(FC.format('Bold'), fallbacks=[Font(DJ.format('DejaVuSansMono-Bold')), Font(DROID)])
    cell = mono.advance('M', size)
    pad_x, top = 26, 58
    rows = sum(len(block) for block in script)
    H = top + rows * lh + 34
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
           '<title>Terminal: whoami, focus areas and location of b1acksparrow</title>',
           '<defs><linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c0505"/>'
           '<stop offset="1" stop-color="#120303"/></linearGradient>'
           '<filter id="gl" x="-5%" y="-50%" width="110%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
           '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".35"/></pattern>'
           '</defs>',
           f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{INK}" stroke="#3b0a0a" stroke-width="2"/>',
           f'<path d="M1 13a12 12 0 0 1 12-12h{W - 26}a12 12 0 0 1 12 12v25H1z" fill="url(#bar)"/>',
           f'<line x1="1" y1="38" x2="{W - 1}" y2="38" stroke="#3b0a0a" stroke-width="1.5"/>']
    for i, c in enumerate(('#ff3b30', '#8f1d1d', '#4a1010')):
        out.append(f'<circle cx="{24 + i * 22}" cy="20" r="6.5" fill="{c}"/>')
    tdsc, end, _ = outline(Font(FC.format('Medium')), 'b1acksparrow@kali: ~', 13, 0, 0)
    tw = end
    out.append(f'<path transform="translate({r((W - tw) / 2)},24.5)" d="{tdsc}" fill="{MUTED}"/>')

    t = 0.5
    row = 0
    char_t = 0.055
    for block in script:
        for kind, text in block:
            y = top + row * lh
            if kind == 'prompt':      # two-line Kali prompt, first line
                d1, _, _ = outline(bold, text, size, pad_x, y, cell=cell, wide=('㉿',))
                out.append(f'<path d="{d1}" fill="{RED}" opacity="0">'
                           f'<set attributeName="opacity" to="1" begin="{r(t)}s" fill="freeze"/></path>')
                t += 0.15
            elif kind == 'cmd':       # second prompt line with a typed command
                lead = '└─$ '
                dl, x1, _ = outline(bold, lead, size, pad_x, y, cell=cell)
                out.append(f'<path d="{dl}" fill="{RED}" opacity="0">'
                           f'<set attributeName="opacity" to="1" begin="{r(t)}s" fill="freeze"/></path>')
                if text:
                    dc, x2, _ = outline(bold, text, size, x1, y, cell=cell)
                    n = len(text)
                    cid = f't{row}'
                    out.append(f'<clipPath id="{cid}"><rect x="{r(x1)}" y="{y - size}" height="{lh}" width="0">'
                               f'<animate attributeName="width" from="0" to="{r(n * cell)}" begin="{r(t + 0.25)}s" '
                               f'dur="{r(n * char_t)}s" calcMode="discrete" values="'
                               + ';'.join(r(k * cell) for k in range(n + 1)) + f'" fill="freeze"/></rect></clipPath>')
                    out.append(f'<path d="{dc}" fill="#f2f2f2" clip-path="url(#{cid})"/>')
                    t += 0.25 + n * char_t + 0.35
                else:                 # final idle prompt with a blinking cursor
                    out.append(f'<rect x="{r(x1 + 1)}" y="{y - size + 2}" width="{r(cell * 0.6)}" height="{size + 2}" fill="{RED}" opacity="0">'
                               f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.05s" '
                               f'begin="{r(t)}s" repeatCount="indefinite"/></rect>')
            else:                     # output line: list of (text, colour) runs
                x = pad_x
                for run, colour in text:
                    dd, x, _ = outline(mono, run, size, x, y, cell=cell)
                    if dd:
                        out.append(f'<path d="{dd}" fill="{colour}" opacity="0"'
                                   + (' filter="url(#gl)"' if colour == RED else '')
                                   + f'><set attributeName="opacity" to="1" begin="{r(t)}s" fill="freeze"/></path>')
                t += 0.09
            row += 1
        t += 0.25
    out.append(f'<rect x="1" y="39" width="{W - 2}" height="{H - 41}" rx="0" fill="url(#scan)" pointer-events="none"/>')
    out.append('</svg>')
    open(path_out, 'w').write('\n'.join(out))


# ----------------------------------------------------------------------------------------------- research card
def research(path_out, W=900, H=250):
    bold = Font(FC.format('Bold'))
    reg = Font(FC.format('Regular'), fallbacks=[Font(DJ.format('DejaVuSansMono'))])
    med = Font(FC.format('Medium'))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
           '<title>Auditable by Design: secure AI-assisted migration to post-quantum cryptography</title>',
           '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#140303"/>'
           f'<stop offset=".55" stop-color="{INK}"/><stop offset="1" stop-color="#0b0b0b"/></linearGradient>'
           '<radialGradient id="glow" cx=".82" cy=".45" r=".45"><stop offset="0" stop-color="#ff2b2b" stop-opacity=".22"/>'
           '<stop offset="1" stop-color="#ff2b2b" stop-opacity="0"/></radialGradient></defs>',
           f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="url(#bg)" stroke="#3b0a0a" stroke-width="2"/>',
           f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="url(#glow)"/>',
           f'<rect x="1" y="22" width="5" height="{H - 44}" fill="{RED}"/>']
    # lattice motif (a nod to lattice-based ML-KEM / ML-DSA): points, a basis, and a highlighted short vector
    ox, oy, b1, b2 = 700, 205, (38, -14), (12, -36)
    for i in range(-3, 6):
        for j in range(-1, 6):
            px, py = ox + i * b1[0] + j * b2[0], oy + i * b1[1] + j * b2[1]
            if 600 < px < W - 20 and 20 < py < H - 20:
                out.append(f'<circle cx="{r(px)}" cy="{r(py)}" r="2.2" fill="#ff2b2b" opacity=".35"/>')
    p0 = (ox + 2 * b1[0] + 1 * b2[0], oy + 2 * b1[1] + 1 * b2[1])
    for (vx, vy), op in ((b1, .55), (b2, .55), ((b1[0] - b2[0], b1[1] - b2[1]), 1)):
        out.append(f'<line x1="{r(p0[0])}" y1="{r(p0[1])}" x2="{r(p0[0] + vx)}" y2="{r(p0[1] + vy)}" '
                   f'stroke="#ff2b2b" stroke-width="2" opacity="{op}"/>')
    out.append(f'<circle cx="{r(p0[0])}" cy="{r(p0[1])}" r="4" fill="#ff2b2b"><animate attributeName="r" '
               'values="4;6.5;4" dur="2.4s" repeatCount="indefinite"/></circle>')

    d, _, _ = outline(med, 'FEATURED RESEARCH', 12.5, 30, 42)
    out.append(f'<path d="{d}" fill="{MUTED}"/>')
    d, _, _ = outline(bold, 'AUDITABLE BY DESIGN', 31, 30, 82)
    out.append(f'<path d="{d}" fill="{RED}"/>')
    d, _, _ = outline(reg, 'Secure AI-assisted migration to post-quantum cryptography', 15.5, 30, 110)
    out.append(f'<path d="{d}" fill="#e8e8e8"/>')
    bullets = ['policy gate · one-time exact-action approval · compare-and-set',
               'ML-DSA-signed, hash-chained, witnessed audit evidence',
               '13 verification obligations · zero-knowledge predicate (RISC Zero)']
    for k, b in enumerate(bullets):
        y = 142 + k * 23
        d, _, _ = outline(reg, '▸', 14, 30, y)
        out.append(f'<path d="{d}" fill="{RED}"/>')
        d, _, _ = outline(reg, b, 14, 50, y)
        out.append(f'<path d="{d}" fill="{TEXT}"/>')
    x = 30
    for tag in ('Python', 'Rust', 'RISC Zero', 'liboqs', 'ML-KEM', 'ML-DSA'):
        d, end, _ = outline(med, tag, 12, x + 10, 226)
        w = end - x + 10
        out.append(f'<rect x="{r(x)}" y="210" width="{r(w)}" height="23" rx="11.5" fill="none" stroke="{RED_DEEP}" stroke-width="1.3"/>')
        out.append(f'<path d="{d}" fill="#f0f0f0"/>')
        x += w + 8
    d, end, _ = outline(med, 'open repository →', 13, 0, 0)
    out.append(f'<path transform="translate({r(W - 30 - end)},226)" d="{d}" fill="{RED}"/>')
    out.append('</svg>')
    open(path_out, 'w').write('\n'.join(out))


# ----------------------------------------------------------------------------------------------- divider
def divider(path_out, W=900, H=18):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
           '<title>divider</title>',
           '<defs><linearGradient id="l" x1="0" x2="1"><stop offset="0" stop-color="#ff2b2b" stop-opacity="0"/>'
           '<stop offset=".5" stop-color="#ff2b2b"/><stop offset="1" stop-color="#ff2b2b" stop-opacity="0"/></linearGradient></defs>',
           f'<rect x="0" y="{H / 2 - 0.75}" width="{W}" height="1.5" fill="url(#l)"/>']
    for k, dx in enumerate((-22, 0, 22)):
        cx, cy, s = W / 2 + dx, H / 2, 5.5 if dx == 0 else 4
        pts = ' '.join(f'{r(cx + s * a)},{r(cy + s * b)}' for a, b in
                       ((0, -1), (.866, -.5), (.866, .5), (0, 1), (-.866, .5), (-.866, -.5)))
        out.append(f'<polygon points="{pts}" fill="{INK}" stroke="#ff2b2b" stroke-width="1.5">'
                   f'<animate attributeName="opacity" values="1;.35;1" dur="2.4s" begin="{k * 0.4}s" repeatCount="indefinite"/></polygon>')
    out.append('</svg>')
    open(path_out, 'w').write('\n'.join(out))


if __name__ == '__main__':
    os.makedirs(ASSETS, exist_ok=True)
    banner(os.path.join(ASSETS, 'banner.jpg'))
    avatar(os.path.join(ROOT, 'source', 'avatar.png'))
    typing(os.path.join(ASSETS, 'typing.svg'),
           ['Penetration Tester', 'Security Researcher', 'Post-Quantum Migration',
            'AI & LLM Security', 'Trust nothing. Verify everything.'])
    P = ('prompt', '┌──(b1acksparrow㉿kali)-[~]')
    terminal(os.path.join(ASSETS, 'terminal.svg'), [
        [P, ('cmd', 'whoami'),
         ('out', [('Sergey Mkrtchyan', '#f2f2f2'), (' — independent security researcher & penetration tester', TEXT)])],
        [P, ('cmd', 'cat ~/focus.txt'),
         ('out', [('[+] ', RED), ('offensive security ', '#f2f2f2'), ('...... ', RED_DIM), ('web · api · network', TEXT)]),
         ('out', [('[+] ', RED), ('post-quantum migration ', '#f2f2f2'), ('.. ', RED_DIM), ('ML-KEM · ML-DSA · CNSA 2.0', TEXT)]),
         ('out', [('[+] ', RED), ('ai security ', '#f2f2f2'), ('............. ', RED_DIM), ('LLM agents · prompt-injection containment', TEXT)]),
         ('out', [('[+] ', RED), ('verifiable audit ', '#f2f2f2'), ('........ ', RED_DIM), ('hash chains · witnesses · zero-knowledge', TEXT)])],
        [P, ('cmd', 'cat ~/location'), ('out', [('Yerevan, Armenia', TEXT)])],
        [P, ('cmd', '')],
    ])
    research(os.path.join(ASSETS, 'research.svg'))
    divider(os.path.join(ASSETS, 'divider.svg'))
    print('assets written to', ASSETS)
