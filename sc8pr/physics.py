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
