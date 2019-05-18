# Copyright 2015-2019 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

version = 2, 1, "dev"

import sys, os, struct, zlib
from math import hypot
import pygame
import pygame.display as _pd
from pygame.transform import flip as _pyflip
from sc8pr._event import EventManager
from sc8pr.geom import transform2d, positiveAngle, delta
from sc8pr.util import CachedSurface, style, logError, sc8prData,\
    tile, rgba, drawBorder, hasAlpha

# Anchor point constants
TOPLEFT = 0
TOP = 1
TOPRIGHT = 2
LEFT = 4
CENTER = 5
RIGHT = 6
BOTTOMLEFT = 8
BOTTOM = 9
BOTTOMRIGHT = 10

# Edge behaviour constants
HORIZONTAL = 1
VERTICAL = 2
BOTH = 3
REMOVE_X = 4
REMOVE_Y = 8
REMOVE = 12
CIRCLE = 0
RECT = 1


class PixelData:
    "A class for storing, compressing, and converting raw pixel data"

    def __str__(self):
        name = type(self).__name__
        kb = len(self._data) / 1024
        return "<{0} {1} {3}x{4} [{2:.1f} kb]>".format(name, self.mode, kb, *self.size)

    def __init__(self, img, compress=False, codec=zlib):
        rgb = "RGBA", "RGB"
        self.compressed = False
        if type(img) is bytes: img = img[:-12], img[-12:]
        elif isinstance(img, Graphic):
            try: img = img.image
            except: img = img.snapshot()
        if type(img) is tuple:
            m, w, h, c = self._unpack(img[1])
            self.compressed = c
            self._data = img[0]
            self.size = w, h
        elif isinstance(img, pygame.Surface):
            self.size = img.get_size()
            bits = img.get_bitsize()
            m = "RGB" if bits == 24 else "RGBA" if bits == 32 else None
            self._data = pygame.image.tostring(img, m)
        else: # Pillow image
            self.size = img.size
            m = img.mode
            if m not in rgb:
                m = rgb[0]
                img = img.convert(m)
            self._data = img.tobytes()
        if m in rgb: self.mode = m
        else: raise NotImplementedError("Only RGB and RGBA modes are supported")
        self.codec = codec
        if compress: self.compress()

    def compress(self):
        if not self.compressed:
            self._data = self.codec.compress(self._data)
            self.compressed = True
        return self

    def decompress(self):
        if self.compressed:
            self._data = self.codec.decompress(self._data)
            self.compressed = False
        return self

    def _pack(self):
        m = self.mode
        m = 0 if m == "RGB" else 1
        if self.compressed: m += 2
        return struct.pack("!3I", m, *self.size)

    @staticmethod
    def _unpack(p):
        m, w, h = struct.unpack("!3I", p)
        c = bool(m & 2)
        m = "RGBA" if (m & 1) else "RGB" 
        return m, w, h, c

    def raw(self): return self._data, self._pack()
    
    def __eq__(self, other): return self.raw() == other.raw()

    def writeTo(self, f):
        for b in self.raw(): f.write(b)
        return self

    def __bytes__(self):
        b = self.raw()
        return b[0] + b[1]

    def _image(self, fn):
        "Convert raw data to an image using the function provided"
        data = self._data
        if self.compressed: data = self.codec.decompress(data)
        return fn(data, self.size, self.mode)

    @property
    def srf(self): return self._image(pygame.image.fromstring)

    @property
    def img(self): return Image(self.srf)

    def pil(self, pil):
        fn = lambda d,s,m: pil.Image.frombytes(m, s, d)
        return self._image(fn)


class Graphic:
    """Base class for graphics objects. Subclasses may provide a 'draw' method
    that draws the graphic onto the canvas as described by the clipping region
    of the surface passed as an argument. Alternatively, the subclass may
    provide a 'image' property which gives a surface that Graphic.draw can use."""
    autoPositionOnResize = True
    _avgColor = None
    canvas = None
    pos = 0, 0
    anchor = CENTER
    angle = 0
    focusable = False
    ondraw = None
    effects = None
    radiusFactor = 0.25

    @property
    def name(self):
        "The key used when adding the instance to a canvas"
        return getattr(self, "_name", None)

    def anon(self):
        "Remove the instance's key (_name)"
        if hasattr(self, "_name"): del self._name
        return self

    def __str__(self):
        name = self.name
        return "<{} '{}'>".format(type(self).__name__, name if name else id(self))

    def config(self, **kwargs):
        "Set multiple instance properties"
        for i in kwargs.items(): setattr(self, *i)
        return self

    def bind(self, *args, **kwargs):
        "Bind functions to an instance as methods"
        for f in args:
            setattr(self, f.__name__, f.__get__(self, self.__class__))
        for n, f in kwargs.items():
            if f is None: delattr(self, n)
            else:
                setattr(self, n, f.__get__(self, self.__class__))
        return self

    @property
    def avgColor(self): return self._avgColor


