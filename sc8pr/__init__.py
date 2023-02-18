# Copyright 2015-2023 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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


version = 3, 0, "a2"
print("sc8pr {}.{}.{}: https://dmaccarthy.github.io/sc8pr".format(*version))

import PIL.Image  # Omit from sc8pr-core
import sys, struct, zlib #, io
from math import hypot, sqrt
import pygame
import pygame.display as _pd
from pygame.transform import flip as _pyflip
from sc8pr._event import EventManager
from sc8pr._cs import CoordSys
from sc8pr.geom import transform2d, positiveAngle, delta, sigma, vmult, neg
from sc8pr.util import CachedSurface, style, logError, sc8prData, resolvePath, tile, rgba, drawBorder, crop, export, customEv

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

# pygame 1.9 <--> 2.0 compatibility
SIZECHANGED = getattr(pygame, "WINDOWSIZECHANGED", None)
WINEXPOSED = getattr(pygame, "WINDOWEXPOSED", None)

pygame.init()
pygame.key.set_repeat(400, 80)


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
        elif type(img) is PixelData: img = img.raw()
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
        else: raise NotImplementedError("Only RGB (24-bit) and RGBA (32-bit) modes are supported")
        self.codec = codec
        if compress: self.compress()
        elif self.compressed: self.decompress()

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

    @property
    def png(self): return export(self.srf).read()

    @property
    def jpg(self): return export(self.srf, "a.jpg").read()

# Omit pil and _frombytes from sc8pr-core

    @property
    def pil(self):
        return self._image(self._frombytes)
#         raise NotImplementedError("sc8pr-core disables features that depend on Pillow")

    @staticmethod
    def _frombytes(d, s, m): return PIL.Image.frombytes(m, s, d)


class Graphic:
    """Base class for graphics objects. Subclasses may provide a 'draw' method
    that draws the graphic onto the canvas as described by the clipping region
    of the surface passed as an argument. Alternatively, the subclass may
    provide a 'image' property which gives a surface that Graphic.draw can use."""
    autoPositionOnResize = True
    _avgColor = None
    _preserve = "xy", "size"
    scrollable = True
    canvas = None
    pos = 0, 0
    anchor = CENTER
    angle = 0
    hoverable = True
    focusable = False
    effects = None
    radiusFactor = 0.25

    @property
    def name(self):
        "The key used when adding the instance to a canvas"
        return getattr(self, "_name", None)

    @property
    def _str_name(self):
        name = self.name
        if name is None: name = id(self)
        return "{} '{}'".format(type(self).__name__, name)

    def anon(self):
        "Remove the instance's key (_name)"
        if hasattr(self, "_name"): del self._name
        return self

    def __str__(self):
        name = self.name
        return "<{} '{}'>".format(type(self).__name__, name if name else id(self))

    def _config(self, error_mode=1, **kwargs):
        "Set multiple instance properties; handle excpetions"
        for i in kwargs.items():
            try: setattr(self, *i)
            except Exception as e:
                if error_mode == 1: logError()
                elif error_mode == 2: raise e
        return self

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

    def scale(self, sx, sy=None):
        w, h = self.size
        self.size = sx * w, (sx if sy is None else sy) * h
        return self

    @property
    def center(self):
        size = self.size
        return (size[0] - 1) / 2, (size[1] - 1) / 2

    @property
    def clockwise(self):
        try: return self.canvas.clockwise
        except: return True

    @property
    def xy(self):
        "Position relative to canvas coordinate system"
        try: return self.canvas.cs(*self.pos)
        except: return self.pos

    @xy.setter
    def xy(self, pos):
        try: self.pos = self.canvas.px(*pos)
        except: self.pos = pos

    @property
    def theta(self):
        "Graphic angle in the same sense as the coordinate system"
        return self.angle if self.clockwise else -self.angle

    @theta.setter
    def theta(self, theta):
        self.angle = theta if self.clockwise else -theta

    def blitPosition(self, offset, blitSize):
        "Return the position (top left) to which the graphic is drawn"
        x, y = self.pos
        x += offset[0]
        y += offset[1]
        a = self.anchor
        if a: # (blitSize[*] - 1) makes robot jiggly
            x -= blitSize[0] * (a & 3) // 2
            y -= blitSize[1] * (a & 12) // 8
        return x, y

    def calcBlitRect(self, blitSize):
        cv = self.canvas
        offset = cv.rect.topleft if cv else (0,0)
        return pygame.Rect(self.blitPosition(offset, blitSize), blitSize) ## !!!

    def relPos(self, pos):
        "Calculate coordinates relative to the graphic object"
        if self.angle:
            x, y = transform2d(pos, shift1=neg(self.rect.center), matrix=-self.angle, shift2=self.center)
            return round(x), round(y)
        else:
            return delta(pos, self.rect.topleft)

    def contains(self, pos):
        "Check if the graphic contains the coordinates"
        if self.angle:
            r = pygame.Rect((0,0), self.size)
            pos = self.relPos(pos)
        else: r = self.rect
        return bool(r.collidepoint(pos))

    def scaleVectors(self, fx, fy, attr=("pos", "vel", "acc", "_scrollSize")):
        "Scale one or more 2-vectors"
        for a in attr:
            try: # Skip undefined or fixed attributes
                x, y = getattr(self, a)
                setattr(self, a, (x * fx, y * fy))
            except: pass


