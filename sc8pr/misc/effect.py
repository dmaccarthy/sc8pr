# Copyright 2015-2023 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


from random import uniform, random
from math import sqrt, tan, pi, sin, cos, hypot
import pygame
from pygame.pixelarray import PixelArray
from sc8pr.util import rgba, style
try:
    from pygame.surfarray import pixels_alpha
except:
    pixels_alpha = None

pi2 = 2 * pi


def shift(gr, dt):
    "Shift effect timing"
    for e in gr.effects:
        try:
            t0, t1 = e._time
            e._time = t0 + dt, t1 + dt
        except: pass
    return gr


class Effect:
    "Base class for all effects / transitions"
    _time = None

    def time(self, fullEffect, noEffect=0):
        "Set effect timing"
        self._time = fullEffect, noEffect
        return self

    def transition(self, img, n):
        "Apply an effect as a transition in/out"
        if self._time is None: n = 0
        else:
            t0, t1 = self._time
            n = (n - t0) / (t1 - t0)
        return self.apply(img, 0 if n <= 0 else 1 if n >= 1 else n)

    def srfSize(self, img, size=False):
        srf = img if isinstance(img, pygame.Surface) else img.image
        return (srf, srf.get_size()) if size else srf


class Remove(Effect):
    "Remove a graphic, or its effects lists, at the specified frame"

    def __init__(self, gr, complete=False):
        self._gr = gr
        self._complete = complete

    def apply(self, img, n=0):
        if n <= 0:
            if self._complete:
                self._gr.bind(ondraw=self.finish)
            else: self._gr.effects = None
        return img

    @staticmethod
    def finish(gr, ev=None): gr.remove()


class ReplaceColor(Effect):
    "Replace one color by another (non-animated)"

    def __init__(self, color, replace=(0,0,0,0), dist=0.0):
        self.color1 = rgba(color)
        self.color2 = rgba(replace)
        self.dist = dist

    def apply(self, img, n=0):
        if n >= 1: return img
        srf = self.srfSize(img)
        d = self.dist * (1 - n)
        pygame.PixelArray(srf).replace(self.color1, self.color2, d)
        return img


class Style(Effect):
    "Add a border or background (non-animated)"
    
    def __init__(self, **kwargs):
        if "padding" in kwargs: # Alters blit rect!
            raise NotImplementedError("Keyword 'padding' is not permitted")
        self.kwargs = kwargs
    
    def apply(self, img, n=0):
        if not isinstance(img, pygame.Surface): img = img.image
        return style(img, **self.kwargs)


class Tint(Effect):
    "Adjust the color and/or transparency"

    def __init__(self, color=(255,255,255,0)):
        self.color = rgba(color)

    def apply(self, img, n=0):
        if n >= 1: return img
        srf = self.srfSize(img)
        color = [round(c + (255 - c) * n) for c in self.color]
        srf.fill(color, None, pygame.BLEND_RGBA_MULT)
        return srf


class Assemble(Effect):
    "(Dis)assemble into many small rectangles"

    def __init__(self, grid=(16, 9), angles=(0, 360)):
        self._dir = d = []
        for i in range(grid[0] * grid[1]):
            r = uniform(1, 1.5)
            a = uniform(*angles) / 180 * pi           
            d.append([r*cos(a), r*sin(a), uniform(0, 540)])
        self._grid = grid

    def apply(self, img, n=0):
        if n >= 1: return img
        gx, gy = self._grid
        img, size = self.srfSize(img, True)
        w, h = size[0] // gx, size[1] // gy
        n = (1 - n) ** 1.5
        hyp = n * hypot(size[0], size[1])
        srf = pygame.Surface(size, pygame.SRCALPHA)
        for r in range(gy):
            y = h * r
            for c in range(gx):
                dx, dy, a = self._dir[c + r * gy]
                x = w * c
                sqr = img.subsurface((x, y, w, h))
                sqr = pygame.transform.rotate(sqr, a * n)
                wr, hr = sqr.get_size()
                xb = x - (wr - w) // 2 + hyp * dx
                yb = y - (hr - h) // 2 + hyp * dy
                srf.blit(sqr, (xb, yb))
        return srf