# Metrics

    @property
    def size(self): return self._size

    def resize(self, size): self._size = size

    @property
    def width(self): return self.size[0]

    @property
    def height(self): return self.size[1]

    @property
    def radius(self): return sum(self.size) * self.radiusFactor

    @property
    def aspectRatio(self):
        size = self.size
        return size[0] / size[1]

    @size.setter
    def size(self, size): self.resize(size)

    @width.setter
    def width(self, width):
        self.resize((width, width / self.aspectRatio))

    @height.setter
    def height(self, height):
        self.resize((height * self.aspectRatio, height))

    @property
    def center(self):
        size = self.size
        return (size[0] - 1) / 2, (size[1] - 1) / 2

    def blitPosition(self, offset, blitSize):
        "Return the position (top left) to which the graphic is drawn"
        x, y = self.pos
        x += offset[0]
        y += offset[1]
        a = self.anchor
        if a:
            x -= blitSize[0] * (a & 3) // 2
            y -= blitSize[1] * (a & 12) // 8
        return x, y

    def calcBlitRect(self, blitSize):
        cv = self.canvas
        offset = cv.rect.topleft if cv else (0,0)
        return pygame.Rect(self.blitPosition(offset, blitSize) + blitSize) 

    def relXY(self, pos):
        "Calculate coordinates relative to the graphic object"
        if self.angle:
            xc, yc = self.rect.center
            x, y = transform2d(pos, preShift=(-xc,-yc), rotate=-self.angle)
            xc, yc = self.center
            return round(x + xc), round(y + yc)
        else:
            r = self.rect.topleft
            return pos[0] - r[0], pos[1] - r[1]

    def contains(self, pos):
        "Check if the graphic contains the coordinates"
        if self.angle:
            r = pygame.Rect((0,0), self.size)
            pos = self.relXY(pos)
        else: r = self.rect
        return bool(r.collidepoint(pos))

    def scaleVectors(self, fx, fy, attr=("pos", "vel", "acc")):
        "Scale one or more 2-vectors"
        for a in attr:
            try: # Skip undefined attributes
                x, y = getattr(self, a)
                setattr(self, a, (x * fx, y * fy))
            except: pass


# Canvas interaction

    def setCanvas(self, cv, key=None):
        "Add the object to a canvas"
#        key = self._name
        self.remove()
        if key: 
            if key in cv and cv[key] is not self:
                raise KeyError("Key '{}' is already in use".format(key))
            self._name = key
        self.canvas = cv
        cv._items.append(self)
        return self

    def remove(self, deleteRect=True):
        "Remove the instance from its canvas"
#        if cv and self in cv._items:
        try:
            cv = self.canvas
            self.anon()
            if deleteRect and hasattr(self, "rect"):
                del self.rect
            cv._items.remove(self)
        except: pass
        return self

    @property
    def layer(self): return self.canvas._items.index(self)

    @layer.setter
    def layer(self, n):
        "Arrange graphic within canvas"
        g = self.canvas._items
        if n < 0: n += len(g)
        i = g.index(self)
        g = g[:i] + g[i+1:]
        self.canvas._items = g[:n] + [self] + g[n:]

    @property
    def sketch(self):
        sk = self
        while sk.canvas: sk = sk.canvas
        return sk if isinstance(sk, Sketch) else None

    @property
    def focussed(self):
        return self is self.sketch.evMgr.focus

    def blur(self):
        sk = self.sketch
        ev = sk.evMgr
        if ev.focus is self: ev.focus = sk
        return self

    @property
    def path(self): return self.pathTo(None)

    def pathTo(self, cv):
        "List of parent canvases, beginning with the instance itself"
        g = self
        p = []
        while g is not None:
            p.append(g)
            if g is cv: g = None
            else: g = g.canvas                
        return p

    @property
    def dialog(self): return self.path[-2]

    def bubble(self, eventName, ev):
        "Pass an event to a different handler"
        self.sketch.evMgr.handle(self, eventName, ev)

    @property
    def timeFactor(self):
        sk = self.sketch
        return sk.timeFactor if (sk and sk.realTime) else 1

