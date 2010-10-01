#!/usr/bin/env python
#
# $Header$
#
# Save RFB framebuffer to a file
#
# Usage:
#	python rfbimg.py [0|1 [filename [type [quality]]]]
# where:
#	0==oneshot (default)
#	1==loop mode
#	filename is rfbimg.jpg by default
#	type is autodetect, can be "JPEG" or "BMP" etc.
#	quality is unset, can be JPEG-quality (like 15) in percent
#
# Needs python-imaging (PIL)
#
# $Log$
# Revision 1.1  2010/10/01 15:13:19  tino
# added
#

import easyrfb

import sys
import os

import twisted
from PIL import Image

class rfbImg(easyrfb.client):

    count = 0
    dirt = False
    again = False

    next = False
    def timer(self):
	if self.dirt:
		self.flush()

	if self.again:
		self.next = self.again
		self.again = None

	if self.next:
        	self.next.framebufferUpdateRequest(incremental=1)
		self.next = None

    def __init__(self, argv):
	easyrfb.client.__init__(self)
	self._timer = twisted.internet.task.LoopingCall(self.timer);
	self._timer.start(1.5, now=False)
	self.name = "rfbimg.jpg"
	self.type = None
	self.quality = None
	self.loop = False
	if len(argv)>1:
		self.loop = int(argv[1])!=0
	if len(argv)>2:
		self.name = argv[2]
	if len(argv)>3:
		self.type = argv[3]
	if len(argv)>4:
		self.quality = int(argv[4])

    def flush(self):
	if self.loop and self.count < self.width * self.height / 10:
		self.count += self.width
		self.dirt = True
		return

	self.dirt = False
	self.count = 0

	tmp = os.path.splitext(self.name)
	tmp = tmp[0]+".tmp"+tmp[1]
	if self.quality!=None:
		self.img.convert("RGB").save(tmp, self.type, quality=self.quality)
	elif self.type!=None:
		self.img.convert("RGB").save(tmp, self.type)
	else:
		self.img.convert("RGB").save(tmp)
	os.rename(tmp,self.name)

	print "out %s" % ( self.name )

	if not self.loop:
		self.halt()

    def connectionMade(self, vnc):
	print "connection made"

    def vncConnectionMade(self, vnc):
	easyrfb.client.vncConnectionMade(self, vnc)

	self.width = vnc.width
	self.height = vnc.height

	self.img = Image.new('RGBX',(self.width,self.height),None)

    def updateRectangle(self, vnc, x, y, width, height, data):
	print "%s %s %s %s" % (x, y, width, height)
	img = Image.frombuffer("RGBX",(width,height),data,"raw","RGBX",0,1)
	if x==0 and y==0 and width==self.width and height==self.height:
		self.img = img
	else:
		self.img.paste(img,(x,y))
	self.count += width*height

    def beginUpdate(self, vnc):
	self.again = None

    def commitUpdate(self, vnc, rectangles=None):
	self.again = vnc
	print "commit %d %s" % ( self.count, repr(rectangles) )
	self.flush()

if __name__=='__main__':
	# Usage: python rfbimg.py 
	rfbImg(sys.argv).run()

