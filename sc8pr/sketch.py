# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from sc8pr.papplet import PApplet
from sc8pr.util import step, logError, CENTER, rectAnchor, addToMap
from sc8pr.gui import GUI
from sc8pr.io import prompt, fileDialog, USERINPUT
from sc8pr.grid import OPEN, SAVE, FOLDER
from sc8pr.search import search
from sc8pr.image import Image
from sc8pr.geom import DEG, unitVector, mag, neg, add, sub, times, sprod, cross2d,\
    vec2d, deg2d, Polygon2D, Circle2D, impact, ellipsygon, resolve2d, avg
from sc8pr.cache import Cache
from math import hypot, cos, sin, sqrt
import pygame
from pygame.mixer import Sound

# Status constants...
DISABLED = 0
VISIBLE = 1
HIDDEN = 2
ENABLED = 3

# Edge actions...
REMOVE_X = 1
WRAP_X = 2
BOUNCE_X = 4
REMOVE_Y = 16
WRAP_Y = 32
BOUNCE_Y = 64
REMOVE = REMOVE_X | REMOVE_Y
WRAP = WRAP_X | WRAP_Y
BOUNCE = BOUNCE_X | BOUNCE_Y


class LockedException(Exception):
    def __init__(self):
        super().__init__("SpriteList modified while iterating")


def collide_shape_only(left, right):
    "Detect collisions based on sprites' shape attribute"
    return left.shape.collide(right.shape)

def collide_shape(left, right):
    "Detect collisions based on sprites' shape attribute only if blit rectangles overlap"
    brf = left.blitRectFilter and right.blitRectFilter
    if not brf or left.rect.colliderect(right.rect):
        return left.shape.collide(right.shape)
    return False

def collide_rect(left, right):
    "Collision based on simple rectangle overlap"
    return left.rect.colliderect(right.rect)


class Sprite():
    "A class for creating sprites with multiple costumes, motion, rotation, and zooming"
    _collideRegion = 0,
    _costumeTime = 0
    _nextChange = 0
    _shape = None
    posn = 0, 0
    velocity = 0, 0
    mass = 0
    spriteList = None
    status = VISIBLE
    currentCostume = 0
    tint = None
    accel = 0, 0
    jerk = 0, 0
    zoom = 1
    zoomRate = 0
    angle = 0
    spin = 0
    orient = False
    edgeAdjust = set()
    collideUpdate = False
    elasticity = 1.0
    drag = 0.0
    spinDrag = 0.0
    blitRectFilter = True

    def __init__(self, sprites, costumes, *group, **kwargs):
        self.costumes = costumes
        if not isinstance(sprites, SpriteList):
            sprites = sprites.sprites
        self.spriteList = sprites
        sprites.append(self, *group)
        self.polygon()
        if kwargs.get("posn") is None:
            self.posn = self.sketch.center
        self.config(**kwargs)
        self._shapeCache = Cache()
        if kwargs.get("edge") is None:
            self.edge = BOUNCE if self.sketch.wall else REMOVE

    def ellipsygon(self, n=1, size=(1,1), v=16):
        "Set shape property to a polygon that approximates an ellipse"
        w, h = self._image.size
        w = (w * size[0]) / 2
        h = (h * size[1]) / 2
        self.shape = ellipsygon(w, h, n, v)
        self.blitRectFilter = max(size) <= 1
        return self

    def polygon(self, *points):
        "Set shape property to a polygon"
        w, h = self._image.size
        self._moment = (w * w + h * h) / 12
        x = w/2
        y = h/2
        if len(points) == 0:
            points = (0,0), (w,0), (w,h), (0,h)
        self.shape = Polygon2D(points).transform2d(shift=neg((x,y)))
        self.blitRectFilter = True
        for px,py in self._shape.points:
            if px < -x or px > x or py < -y or py > y:
                self.blitRectFilter = False
                break
        return self
    
    def circle(self, radius=1):
        "Set shape property to a circle"
        r = min(self._image.size) / 2
        self._moment = r * r / 2
        self.shape = Circle2D(r * radius)
        self.blitRectFilter = radius <= 1
        return self

    @property
    def shape(self):
        "Return a zoomed and rotated shape"
        if self._shape is None: self.polygon()
        a = 0 if type(self._shape) is Circle2D else self.angle * DEG
        key = dict(scale=self.zoom, rotate=a, shift=self.posn)
        s = self._shapeCache.get(key)
        if s is None:
            s = self._shape.transform2d(**key)
            self._shapeCache.put(key, s)
        return s

    @shape.setter
    def shape(self, s): self._shape = s

    @property
    def moment(self):
        "Calculate the moment of inertia for collisions"
        return self.mass * self._moment * self.zoom ** 2

    def impulse(self, dp, a):
        "Adjust velocity and spin to account for an impulse"
        m = self.mass
        self.velocity = add(self.velocity, times(dp, 1/m))
        self.spin += mag(dp) * a / DEG

    def collideRegions(self, color=(0, 0, 255, 92), flags=3):
        "Set sprite to draw blit rectangle and/or shape"
        self._collideRegion = flags, color
        return self

    def _collideDraw(self):
        "Draw collision shape (circle or polygon)"
        img = Image(pygame.display.get_surface())
        s = self.shape
        if type(s) is Circle2D:
            circ = Image.ellipse(s.radius, fill=self._collideRegion[1], stroke=None)
            circ.blitTo(img, tuple(s.center), CENTER)
        else:
            img.plot(s.points, fill=self._collideRegion[1], stroke=None, closed=True)