# Drawing

    def draw(self, srf):
        "Draw the graphic to a surface"
        img = self.surfaceEffect
        r = self.calcBlitRect(img.get_size())
        srf.blit(img, r.topleft)
        return r

    @property
    def surfaceEffect(self):
        "Apply effects to the surface"
        srf = self.image
        if self.effects:
            srf = srf.copy()
            for e in self.effects: srf = e.transition(srf, self.sketch.frameCount)
        return srf

    def snapshot(self, **kwargs):
        "Take a snapshot of the graphic and return it as a new Image instance"
        srf = self.surfaceEffect
        if kwargs: srf = style(srf, **kwargs)
        return Image(srf)

    def save(self, fn, **kwargs):
        "Save a snapshot of the graphic"
        self.snapshot(**kwargs).save(fn)
        return self

    def at(self, pos, r=None):
        "Get the pixel color at the specified coordinates"
        srf = self.image
        if r is None:
            try: r = self.rect
            except: r = pygame.Rect((0,0), srf.get_size())
        if r.collidepoint(pos):
            x, y = r.topleft
            x, y = transform2d(pos, shift=(-x,-y))
            try: return srf.get_at((round(x), round(y)))
            except: pass


class Renderable(Graphic):
    "Graphics produced by calling a render method"
    stale = True

    def config(self, **kwargs):
        super().config(**kwargs)
        self.stale = True
        return self

    def refresh(self):
        if self.stale: self.image

    @property
    def avgColor(self):
        self.refresh()
        if self._avgColor is None:
            self._avgColor = pygame.transform.average_color(self._srf)
        return self._avgColor

    @property
    def image(self):
        if self.stale:
            self._srf = self.render()
            self._rotated = None
            self.stale = False
            self._avgColor = None
        srf = self._srf
        a = self.angle
        if a:
            r = self._rotated
            if r and r[0] == a: srf = r[1]
            else:
                srf = pygame.transform.rotate(srf, -a)
                self._rotated = a, srf
        return srf

    @property
    def size(self):
        self.refresh()
        return self._srf.get_size()

    def resize(self, size):
        self._size = size
        self.stale = True

    @size.setter
    def size(self, size): self.resize(size)


