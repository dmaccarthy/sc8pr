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


version = 2, 2, "a0"

import sys, os, struct, zlib
from math import hypot
import pygame
import pygame.display as _pd
from pygame.transform import flip as _pyflip
from sc8pr._event import EventManager
from sc8pr.geom import transform2d, positiveAngle, delta, sigma
from sc8pr.util import CachedSurface, style, logError, sc8prData, tile, rgba, drawBorder, hasAlpha

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
    _scrollAdjust = True
    canvas = None
    pos = 0, 0
    anchor = CENTER
    angle = 0
    hoverable = True
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

# Properties for PCanvas (plotting, scrollable)

    def _warn(self):
        print("Warning: {} has no canvas while setting cvPos or theta".format(str(self)), file=sys.stderr)

    @property
    def theta(self):
        cv = self.canvas
        return self.angle if cv is None or cv.clockwise else -self.angle

    @theta.setter
    def theta(self, t):
        cv = self.canvas
        if cv is None: self._warn()
        self.angle = t if cv is None or cv.clockwis else -t

    @property
    def csPos(self):
        cv = self.canvas
        return self.pos if cv is None else cv.cs(*self.pos)

    @csPos.setter
    def csPos(self, pos):
        cv = self.canvas
        if cv is None: self._warn()
        self.pos = pos if cv is None else cv.px(*pos)

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

    def scaleVectors(self, fx, fy, attr=("pos", "vel", "acc", "_scrollSize")):
        "Scale one or more 2-vectors"
        for a in attr:
            try: # Skip undefined attributes
                x, y = getattr(self, a)
                setattr(self, a, (x * fx, y * fy))
            except: pass


# Canvas interaction

    def setCanvas(self, cv, key=None):
        "Add the object to a canvas"
        self.remove()
        if key: 
            if key in cv and cv[key] is not self:
                raise KeyError("Key '{}' is already in use".format(key))
            self._name = key
        self.canvas = cv
        cv._items.append(self)
        return self

    def remove(self, deleteRect=False):
        "Remove the instance from its canvas"
        try:
            cv = self.canvas
            self.anon()
            if deleteRect and hasattr(self, "rect"):
                del self.rect
            cv._items.remove(self)
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

    def bubble(self, eventName, ev):
        "Pass an event to a different handler"
        self.sketch.evMgr.handle(self, eventName, ev)

    @staticmethod
    def _deiconify(icon, ev):
        "Icon 'onclick' handler"
        icon.icon_restore.deiconify()

    def iconify(self, **kwargs):
        "Replace a graphic by its icon"
        cv = self.canvas
        if self in cv:
            attr = dict(pos=self.pos, anchor=self.anchor, size=cv.iconSize)
            attr.update(kwargs)
            icon = self.icon.config(icon_restore=self, **attr)
            self.remove()
            cv += icon.bind(onclick=self._deiconify)
            cv.icons.append(icon)
        return self

    def deiconify(self):
        "Restore a previously iconified graphic"
        cv = self.canvas
        icon = self.icon
        if icon in cv.icons:
            icon.remove()
            cv.icons.remove(icon)
            cv += self
        return self

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

    def remove(self, deleteRect=False): # !!!
        super().remove(deleteRect)
        self.stale = True

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

    def crop(self, *args):
        "Create a new Image instance by cropping an existing image"
        return Image(self.image.subsurface(pygame.Rect(*args)))

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
    _scroll = 0, 0
    clipArea = None
    weight = 0
    resizeContent = True
    iconSize = 32, 32

    @staticmethod
    def _px(x): return x

    _cs = _px

    def __init__(self, image, bg=None):
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
        self.icons = [] # !!!
        self.bg = bg

    @property
    def clockwise(self): return True

    @property
    def units(self): return 1, 1

    @property
    def unit(self): return 1

    def px(self, *pt): return delta(self._px(pt), self._scroll)
    def cs(self, *pt): return self._cs(sigma(pt, self._scroll))

    def call(self, methodname, seq, *args, **kwargs):
        "Call the specified method on the canvas contents"
        if type(seq) is bool:
            seq = self.everything() if seq else self
        for obj in seq:
            fn = getattr(obj, methodname, None)
            if fn: fn(*args, **kwargs)

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

        # Resize content
        if resizeContent is None: resizeContent = self.resizeContent  
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
                if g.ondraw: ondrawList.append(g) # g.ondraw()

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
#                 xy = g.blitPosition((0,0), g.size)
#                 srf.blit(g.snapshot().image, xy)
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
        raise NotImplementedError("Use PCanvas class to scroll.")

    def cover(self):
        return Image(self.size, "#ffffffc0").config(anchor=TOPLEFT)


class Sketch(Canvas):
    capture = None
    realTime = False
    frameRate = 60
    _fixedAspect = True
    dirtyRegions = []
    resizeTrigger = False

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
        super().resize(self.size) # !!!
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
            if hasattr(self, "_defer_coords"):
                self.setCoords(*self._defer_coords)
                del self._defer_coords
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
                if self.capture is not None: self.capture.capture(self)
                for gr in self.ondrawList:
                    try: gr.ondraw()
                    except: logError()
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
                    setattr(ev, "originalSize", self.size)
                    self._resize_ev = ev
                    s = hasattr(self, "_scrollSize")
                    if s: self.scrollTo()
                    self.resize(ev.size)
                    if s: self.resizeCoords(ev)
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
