# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


from wigs.util import randColor
from wigs.video.video import ImageLayer
from pygame import PixelArray
from random import random
from wigs.image import Image


class PixEffect(ImageLayer):
    "A class to represent layers with individual pixel effects"
    
    def __init__(self, scene, src, start=0, end=None, pixelFilter=None, **kwargs):
        super().__init__(scene, src, start, end, **kwargs)
        if pixelFilter:
            self.pixelFilter = pixelFilter.__get__(self, self.__class__)

    def postFilter(self, img, frame):
        n = self.effectSize(frame, self.frames)
        if n:
            img = img.clone()
            pxa = PixelArray(img.surface)
            c = 0
            for pxCol in pxa:
                for r in range(len(pxCol)):
                    px = self.pixelFilter(n, r, c, pxCol[r])
                    if px: pxCol[r] = px
                c += 1
        return img


class MathEffect(PixEffect):
    "Filter pixels based on a function y = f(x)"
    side = 1

    def yAsInt(self, y, h):
        y = int(y)
        if y < 0: y = 0
        elif y > h: y = h
        return y

    def postFilter(self, img, frame):
        n = self.effectSize(frame, self.frames)
        if n:
            if img.surface.get_bitsize() == 32:
                img = img.clone()
            else:
                img = Image(img.surface.convert_alpha())
            pxa = PixelArray(img.surface)
            h = img.height
            c = 0
            px = 0, 0, 0, 0
            for pxCol in pxa:
                y = self.pixelFilter(c, n)
                if type(y) is tuple:
                    y1 = self.yAsInt(y[0], h)
                    y2 = self.yAsInt(y[1], h)
                    if self.side == 1:
                        pxCol[:y1] = px
                        pxCol[y2:] = px
                    else:
                        pxCol[y1:y2] = px
                else:
                    y = self.yAsInt(y, h)
                    if self.side == 1:
                        pxCol[:y] = px
                    else:
                        pxCol[y:] = px
                c += 1
        return None if n == 0 else img


class CustomMathEffect(MathEffect):
    "pixelFilter will be supplied as a method rather than as a constructor argument"

    def __init__(self, scene, src, start=0, end=None, **kwargs):
        assert "pixelFilter" not in kwargs, "invalid keyword argument"
        super().__init__(scene, src, start, end, **kwargs)


# Filters for PixEffect...

def dissolve(layer, n, r, c, pixel):
    return None if random() < n else (0,0,0,0)

def noise(layer, n, r, c, pixel):
    return None if random() < n else randColor()


# Filters for MathEffect...

def ellipse(layer, x, n, circ=False):
    w, h = layer.src.size
    w, h = w/2, h/2
    r = max(w, h)
    y = 2 * n**2 - ((x - w) / (r if circ else w)) ** 2
    if y < 0: return 0, -1
    y = (r if circ else h) * y ** 0.5
    return h - y, h + y

def circle(layer, x, n): return ellipse(layer, x, n, True)
