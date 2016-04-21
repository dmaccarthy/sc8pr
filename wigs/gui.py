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


import pygame
from time import time
from wigs.image import Image, Position, CENTER
from wigs.util import fontHeight, handleEvent, getValues, dragging, MOVE

GUI_MIN = pygame.USEREVENT + 100
GUI_MAX = GUI_MIN + 14
#PyEvent = pygame.event.EventType


def position(srcSize, where=CENTER, margin=0, destSize=None):
	if type(where) in (tuple, list): return where 
	return Position(margin, where).xy(destSize, srcSize)


class NoFont(Exception):

	def __init__(self, obj):
		super().__init__("No font has been assigned for {}".format(obj))


class GuiEvent:
	"""Class for describing events intercepted by the GUI"""

	names = ("mouseDown", "doubleClick", "mouseOver", "mouseOut", "keyDown", "focus", "blur",
		"select", "deselect", "enter", "escape", "cancel", "change", "submit", "drag")
	MOUSEDOWN = GUI_MIN
	DBL_CLICK = GUI_MIN + 1
	MOUSEOVER = GUI_MIN + 2
	MOUSEOUT = GUI_MIN + 3
	KEYDOWN = GUI_MIN + 4
	FOCUS = GUI_MIN + 5
	BLUR = GUI_MIN + 6
	SELECT = GUI_MIN + 7
	DESELECT = GUI_MIN + 8
	ENTER = GUI_MIN + 9
	ESCAPE = GUI_MIN + 10
	CANCEL = GUI_MIN + 11
	CHANGE = GUI_MIN + 12
	SUBMIT = GUI_MIN + 13
	DRAG = GUI_MIN + 14

	def __init__(self, ev, orig, wdg):
		self.type = ev
		self.original = orig
		self.target = wdg

	@property
	def name(self): return self.names[self.type - GUI_MIN]

	@property
	def dialog(self): return self.target.dialog

	def __str__(self):
		return "<{}({}-{} @ {})>".format(type(self).__name__, self.type, self.name, str(self.target))

	def relPosn(self, fromCenter=False):
		"""Get event position relative to target widget"""
		x, y = self.target.getAbsPosn()
		if fromCenter:
			x += self.target.getWidth() // 2
			y += self.target.getHeight() // 2
		mx, my = self.original.pos
		return mx - x, my - y


class GUI():
	"""Class for drawing GUI and dispatching events to Widgets"""

	widgets = []
	hover = None
	focus = None
	lastClick = None, 
	focusable = True
	name = index = None
	dblClickTime = 400
	level = -1
	drag = None

	def __init__(self, sk=None): Widget.sketch = self.sketch = sk

	@staticmethod
	def mouseEvent(ev): return hasattr(ev, "pos")

	def contains(self, ev): return True
	def isEnabled(self): return True

	def dialogCount(self): return len(self.widgets)

	@property
	def gui(self): return self

	@property
	def path(self): return [self]

	@property
	def cursorId(self):	
		if self.hover:
			if self.modal:
				dlg = self.topDialog
				if not (self.hover is dlg or self.hover.inside(dlg)): return 0
			if self.hover.level == 0:
				if not self.hover.fixedPosn: return MOVE  # and self.hover is self.drag
		return self.hover.cursorId if self.hover else 0

	@property
	def topDialog(self):
		wdg = self.widgets
		return wdg[-1] if len(wdg) else None

	def find(self, name):
		i = len(self.widgets) - 1
		while i >= 0:
			wdg = self.widgets[i].find(name)
			if wdg != None: return wdg
			i -= 1

	def place(self, *args):
		"Blur top dialog; unhandled blur is NOT sent to Sketch._onEvent!"
#		modal = False
		for w in args:
			w.focusable = True
