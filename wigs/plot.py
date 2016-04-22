# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


from wigs.image import Image
from wigs.util import rgba, CENTER, EAST, NORTH, WEST, SOUTH, NE, NW
from wigs.geometry import locus, arrow, tuple_add
import pygame


BLACK, WHITE, GREY = rgba("black", "white", "grey")


class Plot(Image):

    def __init__(self, img, xrange, yrange=None, margin=(0,0,0,0)):
        "Encapsulate an Image with an associated coordinate system"
        super().__init__(img)
        w, h = self.size
        xmin, xmax = xrange
        mx1, mx2, my2, my1 = margin
        xscale = (w - 1 - (mx1 + mx2)) / (xmax - xmin)
        if yrange is None or type(yrange) in (int, float):
            yscale = -xscale
            ymin = (h - 1 - (my1 + my2)) / yscale / 2
            ymax = -ymin
            if yrange is not None:
                ymax += yrange - ymin
                ymin = yrange
        else:
            ymin, ymax = yrange
            yscale = (h - 1 - (my1 + my2)) / (ymin - ymax)
        self.coeff = xscale, mx1 - xscale * xmin, yscale, my1 - yscale * ymax
        self.limit = xmin, xmax, ymin, ymax

    @property
    def scale(self):
        x = self.coeff[0]
        y = self.coeff[2]
        r = abs(x * y) ** 0.5
        return dict(x=x, y=y, r=r)

    @property
    def left(self): return self.limit[0]

    @property
    def right(self): return self.limit[1]

    @property
    def bottom(self): return self.limit[2]

    @property
    def top(self): return self.limit[3]

    def getRect(self, r=True):
        "Return the pygame.Rect for the region r"
        x0, x1, y0, y1 = self.limit if r is True else (r[0], r[0]+r[2], r[1], r[1]+r[3])
        x0, y0 = self.coords((x0,y0))
        x1, y1 = self.coords((x1,y1))
        w = abs(x1 - x0) + 1
        h = abs(y1 - y0) + 1
        return pygame.Rect((min(x0,x1), min(y0,y1), w, h))

    def clip(self, r=True):
        "Set the clipping area"
        self.surface.set_clip(r if r is None else self.getRect(r))

    def coords(self, xy, invert=False):
        "Convert between an abstract coordinate system and pixel coordinates"
        a, b, c, d = self.coeff
        x, y = xy[:2]
        return ((x-b)/a, (y-d)/c) if invert else (a*x+b, c*y+d)

    def coordGen(self, pts, invert=False):
        for pt in pts: yield self.coords(pt, invert)

    def gridLabel(self, x, n, formats=(None,None), anchors=(NORTH, EAST), rotate=(0,-90), offsets=((0,0,0,0)), **kwargs):
        "Add labels to the gridlines"
        if formats[n]:
            img = Image.text(formats[n].format(x), **kwargs)
            if rotate[n]: img = img.rotate(rotate[n])
            posn = (0, x) if n else (x, 0)
            posn = tuple_add(self.coords(posn), offsets[2*n:2*n+2])
            img.blitTo(self, posn, anchors[n])

    def grid(self, delta=(1,1), axisStyle=(BLACK,3), gridStyle=(GREY,1), **kwargs):
        "Draw a coordinate grid on the image"
        srf = self.surface
        xmin, xmax, ymin, ymax = self.limit

        # Draw gridlines...
        if gridStyle: c, w = gridStyle
        x = delta[0] * int(xmin / delta[0])
        while x <= xmax:
            if gridStyle:
                p0 = self.coords((x,ymin))
                p1 = self.coords((x,ymax))
                pygame.draw.line(srf, c, p0, p1, w)
            self.gridLabel(x, 0, **kwargs)
            x += delta[0]
        y = delta[1] * int(ymin / delta[1])
        while y <= ymax:
            if gridStyle:
                p0 = self.coords((xmin,y))
                p1 = self.coords((xmax,y))
                pygame.draw.line(srf, c, p0, p1, w)
            self.gridLabel(y, 1, **kwargs)
            y += delta[1]

        # Draw axes...
        if axisStyle:
            c, w = axisStyle
            p0 = self.coords((xmin,0))
            p1 = self.coords((xmax,0))
            pygame.draw.line(srf, c, p0, p1, w)
            p0 = self.coords((0,ymin))
            p1 = self.coords((0,ymax))
            pygame.draw.line(srf, c, p0, p1, w)

        return self

    def arrow(self, tail, tip, tailWidth=None, headLength=None, flatness=1, fill=None, stroke=None, strokeWeight=1):
        "Plot an arrow"
        pts = arrow(self.coords(tail), self.coords(tip), tailWidth, headLength, flatness)
        Image.polygon(pts, True, fill, stroke, strokeWeight, self.size).blitTo(self)

    def blit(self, img, posn, anchor=NW):
        "Blit an image to the plot"
        if not isinstance(img, Image): img = Image(img)
        img.blitTo(self, self.coords(posn), anchor)
 
    def errorBars(self, pts, err=True, errWt=1, color=BLACK, marker=None,
            fill=None, stroke=(0,0,0), strokeWeight=1, markerSize=(15,15)):
        "Draw error bars"
        if type(marker) is int:
            marker = self.renderMarker(marker, markerSize, fill, stroke, strokeWeight)
        srf = self.surface
        for pt in pts:
            x, y = pt[:2]
            if err:
                e = pt[2:] if err is True else err
                if len(e) == 1: e = e[0], e[0]
                if e[0]:
                    p0 = self.coords((x + e[0], y))
                    p1 = self.coords((x - e[0], y))
                    pygame.draw.line(srf, color, p0, p1, errWt)
                if e[1]:
                    p0 = self.coords((x, y + e[1]))
                    p1 = self.coords((x, y - e[1]))
                    pygame.draw.line(srf, color, p0, p1, errWt)
            if marker:
                marker.blitTo(self, self.coords((x,y)), CENTER)

    def plot(self, pts, marker=None, fill=None, stroke=(0,0,0), strokeWeight=1, markerSize=(15,15), closed=False):
        "Plot a sequence of points with markers or lines"
        super().plot(self.coordGen(pts), marker, fill, stroke, strokeWeight, markerSize, closed)

    def locus(self, pCurve, t0=None, t1=None, steps=None, color=BLACK, weight=1, marker=None, **params):
        "Connect points along a parameterized curve"
        if t0 is None: t0 = self.left
        if t1 is None: t1 = self.right
        if steps is None: steps = max(1, round(abs(self.coeff[0] * (t1-t0))))
        self.plot(locus(pCurve, t0, t1, steps, **params), marker, stroke=color, strokeWeight=weight)

    def regEq(self, data, x=0, y=1, model=0, x0=None, x1=None, **kwargs):
        "Plot a regression equation"
        coeff = data.regression(x, y, model)
        self.locus(data.locus, x0, x1, coeff=coeff, model=model, **kwargs)
        return coeff

    def title(self, txt, posn=6, offset=(0,0), **kwargs):
        """Render and position a title:
            -1: Left of top end of y-axis
            0: Below right end of x-axis
            1-4: Centred outside grid edge
            5-8: Centred inside image edge
        """
        img = Image.text(txt, **kwargs)
        if posn % 2: img = img.rotate(-90)
        if posn > 4:
            w, h = self.size
            cx, cy = self.center
            x = 0 if posn == 7 else w-1 if posn == 5 else cx
            y = 0 if posn == 6 else h-1 if posn == 8 else cy
            a = (EAST, NORTH, WEST, SOUTH)[posn-5]
        else:
            xmin, xmax, ymin, ymax = self.limit
            if posn > 0:
                x0, y0 = self.coords((xmin, ymin))
                x1, y1 = self.coords((xmax, ymax))
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 
                x = x0 if posn == 3 else x1 if posn == 1 else cx
                y = y1 if posn == 2 else y0 if posn == 4 else cy
                a = (WEST, SOUTH, EAST, NORTH)[posn-1]
            else:
                xy = (xmax, 0) if posn == 0 else (0, ymax)
                x, y = self.coords(xy)
                a = NE
        img.blitTo(self, (x + offset[0], y + offset[1]), a)