# Canvas interaction

    def _setCanvas(self, cv, key):
        self.remove()
        if key:
            if key in cv and cv[key] is not self:
                raise KeyError("Key '{}' is already in use".format(key))
            self._name = key
        self.canvas = cv
        cv._items.append(self)

    def setCanvas(self, cv, key=None):
        "Add the object to a canvas"
        xy = self.xy
        t = self.theta
        self._setCanvas(cv, key)
        self._config(0, xy=xy, theta=t)
        return self

    def remove(self, deleteRect=False):
        "Remove the instance from its canvas"
        cv = self.canvas
        try:
            if deleteRect and hasattr(self, "rect"):
                del self.rect
            if cv:
                self.anon()
                cv._items.remove(self)
                if self.focussed: self.blur()
        except: pass
        return self

    def toggle(self, name=None):
        cv = self.canvas
        if cv is not None:
            if self in cv: self.remove()
            else: self.setCanvas(cv, name)
        return self

    @property
    def layer(self):
        try: return self.canvas._items.index(self)
        except: pass

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

    def blur(self, trigger=False):
        "Relinquish event focus to the sketch"
        sk = self.sketch
        if self is sk.evMgr.focus: sk.focus(trigger)
        return self

    def focus(self, trigger=False):
        "Acquire event focus"
        if not self.focusable:
            raise AttributeError("Graphic instance is not focusable")
        sk = self.sketch
        if not sk:
            raise KeyError("Cannot focus graphic that has not been added to the sketch")
        evMgr = sk.evMgr
        gr = evMgr.focus
        trigger = trigger and gr is not self
        if trigger:
            ev = pygame.event.Event(pygame.USEREVENT, focus=self, hover=evMgr.hover)
            evMgr.handle(gr, "onblur", ev)
        evMgr.focus = self
        if trigger: evMgr.handle(self, "onfocus", ev)
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

    def bubble(self, eventName, ev={}):
        "Pass an event to a different handler"
        if not isinstance(ev, pygame.event.EventType):
            ev = pygame.event.Event(pygame.USEREVENT, **ev)
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
            x, y = delta(pos, r.topleft) 
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

    def remove(self, deleteRect=False): # !!!
        super().remove(deleteRect)
        self.stale = True
        return self

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
        self._size = size # ???
        self.stale = True

    @size.setter
    def size(self, size): self.resize(size)


