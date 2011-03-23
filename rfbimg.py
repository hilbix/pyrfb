#!/usr/bin/env python2.6
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
# Needs json (Python 2.6, should run under Python 2.5 with json.py added)
#
# $Log$
# Revision 1.11  2011/03/23 09:57:31  tino
# Tempates work now, but not so satisfyingly that I think I am ready
#
# Revision 1.10  2011-03-17 11:37:27  tino
# Better counting: Count the biggest batch seen until update is pushed
#
# Revision 1.9  2011-03-17 00:17:15  tino
# Update now only done in timer
#
# Revision 1.5  2010-11-16 07:46:37  tino
# Key codes
#
# Revision 1.4  2010-10-23 20:17:15  tino
# Commands

import easyrfb
import json

import sys
import os
import io
import re

import twisted
from PIL import Image,ImageChops

LEARNDIR='learn/'
IMGEXT='.png'
TEMPLATEDIR='e/'
TEMPLATEEXT='.tpl'

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
		self.img.convert('RGB').save(tmp, type, quality=quality)
	elif type!=None:
		self.img.convert('RGB').save(tmp, type)
	else:
		self.img.convert('RGB').save(tmp)
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
	img = Image.frombuffer('RGBX',(width,height),data,'raw','RGBX',0,1)
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
	self.myVNC.pointerEvent(x, y, click)

    def key(self,k):
	self.force = 2
	self.count += self.width*self.height
	self.myVNC.keyEvent(k,1)
	self.myVNC.keyEvent(k,0)

    waiting = []
    def wait(self,waiter):
	self.waiting.append(waiter)

    def check_template(self,template):
	for r in template['r']:
		# IC.difference apparently does not work on RGBX, so we have to convert to RGB first
		bb = ImageChops.difference(r['img'], self.img.crop(r['rect']).convert('RGB')).getbbox()
		if not (bb is None):
			# We have a difference
#			print "diff",template['name'],r['name'],bb
#			r['img'].save('_want.png')
#			self.img.crop(r['rect']).convert('RGB').save('_is.png')
			return False
	# All rects match, we have a match
#	print "match",template['name']
	return True

    def load_templates(self,templates):
	tpls = []
	for l in templates:
		f = l
		inv = f[0]!='!'
		if not inv:
			inv = l[1]=='!'
			f = l[inv and 2 or 1:]

		t = json.load(io.open(TEMPLATEDIR+f+TEMPLATEEXT))
		n = t['img']
		i = Image.open(LEARNDIR+n).convert('RGB')
		rects = []
		for r in t['r']:
			rect = (r[1],r[2],r[1]+r[3]-1,r[2]+r[4]-1)
			rects.append({ 'r':r, 'name':n, 'img':i.crop(rect), 'rect':rect })
		tpls.append({ 'name':l, 't':t, 'i':i, 'r':rects, 'cond':inv })
	return tpls

    def check_waiter(self,waiter):
	""" check a single waiter (templates) """
	try:
		tpls = waiter['templates']
	except KeyError:
		tpls = self.load_templates(waiter['t'])
		waiter['templates'] = tpls

	for t in tpls:
		# Check all the templates
		if self.check_template(t)==t['cond']:
			waiter['match'] = t
			return True
	return False

    def check_waiting(self):
	for i,w in enumerate(self.waiting):
		if self.check_waiter(w):
			# We found something
			# Remove from list and notify the waiting task
			del self.waiting[i]
			w['cb'](w)
			# We must return here, else i gets out of sync
			return
		w['retries'] -= 1
		if w['retries']<0:
			del self.waiting[i]
			w['match']=None
			w['cb'](w)
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
		if try_link(from_, to+".~"+str(i)+"~"+ext):
			return

def rename_away(to,ext):
	i=0
	while True:
		i = i + 1
		n = to+".~"+str(i)+"~"+ext
		if not os.path.exists(n):
			os.rename(to+ext, n)
			return

from twisted.protocols.basic import LineReceiver
import traceback
class controlProtocol(LineReceiver):

	delimiter='\n'

	valid_filename = re.compile('^[-_a-zA-Z0-9]*$')

	waiting = False
	exiting = False
	bye = False

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

		if self.bye:
			self.transport.loseConnection()

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
		try:
			os.unlink(tmp)
		except Exception,e:
			pass
		self.img.img.convert('RGBA').save(tmp)
		out = LEARNDIR+to
		if os.path.exists(out+IMGEXT):
			rename_away(out, IMGEXT)
		os.rename(tmp, out+IMGEXT)
		return True

	def cmd_key(self,*args):
		for k in " ".join(args):
			self.img.key(ord(k))
		return True

	def cmd_code(self,code):
		self.img.key(int(code))
		return True

	def cmd_exit(self):
		self.exiting = True
		self.bye = not self.waiting
		return True

	def cmd_check(self,*templates):
		return len(templates) and self.img.check_waiter({'t':templates})

	def cmd_wait(self,*templates):
		if len(templates)<2 or self.waiting:
			return False
		timeout = int(templates[0])
		self.waiting = True
#		self.transport.pauseProducing()
		self.img.wait({'cb':self.wait_cb,'t':templates[1:],'retries':timeout})
		return True

	def wait_cb(self,waiter):
		if waiter['match']:
			print "match",waiter['match']
			self.transport.write("found %s\n" % ( waiter['match']['name'] ))
		else:
			print "timeout",waiter['match']
			self.transport.write("timeout\n")
#		self.transport.resumeProducing()
		self.waiting = False
		if self.exiting:
			self.transport.loseConnection()

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

