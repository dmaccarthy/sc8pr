# Copyright 2015-2019 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"A collection of robotics simulations for sc8pr 2"

try:
	from sc8pr import Sketch, Image, Canvas, BOTH
	from sc8pr.geom import dist 
	from sc8pr.shape import Circle 
	from sc8pr.util import rgba, randPixel
	from sc8pr.robot import Robot, RobotThread
	from sc8pr.sprite import physics, Collisions
	from sc8pr.misc.plot import Plot, Series
	from sc8pr.gui.dialog import MessageBox
except Exception as e:
	print(e)
	print("Try running 'pip3 install sc8pr' on command line")
	exit()
from math import sin, pi
from random import randint, uniform, choice, shuffle

def ask(robot, prompt, title="User Input", allowCancel=False):
	"Synchronous input to the robot brain"
	sk = robot.sketch
	btns = None if allowCancel else ["Okay"]
	sk["User"] = mb = MessageBox(prompt, "", btns, title).config(pos=sk.center)
	while not mb.command: robot.updateSensors()
	return None if mb.command.name == "Button_Cancel" else mb["Input"].data

def circles(sk, n=50):
	"Draw random circles for arena floor"
	size = sk.size
	cv = Canvas(size, "white")
	for i in range(n):
		r = randint(10, size[0]/8)
		cv += Circle(r).config(weight=0, fill=rgba(True), pos=randPixel(size))
	return cv.snapshot()


class BrainSketch(Sketch):
	"Sketch class that binds a robot brain OR attaches a robot remote control"

	@staticmethod
	def sensorBrain(robot):
		"Update sensors only"
		while robot.active: robot.updateSensors()

	def bindBrain(self, robot):
		brain = self.brain
		if brain is None:
			self.bind(onkeydown=Robot.remoteControl).config(remoteRobot=robot)
			brain = self.sensorBrain
		return robot.bind(brain=brain)

		
class Arena(BrainSketch):
	"Empty arena for robot challenges"

	def setup(self):
		try:
			img = self.render
			try: self.bg = img(self)
			except: self.bg = Image(img)
		except: self.bg = Image(self.size, "white")
		self.weight = 1
		robo = Robot(["#ff5050", "#ffd428"])
		self["Red"] = self.bindBrain(robo).config(width=60,
			pos=(100,400), angle=270, bounce=BOTH)
		robo.gyro = robo.angle

	@classmethod
	def run(cls, brain=None, render=None):
		cls((640,480)).config(brain=brain, render=render).play("Robot Arena")


class Trace(BrainSketch):
	"Sketch that implements a follow-the-blue-curve challenge"

	def setup(self):
		p = Plot(self.size, [-4, 4, -1.5, 1.5]).config(bg="white")
		marker = Image((6, 6), "blue")
		p["Curve"] = Series(sin, param=[-pi, pi, 2 * self.width - 1]).config(marker=marker)
		self.bg = p.snapshot()
		robo = Robot(["#ff5050", "#ffd428"])
		self["Traci"] = self.bindBrain(robo).config(width=60, pos=self.center)

	@staticmethod
	def run(brain=None):
		Trace((640,480)).config(brain=brain).play("Trace the Curve")


class ParkingLot(BrainSketch):
	"Sketch that implements a robot parking challenge"

	def __init__(self, size, brain):
		self.brain = brain
		super().__init__(size)

	def drawLot(self):
		n = 3.5
		p = Plot(self.size, [0,6,0,n]).config(bg="#f0f0f0")
		attr = dict(stroke="orange", weight=4)
		for x in range(1,6):
			key = "Line{}".format(x)
			p[key + "a"] = Series([(x, 0), (x, 1)]).config(**attr)
			p[key + "b"] = Series([(x, n), (x, n-1)]).config(**attr)
		attr.update(stroke="blue")
		p["Blue"] = Series([(0.5, n/2), (5.5, n/2)]).config(**attr)
		redDot = Circle(64).config(fill="red").snapshot().config(width=16)
		p["Red"] = Series([(x + 0.5, n/2) for x in range(6)]).config(marker=redDot)
		return p

	def setup(self):
		p = self.drawLot()
		self.bg = p.snapshot()
		h = self.height / 4.5
		x = randint(h, self.width - h)
		y = p.pixelCoords((0, uniform(1.5, 2)))[1]
		attr = dict(height = h, mass = 1, wrap=0)
		robot = Robot(["#ffd428", "#ff5050"]).config(
			pos = (x, y), angle = randint(0, 359), **attr)
		self["Crash"] = self.bindBrain(robot)
		pos = lambda y: p.pixelCoords((0.5 + randint(0, 5), y))
		c = False, False
		a = 90, 270
		self += Robot(c).config(pos=pos(0.5), angle=choice(a), **attr)
		self += Robot(c).config(pos=pos(3), angle=choice(a), **attr)

	def ondraw(self): physics(self)

	@staticmethod
	def run(brain=None):
		ParkingLot((640,360), brain).play("Robot Parking Lot", mode=False)