#            img.plot(arrow(*s.points[:2]).points, stroke=(0,0,0))

    @property
    def costumes(self): return self._costumes

    @costumes.setter
    def costumes(self, costumes):
        "Convert costumes to Image instances and scale to a single size; initialize costume sequence"
        if type(costumes) in (str, Image, pygame.surface.Surface):
            costumes = costumes,
        costumes = [Image(c) for c in costumes]
        size = costumes[0].size
        for i in range(1, len(costumes)):
            if costumes[i].size != size:
                costumes[i] = costumes[i].scale(size)
        self._costumes = costumes
        self._seq = tuple(range(len(self.costumes)))

    def config(self, **kwargs):
        "Set multiple attributes"
        for k in kwargs: setattr(self, k, kwargs[k])
        self.calcRect()
        return self

    @property
    def unitVector(self):
        return vec2d(1, self.angle * DEG)

    @property
    def speed(self): return hypot(*self.velocity)

    def velocityAt(self, posn):
        "Calculate combined translational plus rotational velocity at a point"
        x, y = sub(posn, self.posn)
        w = self.spin / DEG
        return add(self.velocity, (-w * y, w * x))

    @property
    def costumeTime(self): return self._costumeTime

    @costumeTime.setter
    def costumeTime(self, frames):
        "Set the number of frames between costume changes"
        self._costumeTime = abs(frames)
        if self._nextChange > self._costumeTime:
            self._nextChange = self._costumeTime