class BaseSprite(Graphic):
    "Base class for sprite animations"
    # Edge behaviours
    wrap = REMOVE
    bounce = bounceType = 0

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

    def onwrap(self, ev=None): self.penReset()

    def _simpleBounce(self, cv):
        "Bounce sprite from the edge of its canvas"
        vx, vy = self.vel
        w, h = cv.size
        b = self.bounce
        where = CENTER
        if self.bounceType == 0:
            x, y = delta(self.rect.center, cv.rect.topleft)
            r = self.radius
            if b & HORIZONTAL and (x < r and vx < 0 or x > w-r and vx > 0):
                self.vel = -vx, vy
                where += -1 if vx < 0 else 1
            if b & VERTICAL and (y < r and vy < 0 or y > h-r and vy > 0):
                self.vel = vx, -vy
                where += -4 if vy < 0 else 4
        else:
            r = self.rect
            if b & HORIZONTAL and (r.left < 0 and vx < 0 or r.right >= w and vx > 0):
                self.vel = -vx, vy
                where += -1 if x < r else 1
            if b & VERTICAL and (r.top < 0 and vy < 0 or r.bottom >= h and vy > 0):
                self.vel = vx, -vy
                where += -4 if vy < 0 else 4
        return where

    def _simpleWrap(self, cv):
        "Wrap sprite when it leaves the canvas"
        r = self.rect
        x, y = self.pos
        vx, vy = self.vel
        if not cv.rect.colliderect(r):
            if cv.canvas:
                dx, dy = cv.rect.topleft
                r.move_ip((-dx, -dy))
            w = self.wrap
            where = CENTER
            if w is True: w = BOTH
            if w & 5: # HORIZONTAL | REMOVE_X
                d = r.width + cv.width
                if r.right < 0 and vx <= 0:
                    x += d
                    where -= 1
                elif r.left >= cv.width and vx >= 0:
                    x -= d
                    where += 1
                if where != CENTER and (w & 4):
                    self.remove()
                    return
            if w & 10: # VERTICAL | REMOVE_Y
                d = r.height + cv.height
                if r.bottom < 0 and vy <= 0:
                    y += d
                    where -= 4
                elif r.top >= cv.height and vy >= 0:
                    y -= d
                    where += 4
                if (w & 8) and where not in (4, 5, 6):
                    self.remove()
                    return
            self.pos = x, y
            if where != CENTER: # and hasattr(self, "onwrap"):
                self.bubble("onwrap", {"where":where})

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

    def ondraw(self, ev=None):
        "Update sprite properties after drawing each frame"
        cv = self.canvas
        if self.bounce:
            where = self._simpleBounce(cv)
            if where != CENTER: # and hasattr(self, "onbounce"):
                self.bubble("onbounce", {"where":where})
        if self.wrap and self._simpleWrap(cv): return True
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

    def dumpCache(self):
        self._srf.dumpCache()
        return self

    @staticmethod
    def fromBytes(data): return PixelData(data).img

    @staticmethod
    def fromZip(key, archive=None):
        if archive is None: archive = resolvePath("sc8pr.data")
        return PixelData(sc8prData(key, archive=archive)).img

    def tiles(self, cols=1, rows=1, flip=0, padding=0):
        "Create a list of images from a spritesheet"
        srf = self.image
        tiles = [Image(tile(srf, n, cols, rows, padding)) for n in range(cols*rows)]
        if flip & HORIZONTAL:
            tiles += [Image(_pyflip(s.image, True, False)) for s in tiles]
        if flip & VERTICAL:
            tiles += [Image(_pyflip(s.image, False, True)) for s in tiles]
        return tiles

    def _cut(self, x=(), y=(), padding=0):
        "Generate images by cutting the original"
        srf = self.image
        x0 = 0
        for c in range(len(x) + 1):
            y0 = 0
            for r in range(len(y) + 1):
                try: h = y[r] - y0
                except: h = self.height - y0
                try: w = x[c] - x0
                except: w = self.width - x0
                yield Image(srf.subsurface(x0+padding, y0+padding, w-2*padding, h-2*padding))
                y0 += h
            x0 += w

    def cut(self, x=(), y=(), padding=0):
        return list(self._cut(x, y, padding))

    def flip(self, mode=HORIZONTAL):
        "Create a new image by flipping an existing instance"
        return Image(_pyflip(self.image, mode & HORIZONTAL, mode & VERTICAL))

    def crop(self, *args, bg=True):
        "Create a new Image instance by cropping an existing image"
        srf = self._srf.original
        return Image(srf.subsurface(pygame.Rect(*args)) if args else crop(srf, bg)) 

    def replace(self, oldColor=True, newColor=(255,255,255,0), dist=0.0001):
        "Copy the image and replace a (range of) colors"
        srf = self._srf.original.copy()
        if oldColor is True: oldColor = srf.get_at((0, 0))
        pygame.PixelArray(srf).replace(oldColor, rgba(newColor), dist)
        return Image(srf)

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

    @property
    def pix(self): return PixelData(self.image)

    @property
    def png(self): return export(self.image).read()

    @property
    def jpg(self): return export(self.image, "a.jpg").read()

    def copy(self): return Image(self.image.copy())


