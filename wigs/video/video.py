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


from wigs.image import Image, NW, NE, SW, SE, CENTER, NORTH, SOUTH, WEST, EAST
from wigs.geometry import arrow
from wigs.sketch import Sketch
from wigs.video.fileSeq import FileSeq
from pygame import Rect, MOUSEBUTTONDOWN
from sys import stderr
import os


class ImageSeq:
    "A class for loading sequences of images from consecutively numbered files"

    def __init__(self, src):
        assert isinstance(src, Image) or isinstance(src, FileSeq), "invalid argument"
        self.src = src

    @property
    def size(self):
        img = self.src if isinstance(self.src, Image) else self.image(0)
        return img.size

    def image(self, n):
        src = self.src
        return src if isinstance(src, Image) else Image(src[n])

    def __len__(self):
        src = self.src
        return None if isinstance(src, Image) else len(src)


class Scene:
    "A class for rendering videos consisting of multiple layers"

#    file = None
    _size = None

    def __init__(self, img, frames=True):
        self.layers = []
        self._base = img if isinstance(img, ImageSeq) else ImageSeq(img)
        self._frames = len(self._base) if frames is True else frames

    def __len__(self): return self._frames

    def setFrames(self, frames=0):
        self._frames = frames if frames > 0 else (self.overlayTime - frames)

    @property
    def overlayTime(self):
        t = 1
        for layer in self.layers:
            t0 = layer.end
            if t0 is None: return None
            elif t0 > t: t = t0
        return t - 1

    @property
    def base(self):
        img = self._base.image(self.sk.frameCount - 1)
        assert img.surface.get_bitsize() == 24, "Image must be RGB24"
        return img

    def render(self):
        "Render one frame by overlaying all layers"
        n = self.sk.frameCount
        end = len(self)
        render = end is True or n <= end
        if render:
            count = 0
            img = self.base.clone()
            for layer in self.layers:
                i = layer.currentFrame
                if i is not None:
                    layer.render(img, i)
                    count += 1
            print("{} [{}]".format(n, count), file=stderr)
        return img if render else None

    @property
    def size(self):
        if self._size is None:
            self._size = self.base.size
        return self._size

    @property
    def width(self): return self.size[0]

    @property
    def height(self): return self.size[1]

    @property
    def center(self):
        w, h = self.size
        return w//2, h//2


