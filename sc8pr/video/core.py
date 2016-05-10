from sc8pr.sketch import Sketch
from sc8pr.image import NW, Image
from sc8pr.util import rectAnchor
from os.path import isfile


class VideoClip:
	"A class for represented sequences of images composed from layers"
	
	def __init__(self, base):
		self.base = base
		self.layers = []

	@property
	def size(self): return self.base.size

	@property
	def rect(self): return self.base.getRect()

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
			if frame <= layer.last:
				if pending or frame >= layer.first:
					n += 1
		return n

class Layer:
	"Base class for creating video clip layers"
	posn = 0, 0
	anchor = NW
	effects = []

	def __init__(self, clip, first=1, length=None):
		self.clip = clip
		self.size = clip.size  # Change to False for no resizing or True for best fit
		self.first = first
		self.length = length
		clip.add(self)

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
			for e in self.effects:
				img = e.apply(img, frame)
		return img

	def scaleImage(self, img):
		if self.size is True:
			self.size = img.fitAspect(self.clip.size)
		if self.size and img.size != self.size:
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


class FileSequence(Layer):
	"A video layer comprising a sequence of image files"

	def __getitem__(self, i):
		"Return frame image before effects are applied"
		if i >= 0 and i < self.length:
			n = self.seqEnd - i if self.reverse else self.seqStart + i
			img = self.load(n)
			return self.scaleImage(img)

	def __init__(self, clip, pattern="frame{}.png", first=1, seqStart=1, seqEnd=True, reverse=False):
		super().__init__(clip, first)
		self.pattern = pattern
		self.seqStart = seqStart
		self.seqEnd = self.findEnd() if seqEnd is True else seqEnd
		self.length = (1 + self.seqEnd - self.seqStart)
		self.reverse = reverse

	def load(self, n):
		"Load image from a file"
		fn = self.pattern.format(n)
		try: img = Image(fn)
		except: img = None
		return img

	def findEnd(self):
		"Find the last file in the sequence"
		found = None
		n = self.seqStart
		while isfile(self.pattern.format(n)):
			found = n
			n += 1
		return found


def setup(sk):
	sk.clip = sk._clip(sk)
	sk.size = sk.clip.size
	sk.animate(draw)

def draw(sk):
	n = sk.frameCount
#	print("**", n)
	sk.clip.image(n).blitTo(sk.screen)
	if sk.done:
		sk.quit = True
	elif sk.clip.count(n, True) == 0:
		sk.done = True

def play(clip, record=None, fps=None):
	sk = Sketch(setup)
	sk._clip = clip
	sk.done = False
	if record:
		sk.record()
		if record is not True:
			sk.recordName = record
	if fps: sk.frameRate = fps
	sk.run()