class Canvas(Graphic):
    _border = rgba("black")
    _clipArea = None
    weight = 0
    resizeContent = True

    def __init__(self, image, bg=None):
        self.resetCS()
        mode = 0 if type(image) is str else 1 if isinstance(image, Image) else 2
        if mode == 2: # tuple or list
            size = image
        elif bg:
            bg = Image(image, bg)
            size = bg.size
        else: # str or Image
            bg = image if mode else Image(image)
            size = bg.size
        self._size = size
        self._items = []
        self.bg = bg

    @property
    def clipArea(self): return self._clipArea

    @clipArea.setter
    def clipArea(self, r): self._clipArea = pygame.Rect(r)

    @property
    def _scroll(self): return 0, 0

    @property
    def clockwise(self):
        ux, uy = self.units
        return ux * uy > 0

    @property
    def units(self): return self._units

    def px_delta(self, dx=0, dy=0):
        ux, uy = self._units
        return dx*ux, dy*uy

    def cs_delta(self, dx=0, dy=0):
        ux, uy = self._units
        return dx/ux, dy/uy

    @property
    def unit(self):
        ux, uy = self.units
        return sqrt(abs(ux * uy))

    def px(self, *pt): return delta(self._px(pt), self._scroll)
    def cs(self, *pt): return self._cs(sigma(pt, self._scroll))
    def px_list(self, *args): return [self.px(*pt) for pt in args]
    def cs_list(self, *args): return [self.cs(*pt) for pt in args]

    def attachCS(self, lrbt, margin=0, size=None):
        "Attach a coordinate system to the canvas"
        if size is None: size = getattr(self, "scrollSize", self.size)
        self.coordSys = cs = CoordSys(lrbt, size, margin)
        self._cs, self._px = cs._tr
        self._units = delta(self.px(1, 1), self.px(0, 0))
        return self

    def _updateCS(self, adjust=True, scale=True):
        "Update the current coordinate system for the resized canvas"
        if self.coordSys is None:
            raise AttributeError("{} has no coordinate system to update".format(self))
        lrbt, m, (w0, h0) = self.coordSys._args
        size = getattr(self, "scrollSize", self.size)
        if scale: scale = size[0] / w0, size[1] / h0
        if adjust is True: adjust = self.attr_get()
        self.attachCS(lrbt, m)
        if adjust: self.attr_set(adjust, scale)
        return self

    def resetCS(self):
        "Remove the canvas coordinate system and reset to pixel coordinates"
        u = lambda x: x
        self._cs, self._px = u, u
        self._units = 1, 1
        self.coordSys = None
        return self

    @property
    def border(self): return self._border

    @border.setter
    def border(self, color): self._border = rgba(color)

    @property
    def clipRect(self):
        "Calculate the clipping rect so as not to draw outside of the canvas"
        cv = self.canvas
        r = self.rect
        if self.clipArea: r = r.clip(self.clipArea.move(*r.topleft))
        return r.clip(cv.clipRect) if cv else r

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
        elif t is slice:
            raise KeyError("Assignment by layer is not supported")
        if gr not in self:
            if t is int:
                n = key
                key = None
            gr.setCanvas(self, key)
            if t is int: gr.config(layer=n)

    def __iadd__(self, gr):
        "Add a Graphics instance(s) to the Canvas"
        if isinstance(gr, Graphic): gr.setCanvas(self)
        else:
            for g in gr: g.setCanvas(self)
        return self

    def __isub__(self, gr):
        "Remove item(s) from the canvas"
        if type(gr) is str: self[gr].remove()
        elif isinstance(gr, Graphic):
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
        return self

    def removeItems(self, *args):
        "Remove specified items without raising exceptions if item is not in canvas"
        for gr in args:
            try: self -= gr
            except: pass
        return self

    def shiftContents(self, offset, *args, resize=True):
        "Move contents and (optionally) adjust canvas size"
        dx, dy = offset
        for gr in self:
            if gr not in args:
                x, y = gr.pos
                gr.pos = x + dx, y + dy
        if resize:
            self._size = self._size[0] + dx, self._size[1] + dy
        return self

    def resize(self, size, resizeContent=None):
        "Resize the canvas contents"
        size = max(1, round(size[0])), max(1, round(size[1]))
        fx, fy = size[0] / self._size[0], size[1] / self._size[1]
        self._size = size

        # Resize scroll size
        if getattr(self, "resizeScroll", False):
            w, h = self.scrollSize
            self.scrollSize = round(fx * w), round(fy * h)

        # Resize content
        if resizeContent is None: resizeContent = self.resizeContent  
        if resizeContent:
            if self.coordSys: self._updateCS()
            else:
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
            ondrawList = self.sketch.ondrawList
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
                if hasattr(g, "ondraw"): ondrawList.append(g)

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
                img = g.snapshot().image
                srf.blit(img, g.blitPosition((0,0), img.get_size()))
            else: g.draw(srf, snapshot=True)

        # Draw border
        if self.weight: drawBorder(srf, self.border, self.weight)
        return Image(srf)

    def flatten(self, keep=()):
        "Draw graphics onto background and remove"
        if isinstance(keep, Graphic): keep = (keep,)
        keep = [(gr.name, gr) for gr in keep]
        for gr in keep: gr[1].remove()
        self.config(bg=self.snapshot()).purge()
        for name, gr in keep:
            if name: self[name] = gr
            else: self += gr
        return self

    def objectAt(self, pos, includeAll=False):
        obj = self
        for g in self:
            try: # Objects added but not yet blitted have no rect
                if (includeAll or g.hoverable) and g.contains(pos):
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

    def scroll(self, dx=0, dy=0):
        raise NotImplementedError("Use ScrollCanvas class.")

    def cover(self):
        return Image(self.size, "#ffffffc0").config(anchor=TOPLEFT)

    def attr_get(self, *args):
        data = {}
        for gr in self:
            d = {}
            for a in (args if args else gr._preserve):
                try: d[a] = getattr(gr, a)
                except: pass
            if d: data[gr] = d
        return data

    def attr_set(self, data, scale=None):
        for gr, d in data.items():
            if scale and "size" in d:
                d = d.copy()
                d["size"] = vmult(d["size"], scale)
            gr._config(0, **d)