class BaseSprite(Graphic):
    "Base class for sprite animations"
    # Edge behaviours
    wrap = REMOVE
    bounce = bounceType = 0
    onbounce = None

    # Kinematics
    spin = 0
    vel = 0, 0
    acc = None
    drag = 0

    _pen = None

    @property
    def pen(self):
        p = self._pen
        return p[:2] if p else None

    @pen.setter
    def pen(self, p):
        if p and len(p) == 2:
            p = p + (self._pen[2] if self._pen else None,)
        if p: p = (rgba(p[0]),) + p[1:]
        self._pen = p

    def penReset(self):
        p = self._pen
        if p: self._pen = p[:2] + (None,)

    def resize(self, size):
        self._size = size
        self.penReset()

    def onwrap(self, update): self.penReset()

    def _bounce(self, cv):
        "Bounce sprite from the edge of its canvas"
        vx, vy = self.vel
        w, h = cv.size
        b = self.bounce
        update = 0
        if self.bounceType == 0:
            x, y = delta(self.rect.center, cv.rect.topleft)
            r = self.radius
            if b & HORIZONTAL and (x < r and vx < 0 or x > w-r and vx > 0):
                self.vel = -vx, vy
                update += HORIZONTAL
            if b & VERTICAL and (y < r and vy < 0 or y > h-r and vy > 0):
                self.vel = vx, -vy
                update += VERTICAL
        else:
            r = self.rect
            if b & HORIZONTAL and (r.left < 0 and vx < 0 or r.right >= w and vx > 0):
                self.vel = -vx, vy
                update += HORIZONTAL
            if b & VERTICAL and (r.top < 0 and vy < 0 or r.bottom >= h and vy > 0):
                self.vel = vx, -vy
                update += VERTICAL  
        return update

    circleBounce = _bounce

    def simpleWrap(self, cv):
        "Wrap sprite when it leaves the canvas"
        r = self.rect
        x, y = self.pos
        vx, vy = self.vel
        if not cv.rect.colliderect(r):
            if cv.canvas:
                dx, dy = cv.rect.topleft
                r.move_ip((-dx, -dy))
            w = self.wrap
            if w is True: w = BOTH
            if w & 5: # HORIZONTAL | REMOVE_X
                d = r.width + cv.width
                wrapX = True
                if r.right < 0 and vx <= 0: x += d
                elif r.left >= cv.width and vx >= 0: x -= d
                else: wrapX = False
                if wrapX and (w & 4):
                    self.remove()
                    return
            else: wrapX = False
            if w & 10: # VERTICAL | REMOVE_Y
                wrapY = True
                d = r.height + cv.height
                if r.bottom < 0 and vy <= 0: y += d
                elif r.top >= cv.height and vy >= 0: y -= d
                else: wrapY = False
                if wrapY and (w & 8):
                    self.remove()
                    return
            else: wrapY = False
            if wrapX or wrapY:
                update = HORIZONTAL if wrapX else 0
                if wrapY: update += VERTICAL
                self.onwrap(update)
            self.pos = x, y

    def kinematics(self):
        "Update motion based on spin, vel, acc, and drag properties"
        t = self.timeFactor
        x, y = self.pos
        vx, vy = self.vel
        if self.acc is not None:
            dvx, dvy = tuple(t * a for a in self.acc)
            self.pos = x + (vx + dvx / 2) * t, y + (vy + dvy / 2) * t
            self.vel = vx + dvx, vy + dvy
        else: self.pos = x + vx * t, y + vy * t
        self.angle = positiveAngle(self.angle + self.spin * t)
        d = self.drag 
        if d:
            if type(d) in (int, float): s = d
            else: d, s = d
            d = 1 - d
            self.vel = d * vx, d * vy
            self.spin *= 1 - s 

    def ondraw(self):
        "Update sprite properties after drawing each frame"
        cv = self.canvas
        if self.bounce:
            update = self._bounce(cv)
            if update and self.onbounce: self.onbounce(update)
        if self.wrap and self.simpleWrap(cv): return True
        self.kinematics()
        if self._pen:
            c, w, pos = self._pen
            if pos: cv._paint(pos, self.pos, c, w)
            self._pen = c, w, self.pos

    def toward(self, pos, mag=None):
        "Return a vector directed toward the specified position"
        if mag is None: mag = hypot(*self.vel)
        return delta(pos, self.pos, mag)


class Image(Graphic):
    "A class representing scaled and rotated images"

    def __init__(self, data=(2,2), bg=None):
        self._srf = CachedSurface(data, bg)
        self._size = self._srf.get_size()

    @property
    def original(self): return self._srf.original

    @property
    def avgColor(self):
        if self._avgColor is None:
            self._avgColor = pygame.transform.average_color(self._srf.original)
        return self._avgColor

    def dumpCache(self): self._srf.dumpCache()

    @staticmethod
    def fromBytes(data): return PixelData(data).img

    def tiles(self, cols=1, rows=1, flip=0, padding=0):
        "Create a list of images from a spritesheet"
        srf = self.image
        tiles = [Image(tile(srf, n, cols, rows, padding)) for n in range(cols*rows)]
        if flip & HORIZONTAL:
            tiles += [Image(_pyflip(s.image, True, False)) for s in tiles]
        if flip & VERTICAL:
            tiles += [Image(_pyflip(s.image, False, True)) for s in tiles]
        return tiles

    @property
    def image(self):
        "Return a scaled and rotated surface"
        return self._srf.get_surface(self._size, self.angle)

    def contains(self, pos):
        "Determine if the position is contained in the rect and not transparent"
        try: return bool(self.at(pos, self.rect).a)
        except: return False

    def save(self, fn):
        pygame.image.save(self._srf.original, fn)
        return self

    def copy(self): return Image(self.image.copy())


