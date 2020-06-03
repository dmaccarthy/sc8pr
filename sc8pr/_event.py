# Copyright 2015-2020 D.G. MacCarthy <http://dmaccarthy.github.io>
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

import pygame

class EventManager:
    "Process events (except VIDEORESIZE) from the pygame event queue"
    debug = False

    def __init__(self, sk):
        self.sk = sk
        self.focus = sk
        self.hover = sk
        self.drag = None

    def dispatch(self, ev):
        "Process one pygame event"

        # Encapsulate mouse and keyboard events as sketch attributes
        sk = self.sk
        other = False
        key = hasattr(ev, "key")
        if key: sk.key = ev
        elif hasattr(ev, "pos"): sk.mouse = ev
        else: other = True

        # Determine 'hover' graphic
        path = sk.objectAt(sk.mouse.pos).path
        if not path: path = [sk]
        self._oldHover = self.hover
        self.hover = path[0]
        setattr(ev, "hover", path[0])
    
        # Set 'focus' graphic and handler name
        setattr(ev, "focus", self.focus)
        name = "on" + pygame.event.event_name(ev.type).lower()

        # Call sk.onevent
        if hasattr(sk, "onevent"):
            if sk.onevent(ev): return

        # Send non-mouse and non-keyboard events
        # to the appropriate sketch event handler
        if other: self.handle(sk, name.replace("event", ""), ev)

        # Send KEYDOWN and KEYUP events to the focused object
        elif key: self.handle(self.focus, name, ev)

        # Process MOUSEBUTTONDOWN events by calling as necessary:
        # onrelease, onblur, onfocus, onmousedown
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if self.drag is not None: self._dragRelease(ev)
            for p in path:
                if p.focusable:
                    focus = p
                    break
            if self.focus is not focus:
                setattr(ev, "focus", focus)
                self.handle(self.focus, "onblur", ev)
                self.focus = focus
                self.handle(focus, "onfocus", ev)
            self._mousedown = path[0]
            self.handle(path, "onmousedown", ev)

        # Process MOUSEBUTTONUP events by calling onrelease or onmouseup/onclick
        elif ev.type == pygame.MOUSEBUTTONUP:
            if not self._dragRelease(ev):
                self.handle(path, "onmouseup", ev)
                if path[0] is self._mousedown:
                    self.handle(path, "onclick", ev)

        # Process MOUSEMOTION events by calling as necessary:
        # onmouseout, onmouseover, ondrag, onmousemotion
        elif ev.type == pygame.MOUSEMOTION:
            self._overOut(path, ev)
            drag = False
            if sum(ev.buttons): # Dragging
                current = _find(self._oldHover.path, "ondrag") \
                    if self.drag is None else self.drag
                if current is not None:
                    if self.drag is not current: self.drag = current
                    self.handle(current, "ondrag", ev)
                    drag = True
            if not drag: self.handle(path, "onmousemotion", ev)

        # Call sk.onhandled
        if hasattr(sk, "onhandled"):
            delattr(ev, "target")
            sk.onhandled(ev)

    def handle(self, path, eventName, ev):
        "Locate and call the appropriate event handler"
        if type(path) is not list: path = path.path
        setattr(ev, "target", path[0])
        setattr(ev, "handler", eventName)
        current = _find(path, eventName)
        handle = current is not None
        if self.debug: print("Handling  :" if handle else "No handler:", ev)
        if handle: getattr(current, eventName)(ev)

    def _dragRelease(self, ev):
        "Handle RELEASE events for graphic being dragged"
        drag = self.drag
        if drag is not None:
            self.handle(drag, "onrelease", ev)
            drag = True
        else: drag = False
        self.drag = None
        return drag

    def _overOut(self, path, ev):
        "Handle MOUSEOVER and MOUSEOUT events"
        oldHover = self._oldHover.path
        obj = oldHover[0]
        while obj not in path:
            self.handle(obj, "onmouseout", ev)
            obj = obj.canvas
        i = path.index(obj)
        for obj in reversed(path[:i]):
            self.handle(obj, "onmouseover", ev)


def _find(p, a):
    "Find an object in the path that has the given attribute"
    for i in range(len(p)):
        g = p[i]
        if hasattr(g, a): return g
