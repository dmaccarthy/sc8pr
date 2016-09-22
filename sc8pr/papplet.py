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


import pygame, os, json
from time import time
from pygame import display
from sc8pr.image import Image, ZImage, NW
from sc8pr.util import logError, setCursor, handleEvent, fontHeight, sc8prPath, ARROW, randPixel
from sc8pr.geom import distSq
from sc8pr.ram import RAMFolder


class PApplet:
	"Class for creating Processing-style sketches using Pygame 1.9.1 or 1.9.2a0"
	_fontJson = sc8prPath("fonts.json")
	_quit = False
	_snapMode = 0
	eventMap = {}
	captureFolder = "capture"
	saveName = "image{:05d}.png"
	recordName = "seq{:03d}_{:05d}.png"
	light = None
	cursor = ARROW
	gui = None
	recordGui = False

	@staticmethod
	def display(): return Image(pygame.display.get_surface())

	@staticmethod
	def _onQuit(): PApplet._quit = True

	def __init__(self, setup=None, draw=None, eventMap=None):
		"Initialize properties"
		self.frameCount = 0
		self.frameRate = 60
		self.drawTime = 0.0
		self.eventTime = 0.0
		self.surface = None
		self.bgColor = None
		self._bgImage = None
		self._frameInterval = None
		self._recordSequence = -1, 0
		self._lumin = []
		self._bind(setup, draw, eventMap)
		self._clock = pygame.time.Clock()

	@classmethod
	def useFonts(cls, path): cls._fontJson = path

	def _bind(self, setup=None, draw=None, eventMap=None):
		"Bind functions to sketch instance"
		if setup != None: self.setup = setup.__get__(self, self.__class__)
		if draw != None: self.draw = draw.__get__(self, self.__class__)
		if eventMap: self.eventMap = eventMap if type(eventMap) is dict else {None:eventMap}

	@classmethod
	def _fontDict(cls):
		"Search for common system fonts and set default pseudonyms"
		try:
			with open(cls._fontJson) as f:
				generic = json.load(f)
		except:
			generic = ()
		fList = pygame.font.get_fonts()
		fonts = {}
		for g in generic:
			f = cls._selectFont(g, fList)
			if f: fonts[g[0]] = f
		return fonts

	@staticmethod
	def _selectFont(names, sysList=None):
		"Locate a system font from a list of font names"
		if sysList is None: sysList = pygame.font.get_fonts()
		for f in names:
			if f in sysList: return f

	def pseudonym(self, pseudo, name=None):
		"Get or set the font associated with a pseudonym"
		if name: self._fonts[pseudo] = name
		if type(pseudo) in (tuple, list):
			f = PApplet._selectFont(pseudo)
			pseudo = pseudo[0]
			if f: self._fonts[pseudo] = f
		return self._fonts[pseudo] if pseudo in self._fonts else None

	def loadFont(self, name=None, size=16, bold=False, italic=False, lineHeight=False):
		"Load a font file or system font (pseudonyms allowed)"
		font = None
		sz = max(4, round(0.7 * size)) if lineHeight else size
		if name in self._fonts: name = self._fonts[name]
		if name and os.path.isfile(name):
			font = pygame.font.Font(name, sz)
		if not font:
			font = pygame.font.SysFont(name, sz, bold, italic)
		if lineHeight:
			h = fontHeight(font)
			if h != size:
				sz = round(size * sz / h)
				font = self.loadFont(name, sz, bold, italic)
		return font

	@property
	def time(self):
		"Time elapsed since setup method was called"
		return time() - self._t0

	@property
	def size(self): return self.surface.get_size() if self.surface else None

	@property
	def width(self): return self.size[0]

	@property
	def height(self): return self.size[1]

	@size.setter
	def size(self, size): self.resize(size)

	@width.setter
	def width(self, w): self.resize((w, self.height))

	@height.setter
	def height(self, h): self.resize((self.width, h))

	@property
	def center(self):
		"Coordinates of the pixel closest to the center of the sketch"
		x, y = self.size
		return x//2, y//2

	@property
	def centerX(self): return self.center[0]

	@property
	def centerY(self): return self.center[1]

	@property
	def hRatio(self): return self.size[1] / self.initHeight

	@hRatio.setter
	def hRatio(self, r): self.resize((self.width, r * self.initHeight))

	@property
	def aspect(self):
		"Return the aspect ratio of the background, or None"
		img = self._bgImage
		return img.getAspect() if img else None

	def _targetSize(self, size=None):
		"Adjust requested sketch size to match background aspect ratio"
		sz = self.size
		w, h = size if size else sz
		ratio = self.aspect
		if ratio:
			mode = self._snapMode # 1=Width, 2=Height, 3=Fit, 0=Auto
			if mode == 0:
				mode = 3
				if size:
					if w == sz[0]: mode = 2
					elif h == sz[1]: mode = 1
			if mode == 2 or mode == 3 and w / h > ratio:
				w = round(ratio * h)
			else: h = round(w / ratio)
		return w, h

	def randPixel(self): return randPixel(self)

	@property
	def keyCode(self):
		"Key code for most recent keyboard event"
		return None if self.key is None else self.key.key

	@property
	def char(self):
		"Character from most recent keyboard event"
		key = self.key
		if key is None: return ""
		return key.unicode if hasattr(key, "unicode") else ""

	@property
	def mouseX(self): return self.mouseXY[0]

	@property
	def mouseY(self): return self.mouseXY[1]

	def _fitImg(self, size):
		"Create an image scaled to the screen size"
		self._bgImage.transform(size=size)

	def resize(self, size, mode=None, ev=None):
		"Change the sketch size and mode (optional)"
		tsize = self._targetSize(size)
		size0 = self.size
		if mode is None: mode = self._mode
		if size != size0:
			self.surface = display.set_mode(size, mode)
			display.flip()
		if tsize != self.size:
			if distSq(tsize, self.size) > 1:
				if ev: ev.adjustSize = tsize
				self.surface = display.set_mode(tsize, mode)
		if self._bgImage: self._fitImg(self.size)

	@property
	def bgImage(self): return self._bgImage

	@bgImage.setter
	def bgImage(self, img):
		"Set a background image"
		try:
			if img:
				self._bgImage = img if isinstance(img, Image) else Image(img)
				tsize = self._targetSize(self.size)
				self._fitImg(tsize)
				if tsize != self.size: display.set_mode(tsize, self._mode)
			else: self._bgImage = None
		except: logError()
		return self._bgImage

	def setBackground(self, bgImage=None, bgColor=None):
		"Set background image and/or color"
		if bgImage and bgColor:
			# Blit image onto background...
			if not isinstance(bgImage, Image):
				bgImage = Image(bgImage)
			img = Image(bgImage.size, bgColor)
			bgImage.blitTo(img)
			bgImage = img
			bgColor = None
		self.bgImage = bgImage
		self.bgColor = bgColor

	def _update(self):
		"Update the display surface; record frame if requested"
		cursor = self.cursor
		if self.light: self.tint(self.light)
		for img, posn in self._lumin:
			self.blit(img, posn)
		self._lumin = []
		if not self.gui or not self.recordGui: self._captureFrame()
		if self.gui:
			if self.gui.widgets: self.gui.draw()
			if self.recordGui: self._captureFrame()
			if self.gui.hover.dialog in self.gui.widgets if self.gui.hover else False:
				cursor =  self.gui.cursorId
		setCursor(cursor)
		display.flip()

	def record(self, interval=1):
		"Start or stop automatic recording of frames"
		self.frameRecord = self.frameCount + 1
		self._frameInterval = interval
		if interval is not None:
			self._recordSequence = self._recordSequence[0] + 1, 1

	def save(self, path=None):
		"Save a surface; default file name is based on frameCount property"
		if path is None:
			if self._frameInterval is None:
				path = self.saveName.format(self.frameCount)
			else:
				s, f = self._recordSequence
				path = self.recordName.format(s, f)
				self._recordSequence = s, f + 1
		fldr = self.captureFolder
		if isinstance(fldr, RAMFolder):
			fldr[path] = ZImage(self.surface.copy())
		else:
			pygame.image.save(self.surface, fldr + "/" + path)

	def _captureFrame(self):
		"Save a single frame when recording is enabled"
		if self._frameInterval != None:
			if self.frameCount == self.frameRecord:
				self.save()
				self.frameRecord += self._frameInterval

	@property
	def scaledBgImage(self):
		"Return the background image scaled to the sketch size"
		img = self.bgImage
		if img and img._trnsfm: img = img._trnsfm[0]
		return img

	def drawBackground(self):
		"Redraw the sketch background"
		srf = self.surface
		if self.bgColor: srf.fill(self.bgColor)
		img = self.scaledBgImage
		if img: srf.blit(img.surface, (0,0))