#     @property
#     def location(self):
#         "Determine if sprite is within, on edge, or outside of sketch"
#         sk = self.sketch
#         skRect = pygame.Rect((0,0), sk.size)
#         spRect = self.shape.rect
#         if skRect.contains(spRect): n = 1
#         elif skRect.colliderect(spRect): n = 0
#         else: n = -1
#         return n

    def bounce(self, pMap, *lines):
        "Bounce the sprite upon collision with wall"
        edge = []
        for line in lines:
            pt = pMap[line] if line in pMap else None
            if pt:
                vx, vy = resolve2d(self.velocity, line.unit)
                if vy < 0:
                    edge.append(line)
                    if self.mass:
                        self.spriteList.impulse(self, None, avg(*pt), line.normal)
                    else:
                        e = self.elasticity
                        if e != 1:
                            e = sqrt(e)
                            vy *= e
                            if self.spin: self.spin *= e
                        self.velocity = add(times(line.unit, vx), times(line.normal, -vy))
        return edge

    def wrap(self, e):
        "Wrap or remove sprite after leaving sketch area"
        x = e & (WRAP_X | REMOVE_X)
        y = e & (WRAP_Y | REMOVE_Y)
        if x or y:
            w, h = self.sketch.size
            r = self.rect
            vx, vy = self.velocity
            dx = dy = 0
            if x:
                if vx <= 0 and r.right < 0:
                    dx = w + r.width
                    self.edgeAdjust.add(3)
                elif vx >= 0 and r.left >= w:
                    dx = -(w + r.width)
                    self.edgeAdjust.add(1)
            if y:
                if vy <= 0 and r.bottom < 0:
                    dy = h + r.height
                    self.edgeAdjust.add(0)
                elif vy >= 0 and r.top >= h:
                    dy = -(h + r.height)
                    self.edgeAdjust.add(2)
            if dx or dy:
                if (dx and x & REMOVE_X) or (dy and y & REMOVE_Y):
                    self._setStatus(REMOVE)
                else: self.posn = add(self.posn, (dx, dy))

    def edgeAction(self, e):
        "Check sprite for bounce, wrap, or remove action at sketch edge"
        self.edgeAdjust = set()
        wall = self.sketch._wallPoly
        pMap = {}
        for seg in wall.segments:
            pt = self.shape.intersect2d(seg.lineClone())
            if pt: pMap[seg] = pt
        if e & BOUNCE:
            segs = wall.segments
            if not e & BOUNCE_Y: segs = segs[1], segs[3]
            elif not e & BOUNCE_X: segs = segs[0], segs[2]
            self.edgeAdjust = set(wall.segments.index(line) for line in self.bounce(pMap, *segs))
        if e & (REMOVE | WRAP): # not self.edgeAdjust and 
            if not wall.containsPoint(self.posn):
                self.wrap(e)

    def frameStep(self):
        "Update the sprite state based on its velocity, spin, and zoom rate"
        if self.drag:
            self.velocity = times(self.velocity, 1 - self.drag)
        a = self.accel
        self.posn, self.velocity, self.accel = step(1, self.posn, self.velocity, a, self.jerk)
        self.edgeAction(self.edge)
        if self.orient:
            self.angle = deg2d(self.velocity)
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
        self.calcRect()

    update = frameStep

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
            a = round(self.angle, 2) if self.angle else None
            if a and 360 - a < 0.01: a = 0
            img = img.transform(self.getSize(False), a)
        if self.tint: img = img.clone().tint(self.tint)
        return img

    def getSize(self, rotated):
        "Calculate the sprite's rotated or unrotated size"
        w, h = self._image.size
        if rotated and self.angle:
            a = self.angle * DEG
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

    @property
    def center(self):
        w, h = self.size
        return w//2, h//2

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

    def calcRect(self):
        "Determine the sprite's blit rectangle"
        size = self.getSize(True)
        self._rect = rectAnchor(self.posn, size, CENTER)
        return self._rect

    @property
    def rect(self): return self._rect

    def contains(self, *pts):
        "Determine if the sprite contains any of a sequence of points"
        for p in pts:
            if (not self.blitRectFilter or self.rect.collidepoint(p)) and self.shape.containsPoint(p):
                return True
        return False

    def toward(self, posn, mag=1):
        return times(unitVector(sub(posn, self.posn)), mag)

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

    def colliding(self, group=None, collided=collide_shape):
        "Test if sprite is currently colliding"
        if group is None: group = self.spriteList
        for s in group:
            if s is not self and collided(self, s):
                return True
        return False

    def collisionGen(self, group=None, collided=collide_shape):
        "Generate a sequence of colliding sprites"
        if group is None: group = self.spriteList
        for s in group:
            if s is not self and collided(self, s):
                yield s

    def collisions(self, group=None, collided=collide_shape, seqType=set):
        "Return a set of colliding sprites"
        return seqType(self.collisionGen(group, collided))

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

    def energy(self):
        return (self.mass * mag(self.velocity, 2) + self.moment * (self.spin * DEG) ** 2) / 2


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
            if s.status != DISABLED:
                debug = s._collideRegion[0]
                if s.status == VISIBLE and not (debug & 128):
                    srf.blit(s.image.surface, s.rect)
                if debug & 1: pygame.draw.rect(srf, (0,0,0), s.rect, 1)
                if debug & 2: s._collideDraw()
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

    @staticmethod
    def impulse(sp1, sp2, pt, normal):
        "Apply linear and angular impulses to impacting sprites"
        v1 = sp1.velocity
        s1 = sp1.spin * DEG
        b1 = cross2d(sub(pt, sp1.posn), normal)
        if sp2:
            v2 = sp2.velocity
            s2 = sp2.spin * DEG
            b2 = cross2d(sub(pt, sp2.posn), normal)
            b = sprod(normal, sub(v1, v2)) + s1 * b1 - s2 * b2
        else:
            b = sprod(normal, v1) + s1 * b1
        if b < 0:
            m1 = sp1.mass 
            I1 = sp1.moment
            a1 = b1 / I1
            if sp2:
                m2 = sp2.mass
                I2 = sp2.moment
                a2 = b2 / I2
                E = (m1 * mag(v1, 2) + m2 * mag(v2, 2) + I1 * s1 * s1 + I2 * s2 * s2) / 2
                a = (1 / m1 + 1 / m2 + b1 * a1 + b2 * a2) / 2
                c = (1 - (sp1.elasticity + sp2.elasticity) / 2) * E
            else:
                E = (m1 * mag(v1, 2) + I1 * s1 * s1) / 2
                a = (1 / m1 + b1 * a1) / 2
                c = (1 - sp1.elasticity) * E
            d = (-b + sqrt(max(0, b*b - 4*a*c))) / (2*a)
            d = times(normal, d)
            sp1.impulse(d, a1)
            if sp2: sp2.impulse(neg(d), -a2)