class Wipe(Effect):
    "Wipe in or out from any corner, side, or center"

    def __init__(self, start=5): self.start = start

    @staticmethod
    def _dim(n, start, w0):
        "Calculate 'wiped' position and size in one dimension"
        if start is not None:
            w = round(n * w0)
            dw = w0 - w
            x = dw//2 if start & 1 else dw if start & 2 else 0
            return x, w
        return 0, w0

    @staticmethod
    def _apply(srf, pos, size, origSize):
        "Blit the visible subsurface onto a transparent background"
        img = pygame.Surface(origSize, pygame.SRCALPHA)
        img.blit(srf.subsurface(pos, size), pos)
        return img

    def apply(self, img, n=0):
        if n >= 1: return img
        srf, sz = self.srfSize(img, True)
        s = self.start
        wx = None if s in (1, 9) else (s & 3)
        wy = None if s in (4, 6) else (s >> 2)
        x, w = self._dim(n, wx, sz[0])
        y, h = self._dim(n, wy, sz[1])
        return self._apply(srf, (x,y), (w,h), sz)


class Squash(Wipe):

    @staticmethod
    def _apply(srf, pos, size, origSize):
        "Blit the scaled image onto a transparent background"
        srf = pygame.transform.smoothscale(srf, size)
        img = pygame.Surface(origSize, pygame.SRCALPHA)
        img.blit(srf, pos)
        return img


class Dissolve(Effect):
    "Replace pixels randomly by a specified or random color"

    def __init__(self, colors=(0,0,0,0), keepTransparent=True, alpha=True):
        t = type(colors)
        if t is int:
            self.colors = [rgba(alpha) for i in range(colors)]
        elif t is bool: self.colors = colors
        else:
            if t in (str, pygame.Color) or type(colors[0]) is int:
                colors = colors,
            self.colors = [rgba(i) for i in colors]
        self.n = -1
        self.keep = keepTransparent

    def apply(self, img, n):
        "Apply pixel-by-pixel effect"
        if n >= 1: return img
        srf = self.srfSize(img)
        if pixels_alpha: # Use numpy/pixels_alpha
            sa = pixels_alpha(srf)
            h = len(sa[0])
            for c in sa:
                for r in range(h):
                    if random() > n: c[r] = 0
        else: # No numpy!
            self.alphaMask = srf.map_rgb((0,0,0,255))
            pxa = PixelArray(srf)
            x = 0
            for pxCol in pxa:
                for y in range(len(pxCol)):
                    pxCol[y] = self.pixel(n, x, y, pxCol[y])
                x += 1
        return srf

    def pixel(self, n, x, y, c):
        "Calculate pixel color"
        if random() <= n or (self.keep and c & self.alphaMask == 0):
            return c
        c = self.colors
        if type(c) is bool: return rgba(c)
        self.n = (self.n + 1) % len(self.colors)
        return c[self.n]


class Pixelate(Effect):

    def __init__(self, size=64, linear=True):
        if linear: # Better for smaller squares?
            self._calc = lambda x: max(1, round((1 - x) * size))
        else:      # Better for larger squares?
            self._calc = lambda x: round(size ** (1 - x))

    def apply(self, img, n=0):
        if n >= 1: return img
        srf, (w, h) = self.srfSize(img, True)
        n = self._calc(n)
        if n > 1:
            r = pygame.Rect(0, 0, w, h)
            dx = n - (w % n) // 2
            dy = n - (h % n) // 2
            for x in range(0, w + n, n):
                for y in range(0, h + n, n):
                    clip = r.clip(x - dx, y - dy, n, n)
                    if clip.width and clip.height:
                        subsrf = srf.subsurface(clip)
                        c = pygame.transform.average_color(subsrf)
                        subsrf.fill(c)
        return srf


class MathEffect(Effect):
    "Effect based on y < f(x) or y > f(x)"

    def __init__(self, noise=0.15, fill=(0,0,0,0)):
        self.fill = rgba(fill)
        self.above = noise > 0
        noise = abs(noise / 2)
        self.limits(-noise, noise)

    def func(self, x, t): return self.A * uniform(-1, 1)

    def limits(self, y0, y1):
        self.avg = (y1 + y0) / 2
        self.A = (y1 - y0) / 2
        self.h = 2 * self.A + 1
        self.top = y1

    def apply(self, img, n=0):
        "Modify image based on equation provided"
        if n >= 1: return img
        srf, size = self.srfSize(img, True)
        w, h = size
        pxa = PixelArray(srf)
        x = 0
        t = n if self.above else (1 - n)
        try: mid = t * self.h - self.A
        except: pass
        for pxCol in pxa:
            if hasattr(self, "eqn"):  # Let subclass do all calculations
                y = self.eqn(x, n, size)
            else:  # Graph a function (scaled to (0,1)) with rising offset
                y = (h - 1) * (self.func(x / (w - 1), t) + mid - self.avg)
            if type(y) is tuple: y, above = y
            else: above = self.above #True
            if type(y) is float: y = int(y)
            if above:
                if y < h - 1:
                    if y < 0: y = 0
                    pxCol[y:] = self.fill
            elif y > 0:
                if y > h: y = h
                pxCol[:y] = self.fill
            x += 1
        return srf


