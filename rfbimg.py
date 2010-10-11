#!/usr/bin/env python
#
# $Header$
#
# Save RFB framebuffer to a file
#
# Usage:
#	python rfbimg.py [0|1|2 [filename [type [quality]]]]
# where:
#	0==oneshot (default)
#	1==loop mode
#	2==oneshot, try to ignore mouse
#	filename is rfbimg.jpg by default
#	type is autodetect, can be "JPEG" or "BMP" etc.
#	quality is unset, can be JPEG-quality (like 15) in percent
#
# Needs python-imaging (PIL)
#
# $Log$
# Revision 1.2  2010/10/11 20:51:44  tino
# Current
#
# Revision 1.1  2010-10-01 15:13:19  tino
# added

import easyrfb

import sys
import os

import twisted
from PIL import Image

class rfbImg(easyrfb.client):

    count = 0		# Count the number of pixels changed so far
    dirt = False	# Need to call self.flush()
    again = None	# vnc object store for framebufferUpdateRequest

    def __init__(self, argv, appname):
	easyrfb.client.__init__(self, appname)

	# Start the timer
	self.tick = True
	self._timer = twisted.internet.task.LoopingCall(self.timer);
	self._timer.start(1.5, now=False)

	# Remember the args

	self.loop = False
	self.mouse = True
	self.name = "rfbimg.jpg"
	self.type = None
	self.quality = None

	if len(argv)>1:
		self.loop = int(argv[1])==1
		self.mouse = int(argv[1])<2
	if len(argv)>2:
		self.name = argv[2]
	if len(argv)>3:
		self.type = argv[3]
	if len(argv)>4:
		self.quality = int(argv[4])

    next = None		# one tick delay store for self.again
    def timer(self):
	self.tick = True

	"""Called each 1.5 seconds when reactor is idle"""
	if self.dirt:
		self.flush()

	if self.next:
        	self.next.framebufferUpdateRequest(incremental=1)
		self.next = None

	if self.again:
		self.next = self.again
		self.again = None

    # Called when the image must be written to disk
    def flush(self):
	# Some arbitrary delay.
	# If output hasn't changed a lot
	# (less than 6% of the screen has changed)
	# then leave it for the timer to delay the update.
	if self.loop and ( ( not self.tick ) or ( self.width * self.height > self.count * 50 )):
		# Consider a screen line of progress even when idle
		self.count += self.width
		self.dirt = True
		return

	# Flush the image to disk
	# The target is overwritten atomically by rename()

	self.dirt = False
	self.count = 0
	self.tick = 0

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

	# If one-shot then we are ready
	if not self.loop:
		self.halt()

    def connectionMade(self, vnc):
	print "connection made"
	self.myVNC = vnc

    def vncConnectionMade(self, vnc):
	easyrfb.client.vncConnectionMade(self, vnc)

	self.width = vnc.width
	self.height = vnc.height

	self.img = Image.new('RGBX',(self.width,self.height),None)

    def updateRectangle(self, vnc, x, y, width, height, data):
	print "%s %s %s %s" % (x, y, width, height)
	img = Image.frombuffer("RGBX",(width,height),data,"raw","RGBX",0,1)
	if x==0 and y==0 and width==self.width and height==self.height:
		# Optimization on complete screen refresh
		self.img = img
	elif self.mouse:
		# If not looping this apparently updates the mouse cursor
		self.img.paste(img,(x,y))
	self.count += width*height

    def beginUpdate(self, vnc):
	self.again = None

    def commitUpdate(self, vnc, rectangles=None):
	self.again = vnc
	print "commit %d %s" % ( self.count, repr(rectangles) )
	self.flush()

    def getVNC(self):
	self.count += self.width * self.height / 100
	return self.myVNC

from twisted.protocols.basic import LineReceiver
class controlProtocol(LineReceiver):

	delimiter='\n'

	def lineReceived(self, line):
		args = line.split(" ")
		if args[0]=='mouse' and len(args)>2:
			x = int(args[1])
			y = int(args[2])
			click = 0
			if len(args)>3: click=1<<int(args[3])
			self.factory.img.getVNC().pointerEvent(x,y,click)
			print "mouse",x,y,click
		else:
			print "UNKNOWN:",line

from twisted.internet import reactor
class createControl(twisted.internet.protocol.Factory):
	protocol = controlProtocol

	def __init__(self, sockname, img):
		self.img = img
		try:
			os.unlink(sockname)
		except:
			pass
		reactor.listenUNIX(sockname,self)

if __name__=='__main__':
	img = rfbImg(sys.argv,"RFB image writer")
	createControl(".sock", img)
	img.run()

