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
# Revision 1.5  2010/11/16 07:46:37  tino
# Key codes
#
# Revision 1.4  2010-10-23 20:17:15  tino
# Commands
#
# Revision 1.3  2010-10-12 08:22:13  tino
# better
#
# Revision 1.2  2010-10-11 20:51:44  tino
# Current
#
# Revision 1.1  2010-10-01 15:13:19  tino
# added

import easyrfb

import sys
import os
import re

import twisted
from PIL import Image

class rfbImg(easyrfb.client):

    count = 0		# Count the number of pixels changed so far
    tick = False

    def __init__(self, argv, appname):
	easyrfb.client.__init__(self, appname)

	# Start the timer
        self.tick = True
	self._timer = twisted.internet.task.LoopingCall(self.timer);
	self._timer.start(0.5, now=False)

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

    def timer(self):
	"""Called each 1.5 seconds when reactor is idle"""

	self.tick = True

	if self.dirt:
		self.count += self.width
		self.flush()

    # Called when the image must be written to disk
    def flush(self):
	if self.loop and (not self.tick or self.width * self.height > self.count * 50):
		self.dirt = True
		return

	# Flush the image to disk
	# The target is overwritten atomically by rename()

	self.tick = False
	self.dirt = False
	self.count = 0

	self.write(self.name,self.type,self.quality)

	# If one-shot then we are ready
	if not self.loop:
		self.halt()

    def write(self,name,type=None,quality=None):
	tmp = os.path.splitext(name)
	tmp = tmp[0]+".tmp"+tmp[1]
	if quality!=None:
		self.img.convert("RGB").save(tmp, type, quality=quality)
	elif type!=None:
		self.img.convert("RGB").save(tmp, type)
	else:
		self.img.convert("RGB").save(tmp)
	os.rename(tmp,name)

	print "out %s" % ( name )

    def connectionMade(self, vnc):
	print "connection made"
	self.myVNC = vnc

    def vncConnectionMade(self, vnc):
	easyrfb.client.vncConnectionMade(self, vnc)

	self.width = vnc.width
	self.height = vnc.height

	self.img = Image.new('RGBX',(self.width,self.height),None)

    def updateRectangle(self, vnc, x, y, width, height, data):
	#print "%s %s %s %s" % (x, y, width, height)
	img = Image.frombuffer("RGBX",(width,height),data,"raw","RGBX",0,1)
	if x==0 and y==0 and width==self.width and height==self.height:
		# Optimization on complete screen refresh
		self.img = img
	elif self.mouse:
		# If not looping this apparently updates the mouse cursor
		self.img.paste(img,(x,y))
	self.count += width*height

    def beginUpdate(self, vnc):
	self.dirt = False

    def commitUpdate(self, vnc, rectangles=None):
	print "commit %d %s" % ( self.count, len(rectangles) )
	self.flush()
        vnc.framebufferUpdateRequest(incremental=1)

    def pointer(self,x,y,click=None):
	self.tick = True
	if click == None:
		click = 0
	else:
		click = 1<<(click)
	self.myVNC.pointerEvent(x, y, click)

    def key(self,k):
	self.tick = True
	self.count += self.width*self.height
	self.myVNC.keyEvent(k,1)
	self.myVNC.keyEvent(k,0)

from twisted.protocols.basic import LineReceiver
import traceback
class controlProtocol(LineReceiver):

	delimiter='\n'

	valid_filename = re.compile('^[-_a-zA-Z0-9]*$')

	def lineReceived(self, line):
		self.img = self.factory.img
		args = line.split(" ")
		ok = False
		try:
			ok = getattr(self,'cmd_'+args[0])(*args[1:])
		except Exception,e:
			print traceback.format_exc()
		if ok:
			self.transport.write("ok\n")
			print "ok",line
		else:
			self.transport.write("ko\n")
			print "ko",line

	def cmd_mouse(self,x,y,click=None):
		x = int(x)
		y = int(y)
		if click!=None:
			click = int(click)
		self.img.pointer(x,y,click)
		return True

	def cmd_learn(self,to):
		if not self.valid_filename.match(to):
			return False
		self.img.img.convert('RGBA').save('learn/'+to+'.png')
		return True

	def cmd_key(self,*args):
		for k in " ".join(args):
			self.img.key(ord(k))
		return True

	def cmd_code(self,code):
		self.img.key(int(code))
		return True

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
	if img.loop:
		createControl(".sock", img)
	img.run()

