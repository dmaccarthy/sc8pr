# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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
from pygame.sprite import collide_mask, collide_rect, collide_circle
from sc8pr import BaseSprite, Image


class Sprite(BaseSprite):
    "Sprite animation with one or more costumes"
    costumeTime = 0
    _costumeNumber = 0

    def __init__(self, image, cols=1, rows=1, flip=0, padding=0):
        # Clone costumes images from existing list
        if type(image) in (list, tuple):
            tiles = [Image(s.image) for s in image]

        # Slice spritesheet into individual costumes and make flipped copies
        else: tiles = Image(image).tiles(cols, rows, flip, padding)

        # Initialize
        self._costumes = self.costumeList = tiles
        self._size = tiles[0].size

    @property
    def costumeNumber(self): return self._costumeNumber
 
    @costumeNumber.setter
    def costumeNumber(self, n):
        self._costumeNumber = n % len(self._costumes)

    def costume(self):
        "Return an Image instance of the current costume"
        n = self.costumeNumber
        return self._costumes[n].config(size=self.size, angle=self.angle)

    def costumeSequence(self, seq):
        "Select and order the costumes to animate"
        self._costumes = tuple(self.costumeList[i] for i in seq)
        return self

    @property
    def image(self):
        "Return the current costume as a scaled and rotated surface"
        return self.costume().image

    def contains(self, pos):
        "Determine if sprite contains the specified point"
        img = self.costume()
        img.rect = self.rect
        return img.contains(pos)

    def ondraw(self, cv):
        "Update sprite after drawing"
        n = self.costumeTime
        if n and cv.sketch.frameCount % n == 0:
            self.costumeNumber = self._costumeNumber + 1
        #return
        super().ondraw(cv)


def collide_rect_mask(left, right):
    return collide_rect(left, right) and collide_mask(left, right)

def collide_rect_circ(left, right):
    return collide_rect(left, right) and collide_circle(left, right)


class Collisions:

    def __init__(self, sk, collide=collide_rect_circ):
        self.sk = sk
        self.collide = collide

    def _group(self, g, convert=False):
        if g is None: g = self.sk.sprites()
        if convert and type(g) not in (tuple, list, set): g = tuple(g)
        return g

    def collisions(self, sprite, group=None, asBool=False):
        "Detect whether a sprite is colliding with any of the specified sprites"
        coll = {}
        for s in self._group(group):
            if s is not sprite:
                c = self.collide(sprite, s)
                if c:
                    if asBool: return True
                    coll[s] = c
        return False if asBool else coll

    def betweenMap(self, group1, group2=None):
        "Detect collisions between two groups and return a map"
        group2 = self._group(group2, True)
        collMap = {}
        for s in self._group(group1):
            for k, v in self.collisions(s, group2).items():
                collMap[(s,k)] = v
        return collMap

    def between(self, group1, group2=None, remove=False):
        "Detect collisions between two groups and return a 2-tuple of tuples"
        collMap = self.betweenMap(group1, group2)
        s1 = tuple(s[0] for s in collMap)
        s2 = tuple(s[1] for s in collMap)
        if remove:
            for s in s1 + s2: s.remove()
        return s1, s2

    def among(self, group=None, remove=False):
        "Return a map of collisions within a group of sprites"
        collMap = {}
        group = self._group(group, True)
        n = len(group)
        for i in range(n):
            s = group[i]
            c = self.collisions(s, group[i+1:])
            if c:
                if s not in collMap: collMap[s] = {}
                m = collMap[s]
                for k, v in c.items():
                    m[k] = v
                    if k not in collMap: collMap[k] = {s:True}
                    else: collMap[k][s] = True
        if remove:
            for k in collMap: k.remove()
        return collMap


def elasticCircles(mass1, mass2):
    "Set final velocities for an elastic collision between two circles"

    # Calculate the normal vector at contact point
    x1, y1 = mass1.pos
    x2, y2 = mass2.pos
    nx = x2 - x1
    ny = y2 - y1
    r = hypot(nx, ny)
    if r >= mass1.radius + mass2.radius:
        return # No contact!
    nx /= r
    ny /= r

    # Calculate initial momenta
    m1 = mass1.mass
    m2 = mass2.mass
    v1x, v1y = mass1.vel
    v2x, v2y = mass2.vel
    p1x = m1 * v1x
    p1y = m1 * v1y
    p2x = m2 * v2x
    p2y = m2 * v2y

    # Calculate impulse and final velocities
    impulse = 2 * (m2 * (p1x * nx + p1y * ny) - m1 * (p2x * nx + p2y * ny)) / (m1 + m2)
    if impulse > 0:
        mass1.vel = (p1x - impulse * nx) / m1, (p1y - impulse * ny) / m1
        mass2.vel = (p2x + impulse * nx) / m2, (p2y + impulse * ny) / m2
        return True

def physics(sk, model=elasticCircles):
    "Update colliding masses on a pair-wise basis"
    masses = tuple(sk.sprites("mass"))
    coll = []
    n = len(masses)
    for m1 in range(n-1):
        m = masses[m1]
        for m2 in range(m1 + 1, n):
            args = m, masses[m2]
            if model(*args): coll.extend(args)
    return tuple(m for m in masses if m in coll)