#			if self.modal and w.modal and w not in self.widgets: modal = True
# 		if modal:
# 			raise RuntimeError("Cannot place widgets above modal dialog")
		if len(self.widgets):
			fDlg = self.widgets[-1]
			fDlg._event(GuiEvent(GuiEvent.BLUR, None, fDlg))
		Container.place(self, *args)
		f = self.widgets[-1]
		self.focus = f if f.focusable else None
		return self

	def compose(self, *args, **kwargs):
		"Place Widgets into the GUI, contained in a new dialog"
		title, name, posn = getValues("title", "name", "posn", **kwargs)
		if not posn: posn = CENTER
		c = Container(name, posn, title).setStyle(**kwargs).place(*args)
		self.place(c)
		return c

	def closeAll(self, color=None, dest=None):
		while len(self.widgets):
			self.close(self.widgets[-1], color, dest)

	def close(self, wdg, color=None, dest=None):
		assert wdg.container == self
		r = wdg.clear(color, dest)
		wdg.remove()
		if self.focus == wdg: self.focus = self.topDialog #None
		return r

	def draw(self, dest=None):
		if dest == None: dest = pygame.display.get_surface()
		r = []
		for wdg in self.widgets:
			posn = position(wdg.getSize(), wdg.getBlitPosn())
			img = wdg.getImage()
			if img: r.append(dest.blit(img.surface, posn))
		return r

	def findHover(self, ev):
		"""Locate 'hover' and 'focus' widgets"""
		f = h = Container.findHover(self, ev.pos)
		if f == self: return f, None
		while not (f.focusable):
			f = f.container
		return h, f

	@property
	def modal(self):
		if len(self.widgets): return self.topDialog.modal
		return False

	def ignore(self, ev):
		"""Ignore event while modal dialog is running"""
		self.hover = None

	def overAndOut(self, hover, ev):
		"""Send MOUSEOUT and MOUSEOVER events"""

		eventQueue = []
		if hover or self.hover and not hover is self.hover:
			
			# Get old and new hover widget paths...
			h, s = 0, 0
			if hover:
				hPath = hover.path
				h = len(hPath)
			if self.hover:
				sPath = self.hover.path
				s = len(sPath)

			# Find common container...
			i = 1
			if hover and self.hover:
				while i < min(h,s) and hPath[i] is sPath[i]: i += 1

			# Send MOUSEOUT events...
			if self.hover:
				for wdg in [sPath[j] for j in range(s-1, i-1, -1)]:
					if wdg.gui:
						eventQueue.append(wdg._event(GuiEvent(GuiEvent.MOUSEOUT, ev, wdg)))

			# Send MOUSEOVER events...
			if hover:
				for wdg in hPath[i:]:
					eventQueue.append(wdg._event(GuiEvent(GuiEvent.MOUSEOVER, ev, wdg)))

		self.hover = hover
		return eventQueue

	def _event(self, ev):
		"""Fires BLUR, FOCUS, MOUSEDOWN, DBL_CLICK, or KEYDOWN for intercepted events"""

		# Drag top dialog...
		if self.drag and self.focus is self.drag:
			if dragging(ev):
				self.focus.move(ev.rel)
				return self.focus._event(GuiEvent(GuiEvent.DRAG, ev, self.focus))
		self.drag = None

		# Check if event needs to be intercepted...
		key, mouse = ev.type == pygame.KEYDOWN, self.mouseEvent(ev)
		if not (key or mouse):
			return None if self.modal and ev.type != pygame.VIDEORESIZE else ev

		# KEYDOWN events are intercepted when there is a focused widget...
		if key:
			if self.focus:
				if self.focus.dialog.gui: # Dialog might have been closed!
					return self.focus._event(GuiEvent(GuiEvent.KEYDOWN, ev, self.focus))
			return ev

		# Find 'blur', 'hover', 'mouseDown' and 'focus' widgets...
		click = ev.type == pygame.MOUSEBUTTONDOWN
		hover, focus = self.findHover(ev)
		if hover is self: hover = None
		mouseDown = hover if click else None
		blur = self.focus if click and not focus is self.focus else None
		if not click or focus in (self, self.focus): focus = None

		# Adjust event if top dialog is modal...
		if self.modal:
			if not hover: return self.ignore(ev)
			if hover:
				if not (hover is self.topDialog or hover.inside(self.topDialog)):
					return self.ignore(ev)

		# Send MOUSEOUT and MOUSEOVER events...
		eventQueue = self.overAndOut(hover, ev)

		# Send BLUR event...
		if blur:
			eventQueue.append(self.focus._event(GuiEvent(GuiEvent.BLUR, ev, self.focus)))
			self.focus = None

		# Send FOCUS event...
		if focus:
			eventQueue.append(focus._event(GuiEvent(GuiEvent.FOCUS, ev, focus)))
			self.focus = focus
			
			# Ensure focused widget's dialog is on top...
			if not focus.dialog is self.topDialog:
				focus.dialog.remove()
				self.widgets.append(focus.dialog)
				focus.dialog.container = self

		# Send MOUSEDOWN or DBL_CLICK event...
		if mouseDown:
			eType = GuiEvent.MOUSEDOWN
			if not mouseDown is focus:
				if mouseDown is self.lastClick[0]:
					if (ev.button <= 3 and ev.button == self.lastClick[2] and
							(time() - self.lastClick[1]) < self.dblClickTime / 1000):
						eType = GuiEvent.DBL_CLICK
						self.lastClick = None,
				eventQueue.append(mouseDown._event(GuiEvent(eType, ev, mouseDown)))
			if eType == GuiEvent.MOUSEDOWN:
				self.lastClick = mouseDown, time(), ev.button
				if self.hover is self.focus and not self.focus.fixedPosn and self.focus is self.topDialog:
					self.drag = self.focus

		# Return unhandled events...
		if not (focus or mouseDown or self.modal): eventQueue.append(ev)
		return eventQueue