#		return self

	def tint(self, rgba):
		"Apply tint operation to the entire sketch"
		Image(self.surface).tint(rgba)

	def blit(self, img, posn=(0,0), anchor=NW, size=None, angle=None, flags=0):
		"Draw an image on the sketch"
		if type(img) is not Image: img = Image(img)
		return img.blitTo(self.surface, posn, anchor, size, angle, flags)

	def _dispatch(self, ev):
		"Dispatch a list of events to the event handling method"
		if type(ev) != list: ev = [ev]
		for e in ev:
			if e: handleEvent(self, e)

	draw = drawBackground
	def setup(self): pass

	def run(self, size=(512,288), caption="Sketch", icon=None, mode=pygame.RESIZABLE):
		"Initialize sketch and run the main drawing/event loop"

	# Initialize pygame...
		pygame.init()
		pygame.register_quit(self.__class__._onQuit)
		try:
			display.set_caption(str(caption))
			display.set_icon(pygame.image.load(icon))
		except: pass
		pygame.key.set_repeat(400, 80)

	# Set display size and mode...
		self._mode = mode
		if type(size) == int:
			size = round(size/18)
			size = 32*size, 18*size
		self.initHeight = size[1]
		self.resize(size)

	# Initialize sketch...
		self._fonts = self._fontDict()
		self.quit = False
		self.key = None
		self.mouse = None
		self.mouseXY = 0, 0
		self._t0 = time()
		try: self.setup()
		except: logError()

	# Drawing / event loop...
		while not self.quit:
			try:
				t0 = self.time
				for ev in pygame.event.get():

				# Inspect events...
					if ev.type == pygame.VIDEORESIZE:
						self.resize(ev.size, ev=ev)
					elif ev.type == pygame.QUIT:
						self.quit = not self.gui.modal if self.gui else True
					elif ev.type == pygame.ACTIVEEVENT:
						if not ev.gain: self.mouse = None
					elif hasattr(ev, "pos"):
						self.mouse = ev
						self.mouseXY = ev.pos
					elif hasattr(ev, "key"):
						self.key = ev

				# Dispatch events to handlers after GUI event processing...
					self._dispatch(self.gui._event(ev) if self.gui else ev)

				# Quit...
					if self.quit: pygame.event.clear()
				self.eventTime = self.time - t0

			# Draw next frame...
				if not self.quit:
					self.frameCount += 1
					self._clock.tick(self.frameRate)
					t0 = self.time
					self.draw()
					if not self.quit: self._update()
					self.drawTime = self.time - t0

		# Something went wrong...
			except: logError()

		# Save captured images...
		capFldr = self.captureFolder
		if isinstance(capFldr, RAMFolder):
			self.captureFolder = capFldr.saveInNewThread(True)

		pygame.quit()
		return self