class Layer:

    def __init__(self, scene, start=0, end=None, **kwargs):
        self.scene = scene
        self.start = start
        self.end = end
        scene.layers.append(self)
        self.config(**kwargs)
    
    def config(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def currentFrame(self):
        "Return the frame number for the current layer"
        n = self.sk.frameCount
        if n >= self.start and (self.end is None or n < self.end):
            return n - self.start
        return None

    @property
    def sk(self): return self.scene.sk


class ImageLayer(Layer):
    "A class for overlaying one layer of a video; includes rotate, fade, zoom, and wipe effects"

    size = None
    posn = 0, 0
    anchor = NW
    scale = False
    angle = None
    spin = None
    zoom = None
    style = None
    alphakey = None
    alpha = None
    fade = None
    wipe = None

    def __init__(self, scene, src, start=0, end=None, **kwargs):
        super().__init__(scene, start, **kwargs)
        self.end = len(src) + start if end is True else end
        self.src = ImageSeq(src)

    def __len__(self): return self.end - self.start

    def frameImage(self, frame):
        "Return an unprocessed image for the layer"
        return self.src.image(frame)

    def effectSize(self, frame, section):
        f0, f1 = section
        if frame < f0: a = frame / f0
        else:
            frames = self.end - self.start + 1
            if frame > frames - f1:
                a = (frames - 1 - frame) / f1
            else: a = None
        return a

    def setFadeAlpha(self, frame):
        "Calculate alpha value for fade in/out effect"
        a = self.effectSize(frame, self.fade)
        self.alpha = a if a is None else round(255 * a)

    def wipeImage(self, img, frame):
        "Return a sub-image to produce a wipe effect"
        a = self.effectSize(frame, self.wipe[:2])
        if a is not None:
            n = self.wipe[2 if frame < self.wipe[0] else 3]
            w0, h0 = img.size
            a = round(a * (w0 if n % 2 else h0))
            x = w0 - a if n in (3,5) else 0
            if n == 5: x //= 2
            y = h0 - a if n in (2,6) else 0
            if n == 6: y //= 2
            r = (x, y) + ((a, h0) if n % 2 else (w0, a))
            img = Image(img.surface.subsurface(r))
        return img

    def filter(self, img, frame):
        "Process an image before blitting to the frame"
        scale = self.motion(frame)
        if self.alphakey: img.surface.set_colorkey(self.alphakey)
        if scale:
            scale = self.scene.size if scale is True else scale
            img = img.scale(scale)
            if self.alphakey: img.surface.set_colorkey(self.alphakey)
        self.size = img.size
        if self.style: img = img.style(**self.style)
        if self.angle is not None:
            img = img.rotate(self.angle)
            if self.spin: self.angle += self.spin
        if self.alpha not in (None, 255):
            srf = img.surface
            if srf.get_bitsize() == 32:
                img = img.clone().tint((255,255,255, self.alpha))
            else:
                srf.set_alpha(self.alpha)
        if self.wipe: img = self.wipeImage(img, frame)
        return self.postFilter(img, frame)

    def postFilter(self, img, frame): return img

    def render(self, base, frame):
        "Blit the layer to the frame"
        if self.fade: self.setFadeAlpha(frame)
        img = self.filter(self.frameImage(frame), frame)
        if img: img.blitTo(base, *self._motion)

    def motion(self, frame):
        "Adjust layer position and size"
        self._motion = self.posn, self.anchor
        scale = self.scale
        z = self.effectSize(frame, self.zoom) if self.zoom else None
        if z is None: return scale
        if type(scale) is bool: scale = self.scene.size
        sx, sy = scale
        if sx: sx = max(1, round(sx * z))
        if sy: sy = max(1, round(sy * z))
        return sx, sy


# Arrow drawing...

def setAnchor(r, a):
    "Modify arrow layer position for anchors other than NW"
    key = {NW:"topleft", NORTH:"midtop", NE:"topright", WEST:"midleft", CENTER:"center",
        EAST:"midright", SW:"bottomleft", SOUTH:"midbottom", SE:"bottomright"}
    return getattr(r, key[a])

def arrowImg(p0, p1, shape={}, **kwargs):
    "Compose a trimmed image of an arrow"
    return Image.join(arrow(p0, p1, **shape), trim=True, **kwargs)

def arrowLayer(scene, start, end, p0, p1, style={}, shape={}, **kwargs):
    "Return a layer consisting of an arrow image"
    img, posn = arrowImg(p0, p1, shape, **style)
    layer = ImageLayer(scene, img, start, end, **kwargs)
    layer.posn = setAnchor(Rect(posn, img.size), layer.anchor)
    if "zoom" in kwargs and "scale" not in kwargs:
        layer.scale = img.size 
    return layer


# Other effects...

def speechBubble(bubble, content, size, **kwargs):
    "Render a speech bubble from an Image or str"
    if type(content) is str:
        content = Image.text(content, **kwargs)
    speech = Image(bubble).scale(size)
    content.blitTo(speech, speech.center, CENTER)
    return speech


# FFMPEG operations...

def unrender(src, dest, **kwargs):
    "Convert video to a sequence of images with FFMPEG"
    opt = {"ffmpeg":"ffmpeg", "rate":30}
    opt.update(kwargs)
    os.system('"{ffmpeg}" -i {0} -f image2 -r {rate} {1}'.format(src, dest, **opt))


# Create and run the Sketch...

def run(scene, file=None):
    "Run video scene as a Sketch"
    sk = Sketch(setup)
    Scene.sk = sk
    sk.scene = scene
    sk.file = file
    sk.run(caption="Rendering...", mode=0)

def click(sk, ev): print(ev.pos)

def setup(sk):
    sk.frameRate = 30
    sk.animate(draw, {MOUSEBUTTONDOWN:click})

def draw(sk):
    if sk.frameCount == 1:
        sk.scene = sk.scene()
        sk.size = sk.scene.size
    img = sk.scene.render()
    if img:
        sk.blit(img)
        if sk.file:
            img.saveAs(sk.file.format(sk.frameCount))
    else: sk.quit = True
