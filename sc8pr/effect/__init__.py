from math import sin, cos, pi, hypot
from random import uniform, random
import pygame
from pygame.pixelarray import PixelArray
from sc8pr.util import rgba, surface, hasAlpha

try:
    from pygame.surfarray import pixels_alpha
except:
    pixels_alpha = None


class Effect:
    _t0 = _t1 = 0
    remove = True
    _fill = rgba("#ffffff00")

    @staticmethod
    def shift(img, dt):
        "Shift effect timing"
        for e in img.effects:
            e._t0 += dt
            e._t1 += dt
        return img

    @property
    def fill(self): return self._fill

    @fill.setter
    def fill(self, c): self._fill = rgba(c)

    def time(self, t0, t1):
        "Set the 'transparent' and 'opaque' time limits of the transition"
        self._t0 = t0
        self._t1 = t1
        self._t_max = max(t0, t1)
        self._t_min = min(t0, t1)
        return self

    def transition(self, srf, f):
        t0 = self._t0
        t = self.adjust_time((f - t0) / (self._t1 - t0))
        return self.apply(srf, 0 if t <= 0 else 1 if t >= 1 else t)

    @staticmethod
    def adjust_time(t):
        "By default, transition occurs linearly with time"
        return t

    def config(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def nofx(self, srf, n):
        ""
        if n <= 0:
            srf = pygame.Surface(srf.get_size()).convert_alpha()
            srf.fill(4*(0,))
        elif n < 1: srf = None
        return srf


class Tint(Effect):

    def apply(self, img, n=0):
        if n <= 0 or n >= 1: return self.nofx(img, n)
        img = surface(img)
        color = [round(c + (255 - c) * n) for c in self._fill]
        img.fill(color, None, pygame.BLEND_RGBA_MULT)
        return img


class Squash(Effect):

    def __init__(self, start=5, **kwargs):
        ys = start not in (4, 6)
        xs = start not in (1, 9)
        self.scale = xs, ys
        x = 0 if start in (0, 4, 8) else 2 if start in (2, 6, 10) else 1
        y = 0 if start <3 else 2 if start > 7 else 1
        self.pos = x, y
        self.config(**kwargs)

    def apply(self, img, n):
        if n <= 0 or n >= 1: return self.nofx(img, n)
        img = surface(img)
        w0, h0 = img.get_size()
        s = lambda i: n if self.scale[i] else 1
        w, h = [s(0) * w0, s(1) * h0]
        img = pygame.transform.smoothscale(img, (w, h))
        srf = pygame.Surface((w0, h0), pygame.SRCALPHA)
        x, y = self.pos
        if x == 1: x = (w0 - w) / 2
        elif x == 2: x = w0 - w
        if y == 1: y = (h0 - h) / 2
        elif y == 2: y = h0 - h
        srf.blit(img, (x, y))
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
        img = surface(img)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        gx, gy = self._grid
        size = img.get_size()
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
        srf = surface(img)
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
        srf = surface(img)
        if n <= 0 or n >= 1: return self.nofx(srf, n)
        w, h = srf.get_size()
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


class Bar(Effect):
    reverse = False
    width = 0.08
    _color = rgba("blue")

    def __init__(self, **kwargs): self.config(**kwargs)

    @property
    def color(self): return self._color

    @color.setter
    def color(self, c): self._color = rgba(c)

    def apply(self, img, n):
        if n <= 0 or n >= 1: return self.nofx(img, n)
        img = surface(img)
        w, h = img.get_size()

        # Find bar position
        x1 = n * (1 + self.width)
        x0 = round((x1 - self.width) * w)
        x1 = round(x1 * w)
        if self.reverse: x0, x1 = w - x1, w - x0

        # Make rectangles for bar and transparent
        xmax = max(x0, x1)
        xmin= min(x0, x1)
        full = pygame.Rect(0, 0, w, h)
        bar = full.clip(xmin, 0, xmax - xmin, h)
        tr = full.clip(0, 0, xmin, h) if self.reverse else full.clip(xmax, 0, w - xmax, h)

        # Fill transparent region and bar
        if tr: img.subsurface(tr).fill(self._fill)
        if bar: img.subsurface(bar).fill(self._color)
        return img
