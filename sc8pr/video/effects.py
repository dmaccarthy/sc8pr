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


from sc8pr.image import Image
from pygame.pixelarray import PixelArray
import pygame


class Effect:
    "Base class for layer effects"

    def __init__(self, length, frame):
        self.length = length
        self.frame = frame

    def apply(self, img, frame):
        n = self.length
        if n is not None: n = (frame - self.frame) / n
        if n is None or n >= 0 and n < 1:
            img = self.transform(img, n)
        return img


class Scale(Effect):
    "Adjust the size of the layer image"

    def __init__(self, size=None):
        super().__init__(None, None)
        self.size = size

    def transform(self, img, n):
        size = self.size if self.size else img.fitAspect(self.layer.clip.size)
        return img.transform(size)


class Fade(Effect):
    "Fade layer in or out"

    def __init__(self, length, color=None, frame=None):
        super().__init__(length, frame)
        self.color = color

    def transform(self, img, n):
        img = img.clone().setAlpha(round(255 * n))
        if self.color:
            newImg = Image(img.size, self.color)
            img.blitTo(newImg)
            img = newImg
        return img


class Wipe(Effect):
    "Vertical or horizontal wipe effect"

    def __init__(self, length, direction=0, frame=None):
        super().__init__(length, frame)
        self.direction = direction

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

    def transform(self, img, n):
        "Apply wipe effect"
        if self.direction == 0:
            return self.iris(img, n)
        img = img.clone()
        for r in self.rects(img.size, n):
            img.surface.subsurface(r).fill((0,0,0,0))
        return img


class MathEffect(Effect):
    "Layer effect based on y < f(x) or y > f(x)"

    def __init__(self, length, frame=None, eqn=None):
        super().__init__(length, frame)
        if eqn: self.eqn = eqn.__get__(self, self.__class__)

    def transform(self, img, n):
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
    "Diagonal wipe layer effect"
    
    def __init__(self, length, quad=1, frame=None):
        super().__init__(length, frame)
        self.quad = quad

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
