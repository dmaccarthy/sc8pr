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


from sc8pr.util import getAlpha, logError, randPixel, rectAnchor, position, \
    NW, CENTER, WEST, EAST 
from sc8pr.geometry import locus
import math, pygame
from pygame.draw import line

FIT = 1
LEFT = WEST
RIGHT = EAST


class Image:
    font = None

    @staticmethod
    def _qCorner(r, q):
        "Return a rectangle corner by quadrant"
        q %= 4
        return (r.bottomright, r.bottomleft, r.topleft, r.topright)[q if q >= 0 else q+4]
 
    @staticmethod
    def defaultFont(size=14):
        if Image.font is None:
            Image.font = pygame.font.SysFont("sans", size)
        return Image.font

    @staticmethod
    def text(txt, font=None, color=(0,0,0), align=LEFT, bgColor=None):
        "Return a new Image on which multi-line text has been rendered"
        txt = txt.split("\n")
        if font is None: font = Image.defaultFont()
        lineSz = font.get_linesize() + 1
        height = len(txt) * lineSz
        width = 1
        lineWidth = []
#        if type(align) is str: align = anchorStr[align.upper()]
        for l in txt:
            w = font.size(l)[0]
            if w > width: width = w
            if align != LEFT: lineWidth.append(w)
        s = Image((width, height), bgColor)
        y = i = 0
        for l in txt:
            t = font.render(l, True, color)
            a = getAlpha(color)
            if a < 255: Image(t).setAlpha(a)
            x = 0 if align == LEFT else (width - lineWidth[i]) / (1 if align == RIGHT else 2)
            s.surface.blit(t, (x, y))
            y += lineSz
            i += 1
        return s

    def __init__(self, data=None, bgColor=None, alpha=True, bits=None):
        "Create a new Image with alpha channel or wrap a Surface as an Image"
        if isinstance(data, Image):
            self.surface = data.surface
        elif isinstance(data, pygame.Surface):
            self.surface = data
        elif type(data) == str:
            self.surface = pygame.image.load(data)
        else:
            if not bits: bits = 32 if alpha else 24
            self.surface = pygame.Surface(data, pygame.SRCALPHA if alpha else 0, bits)
            if bgColor != None: self.surface.fill(bgColor)
        self.noTransform()

    def innerRect(self, wt):
        "Subtract stroke weight from image dimensions"
        w, h = self.size
        d = 2 * wt
        return pygame.Rect(wt, wt, w - d, h - d)

    @staticmethod
    def rect(size, fill=(0,0,0), stroke=None, strokeWeight=1):
        "Render a rectangle; supports alpha and high quality stroke"
        img = Image(size, bgColor=fill if fill else None)
        if stroke: img.borderInPlace(strokeWeight, stroke)
        return img

    @staticmethod
    def ellipse(size, fill=(0,0,0), stroke=None, strokeWeight=1, angle=None, arc=False, arcWeight=False, trim=None):
        "Render an ellipse, circle, or sector; supports alpha and high quality stroke"
        if arc is False: arc = stroke
        if arcWeight is False: arcWeight = strokeWeight
        if type(size) in (int, float):
            size *= 2
            size = size, size
        elif type(size) is not tuple: size = tuple(size)
        img = Image(size)
        pygame.draw.ellipse(img.surface, arc if arc else fill, (0,0) + size)
        if arc:
            inner = img.innerRect(arcWeight)
            w, h = inner.size
            if w>0 and h>0:
                if not fill: fill = 0,0,0,0
                pygame.draw.ellipse(img.surface, fill, inner)
        if angle:
            a1, a2 = angle
            if a1 == a2: return Image(img.size)
            if trim == None: trim = strokeWeight > 4
            if abs(a2-a1) < 360: img.remove(a2, a1, stroke, strokeWeight, trim)
        return img

    @staticmethod
    def _polySize(poly, weight, maxSize=False):
        "Calculate the size of the polygon image"
        w, h = 0, 0
        x0, y0 = None, None
        for x,y in poly:
            if x > w: w = x
            if y > h: h = y
            if x0 is None: x0, y0 = x, y
            else:
                if x > 0 and x < x0: x0 = x
                if y > 0 and y < y0: y0 = y
        w = 1 + weight + int(w)
        h = 1 + weight + int(h)
        x0 = max(0, int(x0) - weight)
        y0 = max(0, int(y0) - weight)
        if maxSize:
            w0, h0 = maxSize
            if w > w0: w = w0
            if h > h0: h = h0
        return (x0, y0), (w, h), (w - x0, h - y0)

    @staticmethod
    def polygon(poly, closed=True, fill=None, stroke=None, strokeWeight=1, size=False, trim=False):
        "Draw a polygon or lines; supports alpha"
        if size is False:
            posn, size, trimTo = Image._polySize(poly, strokeWeight, size)
        else: trim = False
        img = Image(size)
        if fill:
            pygame.draw.polygon(img.surface, fill, poly)
        if stroke:
            pygame.draw.lines(img.surface, stroke, closed, poly, strokeWeight)
        if trim:
            img = Image(img.surface.subsurface(posn, trimTo)).clone()
            img = img, posn
        return img

    @staticmethod
    def renderMarker(n, size, fill=(255,0,0), stroke=(0,0,0), strokeWeight=1):
        "Render a marker image for the plot method"
        w, h = size
        if n < 4:
            func = (Image.ellipse, Image.rect, Image.rect)[n-1]
            img = func(size, fill=fill, stroke=stroke, strokeWeight=strokeWeight)
            if n == 3: img = img.rotate(45)
        elif n < 8:
            pts = (0,0), (w-1,0), (w//2,h-1)
            img = Image.polygon(pts, True, fill, stroke, strokeWeight)
            if n > 4: img = img.rotate(90 * (n - 4))
        return img

    def plot(self, pts, marker=None, fill=(255,0,0), stroke=(0,0,0), strokeWeight=1, markerSize=(15,15), closed=False):
        "Plot a sequence of points as markers or lines (but not both!)"
        if fill and marker is None:
            if type(pts) not in (list,tuple):
                pts = tuple(pts)
            Image.polygon(pts, closed, fill, stroke, strokeWeight, self.size).blitTo(self)
        else:
            alpha = stroke and getAlpha(stroke) < 255 or fill and getAlpha(fill) < 255
            img = Image(self.size) if alpha else self
            if type(marker) is int:
                marker = self.renderMarker(marker, markerSize, fill, stroke, strokeWeight)
            if closed and marker is None:
                pts = close(pts)
            first = True
            pt0 = None
            for pt in pts:
                try:
                    if pt is not None:
                        pt = round(pt[0]), round(pt[1])
                        if marker:
                            marker.blitTo(img, pt, CENTER)
                        elif first:
                            first = False
                        elif pt0 is not None:
                            line(img.surface, stroke, pt0, pt, strokeWeight)
                    pt0 = pt
                except: logError()
            if alpha: img.blitTo(self)
        return self

    def locus(self, pCurve, t0, t1, steps=None, color=(0,0,255), weight=2, marker=None, **params):
        "Connect points along a parameterized curve"
        if steps is None: steps = max(1, round(abs(t1-t0)))
        return self.plot(locus(pCurve, t0, t1, steps, **params), marker, stroke=color, strokeWeight=weight, fill=None)

    @staticmethod
    def copy(srf):
        "Duplicate a Surface and wrap it as an Image"
        if isinstance(srf, Image): srf = srf.surface
        return Image(srf.copy())

    def convert(self, alpha=True, *args):
        "Convert the pixel format"
        srf = self.surface
        srf = srf.convert_alpha(*args) if alpha else srf.convert(*args)
        return Image(srf)

    def clone(self): return self.copy(self)
    def setAsIcon(self): pygame.display.set_icon(self.surface)

    def randPixel(self): return randPixel(self)

    @property
    def size(self): return self.surface.get_size()

    @property
    def center(self):
        x, y = self.surface.get_size()
        return x // 2, y // 2

    @property
    def width(self): return self.size[0]

    @property
    def height(self): return self.size[1]

    def tileGen(self, number=2, rows=1, trim=0):
        "Generator for chopping an image into tiles"
        cols = 1 + (number - 1) // rows
        w, h = self.width // cols, self.height // rows
        trimX, trimY = (trim, trim) if type(trim) is int else trim
        sz = w - 2 * trimX, h - 2 * trimY
        for r in range(rows):
            for c in range(cols):
                if number > 0:
                    x, y = c * w + trimX, r * h + trimY
                    srf = self.surface.subsurface((x, y) + sz).copy()
                    yield Image(srf)
                    number -= 1

    def tiles(self, number=2, rows=1, trim=0):
        return list(self.tileGen(number, rows, trim))

    def remove(self, angle1, angle2, stroke=None, strokeWeight=1, trim=False):
        "Remove a sector from the image, clockwise from angle1 to angle2"
        if angle1 != angle2:
            angle2 -= 360 * int((angle2 - angle1) // 360)
            w, h = self.size
            r = pygame.Rect((0,0) + (w,h))
            xc, yc = w/2, h/2
            q1 = int(angle1 // 90)
            q2 = int(angle2 // 90)
            angle1 = math.radians(angle1)
            angle2 = math.radians(angle2)
            x1, y1 = xc * (1 + math.cos(angle1)), yc * (1 + math.sin(angle1))
            x2, y2 = xc * (1 + math.cos(angle2)), yc * (1 + math.sin(angle2))
            corners = [(x2,y2), (xc,yc), (x1,y1), Image._qCorner(r, q1)]
            while q1 != q2:
                q1 += 1 if q2>q1 else -1
                corners.append(Image._qCorner(r, q1))
            pygame.draw.polygon(self.surface, (0,0,0,0), corners)
            if stroke:
                pygame.draw.lines(self.surface, stroke, False, corners[:3], strokeWeight)
                if trim:
                    srf = Image.ellipse(self.size, fill=(255,255,255), stroke=None).surface
                    self.surface.blit(srf, (0,0), special_flags=pygame.BLEND_RGBA_MIN)
            self.noTransform()

    def blitTo(self, dest=None, posn=(0,0), anchor=NW, size=None, angle=None, flags=0):
        "Blit the image to another surface"
        if dest == None: dest = pygame.display.get_surface()
        elif isinstance(dest, Image): dest = dest.surface
        img = self.transform(size, angle, flags) if size or angle else self
        if anchor != NW:
            posn = rectAnchor(posn, img.size, anchor).topleft
        return dest.blit(img.surface, posn)

    def getAspect(self, size=None):
        "Calculate aspect ratio"
        if size == None: size = self.size
        w, h = size
        return w / h

    def keepAspect(self, size):
        "Adjust unknown dimension to maintain aspect ratio"
        w, h = size
        if w == None or h == None:
            a = self.getAspect()
            if w == None: w = round(h * a)
            else: h = round(w / a)
        return w, h

    def flip(self, xflip=False, yflip=False):
        return Image(pygame.transform.flip(self.surface, xflip, yflip))

    def fitAspect(self, size):
        "Determine the optimal image size to fit within the specified size without altering the aspect ratio"
        assert None not in size, "Cannot use None in size when fitting an image"
        useWidth = self.getAspect() >= self.getAspect(size)
        sz = (size[0], None) if useWidth else (None, size[1])
        return self.keepAspect(sz)
        
    def scale(self, size=None, width=None, height=None):
        "Scale an image"
        if size == None: size = width, height
        return Image(pygame.transform.smoothscale(self.surface, self.keepAspect(size)))

    def fit(self, size, posn=CENTER, bgColor=None):
        "Best scale without distorting image"
        return self.scale(self.fitAspect(size)).crop(size, posn, bgColor)

    def crop(self, size=None, posn=CENTER, bgColor=None):
        "Crop an Image using the specified size and position"
        w, h = self.size if size is None else size
        srf = self.surface
        if w == None: w = srf.get_width()
        if h == None: h = srf.get_height()
        size = w, h
        if type(posn) in (str, int):
            posn = self.position(posn, 0, size)
            x, y = posn
            posn = -x, -y
        clip = pygame.Rect(posn, size)
        ovr = pygame.Rect.clip(srf.get_rect(), clip)
        srf = srf.subsurface(ovr)
        dest = Image(size, bgColor)
        xy = ovr.left - clip.left, ovr.top - clip.top
        dest.surface.blit(srf, xy)
        return dest

    def rotate(self, angle): return Image(pygame.transform.rotate(self.surface, -angle))

    def noTransform(self):
        "Reset transformed image"
        self._trnsfm = None
        self._size = None
        self._angle = None
        self._flags = 0

    def transform(self, size=None, angle=None, flags=0):
        "Cached image transformation"
        if size != self._size or angle != self._angle or flags != self._flags:
            img = self
            if size == self._size and flags == self._flags and self._trnsfm is not None:
                img = self._trnsfm[1]
            elif size:
                if flags & FIT: size = img.fitAspect(size)
                img = img.scale(size)
            self._trnsfm = (img.rotate(angle), img) if angle else (img, img)
            self._size = size
            self._angle = angle
            self._flags = flags
        return self._trnsfm[0]

    def saveAs(self, fn): pygame.image.save(self.surface, fn)

    def fadeTo(self, bgColor=(0,0,0), frames=90, square=False):
        "Generate a sequence of faded images"
        for frame in range(frames + 1):
            fade = Image(self.size, bgColor, False)
            n = 255 * (1 - frame / frames)
            if square: n *= n / 255
            self.clone().tint((255, 255, 255, int(n))).blitTo(fade)
            yield fade

    def position(self, where=CENTER, margin=0, size=None):
        "Get the coordinates corresponding to a corner or side"
        return position(self.size, size, where, margin)

    def style(self, bgColor=None, pad=0, border=0, borderColor=(0,0,0)):
        "Create a new Image with the specified style data"
        w, h = self.size
        pad, pad0 = 2 * (pad + border), pad
        color = borderColor if border > 0 else bgColor
        img = Image((w + pad, h + pad), bgColor=color)
        srf = img.surface
        if border > 0:
            pad = 2 * pad0
            if bgColor == None: bgColor = 0
            pygame.draw.rect(srf, bgColor, (border, border, w + pad, h + pad))
        border += pad0
        srf.blit(self.surface, (border, border))
#        self.noTransform()
        return img

    def _borderRects(self, width):
        w, h = self.size
        m = min(w,h)
        if width > m: width = m
        return ((0, 0, w, width), (0, 0, width, h), (0, h-width, w, width), (w-width, 0, width, h))

    def borderInPlace(self, width=1, color=(0,0,0)):
        "Draw a border around the existing image"
        for r in self._borderRects(width):
            self.surface.subsurface(r).fill(color)
        self.noTransform()
        return self

    def tint(self, rgba, sf=pygame.BLEND_RGBA_MULT):
        self.surface.fill(rgba, special_flags=sf)
        self.noTransform()
        return self

    def setAlpha(self, a):
        return self.tint((255,255,255,a), pygame.BLEND_RGBA_MIN)

    def averageColor(self):
        "Calculate the average RGBA values for an image"
        w, h = self.size
        r, g, b, a = 0, 0, 0, 0
        for col in range(w):
            for row in range(h):
                pixel = self.surface.get_at((col,row))
                if pixel.a:
                    a += pixel.a
                    r += pixel.r * pixel.a
                    g += pixel.g * pixel.a
                    b += pixel.b * pixel.a
        n = w * h
#        a = round(a / n)
        if a:
            a /= n
            n *= a
            r = min(255, round(r / n))
            g = min(255, round(g / n))
            b = min(255, round(b / n))
        return pygame.color.Color(r, g, b, round(a))


def flipAll(imgs, xflip=False, yflip=False):
    "Apply a flip transformation on a sequence of images"
    return [i.flip(xflip, yflip) for i in imgs]

def close(pts):
    first = None
    for pt in pts:
        yield pt
        if first is None: first = pt
    yield first
