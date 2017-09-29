# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


import sys, os, zlib, struct, pygame
from random import randint
from traceback import format_exc
from zipfile import ZipFile

def sc8prPath(rel=""):
    "Return path to sc8pr folder"
    path = os.path.dirname(__file__)
    if rel: path += "/" + rel
    return os.path.normpath(path)

def _rgba(*args):
    "Generate a sequence of pygame.Color instances"
    for c in args:
        t = type(c)
        if t is bool: # Random color
            c = [randint(0,255) for i in range(4 if c else 3)]
        yield pygame.Color(c) if t is str else pygame.Color(*c)

def rgba(*args):
    "Return a color or list of colors from str or tuple data"
    c = tuple(_rgba(*args))
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

def zipData(archive, *args):
    "Generator for reading zipfile data"
    with ZipFile(archive) as zf:
        for a in args: yield(zf.read(a))

def sc8prData(*args, archive=sc8prPath("sc8pr.data")):
    "Read data from a zipfile"
    t = list(zipData(archive, *args))
    return t if len(args) > 1 else t[0]

def hasAlpha(srf):
    "Check if surface has per-pixel alpha"
    return srf.get_masks()[3] != 0

def setAlpha(srf, a):
    "Create a new surface with a minimum transparency "
    srf.fill((255,255,255,a), special_flags=pygame.BLEND_RGBA_MIN)
    return srf

def style(srf, bg=None, border=(0,0,0), weight=0, padding=0):
    "Create a new surface with padding, background color, and/or border"
    w, h = srf.get_size()

    # Add padding
    padding += weight
    w += 2 * padding
    h += 2 * padding
    img = pygame.Surface((w, h), pygame.SRCALPHA)

    # Add background color and border
    if bg: img.fill(rgba(bg))
    img.blit(srf, (padding, padding))
    if weight: drawBorder(img, border, weight)

    return img
 
def drawBorder(srf, color=(0,0,0), weight=1, r=None):
    "Draw a border around the edges of the surface"
    r0 = srf.get_clip()
#    r0 = pygame.Rect((0, 0), srf.get_size())
    if r is None: r = r0
    w, h = r.size
    x, y = r.topleft
    hor = w, weight
    ver = weight, h - 2 * weight
    color = rgba(color)
    for r in ((x, y) + hor, (x, y + h - weight) + hor,
            (x, y + weight) + ver, (x + w - weight, y + weight) + ver):
        r = pygame.Rect(r).clip(r0)
        if max(r.size): srf.subsurface(r).fill(color)

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

def surfaceData(srf, compress=zlib.compress):
    "Convert surface to bytes data with optional compression"
    if not isinstance(srf, pygame.Surface): srf = srf.image
    w, h = srf.get_size()
    a = hasAlpha(srf)
    mode = (1 if a else 0) + (2 if compress else 0)
    mode = struct.pack("!3I", mode, w, h)
    data = pygame.image.tostring(srf, "RGBA" if a else "RGB")
    return (compress(data) if compress else data), mode


class CachedSurface:
    "A class for caching scaled and rotated surfaces"

    def __init__(self, srf, bg=None, decompress=zlib.decompress):
        if hasattr(srf, "image"): srf = srf.image
        t = type(srf)
        if t is str:
            srf = pygame.image.load(srf)
            if bg: srf = style(srf, bg)
            elif not hasAlpha(srf): srf = srf.convert_alpha()
        elif t is bytes:
            mode, w, h = struct.unpack("!3I", bg)
            if mode & 2: srf = decompress(srf)
            mode = "RGBA" if mode & 1 else "RGB"
            srf = pygame.image.fromstring(srf, (w,h), mode)
        elif t in (list, tuple):
            srf = pygame.Surface(srf, pygame.SRCALPHA)
            if bg: srf.fill(bg if type(bg) is pygame.Color else rgba(bg))
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
        if sz != size:
            srf = pygame.transform.smoothscale(self.original, size)
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
