# Copyright 2015-2023 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Robot Party Simulation"

from random import randint, uniform, shuffle
from sc8pr import BOTH
from sc8pr.geom import dist
from sc8pr.sprite import physics, Collisions
from sc8pr.robot import RobotThread
from sc8pr.robot.arena import BrainSketch, Robot

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

    def ondraw(self, ev=None):
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

    def oncollide(self, ev=None):
        self.randStart()
        self.collision = False
        self.motors = 0

    onbounce = oncollide

    def brain(self):
        "Robot control function"
        self.randMotors()
        while self.active:
            self.updateSensors()
            if self.restart < self.uptime:
                self.randStart()
                self.randMotors()
