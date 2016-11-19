# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Apply transition effects to an Image or ScriptSprite"

from sc8pr.image import Image, CENTER
from sc8pr.util import randColor
from sc8pr.sketch import Sprite, REMOVE
from pygame.pixelarray import PixelArray
import pygame
from random import uniform, randint, random
from math import sqrt


class Effect:
    "Base class for all effects"
    offset = 0
    duration = 60

    def dur(self, duration):
        "Change effect duration"
        self.duration = duration
        return self


class Tint(Effect):
    "Apply a tint operation to the image"

    def __init__(self, color=(255,255,255,0)):
        self.color = color

    def apply(self, img, n=0):
        if n >= 1: return img
        c = [round(c + n * (255 - c)) for c in self.color] if n > 0 else self.color
        return img.clone().tint(c)


class Remove(Effect):

    def __init__(self, color=(255,255,255), dist=0):
        self.color = color
        self.dist = dist

    def apply(self, img, n=0):
        if n >= 1: return img
        return img.removeColor(self.color, self.dist)


class Border(Effect):
    "Draw a border around the image"

    def __init__(self, width=2, color=(255,0,0)):
        self.width = width
        self.color = color

    def apply(self, img, n=0):
        return img.clone().borderInPlace(self.width, self.color)


class Wipe(Effect):
    "Vertical or horizontal wipe effect"

    def __init__(self, direction=0): self.direction = direction

    def rects(self, size, n):
        "Return a tuple of rectangles to set to transparent"
        w, h = size
        d = self.direction
        if d > 8: return self.irisRect(size, 1 - n),
        x = round((w if d % 2 else h) * (1 - n))
        if d > 6: x = x // 2
        size = (x, h) if d % 2 else (w, x)
        if d > 6:
            x = (w - x, 0) if d == 7 else (0, h - x)
            return pygame.Rect((0, 0), size), pygame.Rect(x, size)
        if d == 1: x = w - x, 0
        elif d == 4: x = 0, h - x
        elif d == 5: x = (w - x) // 2, 0
        elif d == 6: x = 0, (h - x) // 2
        else: x = 0, 0
        return pygame.Rect(x, size),

    def irisRect(self, size, n):
        "Determine the central rectangle for an 'iris' effect"
        w, h = size
        w1 = round(w * n)
        h1 = round(h * n)
        x = (w - w1) // 2
        y = (h - h1) // 2
        return pygame.Rect((x,y), (w1,h1))
         
    def iris(self, img, n):
        "Apply 'iris' effect"
        size = img.size
        r = self.irisRect(size, n)
        newImg = Image(size)
        Image(img.surface.subsurface(r)).blitTo(newImg, r.topleft)
        return newImg

    def apply(self, img, n):
        "Apply wipe effect"
        if n >= 1: return img
        if n < 0: n = 0
        if self.direction == 0:
            return self.iris(img, n)
        img = img.clone()
        for r in self.rects(img.size, n):
            img.surface.subsurface(r).fill((0,0,0,0))
        return img


class Tiles(Effect):
    "Create an exploding tiles effect"

    def createTile(self):
        vx, vy, s = uniform(-0.5, 0.5), uniform(1, 2), uniform(-720,720)
        if randint(0,1): vy = -vy
        return vx, vy, s

    @staticmethod
    def randCut(n):
        avg = 1 / n
        var = avg / 3
        return [0] + [i * avg + uniform(-var, var) for i in range(1,n)] + [1]

    def makeRects(self, w, h):
        x, y = self.corners
        self.rects = []
        for r in range(len(y) - 1):
            for c in range(len(x) - 1):
                x0 = w * x[c]
                y0 = h * y[r]
                w0 = w * (x[c+1] - x[c])
                h0 = h * (y[r+1] - y[r])
                self.rects.append(pygame.Rect((x0, y0), (w0, h0)))

    def __init__(self, cols=7, rows=4, power=1.5):
        self.corners = self.randCut(cols), self.randCut(rows)
        self.tiles = [self.createTile() for i in range(cols * rows)]
        self.power = power

    def apply(self, img, n):
        if n >= 1: return img
