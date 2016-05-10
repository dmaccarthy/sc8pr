from sc8pr.image import Image
from pygame.pixelarray import PixelArray
import pygame


class Effect:
    "Base class for layer effects"

    def __init__(self, frame, length):
        self.frame = frame
        self.length = length

    def apply(self, img, frame):
        n = (frame - self.frame) / self.length
        if n >= 0 and n < 1:
            img = self.transform(img, n)
        return img

    @staticmethod
    def alphaClone(img, a=None):
        srf = img.surface
        if srf.get_bitsize() < 32:
            img = Image(srf.convert_alpha())
        else:
            img = img.clone()
        if a is not None: img.setAlpha(a)
        return img


class Fade(Effect):
    "Fade layer in or out"

    def __init__(self, frame, length, color=None):
        super().__init__(frame, length)
        self.color = color

    def transform(self, img, n):
        img = self.alphaClone(img, round(255 * n))
        if self.color:
            pass
        return img


class Wipe(Effect):
    "Vertical or horizontal wipe effect"

    def __init__(self, frame, length, direction=1):
        super().__init__(frame, length)
        self.direction = direction

    def rects(self, size, n):
        w, h = size
        d = self.direction
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

    def transform(self, img, n):
        img = self.alphaClone(img)
        for r in self.rects(img.size, n):
            img.surface.subsurface(r).fill((0,0,0,0))
        return img


class EqnFilter(Effect):
    "Layer effect based on y < f(x) or y > f(x)"

    def __init__(self, frame, length, eqn, **kwargs):
        super().__init__(frame, length)
        self.eqn = eqn
        self.params = kwargs

    def transform(self, img, n):
        img = self.alphaClone(img)
        size = img.size
        h = size[1]
        pxa = PixelArray(img.surface)
        x = 0
        for pxCol in pxa:
            y, above = self.eqn(x, n, size, **self.params)
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


class Diagonal(EqnFilter):
    
    def __init__(self, frame, length, quad=1):
        super().__init__(frame, length, self.diag, quad=quad)

    @staticmethod
    def diag(x, n, size, quad=1):
        w, h = size
        m = w / h
        if quad % 2 == 0: m = -m
        if quad == 1: b = 1 - 2 * n
        elif quad == 2: b = 2 * (1 - n)
        elif quad == 3: b = 2 * n - 1
        else: b = 2 * n
        return round(m * x + b * h), quad > 2
