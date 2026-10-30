"""Stadium advertising V2. Provisional typography, not an official UADE logo.

No institutional images or shields are distributed. Coordinates are world metres.
"""
from dataclasses import replace
import math
from phase7b.visual_scene import Primitive, box
from phase7c.scoreboard import FONT, rectangles

PREFIX = 'uade_ad_'
REAR_CENTERS = ((7.2, -4.3, .47), (7.2, 4.3, .47))
SIDE_X = (-11., -5., 1.)
MAX_GEOMS = 400
GLYPHS = {**FONT,
          'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
          'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110']}
BLUE = (.025, .12, .30, 1.)
WHITE = (.94, .96, .98, 1.)


def lettering(text, x, y, top, scale, name, color):
    width = (len(text)*6-1)*scale
    for index, char in enumerate(text):
        for row, col, height, length in rectangles(GLYPHS[char]):
            yield Primitive(f'{name}_{index}_{row}_{col}', 'box',
                            (x, y+width/2-(index*6+col+(length-1)/2)*scale,
                             top-(row+(height-1)/2)*scale),
                            (.008, length*scale*.48, height*scale*.48), color,
                            emission=.25)


def transformed(item, center, yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    x,y,z=item.position
    return replace(item,position=(center[0]+c*x-s*y,center[1]+s*x+c*y,center[2]+z),yaw=item.yaw+yaw)


def board(name,center,yaw,width=3.4,*,double_sided=False,dark=False):
    """A low perimeter board. Local -X faces the pitch; text has physical depth."""
    background,ink=(BLUE,WHITE) if dark else (WHITE,BLUE)
    items=[box(name+'_frame',(0,0,0),(.055,width/2,.42),BLUE)]
    for face in ((-1,1) if double_sided else (-1,)):
        # Rotate the reverse face 180 degrees so lettering is not mirrored.
        turn=0 if face==-1 else math.pi
        surface=[box(name+f'_face_{face}',(-.064,0,0),(.009,width/2-.035,.375),background),
                 box(name+f'_red_{face}',(-.077,0,-.31),(.006,width/2-.04,.025),(.65,.035,.055,1))]
        surface.extend(lettering('UADE',-.080,0,.255,.085,name+f'_text_{face}',ink))
        items.extend(transformed(p,(0,0,0),turn) for p in surface)
    return [transformed(p,center,yaw) for p in items]


def ribbon():
    """Low concourse fascia, in front of the rear bowl, entirely outside the pitch."""
    items=[];segments=12;radius=19.7
    for i in range(segments):
        angle=-math.pi/2+(i+.5)*math.pi/segments
        center=(-8+radius*math.cos(angle),radius*math.sin(angle),.56)
        half=radius*math.tan(math.pi/(2*segments))+.015
        name=f'{PREFIX}ribbon_{i}'
        local=[box(name,(0,0,0),(.045,half,.30),BLUE),
               box(name+'_red',(-.052,0,.245),(.008,half,.035),(.65,.035,.055,1)),
               box(name+'_line',(-.052,0,-.26),(.008,half,.012),WHITE)]
        if i in (2,5,6,9):
            local.extend(lettering('UADE',-.066,0,.18,.060,name+'_text',WHITE))
        items.extend(transformed(p,center,angle) for p in local)
    return items


def advertisements():
    items=[]
    for i,center in enumerate(REAR_CENTERS):
        items.extend(board(f'{PREFIX}rear_{i}',center,0,double_sided=True))
    for side in (-1,1):
        for i,x in enumerate(SIDE_X):
            items.extend(board(f'{PREFIX}side_{side}_{i}',(x,side*12.45,.47),side*math.pi/2,
                               width=4.5,dark=i%2==0))
    items.extend(ribbon())
    if len(items)>MAX_GEOMS:raise RuntimeError('Advertising geometry budget exceeded')
    return items
