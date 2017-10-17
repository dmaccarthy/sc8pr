# Copyright 2017 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from math import sin, pi
from random import randint, uniform, choice
from sc8pr import Sketch, Image, Canvas, BOTH
from sc8pr.shape import Circle 
from sc8pr.util import rgba, randPixel 
from sc8pr.robot import Robot
from sc8pr.sprite import physics
from sc8pr.misc.plot import Plot
		
def dumb(r): pass


class Arena(Sketch):

	def setup(self):
		self.bg = self.renderBG()
		robo = Robot(["#ff5050", "#ffd428"]).bind(brain=self.brain)
		self += robo.config(width=60, pos=(100,400), angle=270, bounce=BOTH)
		robo.gyro = robo.angle

	def renderBG(self): return Image(self.size, "white")

	@classmethod
	def run(cls, brain=dumb, **kwargs):
		cls((640,480)).config(brain=brain).play("Robot Arena")


class Circles(Arena):

	def renderBG(self, n=50):
		size = self.size
		cv = Canvas(size, "white")
		for i in range(n):
			r = randint(10, size[0]/8)
			cv += Circle(r).config(weight=0, fill=rgba(True), pos=randPixel(size))
		return cv.snapshot()


class Trace(Sketch):

	def setup(self):
		pl = Plot(self.size, [-4, 4, -1.5, 1.5]).config(bg="white")
		pl.series(sin, param=[-pi, pi, 2 * self.width - 1], marker=("blue", 4))
		self.bg = pl.snapshot()
		robo = Robot(["#ff5050", "#ffd428"]).bind(brain=self.brain)
		self += robo.config(width=60, pos=self.center)

	@staticmethod
	def run(brain=dumb):
		Trace((640,480)).config(brain=brain).play("Trace the Curve")


class ParkingLot(Sketch):

	def __init__(self, size, brain):
		self.brain = brain
		super().__init__(size)
#		self.config(weight=1, border="yellow")

	def drawLot(self):
		n = 3.5
		p = Plot(self.size, [0,6,0,n]).config(bg="#f0f0f0")
		attr = dict(stroke="orange", weight=4)
		for x in range(1,6):
			p.series([(x, 0), (x, 1)], **attr)
			p.series([(x, n), (x, n-1)], **attr)
		attr.update(stroke="blue")
		p.series([(0.5, n/2), (5.5, n/2)], **attr)
		p.series([(x + 0.5, n/2) for x in range(6)], marker=("red", 8))
		return p

	def setup(self):
		p = self.drawLot()
		self.bg = p.snapshot()
		h = self.height / 4.5
		x = randint(h, self.width - h)
		y = p.pixelCoords((0, uniform(1.5, 2)))[1]
		attr = dict(height = h, mass = 1, wrap=0)
		robot = Robot(["#ffd428", "#ff5050"]).config(
			name = "Crash", pos = (x, y),
			angle = randint(0, 359), **attr)
		self += self.bindBrain(robot)
		pos = lambda y: p.pixelCoords((0.5 + randint(0, 5), y))
		c = False, False
		a = 90, 270
		self += Robot(c).config(pos=pos(0.5), angle=choice(a), **attr)
		self += Robot(c).config(pos=pos(3), angle=choice(a), **attr)

	def ondraw(self): physics(self)

	def bindBrain(self, robot):
		brain = self.brain
		if brain is None:
			self.bind(onkeydown=Robot.remote).config(remote=robot)
		else: robot.bind(brain=brain)
		return robot

	@staticmethod
	def run(brain=dumb):
		ParkingLot((640,360), brain).play("Robot Parking Lot", mode=False)