class Widget:
	DEFAULT = 0
	NORMAL = 1
	HOVER = 2
	FOCUS = 3
	SELECT = 4
	DISABLE = 5

	visible = True
	enabled = False
	focusable = False
	selectable = False
	selected = False
	fixedPosn = True
	modal = False

	size = None
	container = None
	sketch = None
	eventMap = None
	cursorId = 0

	font = None
	border = 0
	pad = 0
	color = 0, 0, 0
	borderColor = altColor = 144, 144, 144
	bgColor = None
	colors = {
		DEFAULT: (232,232,232),
		HOVER: (208,208,255),
		SELECT: (176,176,255),
		FOCUS: (255,255,255),
		DISABLE: (232,232,232)
	}

	def __init__(self, name=None, posn=(0,0)):
		self.posn = posn
		self.name = name
		self.imgs = {}

	def __str__(self):
		name = "('{}')" if self.name else ""
		return ("{}" + name).format(type(self).__name__, self.name)

	def bind(self, eventMap=None):
		if eventMap:
			self.eventMap = eventMap if type(eventMap) is dict else {None:eventMap}
		else:
			self.eventMap = None
		return self

# Widget state...

	def isEnabled(self): return self.visible and self.enabled
	def isFocus(self): return self == self.gui.focus

	def show(self):
		self.visible = True
		return self

	def hide(self):
		self.visible = False
		return self

	def enable(self):
		self.enabled = self.visible = True
		return self
	
	def disable(self):
		self.enabled = False
		return self

	def getState(self, sDict=None):
		if not self.enabled: s = self.DISABLE
		elif self.selected: s = self.SELECT
		else:
			gui = self.gui
			if self == gui.focus: s = self.FOCUS
			elif self == gui.hover: s = self.HOVER
			else: s = self.NORMAL
		if sDict != None and s not in sDict: s = 0
		return s

# Style...

	def setStyle(self, **kwargs):
		for a in ("bgColor", "color", "altColor", "pad", "border", "borderColor", "altBdColor", "font"):
			if a in kwargs:
				setattr(self, a, kwargs[a])
		return self

