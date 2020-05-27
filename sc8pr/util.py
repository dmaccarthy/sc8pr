# Copyright 2015-2020 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "sc8pr".
#
# "sc8pr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr".  If not, see <http://www.gnu.org/licenses/>.


import sys, pygame
from random import randint
from traceback import format_exc
from zipfile import ZipFile
from pathlib import Path
from sc8pr.geom import sigma, delta

scale = pygame.transform.smoothscale

def nothing(*args): pass

# from pygame.constants import K_LSHIFT, K_RSHIFT, K_LALT, K_RALT, K_LCTRL, K_RCTRL 

def modKeys():
    key = pygame.key.get_pressed()
    m = 0
    if key[pygame.K_LALT] or key[pygame.K_RALT]: m += 1
    if key[pygame.K_LCTRL] or key[pygame.K_RCTRL]: m += 2
    if key[pygame.K_LSHIFT] or key[pygame.K_RSHIFT]: m += 4
    return m

def resolvePath(rel, start=__file__, isDir=False):
    "Return an absolute path relative to a starting file or folder"
    p = Path(start)
    if not isDir: p = p.parent
    return str(p.joinpath(rel).resolve())

def _rgba(*args):
    "Generate a sequence of pygame.Color instances"
    for c in args:
        t = type(c)
        if t is bool: # Random color
            c = [randint(0,255) for i in range(4 if c else 3)]
        yield pygame.Color(c) if t is str else pygame.Color(*c)

def rgba(*args):
    "Return a color or list of colors from str or tuple data"
    c = list(_rgba(*args))
    return c[0] if len(c) == 1 else c

def randPixel(size):
    "Select a pixel randomly"
    if type(size) not in (list, tuple): size = size.size
    return randint(0, size[0] - 1), randint(0, size[1] - 1)

def noise(c, amt=8, alpha=None):
    "Add randomness to a color"
    c = pygame.Color(*[min(255, max(0, val + randint(-amt, amt))) for val in c])
    if alpha is not None: c.a = alpha
    return c

def divAlpha(c):
    a = c.a
    if a < 255:
        c = rgba(tuple(min(255, round(i * 255 / a)) for i in c[:3]))
    return c

def logError():
    "Print error message to stderr"
    print(format_exc(), file=sys.stderr)

def tall(w, h): return 1 if h > w else 0

def hasAny(data, keys):
    "Check if any of a sequence of keys is in a dictionary"
    for k in keys:
        if k in data: return True
    return False

def rangef(x, xEnd, dx):
    "Float version of built-in range function"
    while (dx > 0 and x < xEnd) or (dx < 0 and x > xEnd):
        yield x
        x += dx

def zipData(archive, *args):
    "Generator for reading zipfile data"
    with ZipFile(archive) as zf:
        for a in args: yield(zf.read(a))

def sc8prData(*args, archive=resolvePath("sc8pr.data")):
    "Read data from a zipfile"
    t = list(zipData(archive, *args))
    return t if len(args) > 1 else t[0]

def hasAlpha(srf):
    "Check if surface has per-pixel alpha"
    return srf.get_masks()[3] != 0

def setAlpha(srf, a):
    "Adjust surface with a minimum transparency "
    srf.fill((255,255,255,a), special_flags=pygame.BLEND_RGBA_MIN)
    return srf

def style(srf, bg=None, border=(0,0,0), weight=0, padding=0, borderradius=None):
    "Create a new surface with padding, background color, and/or border"
    w, h = srf.get_size()

    # Add padding
    if type(padding) is int: px = py = padding + weight
    else: px, py = [p + weight for p in padding]
    w += 2 * px
    h += 2 * py
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    # Add background color and border
    if bg: img.fill(rgba(bg))
    img.blit(srf, (px, py))
    if weight: drawBorder(img, border, weight)
    if borderradius: img = borderRadius(img, borderradius)

    return img

def borderRadius(srf, r=True):
    w, h = srf.get_size()
    if r is True: r = round(h / 6)
    size = r, r
    stamp = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.circle(stamp, (255,255,255), (0,0), r)
    for p in [(w-r, h-r), (w-r, 0), (0, 0), (0, h-r)]:
        srf.blit(stamp, p, special_flags=pygame.BLEND_RGBA_MIN)
        stamp = pygame.transform.rotate(stamp, 90)
    return srf
