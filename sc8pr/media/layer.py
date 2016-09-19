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


from sc8pr.sketch import Sketch, Sprite, SpriteList
from sc8pr.image import Image
from sc8pr.util import rectAnchor, CENTER, NW
from sc8pr.media.effects import Effect
from os.path import isfile
from random import randint


class Layer:
	"Base class for creating video clip layers"
	posn = 0, 0
	anchor = NW

	def __init__(self, clip, first=1, length=None):
		self._effect = []
		self.first = first
		self.length = length
		if clip: clip.add(self)

	@property
	def effect(self): return self._effect

	@effect.setter
	def effect(self, eff):
		if isinstance(eff, Effect):
			eff = eff,
		for e in eff:
#			e.layer = self
			if e.frame is None and e.length:
				e.frame = 0 if e.length > 0 else self.length
		self._effect.extend(eff)

	@property
	def last(self):
		"Last frame number"
		n = self.length
		return self.first + n - 1 if n is not None else None

	def after(self, n): return n + self.last

	def config(self, **kwargs):
		"Set multiple attributes"
		for key in kwargs:
			setattr(self, key, kwargs[key])
		return self

	def applyEffects(self, img, frame):
		if img:
			for e in self.effect:
				img = e.apply(img, frame)
		return img
		
	def image(self, frame):
		"Return frame image after effects are applied"
		self.frame = frame
		return self.applyEffects(self[frame], frame)

	def centered(self, offset=0):
		"Center the layer in the video clip"
		x, y = self.clip.base.center
		self.posn = x, y + offset
		self.anchor = CENTER
		return self


class VideoClip(Layer):
	"A class for represented sequences of images composed from layers"

	def __init__(self, base, first=1, length=None, clip=None):
		super().__init__(clip, first, length)
		self.base = base
		self.layers = []

	@property
	def currentLength(self):
		n = 0
		for layer in self.layers:
			i = layer.last
			if i is None: return None
			elif i > n: n = i
		return n

	@property
	def size(self): return self.base.size

	@property
	def width(self): return self.base.size[0]

	@property
	def height(self): return self.base.size[1]

	@property
	def center(self):
		w, h = self.size
		return w // 2, h // 2

	def add(self, layer):
		"Add a layer to the clip"
		self.layers.append(layer)
		layer.clip = self

	def image(self, frame):
		"Render an image for one frame"
		self.frame = frame
		if frame < 1 or frame > self.length: return None
		frameImg = self.base.clone()
		for layer in self.layers:
			img = layer.image(frame - layer.first)
			if img:
				posn = rectAnchor(layer.posn, img.size, layer.anchor)
				img.blitTo(frameImg, posn)
		return self.applyEffects(frameImg, frame)

	def count(self, frame, pending=False):
		"Count current layers or layers to be completed"
		n = 0
		for layer in self.layers:
			if layer.length is None or frame <= layer.last:
				if pending or frame >= layer.first:
					n += 1
		return n


class ImageLayer(Layer):
	"A video layer comprising a single static image"

	def __init__(self, clip, img, first=1, length=None):
		super().__init__(clip, first, length)
		self.img = Image(img).convert()

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		n = self.length
		if i >= 0 and (n is None or i < n):
			return self.img


class GenLayer(Layer):
	"A video layer of images produced by a generator function"

	def __init__(self, clip, gen, first=1, length=None):
		super().__init__(clip, first, length)
		self.gen = gen

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		n = self.length
		if i >= 0 and (n is None or i < n):
			return next(self.gen)


class FileSeq(GenLayer):
	"Generate a layer from a sequence of file names"

	def __init__(self, clip, pattern, first, length=None, start=1, reverse=False):
		if length is None: length = self.findEnd(pattern, start)
		if reverse:
			r = start + length - 1, start - 1, -1
		else:
			r = start, start + length
		gen = self.images(self.names(pattern, range(*r)))
		super().__init__(clip, gen, first, length)

	@staticmethod
	def images(files):
		"Generate images"
		for f in files: yield Image(f).convert()

	@staticmethod
	def names(pattern, seq):
		"Generate file names from a pattern"
		for n in seq: yield pattern.format(n)

	@staticmethod
	def findEnd(pattern, n):
		"Find the last file in the sequence"
		while isfile(pattern.format(n)): n += 1
		return n - 1


class RandomFile(FileSeq):
	"Return a random frame from a file"
	
	def __init__(self, clip, pattern, first, length=None, start=1):
		super().__init__(clip, pattern, first, None, start)
		self.count = self.length
		self.length = length
		self.start = start
		self.pattern = pattern

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		n = self.length
		if i >= 0 and (n is None or i < n):
			s = self.start
			i = randint(s, s + self.count - 1)
			return Image(self.pattern.format(i)).convert()


class VideoSprite(Sprite):
	"Sprites with references to their layer and video clip"

	@property
	def clip(self): return self.spriteList.sketch

	@property
	def layer(self): return self.spriteList.layer


class SpriteLayer(Layer):
	"A video layer of sprites"

	def __init__(self, clip, first=1, length=None):
		super().__init__(clip, first, length)
		self.sprites = SpriteList(clip)
		self.sprites.layer = self

	def __getitem__(self, i):
		n = self.length
		if i >= 0 and (n is None or i < n):
			img = Image(self.clip.size)
			self.sprites.draw(img.surface)
			return img


def setup(sk):
	sk.clip = sk._clip(sk)
	if sk.clip.last is None:
		print("Video clip length has not been specified.")
		sk.quit = True
	else:
		sk.size = sk.clip.center if sk.half else sk.clip.size
		sk.animate(draw)
		print("Rendering", sk.clip)

def printFrame(t, n):
		print("{:7.1f} s: {}".format(t, n))

def draw(sk):
	n = sk.frameCount
	if n >= sk.clip.last: sk.quit = True
	if n % 25 == 0 or sk.quit:
		printFrame(sk.time, n)
	img = sk.clip.image(n)
	if sk.half:
		assert len(sk.sprites) == 0, "Half size preview is not allowed when sprites are used"
		img.scale(sk.size).blitTo(sk.surface)
	else:
		img.blitTo(sk.surface)
		sk.sprites.draw()

def play(clip, record=None, fps=True, half=False):
	sk = Sketch(setup)
	sk.half = half
	sk._clip = clip
	if record:
		sk.record()
		if record is not True:
			sk.recordName = record
	if fps is True:
		sk.frameRate = 9999 if record else 30
	elif fps: sk.frameRate = fps
	sk.run(caption="sk8pr Video", mode=0)
