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
# Revision 1.10  2011/03/17 11:37:27  tino
# Better counting: Count the biggest batch seen until update is pushed
#
# Revision 1.9  2011-03-17 00:17:15  tino
# Update now only done in timer
#
# Revision 1.8  2011-03-16 19:40:47  tino
# typo fixes
#
# Revision 1.7  2011-01-21 16:20:51  tino
# ln_versioned without binsearch
#
# Revision 1.6  2011-01-21 16:17:57  tino
# intermediate version
#
# Revision 1.5  2010-11-16 07:46:37  tino
# Key codes
#
# Revision 1.4  2010-10-23 20:17:15  tino
# Commands

import easyrfb

import sys
import os
import re

import twisted
from PIL import Image,ImageChops

class rfbImg(easyrfb.client):

    count = 0		# Count the number of pixels changed so far
    fuzz = 0		# Additional dirt added by timer to flush from time to time
    force = 0		# Force update in given count of timers
    changed = 0		# Changed pixel count in batch
    delta = 0		# Max delta seen so far before update

    def __init__(self, argv, appname):
	easyrfb.client.__init__(self, appname)

	# Start the timer
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
	"""Called each 0.5 seconds when reactor is idle"""

	if self.count>0:
		self.fuzz += self.width
		if self.force==1 or self.width * self.height < self.count * 50 + self.fuzz:
			self.flush()
	if self.force:
		self.count += 1
		self.force -= 1

    # Called when the image must be written to disk
    def flush(self):
	"""
	Flush the image to disk
	The target is overwritten atomically by rename()
	"""

	self.count = 0
	self.fuzz = 0
	self.delta = 0

	self.write(self.name,self.type,self.quality)

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
		# Skip update if nothing changed
		#if ImageChops.difference(img,self.img.crop((x,y,x+width-1,y+height-1))).getbbox() is None:	return
		#print ImageChops.difference(img,self.img.crop((x,y,x+width-1,y+height-1))).getbbox()
		# If not looping this apparently updates the mouse cursor
		self.img.paste(img,(x,y))

	self.changed += width*height
	self.rect = [ x,y,width,height ]

    def beginUpdate(self, vnc):
	self.changed = 0

    def commitUpdate(self, vnc, rectangles=None):
	print "commit %d %s %s" % ( self.count, len(rectangles), self.rect )

	# Increment by the biggest batch seen so far
	if self.changed > self.delta:
		self.delta = self.changed
	self.count += self.delta

	# If one-shot then we are ready
	if not self.loop:
		self.flush()
		self.halt()

	self.check_waiting()
        vnc.framebufferUpdateRequest(incremental=1)

    def pointer(self,x,y,click=None):
	self.force = 2
	if click == None:
		click = 0
	else:
		click = 1<<(click)
	self.myVNC.pointerEvent(x, y, click)

    def key(self,k):
	self.force = 2
	self.count += self.width*self.height
	self.myVNC.keyEvent(k,1)
	self.myVNC.keyEvent(k,0)

    waiting = []
    def wait(self,cb,templates):
	self.waiting.append([cb,templates])

    def check_waiting(self):
	# It is not safe to modify waiting while looping
	# But we bail out with "return" as soon as we modify waiting[]
	for i,w in enumerate(self.waiting):
		for t in w[1]:
			print "check %s" % t
			w[0](t,-1)
			del self.waiting[i]
			return

def try_link(from_, to):
	try:
		os.link(from_, to)
		return True
	except OSError,e:
		if e.errno!=17:
			raise
		return False
	
def ln_versioned(from_, to, ext):
	if try_link(from_,to+ext):
		return
	i=0
	while True:
		i = i + 1
		if try_link(from_, to+".~"+i+"~"+ext):
			return

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
		tmp = 'learn.png'
		os.unlink(tmp)
		self.img.img.convert('RGBA').save(tmp)
		ln_versioned(tmp, 'learn/'+to, '.png');
		return True

	def cmd_key(self,*args):
		for k in " ".join(args):
			self.img.key(ord(k))
		return True

	def cmd_code(self,code):
		self.img.key(int(code))
		return True

	waiting = False
	exiting = False

	def cmd_exit(self):
		self.exiting = True
		if self.waiting:
			return True
		self.transport.loseConnection()
		return True

	def cmd_wait(self,*templates):
		if not templates:
			return False
		self.wait()
		self.img.wait(self.wait_cb,templates)
		return True

	def wait_cb(self,template,alpha):
		print "match",template,alpha
		self.transport.write("%s %s\n" % ( template, alpha ))
		self.unwait()

	def wait(self):
		self.waiting = True

	def unwait(self):
		self.waiting = False
		if self.exiting:
			self.cmd_exit()

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

