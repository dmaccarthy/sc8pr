# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from scropr.papplet import PApplet
from scropr.util import randColor, step, logError, CENTER, rectAnchor
from scropr.gui import GUI
from scropr.io import prompt, fileDialog, USERINPUT
from scropr.grid import OPEN, SAVE, FOLDER
from scropr.search import search
from scropr.image import Image
from scropr.geometry import distance, polar, unitVector, scalarProduct, intersect_polygon, tuple_times,\
    tuple_sub, tuple_add, segments, closest, eqnOfLine
from math import hypot, cos, sin, radians, degrees
import pygame


# Status constants...
DISABLED = 0
VISIBLE = 1
HIDDEN = 2
ENABLED = 3

# Edge actions...
NO_EDGE = 0
BOUNCE = -1
WRAP = -2
REMOVE = -3


class LockedException(Exception):
    def __init__(self):
        super().__init__("SpriteList modified while iterating")


def collide_sprite(left, right):
    "Default collision detection"
    if not left.rect.colliderect(right.rect):
        return False
    if left.radius:
        return collide_circ(left, right) if right.radius else collide_circ_rect(left, right)
    elif right.radius:
        return collide_circ_rect(right, left)
    return collide_rect_advanced(left, right)

def collide_circ_rect(circ, rect):
    "Collision between a circular sprite and a rectangular sprite"
    cx, cy = circ.posn
    rx, ry = rect.posn
    dx, dy = cx - rx, cy - ry
    sep, a = polar((dx,dy), True)
    a = (a - rect.angle) % 180
    if a > 90: a = 180 - a
    a = radians(a)
    dx, dy = sep * cos(a), sep * sin(a)
    w, h = rect.getSize(False)
    w /= 2
    h /= 2
    r = circ.radius
    return dx < w + r and dy < h + r

def collide_rect_advanced(left, right):
    "Collision between rectangles based on containment or segment intersection"
    return intersect_polygon(left.corners(), right.corners()) or left.contains(right.posn) or right.contains(left.posn)

def collide_rect(left, right):
    "Collision based on simple rectangle overlap"
    return left.rect.colliderect(right.rect)

def collide_circ(left, right):
    "Collision based on circle"
    sep = left.radius + right.radius
    return distance(left.posn, right.posn) < sep

def _changeSpin(sprite, dv, pt=None):
    "Adjust spin on bounce from edges or on collision"
    if not sprite.radius:
        if pt is None:
            sk = sprite.sketch
            rMin = None
            for cx, cy in sprite.corners():
                r = min(abs(cx), abs(sk.width-1-cx), abs(cy), abs(sk.height-1-cy))
                if pt is None or r <= rMin:
                    if r == rMin:
                        pt = (pt[0] + cx) / 2, (pt[1] + cy) / 2
                    else: pt = cx, cy
                    rMin = r
        x, y = tuple_sub(pt, sprite.posn)
        dL = x * dv[1] - y * dv[0]
        r = max(sprite.getSize(False))
        d = hypot(x, y)
        sprite.spin += degrees(dL / (r * r / 12 + d * d))


