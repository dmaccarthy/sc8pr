from sc8pr.sketch import Sketch, OPEN
from sc8pr.util import rgba
from sc8pr.image import Image
from sc8pr.io import USERINPUT
from pygame.constants import MOUSEBUTTONDOWN

WHITE, RED = rgba("white", "red")

def setup(sk):
    sk.setBackground(None, WHITE)
    sk.fileDialog(OPEN, True, "<Image>")
    sk.animate(eventMap={USERINPUT:start})

def start(sk, ev):
    img = Image(ev.value)
    sk.size = img.size
    bg = Image(img.size, WHITE)
    img.blitTo(bg)
    sk.setBackground(bg)
    sk.dot = Image.ellipse(2, RED)
    sk.poly = []
    sk.animate(draw, {MOUSEBUTTONDOWN:mouse})

def mouse(sk, ev): sk.poly.append(ev.pos)

def draw(sk):
    sk.simpleDraw()
    if len(sk.poly) > 2:
        sk.display().plot(sk.poly, strokeWeight=2, stroke=RED, closed=True)

print(Sketch(setup).play((800,600), mode=0).poly)