#        if self.rects is None:
        self.makeRects(*img.size)
        i = 0
        n = (1 - n) ** self.power
        w, h = img.size
        imgTr = Image(img.size)
        for r in self.rects:
            tile = Image(img.surface.subsurface(r))
            vx, vy, s = self.tiles[i]
            x, y = r.center
            diag = sqrt(r.width**2 + r.height**2) / 2
            x += vx * (diag + max(x, w-x)) * n
            y += vy * (diag + max(y, h-y)) * n
            i += 1
            tile.rotate(s*n).blitTo(imgTr, (x,y), CENTER)
        return imgTr


class MathEffect(Effect):
    "Effect based on y < f(x) or y > f(x)"

    def __init__(self, eqn=None):
        if eqn: self.eqn = eqn.__get__(self, self.__class__)

    def apply(self, img, n):
        "Modify image based on equation provided"
        img = img.clone()
        size = img.size
        h = size[1]
        pxa = PixelArray(img.surface)
        x = 0
        for pxCol in pxa:
            y, above = self.eqn(x, n, size)
            if above:
                if y < h - 1:
                    if y < 0: y = 0
                    pxCol[y:] = 0, 0, 0, 0
            else:
                if y > 0:
                    if y > h: y = h
                    pxCol[:y] = 0, 0, 0, 0
            x += 1
        return img


class Diagonal(MathEffect):
    "Diagonal wipe effect"
    
    def __init__(self, quad=1): self.quad = quad

    def eqn(self, x, n, size):
        q = self.quad
        w, h = size
        m = h / w
        if q % 2 == 0: m = -m
        if q == 1: b = 1 - 2 * n
        elif q == 2: b = 2 * (1 - n)
        elif q == 3: b = 2 * n - 1
        else: b = 2 * n
        return round(m * x + b * h), q > 2


class PaintDrops(MathEffect):
    "Paint drop effect"

    def __init__(self, drops=64):
        self.side = drops > 0
        self.drops = [self.makeDrop() for i in range(abs(drops))]
        n = sum([d[0] for d in self.drops])
        for d in self.drops: d[0] /= n

    def eqn(self, x, n, size):
        "Calculate paint boundary"
        if not self.side: n = 1 - n
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
        return round(y), self.side

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
        return [uniform(0.1,1), min(t1, t2), max(t1, t2)]


class PixelEffect(Effect):

    def apply(self, img, n):
        "Apply pixel-by-pixel effect"
        if n >= 1: return img
        if n < 0 : n = 0
        img = img.clone()
        pxa = PixelArray(img.surface)
        self.mask = img.surface.get_masks()[3]
        c = 0
        for pxCol in pxa:
            for r in range(len(pxCol)):
                px = self.pixel(n, c, r, pxCol[r], img)
                if px: pxCol[r] = px
            c += 1
        return img


class Dissolve(PixelEffect):
    "Dissolve from transparency, solid color, or noise"

    def __init__(self, color=False, transparent=False):
        self.color = (0,0,0,0) if color is False else color
        self.transparent = transparent

    def pixel(self, n, x, y, color, img):
        "Calculate pixel color"
        if (self.transparent or color & self.mask) and random() > n:
            return randColor() if self.color is True else self.color


class ScriptSprite(Sprite):
    script = ()
    log = False

    def __init__(self, sprites, costumes, *group, **kwargs):
        super().__init__(sprites, costumes, *group, **kwargs)
        self._effects = []

    def update(self):
        "Run script actions at scheduled frame number"
        n = self.sketch.frameNumber
        iSum = 0
        for i, s in self.script:
            iSum += i
            if iSum == n:
                if self.log: print(n, self, s)
                t = type(s)
                if t is dict: self.config(**s)
                elif t is int:
                    if s == REMOVE: self.remove()
                    else: self.status = s
                elif isinstance(s, Effect):
                    s.offset = n
                    e = self._effects
                    if e is None: self._effects = [s]
                    else: e.append(s)
                elif not self.action(s):
                    self.noAction(s)
        super().frameStep()

    def noAction(self, a):
        "Unrecognized action"
        raise TypeError("Unrecognized action for {}: {}".format(type(self).__name__, a))

    def action(self, a): pass

    def applyEffects(self, img):
        "Apply effects to zoomed and rotated image"
        n = self.sketch.frameNumber
        rm = []
        for e in self._effects:
            f0 = e.offset
            dt = e.duration
            if dt < 0: f0 -= dt
            x = (n - f0) / dt
            if x >= 0 and x < 1:
                img = e.apply(img, x)
            elif n > max(f0, f0 + dt):
                rm.append(e)
        for e in rm: self._effects.remove(e)
        return img