class Sprite():
    "A class for creating sprites with multiple costumes, motion, rotation, and zooming"
    _costumeTime = 0
    _nextChange = 0
    _radius = False
    spriteList = None
    status = VISIBLE
    currentCostume = 0
    posn = 0, 0
    velocity = 0, 0
    accel = 0, 0
    jerk = 0, 0
    zoom = 1
    zoomRate = 0
    angle = 0
    spin = 0
    orient = False
    edgeAdjust = None
    elasticity = 1.0
    drag = 0.0
    spinDrag = 0.0
    bounceThreshhold = 0

    def __init__(self, sprites, costumes, *group, **kwargs):
        if type(costumes) in (str, Image, pygame.surface.Surface):
            costumes = costumes,
        costumes = [Image(c) for c in costumes]
        size = costumes[0].size
        for i in range(1, len(costumes)):
            if costumes[i].size != size:
                costumes[i] = costumes[i].scale(size)
        self.costumes = costumes
        self._seq = tuple(range(len(self.costumes)))
        if not isinstance(sprites, SpriteList):
            sprites = sprites.sprites
        self.spriteList = sprites
        sprites.append(self, *group)
        self.config(**kwargs)
        if kwargs.get("posn") is None:
            self.posn = self.sketch.center
        edge = kwargs.get("edge")
        if edge is None:
            self.edge = self.sketch.edge()

    def config(self, **kwargs):
        "Set multiple attributes"
        r = kwargs.get("radius")
        for k in kwargs:
            if k != "radius":
                setattr(self, k, kwargs[k])
        if r: self.radius = r
        return self

    @property
    def unitVector(self):
        a = radians(self.angle)
        return cos(a), sin(a)

    @property
    def radius(self):
        return None if self._radius is False else self._radius * self.zoom

    @radius.setter
    def radius(self, r):
        if r is True: r = sum(self.getSize(False)) / 4
        self._radius = r / self.zoom

    @property
    def speed(self): return hypot(*self.velocity)

    def velocityAt(self, posn):
        v = tuple_sub(posn, self.posn)
        return tuple_add(tuple_times(v, self.spin), self.velocity)
        
    @property
    def costumeTime(self): return self._costumeTime

    @costumeTime.setter
    def costumeTime(self, frames):
        self._costumeTime = abs(frames)
        if self._nextChange > self._costumeTime:
            self._nextChange = self._costumeTime

    @property
    def edge(self): return self._edge

    @edge.setter
    def edge(self, edge):
        if edge == NO_EDGE: self._edge = None, None
        else: self._edge = (edge, edge) if type(edge) is int else edge

    def _oneEdge(self, wx, dim=0):
        "Adjust sprite properties when it reaches the edge of the screen"
        wx = wx[dim]
        if wx is not None:
            sk = self.sketch
            x = self.posn[dim]
            w = 2 * self.radius if self.radius else self.getSize(True)[dim]
            x1 = w / 2 * (1 if wx == BOUNCE else -1)
            x2 = sk.size[dim] - x1
            if x < x1 or x > x2:
                if wx not in {WRAP, BOUNCE}: self._setStatus(wx)
                else:
                    if wx == BOUNCE:
                        v = self.velocity[dim]
                        x = 2 * (x1 if x < x1 else x2) - x
                        vx, vy = self.velocity
                        if dim == 0:
                            vx *= -(self.elasticity ** 0.5)
                            if abs(vx) < self.bounceThreshhold: vx = 0
                            dv = vx - v, 0
                        else:
                            vy *= -(self.elasticity ** 0.5)
                            if abs(vy) < self.bounceThreshhold: vy = 0
                            dv = 0, vy - v
                        self.velocity = vx, vy
                        _changeSpin(self, dv)
                    else:
                        if x > x2: x = x1
                        else: x = x2
                    xy = self.posn
                    self.posn = (x, xy[1]) if dim == 0 else (xy[0], x)
                return True
        return False

    def frameStep(self):
        "Update the sprite state based on its velocity, spin, and zoom rate"
        if self.drag:
            self.velocity = tuple_times(self.velocity, 1 - self.drag)
        self.posn, self.velocity, self.accel = step(1, self.posn, self.velocity, self.accel, self.jerk)
        if self._edge is not None:
            x = self._oneEdge(self._edge, 0)
            y = self._oneEdge(self._edge, 1)
            self.edgeAdjust = x or y
        if self.orient:
            self.angle = polar(self.velocity, True)[1]
        elif self.spin:
            self.angle = (self.angle + self.spin) % 360
            if self.spinDrag:
                self.spin *= (1.0 - self.spinDrag)
        if self.zoomRate: self.zoom *= 1 + self.zoomRate
        if self._costumeTime > 0:
            self._nextChange -= 1
            if self._nextChange <= 0:
                n = self.currentCostume + 1
                self.currentCostume = 0 if n >= len(self._seq) else n
                self._nextChange = self._costumeTime

    _update = frameStep

    @property
    def update(self): return self._update

    @update.setter
    def update(self, func):
        self._update = func.__get__(self, self.__class__)

    @property
    def sketch(self):
        sp = self.spriteList
        return sp.sketch if sp else None

    @property
    def _image(self):
        "Return the current unzoomed and unrotated costume image"
        return self.costumes[self._seq[self.currentCostume]]

    @property
    def image(self):
        "Return a zoomed, rotated image"
        img = self._image
        if self.zoom != 1 or self.angle:
            img = img.transform(self.getSize(False), self.angle if self.angle else None)
        return img

    def getSize(self, rotated):
        "Calculate the sprite's rotated or unrotated size"
        w, h = self._image.size
        if rotated:
            a = radians(self.angle)
            c, s = abs(cos(a)), abs(sin(a))
            w, h = w * c + h * s, w * s + h * c
        if self.zoom != 1:
            w = self.zoom * w
            h = self.zoom * h
        return max(1, round(w)), max(1, round(h))

    @property
    def size(self): return self.getSize(False)

    @property
    def width(self): return self.size[0]

    @property
    def height(self): return self.size[1]

    def _setStatus(self, status):
        if status == REMOVE:
            self.remove()
        else: self.status = status

    def _setZoom(self, width=None, height=None):
        "Adjust zoom attribute to give the specified width or height"
        w, h = self._image.size
        self.zoom = width / w if width else height / h
        return self

    @width.setter
    def width(self, w): return self._setZoom(w)

    @height.setter
    def height(self, h): return self._setZoom(height=h)

    @property
    def rect(self):
        "Rectangle for the rotated sprite"
        size = self.getSize(True)
        return rectAnchor(self.posn, size, CENTER)

    def getRect(self, rotated=True):
        "Rectangle for the rotated or unrotated sprite"
        r = self.rect
        if not rotated and self.angle:
            size = self.getSize(False)
            r = rectAnchor(self.posn, size, CENTER)
        return r

    def _corners(self):
        "Generate corners of the rotated sprite"
        x, y = self.posn
        w, h = self.getSize(False)
        w /= 2
        h /= 2
        a = radians(self.angle)
        c, s = cos(a), sin(a)
        for px, py in ((w,h), (-w,h), (-w,-h), (w,-h)):
            yield x + c * px - s * py, y + c * py + s * px

    def corners(self): return tuple(self._corners())

    def contains(self, pts):
        "Determine if the sprite contains any of a sequence of points"
        if len(pts) == 2 and type(pts[0]) in (int, float):
            pts = pts,
        if self.radius:
            for p in pts:
                if distance(p, self.posn) < self.radius:
                    return True
        else:
            a = -radians(self.angle)
            s, c = sin(a), cos(a)
            xc, yc = self.rect.center
            w, h = self.getSize(False)
            w //= 2
            h //= 2
            for x, y in pts:
                x -= xc
                y -= yc
                x, y = abs(c * x - s * y), abs(s * x + c * y)
                if x < w and y < h: return True
        return False

    def exclude(self, pt):
        "Move sprite to exclude the specified point"
        if self.radius:
            r = tuple_sub(pt, self.posn)
            mag = hypot(*r)
            if mag < self.radius:
                dr = tuple_times(r, (mag - self.radius) / mag) if mag else (self.radius, 0)
                self.posn = tuple_add(self.posn, dr)
        elif self.contains(pt):
            rMin = None
            for s in segments(self.corners()):
                p = closest(eqnOfLine(*s), pt)
                r = distance(p, pt)
                if rMin is None or r < rMin:
                    rMin = r
                    closePt = p
            dr = tuple_sub(pt, closePt)
            self.posn = tuple_add(self.posn, dr)

    def toward(self, posn, mag=1):
        ux, uy = unitVector(self.posn, posn)
        return mag * ux, mag * uy

    def moveTo(self, path, speed=None):
        "Reposition the sprite on the path and make its velocity parallel to the path"
        self.posn, seg = path.closest(self.posn)[1:]
        u = unitVector(*seg)
        v = scalarProduct(u, self.velocity)
        if speed is not None:
            v = speed * (1 if v==0 else v / abs(v))
        self.velocity = v * u[0], v * u[1]
        return self

    def costumeSequence(self, costume=0, end=-1, oscillate=False):
        "Specify which costumes to use and their order"
        if type(costume) is int:
            if end < 0: end += len(self.costumes)
            seq = tuple(range(costume, end + 1))
        else: seq = costume
        if oscillate:
            seq = seq + tuple(reversed(seq[1:-1]))
        self._seq = seq
        self.currentCostume = 0
        return self

    def _statusFilter(self, status=None):
        if status == ENABLED: return self.status in {VISIBLE, HIDDEN}
        elif status is not None: return self.status == status
        else: return True

    def colliding(self, group=None, status=None, collided=collide_sprite):
        "Test if sprite is currently colliding"
        if group is None: group = self.spriteList
        for s in group:
            if s is not self and s._statusFilter(status) and collided(self, s):
                return True
        return False

    def collisionGen(self, group=None, status=None, collided=collide_sprite):
        "Generate a sequence of colliding sprites"
        if group is None: group = self.spriteList
        for s in group:
            if s is not self and s._statusFilter(status) and collided(self, s):
                yield s

    def collisions(self, group=None, status=None, collided=collide_sprite, seqType=set):
        "Return a set of colliding sprites"
        return seqType(self.collisionGen(group, status, collided))

    def transform(self, shift=(0,0), factor=1):
        "Apply a shift and/or scale transformation to the sprite's geometry"
        sx, sy = shift
        x, y = self.posn
        self.posn = factor * x + sx, factor * y + sy
        x, y = self.velocity
        self.velocity = factor * x, factor * y
        x, y = self.accel
        self.accel = factor * x, factor * y
        self.zoom *= factor
        self.bounceThreshhold *= factor

    def remove(self):
        sp = self.spriteList
        if sp: sp.remove(self)

    def top(self):
        "Move a sprite to the top of the sprite list"
        sp = self.spriteList
        if sp:
            sp.lock()
            sp.remove(self)
            sp.append(self)
        return self

    @property
    def index(self):
        "Return sprite index in sprite list"
        sp = self.spriteList
        if sp and self in sp: return sp._all.index(self)
        