class Wedge(MathEffect):

    def __init__(self, slope=None, vertex=0.5, fill=(0,0,0,0)):
        self.above = vertex > 0
        self.fill = rgba(fill)
        self.vertex = v = abs(vertex)
        if slope is None:
            self.m = 1/v, -1/(1-v)
            self.limits(0, 1)
        else:
            slope = abs(slope)
            self.m = slope, -slope
            a, b = self.m
            self.limits(0, slope * max(v, 1 - v))
#             print(a, b, self.avg, self.A)

    def func(self, x, t):
        v = self.vertex
        a, b = self.m
        y = a * x if x < v else b * (x - v) + a * v
#         y = x/v if x < v else (x-1)/(v-1)
        return y if self.above else 1-y


class WaterWaves(MathEffect):
    "Rising water effect with waves"

    def __init__(self, *args, speed=0.60, fill=(0,0,0,0), above=False):
        # speed is total displacement over transition as fraction of width
        # arg = (amplitude, wavelength, shift) as fraction of width/height
        # (0.03, -0.2, 0.1)... A is 3% of height, wavelength  is 20% of width, shift is 10% of width
        if not args: args = 6, 0.10, 0.15      # 6 waves, total A around 10%, wavelength around 15%
        if type(args[0]) in (float, int):
            N, A, wl = args
            args = [(A/N*uniform(0.5, 1.5), wl*uniform(0.5, 1.5) * (-1 if i%2 else 1)) for i in range(N)]
        self.args = args = [list(a) for a in args]
        for a in args: a[1] = pi2 / a[1]
        self.sumA = sum(abs(a[0]) for a in args)
        self.fill = rgba(fill)
        self.above = above
        self.speed = speed
        A = self.sumA
        self.limits(-A, A)

    def func(self, x, t):
        p = self.args
        s = self.speed
        f = lambda a: a[0] * sin(abs(a[1]) * ((x + (-s if a[1] < 0 else s) * t) - (a[2] if len(a) > 2 else 0)))
        return sum(f(p[i]) for i in range(len(p)))

    def copy(self, n=-1):
        "Return the 'reversed' or copied wave"
        args = [[a[0], n*pi2/a[1]] + list(a[2:]) for a in self.args]
        return WaterWaves(*args, speed=self.speed, fill=self.fill, above=self.above)


class WipeSlope(MathEffect):
    "Wipe diagonally from any corner"

    def __init__(self, slope=-1, above=True, fill=(0,0,0,0)):
        self.slope = slope
        self.above = above
        self.fill = rgba(fill)
        if slope >= 0: self.limits(0, slope)
        else: self.limits(slope, 0)

    def func(self, x, n): return self.slope * x


class ClockHand(MathEffect):
    above = True

    def __init__(self, clockwise=True, fill=(0,0,0,0)):
        self.fill = rgba(fill)
        self.cw = clockwise

    def eqn(self, x, n, size):
        if n <= 0: return 0
        h = size[1]
        y = h / 2
        x -= size[0] / 2
        if not self.cw: x = -x
        if x < 0:
            return 0 if n <= 0.5 else (y + x * tan((n - 0.75) * pi2), False)
        else:
            return h if n >= 0.5 else (y + x * tan((n - 0.25) * pi2))


class PaintDrops(MathEffect):

    def __init__(self, drops=64, fill=(0,0,0,0)):
        self.fill = rgba(fill)
        self.above = drops > 0
        self.drops = [self.makeDrop() for i in range(abs(drops))]
        n = sum([d[0] for d in self.drops])
        for d in self.drops: d[0] /= n

    def eqn(self, x, n, size):
        "Calculate paint boundary"
        if not self.above: n = 1 - n
        w, h = size
        y = 0
        xc = 0
        for d in self.drops:
            r = d[0] * w / 2
            R = 1.1 * r
            xc += r
            dx = abs(x - xc)
            if dx <= R:
                dy = sqrt(R * R - dx * dx)
                Y = (h + R) * self.posn(n, *d[1:]) + dy - R
                if Y > y: y = Y
            xc += r
        return y, self.above

    def posn(self, n, t1, t2):
        "Calculate drop position"
        if n < t1: return 0
        elif n > t2: return 1
        return (n - t1) / (t2 - t1)

    @staticmethod
    def makeDrop():
        "Create random diameter, start and end time"
        t1 = uniform(0, 0.8)
        t2 = uniform(t1 + 0.1, 1)
        return [uniform(0.1, 1), min(t1, t2), max(t1, t2)]