# Widget hierarchy...

	@property
	def dialog(self):
		"""Return the top-level container"""
		c = self.container
		if c == None or type(c) == GUI: return self
		return c.dialog

	@property
	def gui(self): return self.dialog.container

	@property
	def index(self):
		"""Return the index of a widget within its container"""
		return self.container.widgets.index(self) if self.container else None

	@property
	def level(self):
		"""Return the number of containers between the widget and its dialog"""
		return self.container.level + 1 if self.container else 0

	@property
	def path(self):
		return (self.container.path if self.container else []) + [self]

	def isDialog(self): return isinstance(self.container, GUI)
	def isTopDialog(self): return self is self.gui.topDialog
	def find(self, name): return self if name == self.name else None

	def inside(self, c):
		"""Check if the Widget is contained within a Container"""
		if self.container == c: return True
		if self.isDialog() or self.container == None: return False
		return self.container.inside(c)

	def remove(self):
		self.container.widgets.remove(self)
		self.container = None
		return self

	def close(self): self.gui.close(self.dialog)

	def clear(self, color=None, dest=None):
		if dest == None: dest = pygame.display.get_surface()
		if color == None:
			if self.sketch != None: color = self.sketch.bgColor
			if color == None: color = self.bgColor
			if color == None: color = (0,0,0)
		r = self.getRect()
		pygame.draw.rect(dest, color, r)
#		if self.sketch != None: self.sketch.dirty(r)
		return r