class SpriteList():
    _debugCollide = False
    sketchHeight = None
    run = True
    _lock = False
    _groups = []

    def __init__(self, sk=None):
        self._all = []
        self.sketch = sk
        if sk: sk.sprites = self

    def __len__(self): return len(self._all)
    def __getitem__(self, n): return self._all[n]

    def __iter__(self):
        for s in self._all: yield s

    def lock(self):
        if self._lock: raise LockedException()

    def append(self, sprite, group=()):
        "Append a sprite to the list"
        self.lock()
        self._all.append(sprite)
        if type(group) is set: group = group,
        for g in group:
            g.add(sprite)
            if g not in self._groups:
                self._groups.append(g)
        return self

    def extend(self, sprites, group=()):
        "Append a sequence of sprites to the list"
        for s in sprites: self.append(s, group)

    def remove(self, sprites):
        "Remove a sequence of sprites from the list"
        if type(sprites) is not set:
            sprites = {sprites} if isinstance(sprites, Sprite) else set(sprites)
        for s in sprites:
            if self._lock:
                self._toRemove.add(s)
            else: self._all.remove(s)
        for g in self._groups: g-= sprites
        return sprites

    def empty(self):
        "Remove all sprites"
        self.lock()
        return self.remove(self._all)

    def config(self, sprites=None, **kwargs):
        "Call the config method for a sequence of sprites"
        if sprites is None: sprites = self
        for s in sprites: s.config(**kwargs)

    def action(self, func, sprites=None, **kwargs):
        "Perform an action for a sequence of sprites"
        if sprites is None: sprites = self
        for s in sprites: func(s, **kwargs)

    def search(self, group=None, match=None, **kwargs):
        "Return a list of sprites that match specified criteria"
        if group is None: group = self
        return list(search(group, match, **kwargs)) # set?

    def draw(self, srf=None):
        "Draw all sprites and call their update method"
        if not srf: srf = pygame.display.get_surface()
        for s in self:
            if s.status == VISIBLE:
                s.image.blitTo(srf, s.posn, CENTER)
                if self._debugCollide:
                    if s.radius:
                        x, y = s.posn
                        pygame.draw.circle(srf, randColor(), (round(x), round(y)), round(s.radius))
                    else:
                        pygame.draw.rect(srf, randColor(), s.rect)
        if self.run:
            self._toRemove = set()
            self._lock = True
            for s in self:
                if s.status:
                    try: s.update()
                    except: logError()
            self._lock = False
            if len(self._toRemove):
                self.remove(self._toRemove)
            del self._toRemove

    def transform(self, shift=(0,0), factor=1):
        "Apply a shift and/or scale transformation to the sprites' geometry"
        for s in self: s.transform(shift, factor)

    def at(self, posn, listAll=False):
        "Return the top-layer sprite, or a list of sprites containing the given position"
        if listAll:
            return [s for s in self if s.contains(posn)]
        n = len(self)
        while n:
            n -= 1
            s = self[n]
            if s.contains(posn): return s       

    def collisions(self, group=None, status=None, collided=collide_sprite):
        "Return a set of sprites from the group that are colliding with ANY sprite"
        if group is None: group = self
        coll = set()
        for s in group:
            if s not in coll and s._statusFilter(status):
                if s.colliding(self, status, collided):
                    coll.add(s)
        return coll

    def collisionsBetween(self, group1, group2=None, status=None, collided=collide_sprite):
        "Return the collisions between two groups as a 2-tuple of sprite sets"
        c1, c2 = set(), set()
        if group2 is None: group2 = group1
        for s in group1:
            tmp = s.collisions(group2, status, collided)
            if len(tmp):
                c1.add(s)
                c2 |= tmp
        return c1, c2

    def sort(self, group):
        "Order by sprite list index"
        return [s for s in self if s in group]