class Sketch(Canvas):
    minSize = 32
    capture = None
    realTime = False
    frameRate = 60
    _fixedAspect = True
    dirtyRegions = []
    resizeTrigger = False
    _sys_cursor = pygame.mouse.get_cursor()

    def __init__(self, size=(512,288)):
        super().__init__(size, "white")
        self.quit = False
        self.frameCount = 0
        self.evMgr = EventManager(self)

    @property
    def focusable(self): return True

    @property
    def hoverable(self): return True

    @property
    def pos(self): return 0, 0

    @property
    def anchor(self): 0

    @property
    def caption(self): return _pd.get_caption()[0]

    @caption.setter
    def caption(self, caption):
        return _pd.set_caption(caption)

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
        if self._fixedAspect and hasattr(bg, "aspectRatio"):
            self._fixedAspect = bg.aspectRatio
            size = self.size
            self.resize(self._aspectSize(size, size))
        if self.dirtyRegions is not None:
            self.dirtyRegions = [pygame.Rect((0,0), self._size)]

    @property
    def cursor(self): return pygame.mouse.get_cursor()

    @cursor.setter
    def cursor(self, c):
        if c is True: c = Sketch._sys_cursor #pygame.cursors.arrow
        elif c is False: c = (8,8), (5,4), 8*(0,), 8*(0,)
        pygame.mouse.set_cursor(*c)

    def save(self, fn=None):
        if fn is None: fn = "save/img{:05d}.png".format(self.frameCount)
        pygame.image.save(self.image, fn)

