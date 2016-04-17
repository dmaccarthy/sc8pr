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


import time, re, pygame
from wigs.gui import GuiEvent, Widget, Container, NoFont
from wigs.image import Image, CENTER, WEST
from wigs.util import fontHeight, getValues, copyAttr, controlKey, altKey, isChar, isEnter, isHome, isEnd, isLeft, isRight, isIncr, isDecr, isPgUp, isPgDn, TEXT, MENU
from datetime import date


class Label(Widget):

	def __init__(self, data="", name=None, posn=(0,0), **kwargs):
		super().__init__(name, posn)
		self.setStyle(**kwargs)
		if type(data) == str: self.setText(data)
		else: self.imgs[0] = data

	def setText(self, txt, resize=False):
		self.imgs[0] = Image.text(txt, self.font, self.color)
		if resize: self.getSize(True)
	
	def crop(self, size, posn=WEST):
		self.imgs[0] = self.imgs[0].crop(size, posn)
		return self


class Status(Label): color = 0, 0, 255


class Ghost(Widget):
	"""Invisible Widget creates minimum size for Container"""

	cursorId = MENU
	visible = False

	def __init__(self, size, name=None, posn=(0,0)):
		super().__init__(name, posn)
		self.size = size
		self.imgs[0] = None

	def getSize(self): return self.size


class BaseButton(Widget):
	enabled = True
	border = 1
	pad = 4

	def getState(self): return super().getState(self.colors)

	def renderText(self, txt, align=CENTER):
		"""Convert text to Image for enabled and disabled states"""
		return Image.text(txt, self.font, self.color, align=align), Image.text(txt, self.font, self.altColor, align)

	def render(self, n=0):
		img = self.data[1 if n == self.DISABLE else 0]
		b = self.border
		p = self.pad
		if n == self.SELECT:
			p -= b
			b *= 2
		self.imgs[n] = img = img.style(bgColor=self.colors[n], pad=p, border=b, borderColor=self.borderColor)

	def getSize(self, reset=False):
		"""Calculate and return the outer size of the button"""
		if self.size == None or reset:
			w, h = self.data[0].size
			e = self.getEdge()
			self.size = w + e, h + e
		return self.size

	def resize(self, size, posn=CENTER, fit=False):
		"""Adjust the inner size of the Button by fitting or cropping"""
		imgs = []
		for i in self.data:
			img = i.fit(size, posn) if fit else i.crop(size, posn)
			imgs.append(img)
		self.data = imgs
		self.getSize(True)
		return self

	def getImage(self, s=None):
		if s == None: s = self.getState()
		if s not in self.imgs: self.render(s)
		return self.imgs[s]

	def _event(self, ev):
		if self.selectable and ev.type == GuiEvent.MOUSEDOWN:
			if hasattr(self, "group"): self.select()
			else: self.selected = not self.selected
			ev.type = ev.SELECT if self.selected else ev.DESELECT
		return super()._event(ev)


class Button(BaseButton):

	@staticmethod
	def grid(btns, name=None, posn=(0,0), cols=None, space=None, align=CENTER, group=None, nameFrmt=None, **kwargs):
		if not cols: cols = len(btns)
		if space == None: space = fontHeight(Button) // 2
		c = Container(name, posn)
		n = 0
		for b in btns:
			btnName = nameFrmt.format(b, n) if nameFrmt else None
			n += 1
			c.place(Button(b, btnName, **kwargs))
		Button.sameSize(c, align=align, cols=cols, space=space)
		if group != None:
			if group is False:
				for b in c.widgets: b.selectable = True
			else:
				b = c.widgets[0 if group is True else group];
				b.makeGroup(*c.widgets)
				if group is True: b.selected = False
		return c

	@staticmethod
	def getButtons(btns):
		"""Generate a sequence of buttons within the same container, list, or tuple"""
		if isinstance(btns, Button): btns = btns.container
		if isinstance(btns, Container): btns = btns.widgets
		for b in btns:
			if isinstance(b, Button): yield b

	@staticmethod
	def sameSize(btns, size=None, align=CENTER, fit=False, cols=None, space=4):
		"""Resize a list of Buttons to have the same inner size"""
		e = 0
		if size == None:
			w, h = 1, 1
			for btn in Button.getButtons(btns):
				bw, bh = btn.getSize()
				e = btn.getEdge()
				bw, bh = bw - e, bh - e
				if bw > w: w = bw
				if bh > h: h = bh
			size = w, h
		for btn in Button.getButtons(btns):
			btn.resize(size, align, fit)
		if cols:
			n, x, y = 0, 0, 0
			for btn in Button.getButtons(btns):
				if n == 0:
					w, h = btn.getSize()
					w, h = w + space, h + space
				btn.posn = x, y
				n += 1
				if n % cols: x += w
				else: x, y = 0, y + h
		return size, e

	def __init__(self, data=None, name=None, posn=(0,0), **kwargs):
		"""Data may be str, Surface, Image, or list/tuple of Images; if str, kwargs may specify color and altColor"""
		super().__init__(name, posn)
		self.setStyle(**kwargs)
		if not data: data = name
		t = type(data)
		if t == str:
			data = self.renderText(data)
		elif t == pygame.Surface:
			data = Image(data)
		if type(data) not in (list, tuple): data = (data, data)
		self.data = data


