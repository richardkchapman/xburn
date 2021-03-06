#!/usr/bin/env python
from __future__ import division
import math
import numpy
import argparse
try:
    import Image
except ImportError:
    from PIL import Image

from itertools import groupby
from pprint import pprint
version = "0.7"

def loadArray(arr):
    im = Image.fromarray(arr)

def loadImage(file):
    #Open Source
    img = Image.open(file)
    #aspect
    height = args.width/(img.size[0]/img.size[1])
    #This resize is close
    #Rotated and flipped to look proper
    resize = (
        int(math.floor(args.density * args.width)),
        int(math.floor(args.density * height))
        )
    #TODO: make quantize work with a palette, better.
    if args.palette:
        if args.shades < 3:
            palette = [
                0,   0,   0,
                255,   255, 255,
            ] + [255, ] * 254 * 3
        else:
            palette = [0,   0,   0,]
            steps = int(math.floor(256/(args.shades-1)))
            for c in range(args.shades-2):
                m = c+1
                palette = palette + [steps*m,steps*m,steps*m]
            palette = palette + [255, ] * (256-args.shades) * 3
        pimage = Image.new("P", (1, 1), 0)
        pimage.putpalette(palette)
        if args.debug:
            print "Number of shades:" + str(args.shades)
            print "Number of steps:" + str(steps)
            print palette
        #.convert("L", palette=pimage) \
        img.convert("L") \
            .quantize(colors=args.shades, palette=pimage) \
            .resize(resize, Image.LANCZOS) \
            .transpose(Image.ROTATE_180) \
            .transpose(Image.FLIP_LEFT_RIGHT) \
            .save(args.output+".gcode.jpg")
            #.show()
    else:
        if args.debug:
            print "No palette"
        img.convert("L") \
            .resize(resize, Image.LANCZOS) \
            .transpose(Image.ROTATE_180) \
            .transpose(Image.FLIP_LEFT_RIGHT) \
            .save(args.output+".gcode.jpg")
            #.show()
    #Save temp, TODO: do without writing file? tired.
    img = Image.open(args.output+".gcode.jpg")
    #img.show()
    imgarr = numpy.array(img)
    return imgarr

def laserOff():
    appendGcode(args.laseroff)

def laserOn(power):
    appendGcode(args.laseron+ " " + args.modifier + str(power))

#creates a 255x20 black to white gradient for testing settings
def gradientTest():
    test = Image.new( 'RGB', (255,20), "black") # create a new black image
    pixels = test.load() # create the pixel map
    for i in range(test.size[0]):    # for every pixel:
        for j in range(test.size[1]):
            pixels[i,j] = (i, i, i) # set the colour accordingly
    test.save("gradient_testpatten.jpg")


def appendGcode(line):
    global lines
    lines.append(line)

#Set laser mode for grbl 1.1
#Appears this should work? in practice?
def laserMode(status):
    if status == 1:
        appendGcode("$38=1")
    else:
        appendGcode("$38=0")

def getSpeed(value):
    """Return the speed we should use to burn this grey value"""
    value = 255-value  # now 0 is black
    return int(args.blackburnrate + value*((args.whiteburnrate-args.blackburnrate)/255.0))

#TODO: config profiles so you don't have to mess around.....
#SERIOUSLY! ^^^^^^^
parser = argparse.ArgumentParser()
parser.add_argument('file', help='image file name')
parser.add_argument('width', type=int, help='Output width in MM (ish), FIX ME')

#Versioning
parser.add_argument('-v', '--version', action='version', version=version )
#TODO: arguments and profiles.....
#parser.add_argument('-s', '--size',  type=float, help='pixelsize')
parser.add_argument('-pa', '--palette', action='store_true',
    help='Color Palette, use with shades option, needs work.')
parser.add_argument('-s', '--shades',  type=int, default=16,
    help='Number of shades, default 16')
parser.add_argument('-wv', '--whitevalue',  type=int, default=255,
    help='White value, defaults to 255, anything larger than this is skipped.')
parser.add_argument('-de', '--density',  type=float, default=2.0,
    help='Pixels per MM, default 2.0')
parser.add_argument('-sr', '--skiprate',  type=int, default=3000,
    help='Moving Feed Rate')