RADIUS = 20  # Determines robot size

class Party(BrainSketch):
	"Sketch that implements a robot-mingling party"
	friends = 12

	names = ['Liam', 'Olivia', 'Benjamin', 'Emma', 'Lucas', 'Sophia', 'Oliver',
		'Ava', 'Noah', 'Emily', 'William', 'Charlotte', 'Ethan', 'Amelia', 'Jack',
		'Abigail', 'Lincoln', 'Chloe', 'Owen', 'Aria', 'Jacob', 'Grace', 'Isabella',
		'Alexander', 'James', 'Logan', 'Avery', 'Elizabeth', 'Hunter', 'Lily',
		'Nathan', 'Hannah', 'Carter', 'Ella', 'Grayson', 'Henry', 'Ellie', 'Quinn',
		'Scarlett', 'Isaac', 'Mason', 'Anna', 'Jackson', 'Harper', 'Gabriel',
		'Hailey', 'Daniel', 'Luke', 'Brooklyn', 'Evelyn', 'Samuel', 'Wyatt', 'Isla',
		'Mia', 'Connor', 'Sarah', 'Hudson', 'Claire', 'Bennett', 'Elijah', 'Madison',
		'Mila', 'Joshua', 'Victoria', 'Thomas', 'Addison', 'Caleb', 'Emmett',
		'Natalie', 'Zoey', 'Adam', 'Hazel', 'Matthew', 'Eva', 'Maya', 'David',
		'Zachary', 'Isabelle', 'Michael', 'Sadie', 'Sophie', 'Aiden', 'Jaxon',
		'Everly', 'Sofia', 'Violet', 'Ryan', 'Austin', 'Jayden', 'John', 'Ivy',
		'Paisley', 'Max', 'Brielle', 'Zoe', 'Parker', 'Levi', 'Aubrey', 'Leo',
		'Theodore', 'Nora', 'Audrey', 'Asher', 'Stella', 'Cooper', 'Sebastian',
		'Aurora', 'Alice', 'Dominic', 'Gavin', 'Nolan', 'Piper', 'Kinsley', 'Julia',
		'Naomi', 'Ruby', 'Willow', 'Joseph', 'Eli', 'Blake', 'Harrison', 'Ryker',
		'Sawyer', 'Layla', 'Samantha', 'Mackenzie', 'Brody', 'Clara', 'Leah', 'Maria',
		'Penelope', 'Riley', 'Dylan', 'Evan', 'Marcus', 'Andrew', 'Charles', 'Ryder',
		'Lillian', 'Alexandra']
	shuffle(names)
	names = names[:friends]
	
	def setup(self):
		RobotThread.log = False
		self.config(bg="white", border="blue", weight=1)
		for name in self.names:
			self[name] = PartyRobot(self)
		RobotThread.log = True
		robo = Robot(["#ff5050", "#ffd428"])
		self["Red"] = self.bindBrain(robo).config(width=2*RADIUS,
			pos=self.center, mass=1, bounce=BOTH, greet=None)
		for r in self:
			while min(dist(r.pos, s.pos) for s in self if s is not r) < 2 * r.radius:
				r.pos = r.randPos(self)
		self.cd = Collisions(self)

	def ondraw(self):
		robot = self[-1]
		if robot in physics(self):
			robot.greet = sorted(t.name for t in self.cd.involving(robot))[0]

	@staticmethod
	def run(brain=None):
		Party((640,480)).config(brain=brain).play("Robot Party")


class PartyRobot(Robot):
	"Robots at the party"
	restart = 0
	bounce = BOTH
	mass = 1

	def __init__(self, sk):
		super().__init__([False, False])
		self.config(width=2*RADIUS, pos=sk.center, angle=uniform(0,360))

	def randPos(self, sk):
		w, h = sk.size
		return randint(RADIUS, w-1-RADIUS), randint(RADIUS, h-1-RADIUS)

	def randMotors(self):
		"Randomize the motors"
		f = uniform(-1, 1)
		d = uniform(-0.2, 0.2)
		self.motors = f + d, f - d
	
	def randStart(self):
		"Schedule motor randomization"
		self.restart = self.uptime + uniform(3, 7)

	def oncollide(self):
		self.randStart()
		self.collision = False
		self.motors = 0

	def onbounce(self, u): self.oncollide()

	def brain(self):
		"Robot control function"
		self.randMotors()
		while self.active:
			self.updateSensors()
			if self.restart < self.uptime:
				self.randStart()
				self.randMotors()


if __name__ == "__main__": ParkingLot.run()