class TextInput(BaseButton):
	focusable = True
	cursorId = TEXT

	def __init__(self, name=None, txt="", inner=8, posn=(0,0), password=None, **kwargs):
		self.name = name
		self.setStyle(**kwargs)
		if type(inner) == int:
			if self.font == None: raise NoFont(self)
			h = fontHeight(self)
			inner = (inner * h, h)
		self.inner = inner
		self.posn = posn
		self.password = password
		self.cursor = len(txt)
		self.scroll = 0
		self.setText(txt)

	@property
	def display(self):
		return self.password * len(self.txt) if self.password else self.txt

	def setText(self, txt):
		self.txt = txt
		self.data = self.crop(self.renderText(self.display), 0)
		self.imgs = {}

	def crop(self, imgs, scroll):
		cropped = []
		for img in imgs:
			cropped.append(img.crop(self.inner, (scroll, 0)))
		return cropped

	def drawCursor(self, img):
		w = self.inner[0]
		x, h = self.font.size(self.display[:self.cursor])
		if w >= self.font.size(self.display)[0]:
			self.scroll = 0
		else:
			while x - self.scroll > w - 1: self.scroll += 4
			while x - self.scroll < 0: self.scroll -= 4
		if round(1000 * time.time()) % 1400 < 800:
			pygame.draw.line(img, (0,0,0), (x,0), (x,h), 1)
		return img

	def sizeOf(self, n):
		sz = self.font.size(self.display[:n])[0]
		if n < len(self.display):
			sz += self.font.size(self.display[:n+1])[0]
			sz /= 2
		return sz

	def setCursor(self, ev):
		x = ev.relPosn()[0] - self.pad + self.scroll
		c = 0
		while c < len(self.display) and self.sizeOf(c) < x:
			c += 1
		self.cursor = c

	def getImage(self):
		s = self.getState()
		if s == self.FOCUS:
			img = Image.text(self.display + " ", self.font, self.color)
			img = Image(self.drawCursor(img.surface))
			img = self.crop((img,), self.scroll)[0].style(bgColor=self.colors[s], pad=self.pad, border=self.border, borderColor=self.borderColor)
			return img
		else:
			return super().getImage()

	def _event(self, ev):
		if ev.type == GuiEvent.KEYDOWN and not controlKey() and not altKey():
			uni = ev.original.unicode
			if isEnter(ev.original):
				ev.type = GuiEvent.ENTER
#				self.gui.focus = None
				return self._onEvent(ev)
			txt = self.txt
			n = len(txt)
			txt = txt[:self.cursor], txt[self.cursor:]
			key = ev.original.key
			if isLeft(ev.original):
				if self.cursor > 0: self.cursor -= 1
			elif isRight(ev.original):
				if self.cursor < n: self.cursor += 1
			elif isEnd(ev.original):
				self.cursor = n
			elif isHome(ev.original):
				self.cursor = 0
			else:
				change = True
				if key == pygame.K_ESCAPE:
					self.setText("")
					self.cursor = 0
				elif key == pygame.K_BACKSPACE and self.cursor > 0:
					self.setText(txt[0][:-1] + txt[1])
					self.cursor -= 1
				elif isChar(uni):# and key < 127:
					self.setText(txt[0] + uni + txt[1])
					self.cursor += 1
				elif key == pygame.K_DELETE and len(txt[1]):
					self.setText(txt[0] + txt[1][1:])
				else: change = False
				if change: ev.type = GuiEvent.CHANGE
		elif ev.type == GuiEvent.MOUSEDOWN:
			self.setCursor(ev)
		return self._onEvent(ev) if ev else None