# circle(surface, color, center, radius, width=0, draw_top_right=None, draw_top_left=None, draw_bottom_left=None, draw_bottom_right=None) -> Rect

def drawBorder(srf, color=(0,0,0), weight=1, r=None):
    "Draw a border around the edges of the surface or specified rectangle"
    color = rgba(color)
    if r is None:
        x = y = 0
        w, h = srf.get_size()
    else: x, y, w, h = r
    ver = (x, y, weight, h), (x + w - weight, y, weight, h)
    w -= 2 * weight
    x += weight
    hor = (x, y, w, weight), (x, y + h - weight, w, weight)
    clip = srf.get_clip()
    sides = [pygame.Rect(s).clip(clip) for s in (ver + hor)]
    for s in sides:
        if s: srf.subsurface(s).fill(color)

def tile(srf, tile=0, cols=1, rows=1, padding=0):
    "Return a tile subsurface"
    w, h = srf.get_size()
    n = cols * rows
    if tile < 0: tile += n
    if tile >= n or tile < 0: raise IndexError("tile index is out of range")
    w = w // cols
    h = h // rows
    x = tile % cols * w + padding
    y = tile // cols * h + padding
    padding *= 2
    return srf.subsurface(x, y, w - padding, h - padding)

def ondrag(gr, ev):
    "Move a Graphic instance while dragging"
    gr.pos = sigma(gr.pos, ev.rel)

def dragDrop(gr, ev):
    "Drag a Graphic, possibly into a different canvas"
    gr.hoverable = False
    pos = sigma(gr.pos, ev.rel)
    drop = False
    try:
        cv = [gr for gr in gr.sketch.objectAt(ev.pos).path if getattr(gr, "allowDrop", False)][0]
        if cv is not gr.canvas:
            pos = sigma(pos, delta(gr.canvas.rect.topleft, cv.rect.topleft))
            drop = True
            gr.setCanvas(cv)
    except: pass
    gr.config(pos=pos, hoverable=True)
    if drop: gr.bubble("ondrop", ev)

def fileExt(fn, ext):
    "Force file extension"
    ext = [e.lower() for e in ([ext] if type(ext) is str else ext)]
    if fn.split(".")[-1].lower() not in ext:
        fn += "." + ext[0]
    return fn

def mix(x, y):
    "Generate a sequence of ordered pairs from two sequences"
    try:
        for i in x:
            try:
                for j in y: yield i, j
            except:
                for p in mix(i, [y]): yield p
    except:
        for p in mix([x], y): yield p


class CachedSurface:
    "A class for caching scaled and rotated surfaces"

    def __init__(self, srf, bg=None):
        if hasattr(srf, "image"): srf = srf.image
        t = type(srf)
        if t is str:
            srf = pygame.image.load(srf)
            if bg: srf = style(srf, bg)
            elif srf.get_bitsize() < 32:
                srf = srf.convert_alpha()
        elif t in (list, tuple):
            srf = pygame.Surface(srf, pygame.SRCALPHA)
            if bg is not None:
                srf.fill(bg if type(bg) is pygame.Color else rgba(bg))
        self.original = srf
        self.dumpCache()

    def dumpCache(self):
        "Remove scaled and rotated images from cache"
        srf = self.original
        self.scaled = srf.get_size(), srf
        self.rotated = 0, srf

    def get_surface(self, size=None, angle=0):
        "Obtain a scaled and rotated image, updating the cache"
        if size is None: size = self.original.get_size()
        else: size = max(1, round(size[0])), max(1, round(size[1]))
        sz, srf = self.scaled
        if sz != size: # smoothscale crashes sometimes for 1x1 surface!!
            srf = scale(self.original, size)
            self.scaled = size, srf
            self.rotated = 0, srf
        if angle:
            a, srf = self.rotated
            if a != angle:
                srf = pygame.transform.rotate(self.scaled[1], -angle)
                self.rotated = angle, srf
        return srf

    def get_size(self, n=0):
        srf = getattr(self, ("scaled", "rotated")[n-1])[1] if n else self.original
        return srf.get_size()