parser.add_argument('-bbr', '--blackburnrate',  type=int, default=200,
    help='Burning Feed Rate for black')
parser.add_argument('-wbr', '--whiteburnrate',  type=int, default=800,
    help='Burning Feed Rate for white')
parser.add_argument('-on', '--laseron', default="M106",
    help='Laser ON Gcode Command default: M106')
parser.add_argument('-off', '--laseroff', default="M107",
    help='Laser Off Gcode Command default: M107')
parser.add_argument('-power', '--laserpower', default="255",
    help='Laser power default: 255')
parser.add_argument('-mod', '--modifier', default="S",
    help='Laser Power Modifier, defaults to Spindle Speed (S)')
parser.add_argument('-o', '--output',  default="workfile",
    help='Outfile name prefix')
parser.add_argument('-p', '--preview', action='store_true',
    help='Preview burn output, red is skipped over.')
parser.add_argument('-gr', '--grblver',  type=float, default=0.9,
    help='Default Grbl version is 0.9')
parser.add_argument('-tp', '--testpattern', action='store_true',
    help='Create a test pattern. Use ./cli.py test 100 -tp -p -o testfile')
parser.add_argument('-d', '--debug', action='store_true',
    help='Turns on Debugging')

#Check the arguments
args = parser.parse_args()

#Make sure at least one option is chosen
if not (args.file or args.testpattern):
    #Print help
    parser.print_help()
    #Exit out with no action message
    parser.error('No action requested')

if args.testpattern:
    gradientTest()
    args.file = "gradient_testpatten.jpg"

#Do all the things
if args.file:
    #Load a image file to array
    arr = loadImage(args.file)
    scaley = 1/args.density
    scalex = 1/args.density
    #Create a list to store the output gcode lines
    lines = []
    appendGcode(";Xburn: " + str(args))
    #Y position
    yp=0
    #if the grbl version allows lasermode, enable it
    if args.grblver > 0.9:
        laserMode(1)
    #Turn the laser off
    laserOff()
    if args.preview:
        prv = Image.new( 'RGB', (len(arr[0]),len(arr)), "red")
        pixels = prv.load() # create the pixel map
    #Work in MM
    appendGcode("G21")
    # Start at current position
    appendGcode("G92 X0 Y0")
    #Loop over the list
    for y in arr:
        #If we have an even number for a y axis line
        if yp % 2 != 0:
            #Direction is reversed, set xp to the end
            xp = len(y)
            #Revese the values of y
            y = list(reversed(y))
            rev = True
        else:
            xp = 0
            rev = False
        appendGcode(";xp = " + str(xp))
        appendGcode("G0 X"+str(round(xp*scalex, 3))+" Y" +
            str(round(yp*scaley, 3)) + " F" + str(args.skiprate))
        laserOn(args.laserpower)
        #reset the lastxp position
        lastxp = 0
        #Group pixels by value into a new list
        for i, j in groupby(y):
            #items in the list
            items =  list(j)
            #Number of items
            size = len(items)
            #grey Value in this chunk of the line
            value = items[0]
            #Create the preview
            if args.preview:
                pvx = len(items)-1 if rev else 0
                for item in items:
                    pix = xp-pvx-1 if rev else xp+pvx
                    pixels[pix,yp] = (item, item, item)
                    pvx = pvx-1 if rev else pvx+1
            #Turn on the laser
            #step = (args.highpower-args.lowpower)/args.steps
            #laserOn(math.ceil((args.steps-value)*step))
            #Burn the segment
            goto = xp - size if rev else xp + size
            appendGcode("G1 X" + str(round((goto)*scalex,3)) +
                " F" + str(getSpeed(value)))
            #laserOff()
            #track x position
            lastxp = xp
            #Increment position
            xp = xp - size if rev else xp + size
        yp = yp + 1
        #Turn the laser off
        laserOff()
    #Go to zero
    appendGcode("G0 X0 Y0 F" + str(args.skiprate))
    #if the grbl version allows lasermode, disable it
    if args.grblver > 0.9:
        laserMode(0)
    #Show a preview if enabled
    if args.preview:
        prv.transpose(Image.ROTATE_180).transpose(Image.FLIP_LEFT_RIGHT).show()
    #Output the gcode file
    f = open(args.output+'.gcode', 'w')
    f.write("\n".join(lines))
