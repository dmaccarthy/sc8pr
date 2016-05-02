# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of "scropr".
#
# "scropr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "scropr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "scropr".  If not, see <http://www.gnu.org/licenses/>.


from scropr.sketch import Sketch, VISIBLE, HIDDEN, _changeSpin
from scropr.geometry import tuple_add, tuple_times, tuple_sub, segments, polar, distance, scalarProduct,\
    closest, direction_of_line, eqnOfLine, intersect_segment_circle, intersect_polygon, tuple_avg
from math import pi, sin, cos


class Environment(Sketch):
    "Representation of a physics-based environment suitable for robotics simulations"

    @staticmethod
    def collidable(sprite):
        "Determine which sprites participate in collisions"
        return sprite.status in (VISIBLE, HIDDEN) and hasattr(sprite, "mass") and sprite.mass > 0

    def run(self, size=(800,600), caption="Environment", icon=None, mode=0):
        "Override default arguments"
        super().run(size, caption, icon, mode)

    def physicsDraw(self):
        "Transfer momentum between colliding masses before drawing"
        self.physics()
        self.simpleDraw()

    def physics(self):
        "Locate colliding masses and apply the law of momentum conservation"
        allMasses = self.sprites.search(match=self.collidable)
        masses = self.sprites.collisionsBetween(allMasses)[0]
        self.sprites.config(set(allMasses) - masses, collideUpdate = False)
        if masses:
            masses = list(masses)
            i = 1
            for s1 in masses[:-1]:
                for s2 in s1.collisions(masses[i:]):
                    impDir = contact(s1,s2)
                    if impDir is not None:
                        elas = (s1.elasticity + s2.elasticity) / 2
                        pt, angle = impDir
                        v1 = s1.velocity
                        v2 = s2.velocity
                        dp = impulse(s1.mass, v1, s2.mass, v2, angle, elas)
                        dv = tuple_times(dp, 1 / s1.mass)
                        s1.velocity = tuple_add(v1, dv)
                        _changeSpin(s1, dv, pt)
                        dv = tuple_times(dp, -1 / s2.mass)
                        s2.velocity = tuple_add(v2, dv)
                        _changeSpin(s2, dv, pt)
                        s1.collideUpdate = True
                        s2.collideUpdate = True
            return masses
    
    draw = physicsDraw


# Collision physics...

def momentum(*args):
    "Calculate the net momentum for a system of masses"
    p = [tuple_times(v, m) for (m, v) in args]
    return tuple_add(*p)

def impulse(m1, v1, m2, v2, impulseRadians=0, elasticity=1):
    "Calculate the impulse for collision between two masses"
    p = momentum((m1, v1), (m2, v2))
    dv = tuple_times(p, -1 / (m1 + m2))
    v1 = tuple_add(v1, dv)
    return impulseCM(tuple_times(v1, m1), impulseRadians, elasticity)

def impulseCM(p, impulseRadians, elasticity):
    "Calculate the collision impulse in centre of mass frame"
    mag, angle = polar(p)
    angle += pi - impulseRadians
    a = elasticity ** 2 - sin(angle) ** 2
    dp = cos(angle)
    if a > 0: dp += a ** 0.5
    dp = abs(mag * dp)
    return dp * cos(impulseRadians), dp * sin(impulseRadians)

def contact(sprite1, sprite2):
    "Determine the point of contact and impulse direction for two colliding sprites"
    if sprite1.radius and sprite2.radius:
        c = circ_contact(sprite1, sprite2)
    elif sprite1.radius or sprite2.radius:
        c = circ_rect_contact(sprite1, sprite2)
    else:
        c = rect_contact(sprite1, sprite2)
    if c is not None:
        sprite1.exclude(c[0])
        sprite2.exclude(c[0])
    return c

def circ_rect_contact(c, r):
    "Determine the point of contact and impulse direction for a colliding circle and rectangle"
    switch = not c.radius
    if switch: c, r = r, c
    p = []
    for s in segments(r.corners(), True):
        p.extend(intersect_segment_circle(s, c.posn, c.radius))
    p = tuple_avg(*p)
    if p is None: return None
    seg = (p, c.posn) if switch else (c.posn, p)
    return p, polar(tuple_sub(*seg))[1]

def circ_contact(sprite1, sprite2):
    "Determine the point of contact and direction for two colliding circles"
    seg = sprite1.posn, sprite2.posn
    eqn = eqnOfLine(*seg)
    p = []
    for s in (sprite1, sprite2):
        p.extend(intersect_segment_circle(seg, s.posn, s.radius, eqn))
    p = tuple_avg(*p)
    if p is None: return None
    a = polar(tuple_sub(sprite1.posn, p))[1]
    return p, a

def rect_contact(sprite1, sprite2):
    "Determine the point of contact and impulse direction for two colliding rectangles"
    c1 = sprite1.corners()
    c2 = sprite2.corners()
    p = intersect_polygon(c1, c2, True)
    p = tuple_avg(*p)
    if p is None: return None
    r1, data1 = collisionSegment(c1, p)
    r2, data2 = collisionSegment(c2, p)
    eqn = (data1 if r2 < r1 else data2)[1]
    a = direction_of_line(eqn, True)
    u = cos(a), sin(a)
    dr = tuple_sub(p, sprite1.posn)
    if scalarProduct(u, dr) > 0:
        a += -pi if a >= pi else pi
    return p, a

def collisionSegment(corners, pt):
    "Identify the segment on which the collision point lies"
    rMin = None
    for s in segments(corners):
        eqn = eqnOfLine(*s)
        r = distance(closest(eqn, pt), pt)
        if rMin is None or r < rMin:
            rMin = r
            data = s, eqn
    r = [distance(c, pt) for c in data[0]]
    return min(r), data
