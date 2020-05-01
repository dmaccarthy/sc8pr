# Copyright 2015-2020 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

from math import cos, sin
from sc8pr.geom import DEG
from sc8pr import Image, CENTER
from sc8pr.shape import Arrow


class ArrowImage(Image):
    FACTOR = 6
    FIXED = True, 16/FACTOR, 16/FACTOR, 2
    SCALE = False, 0.1, 0.1, 2
    
    @property
    def anchor(self): return CENTER

    def __init__(self, length, fixed=None, **kwargs):
        f = ArrowImage.FACTOR
        if fixed is None:
            fixed, width, head, flatness = ArrowImage.FIXED if length > 16 else ArrowImage.SCALE
        else:
            fixed, width, head, flatness = fixed
        if fixed is True:
            width *= f / length
            head *= f / length
        attr = {"weight": ArrowImage.FACTOR}
        attr.update(**kwargs)
        super().__init__(Arrow(f * length, width, head, flatness).config(**attr).image)
        self.config(width=length, _length=length)

    def _get_r(self, r):
        L = self._length / 2
        return L if r else -L

    def getPos(self, r=True):
        if type(r) is bool: r = self._get_r(r)
        a = self.angle * DEG
        return self.pos[0] - r * cos(a), self.pos[1] - r * sin(a)

    def setPos(self, pos, r=True):
        if type(r) is bool: r = self._get_r(r)
        a = self.angle * DEG
        pos = pos[0] + r * cos(a), pos[1] + r * sin(a)
        return self.config(pos=pos)

    def rotateTo(self, a, r=True): # r+ = Toward tail, r- = Toward tip
        pos = self.getPos(r)
        self.angle = a
        return self.setPos(pos, r)

    def rotate(self, a, r=True): return self.rotateTo(self.angle + a)

