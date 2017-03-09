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


from sc8pr.image import Image
from sc8pr.effects import ScriptSprite
from sc8pr.util import jdump, jload, defaultExtension, tempDir
import sc8pr

from sys import version_info as ver, stderr
from zipfile import ZipFile
from struct import pack, unpack
from os.path import isfile
import pygame, zlib


class ZImage:
    "A class for compressing and decompressing images using zlib"

    modes = "RGBA", "RGB"
    compress = zlib
    format = "zlib"

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
            self.gz = self.compress.compress(data, level) if level else data
            self.size = srf.get_size()
            self.mode = self.modes.index(mode)

    @staticmethod
    def guessMode(srf):
        return "RGBA" if srf.get_bitsize() == 32 else "RGB"

    @property
    def image(self):
        "Convert to uncompressed Image"
        data = self.compress.decompress(self.gz)
        mode = self.modes[self.mode]
        return Image(pygame.image.fromstring(data, self.size, mode))

    def __bytes__(self):
        "Convert to raw binary data"
        w, h = self.size
        return pack("!3I", w, h, self.mode) + self.gz


class Video:
    "A class for storage and retrieval of compressed image archives"

    output = None
    infoFile = "meta/info.json"
    zlevel = 2
    _pending = 0

    info = dict(python=(ver.major, ver.minor, ver.micro),
        sc8pr=sc8pr.__version__, format=ZImage.format)

    def __init__(self, *archive, interval=None, gui=False, wait=True):
        self.data = []
        self.interval = interval
        self.gui = gui
        if archive:
            if len(archive) == 1:
                self.load(archive[0], wait)
            else:
                archive, nums = archive
                if nums is True: nums = range(1, 1 + self.lastFileIndex(archive))
                file = self.output
                if file:
                    print("Loading and compressing images...", file=file)
                for i in nums:
                    fn = archive.format(i)
                    self.capture(Image(fn))
                    if file and i % 50 == 0: print(i, file=file)

    def __len__(self): return len(self.data)

    @property
    def size(self): return self[0].size

    @property
    def pending(self):
        "Number of ZImages not yet loaded from ZipFile"
        return self._pending

    @pending.setter
    def pending(self, v):
        "Close ZipFile after last image is loaded"
        self._pending = v
        if v == 0:
            self.zip.close()
            del self.zip

    def __getitem__(self, i):
        "Return a ZImage instance by index"
        img = self.data[i]
        if img is None:
            self.data[i] = img = ZImage(self.zip.read(str(i)))
            self.pending -= 1
        return img

    @staticmethod
    def lastFileIndex(path, start=1):
        "Determine the last file in a numbered sequence"
        d = 1024
        end = start
        while isfile(path.format(end)): end += d
        start = end - d
        if start < 0: return
        while end > start + 1:
            n = (start + end) // 2
            exists = isfile(path.format(n))
            if exists: start = n
            else: end = n
        return n if exists else start

    def capture(self, img=None, mode=0):
        "Add a frame (Surface or Image) to the Video"
        if img is None: img = pygame.display.get_surface()
        if type(mode) is int: mode = ZImage.modes[mode]
        self.data.append(ZImage(img, mode=mode, level=self.zlevel))

    def save(self, name):
        "Save the Video as a ZipFile of ZImages (S8V format)"
        if self.pending: self.buffer()
        with ZipFile(defaultExtension(name, ".s8v"), "w") as z:
            i = 0
            for img in self:
                z.writestr(str(i), bytes(img))
                if i == 0: sz = img.size
                elif sz and img.size != sz:
                    print("Warning: Saving s8v with inconsistent image sizes!", file=stderr)
                    sz = None
                i += 1
            info = {"frames": i}
            info.update(self.info)
            z.writestr(self.infoFile, jdump(info))

    def load(self, name, wait):
        "Load a S8V video"
        name = defaultExtension(name, ".s8v")
        self.zip = ZipFile(name, "r")
        info = jload(self.zip.read(self.infoFile))
        self.pending = n = info["frames"]
        self.data = [None for i in range(n)]
        if wait: self.buffer()

    def buffer(self, start=0, end=None):
        "Load frames into the buffer"
        z = self.zip
        d = self.data
        if end is None: end = len(self)
        while start < end:
            if d[start] is None:
                d[start] = ZImage(z.read(str(start)))
                self.pending -= 1
            start += 1

    def clip(self, start=0, end=None):
        "Return a new Video instance containing a contiguous subset of frames; no images are copied"
        if end is None: end = len(self)
        if self.pending: self.buffer(start, end)
        v = Video()
        v.data = self.data[start:end]
        return v

    def export(self, path="?/img{}.png", pattern="05d", start=0, file=None, **kwargs):
        "Export the images as individual files"
        if self.pending: self.buffer()
        path = tempDir(path)
        path = path.format("{{:{}}}".format(pattern))
        i = 0
        if file is None: file = self.output
        if file:
            print("Saving {} images to {}...".format(len(self), path), file=file)
        for img in self:
            img.image.saveAs(path.format(i + start))
            i += 1
            if file and i % 50 == 0: print(i, file=file)
        return path


class VideoSprite(ScriptSprite):
    "A sprite whose costumes are extracted as needed from a Video instance"

    def __init__(self, sk, video, *group, **kwargs):
        self._last = None,
        self.video = video
        self._costumeSeq = tuple(range(len(video)))
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
        return self.getImage(self._costumeSeq[self.currentCostume])

    def load(self, *archive, wait=True):
        "Load a new set of images"
        self.video = v = Video(*archive, wait=wait)
        w1, h1 = v[1].size
        w0, h0 = self.size
        z = (w1/w0 + h1/h0) / 2
        if z != 1: self.zoom /= z
        self._costumeSeq = tuple(range(len(v)))
        self.currentCostume = 0

    def action(self, a):
        "Call load method as a script action"
        if type(a) is str: a = a,
        if type(a) is tuple:
            self.load(*a)
            return True