class Canvas(Graphic):
    _border = rgba("black")
    weight = 0

    def __init__(self, image, bg=None):
        if type(image) is str: bg = Image(image, bg)
        self._size = bg.size if isinstance(bg, Image) else image
        self.bg = bg
        self._items = []

    @property
    def border(self): return self._border

    @border.setter
    def border(self, color): self._border = rgba(color)

    @property
    def clipRect(self):
        "Calculate the clipping rect so as not to draw outside of the canvas"
        cv = self.canvas
        r = self.rect
        return r.clip(cv.clipRect) if cv else r # cv.rect

    @property
    def angle(self): return 0

    @property
    def bg(self): return self._bg

    @bg.setter
    def bg(self, bg): self._setBg(bg)
    
    def _setBg(self, bg):
        t = type(bg)
        if t is str: bg = pygame.Color(bg)
        elif t in (tuple, list): bg = pygame.Color(*bg)
        self._bg = bg

    @property
    def avgColor(self):
        bg = self.bg
        return bg.avgColor if isinstance(bg, Image) else bg

    def _paint(self, p1, p2, c=(255,0,0), w=4):
        try: cs = self.bg._srf
        except AttributeError:
            msg = "painting on canvas requires a background image"
            raise AttributeError(msg)
        key, scaled = cs.scaled
        if scaled is cs.original:
            scaled = scaled.copy()
            cs.scaled = key, scaled
        pygame.draw.line(scaled, c, p1, p2, w)

    def __len__(self): return len(self._items)

    def __contains__(self, i):
        for gr in self._items:
            if gr is i or getattr(gr, "_name", None) == i: return True
        return False

    def __getitem__(self, i):
        if type(i) in (int, slice): return self._items[i]
        if i:
            for gr in self._items:
                if getattr(gr, "_name", None) == i: return gr
        raise KeyError("{} contains no items with key '{}'".format(self, i))

    def __setitem__(self, key, gr):
        t = type(key)
        if not key.__hash__:
            raise KeyError("Type '{}' cannot be used as a key".format(t.__name__))
        elif t in (int, slice):
            raise KeyError("Assignment by layer is not supported")
#        gr._name = key
#        if gr.canvas is not self:
        if gr not in self: gr.setCanvas(self, key)

    def __iadd__(self, gr):
        "Add a Graphics instance(s) to the Canvas"
        if isinstance(gr, Graphic): gr.setCanvas(self)
        else:
            for g in gr: g.setCanvas(self)
        return self

    def __isub__(self, gr):
        "Remove item(s) from the canvas"
        if isinstance(gr, Graphic):
            if gr in self: gr.remove()
            else: raise ValueError("Cannot remove {} from {}".format(gr, self))
        else:
            for g in gr: self -= g
        return self

    append = __iadd__

    def purge(self, recursive=False):
        "Remove all content"
        while len(self._items):
            gr = self[-1]
            if recursive and isinstance(gr, Canvas): gr.purge()
            gr.remove()

    def shiftContents(self, offset, *args, resize=True):
        "Move contents and (optionally) adjust canvas size"
        dx, dy = offset
        for gr in self:
            if gr not in args:
                x, y = gr.pos
                gr.pos = x + dx, y + dy
        if resize:
            self._size = self._size[0] + dx,self._size[1] + dy
        return self

    def resize(self, size, resizeContent=True):
        "Resize the canvas contents"
        size = max(1, round(size[0])), max(1, round(size[1]))
        fx, fy = size[0] / self._size[0], size[1] / self._size[1]
        self._size = size

        # Resize content
        if resizeContent:
            for g in self:
                if g.autoPositionOnResize: g.scaleVectors(fx, fy)
                w, h = g.size
                g.resize((w * fx, h * fy))

    def draw(self, srf=None, mode=3):
        "Draw the canvas to a surface"

        # Calculate blit rectangle
        if srf is None: srf = self.image
        self.rect = r = self.calcBlitRect(self.size)

        # Draw background
        isSketch = isinstance(self, Sketch)
        if mode & 1:
            srf.set_clip(self.clipRect)
            if isinstance(self._bg, Image):
                self._bg.config(size=self._size)
                if isSketch and self.dirtyRegions:
                    self._drawDirtyRegions(srf)
                else: srf.blit(self._bg.image, r.topleft)
            elif self._bg: srf.fill(self._bg)

        # Draw objects
        if mode & 2:
            br = isSketch and self.dirtyRegions is not None
            if br: self.dirtyRegions = []
            for g in list(self):
                srf.set_clip(self.clipRect)
                if not hasattr(g, "image") and g.effects:
                    img = g.snapshot()
                    for a in ["pos", "anchor", "canvas", "effects"]:
                        setattr(img, a, getattr(g, a))
                    grect = img.draw(srf)
                else: grect = g.draw(srf)
                g.rect = grect
                if br: self.dirtyRegions.append(grect)
