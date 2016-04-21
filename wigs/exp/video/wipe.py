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

class WipeDiag(CustomMathEffect):
    "A class for creating diagonal wipe effects"

    def __init__(self, scene, src, start=0, end=None, **kwargs):
        super().__init__(scene, src, start, end, **kwargs)
        self.setData(0)

    def postFilter(self, img, frame):
        if frame == self.frames[0]: self.setData(1)
        return super().postFilter(img, frame)

    def setData(self, i):
        "Coefficients for calculating diagonal equation"
        w, h = self.src.size
        eff = self.effect[i] % 4
        a = h / (w if eff % 2 else -w)
        b = h * (0, 1, 2, -1)[eff]
        s = 1 if eff in (1, 2) else -1
        d = -2 * h * s
        self.side = s
        self.data = a, b, d

    def pixelFilter(self, x, n):
        a, b, d = self.data
        return a * x + b + d * n
    