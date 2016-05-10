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


from sc8pr.sketch import Sketch, SpriteList
from sc8pr.image import NW, Image
from sc8pr.util import rectAnchor
from sc8pr.video.effects import Effect
from os.path import isfile


class VideoClip:
	"A class for represented sequences of images composed from layers"

	def __init__(self, base):
		self.base = base
		self.layers = []
		self.quit = False

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

	def image(self, frame):
		"Render an image for one frame"
		frameImg = self.base.clone()
		for layer in self.layers:
			img = layer.image(frame - layer.first)
			if img:
				posn = rectAnchor(layer.posn, img.size, layer.anchor)
				img.blitTo(frameImg, posn)
		return frameImg

	def count(self, frame, pending=False):
		"Count current layers or layers to be completed"
		n = 0
		for layer in self.layers:
			if layer.length is None or frame <= layer.last:
				if pending or frame >= layer.first:
					n += 1
		return n


class Layer:
	"Base class for creating video clip layers"
	posn = 0, 0
	anchor = NW
	_effect = []

	def __init__(self, clip, first=1, length=None):
		self.clip = clip
		self.size = clip.size  # Change to False for no resizing or True for best fit
		self.first = first
		self.length = length
		clip.add(self)

	@property
	def effect(self): return self._effect

	@effect.setter
	def effect(self, eff):
		if isinstance(eff, Effect):
			eff = eff,
		for e in eff:
			if e.frame is None:
				e.frame = 0 if e.length > 0 else self.length
		self._effect = eff

	@property
	def last(self):
		n = self.length
		return self.first + n - 1 if n else None

	def config(self, **kwargs):
		"Set multiple attributes"
		for key in kwargs:
			setattr(self, key, kwargs[key])
		return self

	def image(self, frame):
		"Return frame image after effects are applied"
		img = self[frame]
		if img:
			for e in self.effect:
				img = e.apply(img, frame)
		return img

	def scaleImage(self, img):
		if self.size is True:
#			self.size = img.fitAspect(self.clip.size)
			img = img.fit(self.clip.size)
		elif self.size and img.size != self.size:
			img = img.scale(self.size)
		return img


class ImageLayer(Layer):
	"A video layer comprising a single static image"

	def __init__(self, clip, img, first=1, length=None):
		super().__init__(clip, first, length)
		self.img = img

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		n = self.length
		if i >= 0 and (n is None or i < n):
			img = self.img
			return self.scaleImage(img)


class GenLayer(Layer):
	"A video layer of images produced by a generator function"

	def __init__(self, clip, gen, first=1, length=None):
		super().__init__(clip, first, length)
		self.gen = gen

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		n = self.length
		if i >= 0 and (n is None or i < n):
			return self.scaleImage(next(self.gen))


class FileSeq(GenLayer):
	"Generate a layer from a sequence of file names"

	def __init__(self, clip, pattern, first, start=1, length=None, reverse=False):
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
		for f in files: yield Image(f)

	@staticmethod
	def names(pattern, seq):
		"Generate file names from a pattern"
		for n in seq: yield pattern.format(n)

	@staticmethod
	def findEnd(pattern, n):
		"Find the last file in the sequence"
		while isfile(pattern.format(n)): n += 1
		return n - 1


class SpriteLayer(Layer):
	"A video layer of sprites"
	
	def __init__(self, clip, first=1, length=None):
		super().__init__(clip, first, length)
		self.sprites = SpriteList(clip)

	def __getitem__(self, i):
		n = self.length
		if i >= 0 and (n is None or i < n):
			img = Image(self.size)
			self.sprites.draw(img.surface)
			return img


def setup(sk):
	sk.clip = sk._clip(sk)
	sk.size = sk.clip.size
	sk.animate(draw)

def draw(sk):
	n = sk.frameCount
	sk.clip.image(n).blitTo(sk.screen)
	sk.sprites.draw()
	if sk.clip.quit:
		sk.quit = True
	elif sk.clip.quit is False and sk.clip.count(n, True) == 0:
		sk.clip.quit = True

def play(clip, record=None, fps=30):
	sk = Sketch(setup)
	sk.done = False
	sk._clip = clip
	if record:
		sk.record()
		if record is not True:
			sk.recordName = record
	if fps: sk.frameRate = fps
	sk.run(caption="sk8pr Video", mode=0)