#                if g.ondraw and g.ondraw(): g.remove()
                if g.ondraw: g.ondraw()

        # Draw border
        if mode & 1 and self.weight:
            drawBorder(srf, self.border, self.weight, r)

        srf.set_clip(None)
        return r

    def snapshot(self):
        "Capture the canvas as an Image instance"
        srf = pygame.Surface(self.size, pygame.SRCALPHA)

        # Draw background
        if isinstance(self._bg, Image):
            self._bg.config(size=self._size)
            srf.blit(self._bg.image, (0,0))
        elif self._bg: srf.fill(self._bg)

        # Draw objects
        for g in self:
            if g.snapshot is not None:
                xy = g.blitPosition((0,0), g.size)
                srf.blit(g.snapshot().image, xy)
            else: g.draw(srf, snapshot=True)

        # Draw border
        if self.weight: drawBorder(srf, self.border, self.weight)
        return Image(srf)

    def objectAt(self, pos):
        obj = self
        for g in self:
            try: # Objects added but not yet blitted have no rect
                if g.contains(pos):
                    obj = g.objectAt(pos) if isinstance(g, Canvas) else g
            except: pass
        return obj

    def instOf(self, cls):
        "Yield all instance of the specified Graphics class"
        for g in self:
            if isinstance(g, cls): yield g

    def sprites(self): return self.instOf(BaseSprite)

    def everything(self):
        "Iterate through all Graphics recursively"
        for gr in self:
            yield gr
            if isinstance(gr, Canvas):
                for i in gr.everything(): yield i

    def find(self, criteria, recursive=False):
        "Yield all Graphics that meet the criteria"
        for gr in (self.everything() if recursive else self):
            if criteria(gr): yield gr

    @staticmethod
    def grid(*args, cols=None, size=None):
        "Arrange graphics in a grid"
        n = len(args)
        if cols is None: cols = n
        rows = n // cols
        if rows * cols < n: rows += 1
        args = [(a if isinstance(a, Graphic) else Image(a)) for a in args]
        w, h = size if size else args[0].size 
        cv = Canvas((w*cols, h*rows))
        r = c = 0
        for i in range(n):
            cv += args[i].config(anchor=TOPLEFT, pos=(c*w, r*h), size=(w, h))
            c += 1
            if c == cols:
                c = 0
                r += 1
        return cv


class Sketch(Canvas):
    capture = None
    realTime = False
    frameRate = 60
    anchor = 0
    _fixedAspect = True
    dirtyRegions = []

    def __init__(self, size=(512,288)):
        super().__init__(size, "white")
        self.quit = False
        self.frameCount = 0
        self.evMgr = EventManager(self)

    @property
    def caption(self): return _pd.get_caption()

    @caption.setter
    def caption(self, caption):
        return _pd.set_caption(caption)

    @property
    def focusable(self): return True

    @property
    def timeFactor(self):
        if self.frameCount == 1: return 1
        t = self.frameRate * self._clock.get_time() / 1000
        return min(t, 5.0)

    def onquit(self, ev): self.quit = True

    @property
    def bg(self): return self._bg

    @bg.setter
    def bg(self, bg):
        self._setBg(bg)
        if self.fixedAspect and hasattr(bg, "aspectRatio"):
            self.fixedAspect = bg.aspectRatio
        if self.dirtyRegions is not None:
            self.dirtyRegions = [pygame.Rect((0,0), self._size)]

    @property
    def cursor(self): return pygame.mouse.get_cursor()

    @cursor.setter
    def cursor(self, c):
        if c is True: c = pygame.cursors.arrow
        elif c is False: c = (8,8), (5,4), (0,0,0,0,0,0,0,0), (0,0,0,0,0,0,0,0)
        pygame.mouse.set_cursor(*c)

    def save(self, fn=None):
        if fn is None: fn = "save/img{:05d}.png".format(self.frameCount)
        pygame.image.save(self.image, fn)

    def cover(self):
        return Image(self.size, "#ffffffc0").config(anchor=TOPLEFT)

