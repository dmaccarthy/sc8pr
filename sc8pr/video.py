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

from zipfile import ZipFile
from struct import pack, unpack
from os import system
from sys import stderr
import pygame, zlib
from sc8pr.image import Image
from sc8pr.sketch import Capture
from sc8pr.effects import ScriptSprite


def defaultExtension(name, ext):
    return name if "." in name.replace("\\","/").split("/")[-1] else name + ext


class ZImage:
    "A class for compressing and decompressing images using zlib"

    modes = "RGBA", "RGB"

    def __init__(self, data, mode=None, level=2):

    # Load bytes from file
        if type(data) is str:
            with open(data, "rb") as f: data = f.read()

    # Create from bytes
        if type(data) is bytes:
            fmt, self.gz = data[:12], data[12:]
            w, h, self.mode = unpack("!3I", fmt)
            self.size = w, h

    # Create from Image or Surface
        else:
            srf = data.surface if isinstance(data, Image) else data
            if mode is None: mode = self.guessMode(srf)
            data = pygame.image.tostring(srf, mode)
            self.gz = zlib.compress(data, level) if level else data
            self.size = srf.get_size()
            self.mode = self.modes.index(mode)

    @staticmethod
    def guessMode(srf):
        return "RGBA" if srf.get_bitsize() == 32 else "RGB"

    @property
    def image(self):
        "Convert to uncompressed Image"
        data = zlib.decompress(self.gz)
        mode = self.modes[self.mode]
        return Image(pygame.image.fromstring(data, self.size, mode))

    def __bytes__(self):
        "Convert to raw binary data"
        w, h = self.size
        return pack("!3I", w, h, self.mode) + self.gz


class Video:
    "A class for fast storage and retrieval of compressed images using ZipFile"

    ffmpeg = "ffmpeg"
    pixfmt = "yuv444p"
    zlevel = 2

    def __init__(self, *archive, interval=0, gui=False):
        self.data = []
        self.interval = interval
        self.gui = gui
        if archive:
            if len(archive) == 1:
                self.load(archive[0])
            else:
                archive, nums = archive
                for i in nums:
                    fn = archive.format(i)
                    self.capture(Image(fn))
                
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]
    def name(self, i): return "img{}.szi".format(i)

    def capture(self, img=None, mode=0):
        "Add a frame (Surface or Image) to the Video"
        if img is None: img = pygame.display.get_surface()
        if type(mode) is int: mode = ZImage.modes[mode]
        self.data.append(ZImage(img, mode=mode, level=self.zlevel))

    def save(self, name):
        "Save the Video as a ZipFile of ZImages (S8V format)"
        i = 0
        with ZipFile(defaultExtension(name, ".s8v"), "w") as z:
            for img in self.data:
                z.writestr(self.name(i), bytes(img))
                i += 1

    def load(self, name):
        "Load a S8V video"
        with ZipFile(defaultExtension(name, ".s8v"), "r") as z:
            n = len(z.infolist())
            for i in range(n):
                self.data.append(ZImage(z.read(self.name(i))))

    def clip(self, start=0, end=None):
        "Return a new Video instance containing a contiguous subset of frames; no images are copied"
        if end is None: end = len(self)
        v = Video()
        v.data = self.data[start:end]
        return v

    def export(self, path="?/img{}.png", pattern="05d", movie=False, clip=None, start=0):
        "Export the images as individual files; encode movie with ffmpeg"
        path = Capture.tempDir(path)
        tmp = path.format("{{:{}}}".format(pattern))
        if clip:
            c0, c1 = clip
            c1 += 1
        else:
            c0, c1 = 0, len(self)
        n = c1 - c0
        print("Saving {} images to {}...".format(n, tmp), file=stderr)
        i = 0
        for img in self[c0:c1]:
            img.image.saveAs(tmp.format(i + start))
            i += 1
            if i % 50 == 0: print("{}".format(i), file=stderr)
        print("...Done!", file=stderr)
        pattern = path.format("%" + pattern)
        args = "-f image2 -start_number {} -r 30 -i {} -r 30 -vcodec h264 -pix_fmt {} {}"
        args = args.format(start, pattern, self.pixfmt, movie if movie else "movie.mp4")
        cmd = "{} {}".format(self.ffmpeg, args)
        print(cmd, file=stderr)
        if movie: system(cmd)


class VideoSprite(ScriptSprite):
    "A sprite whose costumes are extracted as needed from a Video instance"

    def __init__(self, sk, video, *group, **kwargs):
        self._last = None,
        self.video = video
#        self.costumeSequence(0, len(self.video) - 1)
        self.seq = tuple(range(len(video)))
        super().__init__(sk, None, *group, **kwargs)
        if kwargs.get("costumeTime") is None:
            self.costumeTime = 1

    def getImage(self, n):
        "Decompress an image"
        last = self._last
        if n != last[0]:
            self._last = last = n, self.video[n].image
        return last[1]

    @property
    def _image(self):
        "Get the costume image"
        return self.getImage(self.seq[self.currentCostume])

    def load(self, *archive):
        "Load a new set of images"
        self.video = v = Video(*archive)
        w1, h1 = v[1].size
        w0, h0 = self.size
        z = (w1/w0 + h1/h0) / 2
        if z != 1: self.zoom /= z
        self.seq = tuple(range(len(v)))
        self.currentCostume = 0

    def action(self, a):
        "Call load method as a script action"
        if type(a) is str: a = a,
        if type(a) is tuple:
            self.load(*a)
            return True
