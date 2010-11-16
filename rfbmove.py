#!/usr/bin/env python
#
# $Header$
#
# Move mouse on RFB
#
# Usage:
#	python rfbimg.py x y 0|1|2|3
# where:
#	x is horizontal
#	y is vertical
#	0 to 3 is the mouse button to click
#
# $Log$
# Revision 1.1  2010/11/16 07:56:52  tino
# Added example of simple mouse move
#

import easyrfb

import sys
import os

class rfbMove(easyrfb.client):

    def __init__(self, argv):
	easyrfb.client.__init__(self)
	self.x = int(argv[1])
	self.y = int(argv[2])
	self.click = 0
	if len(argv)>3:
		self.click = int(argv[3])

    def connectionMade(self, vnc):
	print "connection made"

    def vncConnectionMade(self, vnc):
	if self.click>0:
		vnc.pointerEvent(self.x,self.y,1<<(self.click-1))
	else:
		vnc.pointerEvent(self.x, self.y)
	vnc.framebufferUpdateRequest()

    def beginUpdate(self, vnc):
	self.halt()

if __name__=='__main__':
	rfbMove(sys.argv).run()