# Metrics...

	def centered(self, x=True, y=True):
		xc, yc = position(self.getSize(), CENTER, 0, self.container.getInnerSize())
		self.posn = xc if x else self.posn[0], yc if y else self.posn[1]
		return self
		
	def posnAsXY(self):
		xy = self.posn
		if self.isDialog() or self.container == None:
			xy = position(self.getSize(), xy)
		return xy

	def getEdge(self): return 2 * (self.pad + self.border)

	def getSize(self, reset=False):
		if self.size == None or reset:
			self.size = self.getImage(0).size
		return self.size

	@property
	def x(self): return self.posnAsXY()[0]

	@property
	def y(self): return self.posnAsXY()[1]

	@x.setter
	def x(self, val): self.posn = (val, self.y)

	@y.setter
	def y(self, val): self.posn = (self.x, val)

	def getWidth(self, s=None): return self.getSize()[0]
	def getHeight(self, s=None): return self.getSize()[1]

	def getBlitPosn(self):
		"""Position in container where the Widget is to be drawn"""
		c = self.container
		x, y = self.posnAsXY()
		if isinstance(c, Container):
			xo, yo = c.getOrigin()
			x += xo
			y += yo
		return x, y

	def getAbsPosn(self):
		"""Position on the screen where the Widget is to be drawn"""
		c = self.container
		if isinstance(c, Container):
			x, y = self.getBlitPosn()
			cx, cy = c.getAbsPosn()
			return x + cx, y + cy
		return self.posnAsXY()

	def getRect(self): return pygame.Rect(self.getAbsPosn(), self.getSize())

	def move(self, rel):
		self.clear()
		x, y = rel
		self.x += x
		self.y += y

	def below(self, pad=0, align="W", adjust=0):
		x, y = self.posnAsXY()
		w, h = self.getSize()
		w -= adjust
		dx = 0 if align == "W" else (w if align=="E" else w // 2)
		return x + dx, y + h + pad

	def beside(self, pad=0):
		x, y = self.posnAsXY()
		return x + self.getWidth() + pad, y

	def contains(self, posn):
		return self.getRect().collidepoint(posn)

# Other...

	def getImage(self, s=None):
		if s == None: s = self.getState()
		if s not in self.imgs: s = 0
		return self.imgs[s]

	def findHover(self, posn):
		return self if self.isEnabled() and self.contains(posn) else None

# Event handlers...

	def _event(self, ev):
		"""Internal processing of GUI event; return unhandled event object"""
		assert(isinstance(ev, GuiEvent))
		return self._onEvent(ev)

	def _onEvent(self, ev):
		"""Event handler to interact with program"""
		if self.eventMap: return handleEvent(self, ev)
		c = self.container
		return ev if self.isDialog() or c == None else c._event(ev)

	def makeGroup(self, *args):
		"""Create a group of selectable Widgets"""
		self.group = {self}
		for r in args:
			self.group.add(r)
			r.group = self.group
			r.selectable = True
		self.selectable = True
		self.select()
		return self.group

	def select(self):
		assert hasattr(self, "group"), "Cannot call select method on Widgets that do not have a group"
		for r in self.group: r.selected = False
		self.selected = True

	def getSelected(self):
		for r in self.group:
			if r.selected: return r


class Container(Widget):
	enabled = True
	fixedPosn = False
	inner = None
	titleImg = None

	borderColor = 0, 0, 255
	altBdColor = 192, 192, 192
	color = 255, 255, 255

	def __init__(self, name=None, posn=(0,0), title=None, **kwargs):
		self.title = title
		self.widgets = []
		super().__init__(name, posn)
		self.setStyle(**kwargs)

	def __getitem__(self, i): return self.widgets[i]

	def print(self, level=0):
		"""Print the widget hierarchy"""
		print(level * "*", str(self), sep="")
		level += 1
		for w in self.widgets:
			if isinstance(w, Container): w.print(level)
			else: print(level * "*", w, sep="")

	def find(self, name):
		if name == self.name: return self
		for wdg in self.widgets:
			tmp = wdg.find(name)
			if tmp != None: return tmp
		return None
	
	def getWidgets(self, cls=None):
		for wdg in self.widgets:
			if cls == None or isinstance(wdg, cls):
				yield wdg

	def place(self, *args):
		for wdg in args:
			if wdg != None:
				if wdg  in self.widgets: wdg.remove()
				self.widgets.append(wdg)
				wdg.container = self
		return self

	def empty(self):
		while len(self.widgets): self.widgets[-1].remove()

	def findHover(self, posn):
		if not self.contains(posn) or not self.isEnabled(): return None
		else: hov = self
		for wdg in self.widgets:
			tmp = wdg.findHover(posn)
			if tmp != None: hov = tmp
		return hov

	def getTitleHeight(self):
		if self.title == None: return 0
		if self.font == None: raise NoFont(self)
		return fontHeight(self)

	def onTitle(self, posn):
		"""Determine if the position is within the title bar"""
		bx, by = self.getBlitPosn()
		x, y = posn
		x -= bx
		y -= by
		h = self.getTitleHeight() + self.border
		w = self.getWidth()
		return x>=0 and y>=0 and x<w and y<h

	def getOrigin(self):
		e = self.border + self.pad
		return (e, e + self.getTitleHeight())

	def getSize(self, reset=False):
		if self.size == None or reset:
			w, h = self.getInnerSize(reset)
			e = self.getEdge()
			self.size = w + e, h + e + self.getTitleHeight()
		return self.size

	def getInnerSize(self, reset=False):
		if self.inner == None or reset:
			width, height = 0, 0
			for wdg in self.widgets:
				x, y = wdg.posn
				w, h = wdg.getSize()
				x += w
				y += h
				if x > width: width = x
				if y > height: height = y
			self.inner = width, height
		return self.inner

	def getImage(self):
		img = Image(self.getSize(), bgColor=self.bgColor)
		for wdg in self.widgets:
			if wdg.visible:
				wdg.getImage().blitTo(img.surface, wdg.getBlitPosn())
		focus = self.gui.focus if self.gui else None
		if focus:
			focus = self is focus or focus.inside(self)
		bc = self.borderColor if focus else self.altBdColor
		if self.border > 0: img.borderInPlace(self.border, bc)
		if self.title != None:
			if self.titleImg == None:
				if self.font == None: raise NoFont(self)
				self.titleImg = []
				for bc in (self.borderColor, self.altBdColor):
					tmp = Image.text(self.title, self.font, self.color, bgColor=bc)
					self.titleImg.append(tmp.crop((self.getWidth(), self.getTitleHeight()), bgColor=bc))
			self.titleImg[0 if focus else 1].blitTo(img.surface, (0, self.border))
		return img
	
	def fixed(self, fix=True):
		self.fixedPosn = fix
		return self
		