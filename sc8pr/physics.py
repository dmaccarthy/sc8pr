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


from math import hypot
from sc8pr.shape import Polygon, Circle
from sc8pr.geom import transform2dGen, delta


def shapeOf(gr):
    "Return a Polygon or Circle describing a graphic object's shape"
    if isinstance(gr, Polygon) or isinstance(gr, Circle):
        return gr
    cache = gr._shapeCache
    angle = gr.angle if gr._shapeModel and hasattr(gr, "angle") else 0
    key = gr.rect, angle
    if key == cache[0]: return cache[1]
    if type(gr._shapeModel) in (int, float):
        s = Circle(gr.radius).config(pos=gr.pos)
    else:
        s = tuple(transform2dGen(gr._shapeModel, scale=gr.size,
            rotate=angle, shift=gr.rect.center))
        s = Polygon(*s, metrics=False)
    gr._shapeCache = key, s
    return s

def collide_shape(left, right):
    return collide_shape_details(left, right, False)

def collide_shape_details(left, right, details=True):
    sleft = shapeOf(left)
    sright = shapeOf(right)
    if type(sleft) is Circle and type(sright) is Circle:
        v = delta(sleft.pos, sright.pos)
        if hypot(*v) < sleft.radius + sright.radius:
            if details:
                c = sright.containsPoint(sleft.pos) or sleft.containsPoint(sright.pos)
                return delta(v, mag=(-1 if c else 1))
            else: return True
    return False