# Resizing methods

    @property
    def size(self): return self.image.get_size()

    @size.setter
    def size(self, size):
        if self._fixedAspect:
            self._fixedAspect = size[0] / size[1]
        self.resize(size)

    @property
    def fixedAspect(self): return bool(self._fixedAspect)

    @fixedAspect.setter
    def fixedAspect(self, a):
        if a:
            w, h = self.size
            self._fixedAspect = w / h
        else: self._fixedAspect = False

    def _aspectSize(self, size, initSize):
        "Modify sketch size to preserve aspect ratio"
        w, h = size
        w0, h0 = initSize
        a = self._fixedAspect
        if w0 == w: w = h * a
        elif h0 == h: h = w / a
        else:
            w = min(w, h * a)
            h = w / a
        return round(w), round(h)

    def _pygameMode(self, n): return pygame.RESIZABLE if n is True else int(n)

    def resize(self, size, mode=None):
        "Resize the sketch, maintaining aspect ratio if required"
        initSize = self._size
        ms = self.minSize
        if self._fixedAspect:
            size = self._aspectSize(size, initSize)
            f = max(1, ms / min(size))
            size = round(f * size[0]), round(f * size[1])
        else:
            size = max(ms, round(size[0])), max(ms, round(size[1]))
        if mode is None: mode = self._mode
        else:
            mode = self._pygameMode(mode)
            self._mode = mode
        self.image = _pd.set_mode(size, mode)
        super().resize(self.size)
        self._size = self.size
        if self.dirtyRegions is not None:
            self.dirtyRegions = [pygame.Rect((0,0), self._size)]
        evMgr = self.evMgr
        ev = getattr(self, "_resize_ev", None)
        self._resize_ev = None
        if ev is None and self.resizeTrigger:
            ev = pygame.event.Event(pygame.USEREVENT, focus=evMgr.focus, hover=evMgr.hover)
        if ev: evMgr.handle(self, "onresize", ev)

# Drawing methods

    def play(self, caption="sc8pr", icon=None, mode=True):
        "Initialize pygame and run the main drawing / event handling loop"

        # Initialize
        if not pygame.get_init(): pygame.init()
        self._clock = pygame.time.Clock()
        _pd.set_caption(caption)
        try:
            try: icon = Image(icon)
            except: icon = Image.fromZip("alien")
            _pd.set_icon(icon.config(width=64).image)
        except: logError()
        w, h = self._size
        if self._fixedAspect: self._fixedAspect = w / h
        mode = self._pygameMode(mode)
        self._mode = mode
        self.image = _pd.set_mode(self._size, mode)
        self.key = None
        self.mouse = customEv(code=None, pos=(0,0), description="Sketch startup")

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
                self.ondrawList = []
                self.draw()
                if not flip:
                    br += self.dirtyRegions
                    flip = self._largeArea()
                self._clock.tick(self.frameRate)
                if flip: _pd.flip()
                else: _pd.update(br)
                self._capture()
                for gr in self.ondrawList:
                    gr.ondraw(customEv(target=gr, handler="ondraw"))
                if hasattr(self, "ondraw"):
                    self.ondraw(customEv(target=self, handler="ondraw"))
                self._evHandle()
            except: logError()

        pygame.quit()
        mod = sys.modules.get("sc8pr.text")
        if mod: mod.Font.dumpCache()
        return self

    def _capture(self):
        "Call screen capture method when recording"
        c = self.capture
        if c is not None:
            i = getattr(c, "interval", 1)
            if self.frameCount % i == 0:
                c.capture(self)

    def _evHandle(self):
        "Handle events in the pygame event queue"
        resized = False
        for ev in pygame.event.get():
            try:
                if ev.type in (pygame.VIDEOEXPOSE, WINEXPOSED) and self.dirtyRegions is not None:
                    self.dirtyRegions = [pygame.Rect((0,0), self._size)]
                if ev.type not in (pygame.VIDEORESIZE, SIZECHANGED):
                    self.evMgr.dispatch(ev)
                elif not resized:
                    size = ev.size if hasattr(ev, "size") else (ev.x, ev.y)
                    if size != self._size:
                        resized = True
                        setattr(ev, "originalSize", self._size)
                        self._resize_ev = ev
                        self.resize(size)
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