class Slider(Widget):
	enabled = True
	focusable = True
	handle = 0
	frmt = None
	step = None
	ticks = False
	swapHome = False
	page = 5

	border = 1
	pad = 4
	bgColor = Widget.colors[Widget.DEFAULT]
	fgColor = Widget.colors[Widget.HOVER]

	def __init__(self, data, size, name=None, posn=(0,0), **kwargs):
		super().__init__(name, posn)
		self.setStyle(**kwargs)
		value = self.config(data, **kwargs)
		w, h = size
		if w == None or h == None:
			line = fontHeight(self)
			if w == None: w = line
			else: h = line
		self.size = w, h
		self.vertical = 1 if h > w else 0
		self.value = value

	def __str__(self):
		return "{}('{}', value={:.2f})".format(type(self).__name__, self.name, self._val)

	@property
	def pixels(self): return self.size[self.vertical]

	@property
	def metrics(self):
		px = self.pixels
		if self.min >= self.max:
			hw = px
		elif self.handle:
			r = self.handle / (self.max - self.min)
			hw = round(r * px / (1 + r)) + 2 * self.pad
			hw = 1 + 2 * (hw // 2)
			px -= hw
		else: hw = 0
		return px - 2 * self.pad, hw

	@property
	def value(self): return self._val

	@value.setter
	def value(self, v=None):
		if v == None: v = self._val
		if self.step != None:
			s = round((v - self.min) / self.step)
			v = self.min + s * self.step
		if v < self.min: v = self.min
		elif v > self.max: v = self.max
		self._val = v
		self.render()

	def config(self, data, **kwargs):
		copyAttr(kwargs, self)
		while len(data) < 3: data = data + (0,)
		self.min, self.max, v = data
		if self.handle: self.pad = 0
		return v

	def getValueText(self):
		f = self.frmt
		return None if f == None else f.format(self.value)

	def handleDecor(self, x0, surf, n):
		w, h = self.size
		space = round(0.3 * (w if self.vertical else h)) if self.handle or self.min >= self.max else 0
		n = (n + 1) // 2
		for i in range(1 - n, n):
			x = x0 + 5 * i
			p1 = (space, x) if self.vertical else (x, space)
			p2 = (w - 1 - space, x) if self.vertical else (x, h - 1 - space)
			pygame.draw.line(surf, self.borderColor, p1, p2, 1)

	def render(self):

		# Calculate metrics
		w, h = self.size
		px, hw = self.metrics
		if self._val <= self.min or self.min >= self.max: x = 0
		elif self._val >= self.max: x = self.pixels - hw
		else: x = round(self.pad + (self._val - self.min) / (self.max - self.min) * px)
		if self.vertical: x = self.pixels - 1 - x - hw

		# Background
		img = Image(self.size, self.bgColor)
		pygame.draw.rect(img.surface, self.bgColor, (0,0) + self.size)

		# Tick marks
		if self.ticks and self.step != None:
			n = round((self.max - self.min) / self.step)
			tick0 = self.pad + hw / 2
			dTick = px / n
			y = (w if self.vertical else h) // 2 - 1
			for i in range(n+1):
				tick = round(tick0 + i * dTick)
				p1 = (y, tick) if self.vertical else (tick, y)
				p2 = (y+1, tick) if self.vertical else (tick, y+1)
				pygame.draw.line(img.surface, self.borderColor, p1, p2, 1)
				tick += dTick

		# Handle
		if self.handle:
			r = pygame.Rect(((0, x) + (w, hw)) if self.vertical else (x, 0) + (hw, h))
			pygame.draw.rect(img.surface, self.fgColor, r)
			r1, r2 = r.bottomleft, r.topright
			if self.vertical:
				r1, r2 = r2, r1
			pygame.draw.line(img.surface, self.borderColor, r.topleft, r1, 1)
			pygame.draw.line(img.surface, self.borderColor, r2, r.bottomright, 1)
		elif self.vertical:
			pygame.draw.rect(img.surface, self.fgColor, (0, x) + (w, h - x))
		else:
			pygame.draw.rect(img.surface, self.fgColor, (0, 0) + (x, h))

		# Handle centre
		x += hw // 2
		self.handleDecor(x, img.surface, 1 if hw < 25 else 3)

		# Text
		txt = self.getValueText()
		if txt != None:
			txt = Image.text(txt, self.font, self.color)
			dx = hw // 2 + 8
			tw = txt.width
			x = x - tw - dx  if x + dx + tw + 4 > (h if self.vertical else w) else x + dx
			if self.vertical:
				txt = Image(pygame.transform.rotate(txt.surface, -90))
				x = (0, x)
			else: x = (x, 0)
			txt.blitTo(img.surface, x)

		# Finish up
		if self.border: img.borderInPlace(self.border, self.borderColor)
		self.imgs = {0: img}

	def _event(self, ev):
		"""Fires CHANGE"""
		xy = self.vertical
		change = True
		if ev.type in (GuiEvent.MOUSEDOWN, GuiEvent.FOCUS):
			px, hw = self.metrics
			x = ev.relPosn()[xy]
			if self.vertical: x = self.size[1] - x
			x = (x - self.pad - hw / 2) / px
			self.value = self.min + x * (self.max - self.min)
		elif ev.type == GuiEvent.KEYDOWN:
			dv = self.step
			if dv == None: dv = (self.max - self.min) / 100
			page = self.handle if self.handle else dv * self.page
			orig = ev.original
			if isIncr(orig): self.value += dv
			elif isDecr(orig): self.value -= dv
			elif isPgUp(orig): self.value += page
			elif isPgDn(orig): self.value -= page
			elif isHome(orig): self.value = self.max if self.swapHome else self.min
			elif isEnd(orig): self.value = self.min if self.swapHome else self.max
			else: return None
		else: change = False
		if change: ev.type = GuiEvent.CHANGE
		return super()._onEvent(ev)


class MsgBox(Container):
	cancelButton = None
	modal = True
	valArgs = None

	bgColor = 224, 224, 224
	pad = 8
	border = 3

	def __init__(self, msg, buttons=None, cols=None, align=CENTER, validator=None, default="", password=None,
			title=None, minSize=None, name=None, posn=CENTER, allowClose=True, allowCancel=True, **kwargs):
		super().__init__(name, posn, title)
		self.validator = MsgBox.date if validator is date else validator
		self.allowClose = allowClose
		self.setStyle(**kwargs)
		if minSize != None: self.place(Ghost(minSize))
		lbl = Label(msg)

		# Buttons
		if buttons == None:
			buttons = ("Close",) if validator == None else ("OK", "Cancel")
		cntnr = Button.grid(buttons, cols=cols, align=align)
		self.buttons = cntnr.widgets
		self.buttonNames = buttons
		n = 0
		for b in buttons:
			if b.lower() == "cancel":
				self.cancelButton = cntnr.widgets[n]
				if not allowCancel: self.cancelButton.disable()
			n += 1
		cntnr.name = "Buttons"

		# Position for button Container
		x, y = lbl.below(8)
		wb = cntnr.getWidth()
		wl = lbl.getWidth()
		if minSize != None:
			w = minSize[0]
			if w > wl: wl = w
		if wb < wl: x += (wl - wb) // 2

		# Input
		self.valMsgDefault()
		if validator != None:
			w = max(wb, wl) - 2 * TextInput.pad
			if TextInput.font == None: raise NoFont("TextInput")
			h = fontHeight(TextInput)
			self.input = TextInput(txt=default, inner=(w, h), posn=(0, y), password=password)
			self.status = Status()
			self.status.posn = self.input.below(2)
		else:
			self.input = None
			self.status = None

		# Place widgets
		cntnr.posn = x, y
		self.place(lbl, self.input, self.status, cntnr)
		if self.input != None: self.setStatus(None)

	def buttonIndex(self, name):
		try: n = self.buttonNames.index(name)
		except: n = None
		return n

	def getButton(self, name):
		n = self.buttonIndex(name)
		return self.buttons[n] if n != None else None

	def setStatus(self, txt=None):
		s = self.status
		if s != None:
			if txt == None:
				s.visible = False
				y = self.input.below(8)
			else:
				s.setText(txt)
				s.visible = True
				s.getSize(True)
				y = s.below(8)
			self.buttons[0].container.y = y[1]
		self.titleImg = None
		self.getSize(True)

	def validConfig(self, **kwargs):
		self.valArgs = {"dialog": self}
		for k in kwargs: self.valArgs[k] = kwargs[k]
		if self.validator in (int, float):
			if self.validator == int: self.valArgs["integer"] = True
			self.validator = MsgBox.number
		return self

	def validate(self):
		"""Run the validator; set status on exception"""
		if self.validator == None: return True
		try:
			self.value
			return True
		except:
			self.setStatus(self.valMsg)
		return False

	def valMsgDefault(self, cls=None):
		"""Set default validator error message"""
		if not cls: cls = self.validator
		if cls in (int, float):
			self.valMsg = "A{} is required!".format(" number" if cls is float else "n integer")
		else: self.valMsg = "Invalid data!"

	@property
	def value(self):
		"""Obtain input value from validator; raises exception on invalid input"""
		if self.validator:
			txt = self.input.txt
			return self.validator(txt, **self.valArgs) if self.valArgs else self.validator(txt)

	def _event(self, ev):
		"""Fires CANCEL or SUBMIT"""
		click = ev.type == GuiEvent.MOUSEDOWN and type(ev.target) == Button
		cancel = click and ev.target is self.cancelButton
		done = click or ev.type == GuiEvent.ENTER
		if cancel: ev.type = GuiEvent.CANCEL
		elif done:
			done = self.validate()
			if done: ev.type = GuiEvent.SUBMIT
			else:
				self.gui.focus = self.input
		if cancel or done:
			ev.value = None if cancel else self.value
			if self.allowClose: self.close()
			self.setStatus(None)
		return self._onEvent(ev)

	@staticmethod
	def date(s, delims=" .-/", **argDict):
		"""Validator for date input"""
		dMin, dMax, dlg = getValues("low", "high", "dialog", **argDict)
		if dlg: dlg.valMsgDefault()
		d = delims[0]
		for c in delims[1:]:
			s = s.replace(c, d)
		s = re.sub("\s+", d, s).strip()
		d = date(*[int(n) for n in s.split(d)])
		if dMin or dMax:
			err = False
			if dMin:
				if d < dMin: err = True
			if dMax:
				if d > dMax: err = True
			if err:
				msg = "Date must be in range\n[{}, {}]".format(dMin, dMax)
				if dlg: dlg.valMsg = msg
				raise ValueError(msg)			
		return d

	@staticmethod
	def number(s, **argDict):
		"""Validator for numerical input within a specified range of values"""
		n0, n1, cls, dlg = getValues("low", "high", "integer", "dialog", **argDict)
		cls = int if cls else float
		if not cls: cls = float
		if dlg: dlg.valMsgDefault(cls)
		n = cls(s)
		if n < n0 or n > n1:
			msg = "Value must be in range\n[{}, {}]".format(n0, n1)
			if dlg: dlg.valMsg = msg
			raise ValueError(msg)
		return n


class Checkbox(Widget):
	"""Class for check box and radio button controls"""

	border = 1
	bgColor = None
	enabled = True
	selectable = True
	group = {}

	def __init__(self, style=0, imgs=None, name=None, posn=(0,0), **kwargs):
		super().__init__(name, posn)
		self.setStyle(**kwargs)
		self.imgs = imgs if style==None else self.makeImages(style, imgs)

	@classmethod
	def fit(cls, *imgs, font=None):
		"""Scale images based on font size"""
		sz = fontHeight(font if font else cls.font)
		return [Image(img).scale((sz,sz)) if img else None for img in imgs]

	def makeImages(self, style=0, mark=None):
		sz = fontHeight(self)
		if style:
			r = sz // 2
			img0 = Image.ellipse(r, fill=self.bgColor, stroke=self.color, strokeWeight=self.border)
		else:
			img0 = Image.rect((sz,sz), fill=self.bgColor, stroke=self.color, strokeWeight=self.border)
		img1 = img0.clone()
		if mark:
			if mark[0]: mark[0].blitTo(img0)
			if mark[1]: mark[1].blitTo(img1)
		elif style:
			pygame.draw.circle(img1.surface, self.color, (r,r), r//2)
		else:
			sz -= 2
			pygame.draw.line(img1.surface, self.color, (1,1), (sz,sz))
			pygame.draw.line(img1.surface, self.color, (1,sz), (sz,1))
		return img0, img1

	@property
	def isRadio(self): return len(self.group) > 0

	def getImage(self, n=None):
		return self.imgs[1 if self.selected else 0]

	def label(self, text=None, **kwargs):
		"""Create a text label and place the Checkbox and Label into a new Container"""
		name = self.name + "_Container" if self.name else None
		c = Container(name, self.posn)
		self.posn = (0, 0)
		pad = kwargs["pad"] if "pad" in kwargs else 1 + self.getWidth() // 3
		if text == None: text = self.name
		f = "font"
		if f not in kwargs: kwargs[f] = self.font
		label = Label(text, posn=self.beside(pad), **kwargs)
		c.place(self, label).getSize()
		return self
		
	def _event(self, ev):
		"""Fires SELECT, DESELECT"""
		if ev.type == GuiEvent.MOUSEDOWN:
			if self.isRadio: self.select()
			else: self.selected = not self.selected
			ev.type = GuiEvent.SELECT if self.selected else GuiEvent.DESELECT
		return self._onEvent(ev)