# Resizing methods

    @property
    def size(self): return self.image.get_size()

    @size.setter
    def size(self, size):
        if self.fixedAspect:
            self._fixedAspect = size[0] / size[1]
        self.resize(size)

    @property
    def fixedAspect(self): return self._fixedAspect

    @fixedAspect.setter
    def fixedAspect(self, a):
        self._fixedAspect = a
        if a: self.resize(self.size)

    def _aspectSize(self, size, initSize):
        "Modify sketch size to preserve aspect ratio"
        w, h = size
        w0, h0 = initSize
        a = self.fixedAspect
        if w0 == w: w = h * a
        elif h0 == h: h = w / a
        else:
            w = min(w, h * a)
            h = w / a
        return round(w), round(h)

    def _pygameMode(self, n): return pygame.RESIZABLE if n is True else int(n)

    def resize(self, size, mode=None):
        "Resize the sketch, maintaining aspect ratio if required"
        if mode is None: mode = self._mode
        else:
            mode = self._pygameMode(mode)
            self._mode = mode
        initSize = self.size
        size = round(size[0]), round(size[1])
        self.image = _pd.set_mode(size, mode)
        _pd.flip()
        if self.fixedAspect: size = self._aspectSize(size, initSize)
        if self.fixedAspect and sum(abs(x-y) for (x,y) in (zip(size, self.size))) > 1:
            return self.resize(size)
        super().resize(self.size)
        self._size = self.size
        if self.dirtyRegions is not None:
            self.dirtyRegions = [pygame.Rect((0,0), self._size)]

# Drawing methods

    def play(self, caption="sc8pr", icon=None, mode=True):
        "Initialize pygame and run the main drawing / event handling loop"

        # Initialize
        pygame.init()
        self._clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 80)
        _pd.set_caption(caption)
        try:
            try: icon = pygame.image.load(icon)
            except: icon = Image.fromBytes(sc8prData("alien")).image 
            _pd.set_icon(icon)
        except: logError()
        w, h = self._size
        self._fixedAspect = w / h
        mode = self._pygameMode(mode)
        self._mode = mode
        self.image = _pd.set_mode(self._size, mode)
        self.key = None
        self.mouse = pygame.event.Event(pygame.USEREVENT,
            code=None, pos=(0,0), description="Sketch startup")

        # Run setup
        try:
            if hasattr(self, "setup"): self.setup()
            else:
                main = sys.modules["__main__"]
                if hasattr(main, "setup"): main.setup(self)
        except: logError()

        # Drawing/event loop
        while not self.quit:
            try:
                self.frameCount += 1
                br = self.dirtyRegions
                flip = br is None
                self.draw()
                if not flip:
                    br += self.dirtyRegions
                    flip = self._largeArea()
                self._clock.tick(self.frameRate)
                if flip: _pd.flip()
                else: _pd.update(br)
                if self.capture is not None: self.capture.capture(self)
                if self.ondraw: self.ondraw()
                self._evHandle()
            except: logError()

        pygame.quit()
        mod = sys.modules.get("sc8pr.text")
        if mod: mod.Font.dumpCache()
        return self

    def _evHandle(self):
        "Handle events in the pygame event queue"
        for ev in pygame.event.get():
            try:
                if ev.type != pygame.VIDEORESIZE:
                    self.evMgr.dispatch(ev)
                elif ev.size != self.size:
                    self.resize(ev.size)
                    if hasattr(self, "onresize"): self.onresize(ev)
            except: logError()

    def _drawDirtyRegions(self, srf):
        "Redraw the background image into the dirtyRegions only"
        sRect = self.rect
        br = self.dirtyRegions
        if br:
            if br[0] == sRect: self.dirtyRegions = [sRect]
            for r in self.dirtyRegions:
                blitRect = r.clip(sRect)
                try: # Subsurface may be outside drawing surface
                    srf.blit(self._bg.image.subsurface(blitRect), blitRect.topleft)
                except: pass

    def _largeArea(self):
        "Determine if dirtyRegions area exceeds total sketch area"
        screen = self.rect
        large = screen.width * screen.height
        area = 0
        for r in self.dirtyRegions:
            r = r.clip(screen)
            area += r.width * r.height
            if area >= large: return True
        return False