#         else:
#             print(normal, v1, sp2 is None)
    
    def physics(self):
        "Detect and apply conservation laws to colliding masses"
        cMap = {}
        for sp1 in self:
            if sp1.mass:
                sp1.collideUpdate = False
                for sp2 in self[sp1.index+1:]:
                    brf = sp1.blitRectFilter and sp2.blitRectFilter
                    if sp2.mass and (not brf or collide_rect(sp1, sp2)):
                        normal = impact(sp1.shape, sp2.shape)
                        if normal:
                            self.impulse(sp1, sp2, *normal)
                            addToMap(cMap, sp1, {sp2})
                            addToMap(cMap, sp2, {sp1})
        for sp1 in cMap: sp1.collideUpdate = True
        return cMap

    def collisionMap(self, group1=None, group2=None, collided=collide_shape):
        "Construct a map of colliding sprites"
        if group1 is None: group1 = self
        if group2 is None: group2 = group1
        group2 = set(group2)
        cMap = {}
        done = set()
        for s in group1:
            if s in cMap: group = group2 - cMap[s]
            else: group = group2
            coll = s.collisions(group - done, collided)
            done.add(s)
            if len(coll):
                addToMap(cMap, s, coll)
                for c in coll:
                    if c in group1:
                        addToMap(cMap, c, {s})
        return cMap

    def collisions(self, group=None, collided=collide_shape):
        "Return a set of sprites from the group that are colliding with ANY sprite"
        cMap = self.collisionMap(group, None, collided)
        return set([c for c in cMap])

    def collisionsBetween(self, group1, group2=None, collided=collide_shape):
        "Return the collisions between two groups as a 2-tuple of sprite sets"
        cMap = self.collisionMap(group1, group2, collided)
        c1 = set()
        c2 = set()
        for s in cMap:
            c1.add(s)
            c2 |= cMap[s]
        return c1, c2

    def sort(self, group):
        "Order by sprite list index"
        return [s for s in self if s in group]


class Sketch(PApplet):
    "A class for creating sketches with sprite and GUI support"
    _start = 0
    _sounds = {}
    io = None
    wall = None

    def __init__(self, setup=None):
        super().__init__(setup)

        # Encapsulate instances of SpriteList and GUI...
        self.sprites = SpriteList(self)
        self.gui = GUI(self)

        # Bind sc8pr.io input functions...
        self.prompt = prompt.__get__(self, self.__class__)
        self.fileDialog = fileDialog.__get__(self, self.__class__)

    def simpleDraw(self):
        "Redraw background and sprites"
        self.drawBackground()
        if self.wall: self.drawWall(self.wall)
        self.sprites.draw()

    draw = simpleDraw

    def physicsDraw(self):
        "Apply 2D physics behaviour to sprites after drawing"
        self.simpleDraw()
        self.sprites.physics()

    def drawWall(self, color, weight=1):
        "Draw a wall around the outside of the sketch"
        w, h = self.size
        w -= 1
        h -= 1
        pts = (0,0), (w,0), (w,h), (0,h)
        pygame.draw.lines(self.surface, color, True, pts, weight)

    def animate(self, draw=None, eventMap=None):
        "Bind new draw and eventMap attributes and reset frameNumber property"
        if eventMap and type(eventMap) is not dict:
            eventMap = {None:eventMap}
        self._bind(None, draw, eventMap)
        self._start = self.frameCount

    @property
    def frameNumber(self):
        "Frames since last call to animate method"
        return self.frameCount - self._start

    def resize(self, size, mode=None, ev=None):
        "Scale all sprites on sketch resize"
        super().resize(size, mode, ev)
        sp = self.sprites
        h = sp.sketchHeight if sp.sketchHeight else self.initHeight
        w1, h1 = self.size
        if h1 != h:
            sp.sketchHeight = h1
            sp.transform(factor=h1/h)
        w1 -= 1
        h1 -= 1
        self._wallPoly = Polygon2D([(0,0), (w1,0), (w1,h1), (0,h1)])

    def loadSounds(self, *args):
        "Pre-load sound files into the '_sounds' buffer"
        for s in args:
            if type(s) is str: key = s
            else: s, key = s
            try: self._sounds[key] = Sound(s)
            except: logError()

    def sound(self, key, cache=True, **kwargs):
        "Play a sound"
        snd = self._sounds.get(key)
        if not cache or snd is None:
            try:
                snd = Sound(key)
                if cache: self._sounds[key] = snd
            except: logError()
        if snd: snd.play(**kwargs)
        return snd
