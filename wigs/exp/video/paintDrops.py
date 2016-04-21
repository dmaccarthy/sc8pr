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


from wigs.video.effects import CustomMathEffect
from random import random

class PaintDrops(CustomMathEffect):
    side = -1

    def __init__(self, scene, src, start=0, end=None, dropSize=32, **kwargs):
        super().__init__(scene, src, start, end, **kwargs)
        self.drops = []
        self._dropSize = dropSize

    def postFilter(self, img, frame):
        if frame == self.frames[0]:
            self.drops = []
            self.side = 1
        return super().postFilter(img, frame)

    def makeDrops(self):
        x, r, w = 0, 0, self.size[0]
        drops = 1 + w // self._dropSize
        self.drops = []
        while x < w:
            diam = (0.1 + 0.9 * random()) / 0.55 * w / drops
            r = diam / 2
            x += 0.9 * r
            n0 = 0.4 * random()
            drop = r, x, n0, 0.6 + 0.4 * random() - n0
            self.drops.append(drop)

    def pixelFilter(self, x, n):
        if len(self.drops) == 0: self.makeDrops()
        if self.side == 1: n = 1 - n
        y = 0
        h = self.size[1]
        for drop in self.drops:
            r, xd, n0, t = drop
            xd -= x
            if n >= n0 and abs(xd) < r:
                yd = (n - n0) / t * (h + 2 * r) - r
                yd += (r**2 - xd**2) ** 0.5 + 2 * (random() - 0.5)
                if yd > y: y = yd
        return y