class Sketch(PApplet):
    "A class for creating sketches with sprite and GUI support"
    _start = 0
    io = None
    wall = False

    def edge(self):
        "Default edge behaviour for sprites"
        return BOUNCE if self.wall else REMOVE

    def __init__(self, setup=None):
        super().__init__(setup)

        # Encapsulate instances of SpriteList and GUI...
        self.sprites = SpriteList(self)
        self.gui = GUI(self)

        # Bind scropr.io input functions...
        self.prompt = prompt.__get__(self, self.__class__)
        self.fileDialog = fileDialog.__get__(self, self.__class__)

    def simpleDraw(self):
        "Redraw background and sprites"
        self.drawBackground()
        self.sprites.draw()

    draw = simpleDraw

    def animate(self, draw=None, eventMap=None):
        "Bind new draw and eventMap attributes and reset frameNumber property"
        if eventMap and type(eventMap) is not dict:
            eventMap = {None:eventMap}
        self._bind(None, draw, eventMap)
        self._start = self.frameCount

    def _fitImg(self, size):
        "Add wall when scaling background image to sketch size"
        self._bgImage.transform(size=size)
        if self.wall:
            self.scaledBgImage.borderInPlace(1, self.wall)
    
    @property
    def frameNumber(self):
        "Frames since last call to animate method"
        return self.frameCount - self._start

    def resize(self, size, mode=None, ev=None):
        "Scale all sprites on sketch resize"
        super().resize(size, mode, ev)
        sp = self.sprites
        h = sp.sketchHeight if sp.sketchHeight else self.initHeight
        h1 = self.height
        f = h1 / h
        if f != 1:
            sp.sketchHeight = h1
            sp.transform(factor=f)
