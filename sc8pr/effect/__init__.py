from math import sin, cos, pi, hypot, ceil
from random import uniform, random, randint
import pygame
from sc8pr.util import rgba, surface, hasAlpha

try:
    from pygame.surfarray import pixels_alpha, pixels3d
except:
    pixels3d = None
    from pygame.pixelarray import PixelArray


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

    def __init__(self, **kwargs): self.config(**kwargs)

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
        for k, v in kwargs.items(): setattr(self, k, v)
        return self

    def nofx(self, srf, n):
        if n <= 0:
            srf = pygame.Surface(srf.get_size()).convert_alpha()
            srf.fill(4*(0,))
        elif n < 1: srf = None
        return srf


class Tint(Effect):

    def apply(self, img, n=0):
        if n <= 0 or n >= 1: return self.nofx(img, n)
        img = surface(img, True)
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
        img = surface(img, True)
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

    def __init__(self, grid=(16, 9), angles=(0, 360), **kwargs):
        self._dir = d = []
        for i in range(grid[0] * grid[1]):
            r = uniform(1, 1.5)
            a = uniform(*angles) / 180 * pi           
            d.append([r*cos(a), r*sin(a), uniform(0, 540)])
        self.grid = grid
        self.config(**kwargs)

    def apply(self, img, n=0):
        img = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        gx, gy = self.grid
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

    _fill = False

    @property
    def fill(self): return self._fill

    @fill.setter
    def fill(self, c):
        self._fill = c if type(c) is bool else rgba(c)

    def apply(self, img, n):
        "Apply pixel-by-pixel effect"
        srf = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(srf, n)
        if pixels3d:
            if self._fill is False: self.sa_dissolve_tr(srf, n)
            else: self.sa_dissolve(srf, n, self.fill)
        else: self.pa_dissolve(srf, n, self._fill)
        return srf

    @staticmethod
    def sa_dissolve(srf, n, c):
        "Use surfarray to dissolve to a specific or random color"
        if c is not True: c = c[:3]
        for col, cola in zip(pixels3d(srf), pixels_alpha(srf)):
            for r in range(len(cola)):
                if cola[r] and random() > n:
                    col[r] = [randint(0, 255) for i in range(3)] if c is True else c

    @staticmethod
    def sa_dissolve_tr(srf, n):
        "Use surfarray to dissolve to transparent"
        for col in pixels_alpha(srf):
            for r in range(len(col)):
                if random() > n: col[r] = 0

    @staticmethod
    def pa_dissolve(srf, n, c):
        "Use PixelArray (slower) to dissolve"
        mask = srf.map_rgb((0,0,0,255))
        pxa = PixelArray(srf)
        x = 0
        for pxCol in pxa:
            for y in range(len(pxCol)):
                if random() > n and mask & pxCol[y]:
                    pxCol[y] = pygame.Color([randint(0, 255) for i in range(3)]) if c is True else c
            x += 1


class Pixelate(Effect):

    def __init__(self, size=64, **kwargs):
        self._calc = lambda x: max(1, round((1 - x) * size))
        self.config(**kwargs)

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

    @property
    def color(self): return self._color

    @color.setter
    def color(self, c): self._color = rgba(c)

    def apply(self, img, n):
        if n <= 0 or n >= 1: return self.nofx(img, n)
        img = surface(img, True)
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


class Checkerboard(Effect):
    grid = 8, 8
    mode = "+Y+Y"

    def apply(self, img, n):
        srf = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(srf, n)
        w, h = srf.get_size()
        mode = self.mode.upper()
        srect = pygame.Rect(0, 0, w, h)
        gx, gy = self.grid
        sw = ceil(w / gx)
        sh = ceil(h / gy)
        late = n > 0.5
        sd = ceil((1 - 2 * (1 - n if late else n)) * (sh if late else sw) + 1)
        for c in range(gx):
            for r in range(gy):
                odd = (r + c) % 2
                y = r * sh
                x = c * sw
                if odd:
                    if n >= 0.5: rect = None
                    else:
                        if mode[0] == "+":
                            if mode[1] == "X": x += sw - sd
                            else: y += sh - sd
                        rect = (x, y, sw, sd) if mode[1] == "Y" else (x, y, sd, sh)
                else:
                    if n <= 0.5: rect = (x, y, sw, sh)
                    else:
                        if mode[2] == "+":
                            if mode[3] == "X": x += sd
                            else: y += sd
                        rect = (x, y, sw, sh - sd) if mode[3] == "Y" else (x, y, sw - sd, sh)
                if rect: srf.subsurface(srect.clip(rect)).fill(self._fill)
        return srf
