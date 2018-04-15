# Copyright 2015-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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

from sc8pr import Canvas, Image, TOPLEFT, BOTTOMLEFT
from sc8pr.util import tall

class ProgressBar(Canvas):
    "Display progress graphically"

    def __init__(self, size=(128,16), color="grey", lower=0, upper=1):
        super().__init__(size)
        cfg = dict(anchor=BOTTOMLEFT, pos=(0, size[1]-1)) if tall(*size) else dict(anchor=TOPLEFT)
        self += Image(bg=color).config(**cfg)
        self.lower = lower
        self.upper = upper
        self.value = lower

    @property
    def value(self): return self._val

    @value.setter
    def value(self, val):
        "Change the current value of the progress bar"
        val = max(self.lower, min(self.upper, val))
        self._val = val
        dim = tall(*self.size)
        x = (val - self.lower) / (self.upper - self.lower)
        x = max(1, round(x * self.size[dim]))
        size = (self.width, x) if dim else (x, self.height)
        self[0].config(size=size)
