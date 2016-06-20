#!/usr/bin/env python2.7
#
# Save RFB framebuffer to a file
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# Usage:
#	python rfbimg.py [0|1|2 [filename [type [quality]]]]
# where:
#	0==oneshot (default)
#	1==loop mode (creates .sock for automation)
#	2==oneshot, try to ignore mouse
#	filename is rfbimg.jpg by default
#	type is autodetect, can be "JPEG" or "BMP" etc.
#	quality is unset, can be JPEG-quality (like 15) in percent
#
# Needs python-imaging (PIL)
# Needs json (Python 2.6, should run under Python 2.5 with json.py added)

import easyrfb
import json

import os
import io
import re

import time

import twisted
from PIL import Image,ImageChops,ImageStat

LEARNDIR='learn/'
IMGEXT='.png'
TEMPLATEDIR='e/'
TEMPLATEEXT='.tpl'

def timestamp():
	t = time.gmtime()
	return "%04d%02d%02d-%02d%02d%02d" % ( t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

cachedimages = {}
def cacheimage(path):
	try:
		if cachedimages[path][0]==os.stat(path).st_mtime:
			return cachedimages[path][1]
	except KeyError:
		pass
	cachedimages[path] = (os.stat(path).st_mtime,Image.open(path).convert('RGB'))
	return cachedimages[path][1]

class rfbImg(easyrfb.client):

    count = 0		# Count the number of pixels changed so far
    fuzz = 0		# Additional dirt added by timer to flush from time to time
    force = 0		# Force update in given count of timers
    changed = 0		# Changed pixel count in batch
    delta = 0		# Max delta seen so far before update
    dirt = 0		# Dirty counter, if too high then force flush
    sleep = 0		# Sleep counter, delay update if recently flushed
    SLEEP_TIME = 3	# 0.3 seconds
    DIRT_LEVEL = 40	# 4.0 seconds

    def __init__(self, appname, loop=None, mouse=None, name=None, type=None, quality=None):
	super(rfbImg, self).__init__(appname)

	if loop is None:	loop	=     self._preset("RFBIMGLOOP", '0') != '0'
	if mouse is None:	mouse	=     self._preset("RFBIMGMOUSE", '1') != '0'
	if name is None:	name	=     self._preset("RFBIMGNAME", 'rfbimg.jpg');
	if type is None:	type	=     self._preset("RFBIMGTYPE", None);
	if quality is None:	quality	=     self._preset("RFBIMGQUALITY", None);
	if quality is not None:	quality = int(quality)

	# Start the timer
	self._timer = twisted.internet.task.LoopingCall(self.timer);
	self._timer.start(0.1, now=False)

	# Remember the args

	self.loop = loop
	self.mouse = mouse
	self.name = name
	self.type = type
	self.quality = quality
	self.dirt = 0
	self.sleep = 0

    def timer(self):
	"""Called each 0.1 seconds when reactor is idle"""

	if self.count>0:
		self.dirt += 1
		self.sleep -= 1
		self.fuzz += self.width/10
		if self.sleep<0 and ( self.dirt>self.DIRT_LEVEL or self.force==1 or self.width * self.height < self.count * 50 + self.fuzz ):
			self.flush()
	if self.force:
		self.count += 1
		self.force -= 1

	self.autonext(False)

    # Called when the image must be written to disk
    def flush(self):
	"""
	Flush the image to disk
	The target is overwritten atomically by rename()
	"""

	self.sleep = self.SLEEP_TIME
	self.count = 0
	self.fuzz = 0
	self.delta = 0
	self.dirt = 0

	self.write(self.name, self.type, quality=self.quality)

    def write(self,name, type=None, quality=None):
	tmp = os.path.splitext(name)
	tmp = tmp[0]+".tmp"+tmp[1]
	if quality is None:
		self.img.convert('RGB').save(tmp, type, quality=quality)
	else:
		self.img.convert('RGB').save(tmp, type)
	os.rename(tmp,name)

	print "out %s" % ( name )

    def connectionMade(self, vnc):
	print "connection made"
	self.myVNC = vnc

    def vncConnectionMade(self, vnc):
	super(rfbImg, self).vncConnectionMade(vnc)

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
		#if ImageChops.difference(img,self.img.crop((x,y,x+width,y+height))).getbbox() is None:	return
		#print ImageChops.difference(img,self.img.crop((x,y,x+width,y+height))).getbbox()
		# If not looping this apparently updates the mouse cursor
		self.img.paste(img,(x,y))

	self.changed += width*height
	self.rect = [ x,y,width,height ]

    def beginUpdate(self, vnc):
	self.changed = 0

    def commitUpdate(self, vnc, rectangles=None):
#	print "commit %d %s %s" % ( self.count, len(rectangles), self.rect )

	# Increment by the biggest batch seen so far
	if self.changed > self.delta:
		self.delta = self.changed
	self.count += self.delta

	# If one-shot then we are ready
	if not self.loop:
		self.flush()
		self.halt()

	self.autonext(True)
        vnc.framebufferUpdateRequest(incremental=1)

    def pointer(self,x,y,click=None):
	self.force = 2
	if click is None:
		click = 0
	self.myVNC.pointerEvent(x, y, click)

    def key(self,k):
	self.force = 2
	self.count += self.width*self.height
	self.myVNC.keyEvent(k,1)
	self.myVNC.keyEvent(k,0)

    delaynext = False
    def autonext(self, force):
	if not force and not self.delaynext:
		self.delaynext = self.waiting or self.nexting
		return

	self.check_waiting()
	self.notify()

	self.delaynext = self.waiting or self.nexting

    nexting = []
    def next(self, cb):
	self.nexting.append(cb)

    def notify(self):
	tmp = self.nexting
	self.nexting = []
	for cb in tmp:
		cb()

    waiting = []
    def wait(self,waiter):
	self.waiting.append(waiter)

    def check_rect(self,template,r,rect,debug,trace):
	# IC.difference apparently does not work on RGBX, so we have to convert to RGB first
	bb = ImageChops.difference(r['img'], self.img.crop(rect).convert('RGB'))
	st = ImageStat.Stat(bb)
	delta = reduce(lambda x,y:x+y, st.sum2)		# /(bb.size[0]*bb.size[1])
	if delta<=r['max']:
		if trace:
			print "same",template['name'],rect,delta
		return True

	# We have a difference
	if debug:
		bb.save('_debug.png')
		print "diff",template['name'],rect,delta,bb.getbbox()
	return False

    def check_rects(self,template,dx,dy,debug,trace):
	for r in template['r']:
		rect = r['rect']
		if not self.check_rect(template,r,(rect[0]+dx,rect[1]+dy,rect[2]+dx,rect[3]+dy),debug,trace):
			return False
		debug = trace
	# All rects match, we have a match
	return True

    def check_template(self,template,debug=False):
	# Always check the center
	if self.check_rects(template,0,0,debug,debug):
		template['dx']=0
		template['dy']=0
		return True

	# Then check the displacements
	for s in template['search']:
		dx = s[0]
		dy = s[1]
		x = y = 0
		print "search",template['name'],s
		for i in range(s[2]):
			x += dx
			y += dy
			if self.check_rects(template,x,y,False,debug):
				if debug:
					print "found",template['name'],"offset",x,y
				template['dx'] = x
				template['dy'] = y
				return True
	return False

    def load_templates(self,templates):
	tpls = []
	for l in templates:
		f = l
		if f=="": continue

		# template	check if template matches
		# !template	check if template does not match
		# DO NOT USE FILENAMES STARTING WITH !
		# !!template	check if !template does not match
		# !!!template	check if !template matches
		# !!!!template	check if !!template matches (and so on)
		inv = f[0]!='!'
		if not inv:
			inv = l[2]=='!' and l[3]=='!'
			f = l[inv and 2 or 1:]

		try:
			t = json.load(io.open(TEMPLATEDIR+f+TEMPLATEEXT))
			n = t['img']
			i = cacheimage(LEARNDIR+n)
			rects = []
			search = []
			for r in t['r']:
				if r[3]==0 or r[4]==0:
					# special rectangle specifying search range
					# if a 0-width or 0-height rectangle is found
					# search along it's line.
					# If it is right/below the middle of the screen
					# search inverse (from right/bottom to left/top)
					# else normal
					if r[3]==0:
						search.append((0, r[2]*2 > i.size[1]-r[4] and -1 or 1, r[4]))
					else:
						search.append((r[1]*2 > i.size[0]-r[3] and -1 or 1, 0, r[3]))
					continue
	
				rect = (r[1],r[2],r[1]+r[3],r[2]+r[4])
				pixels = r[3]*r[4]
				spec = { 'r':r, 'name':n, 'img':i.crop(rect), 'rect':rect, 'max':r[0], 'pixels':r[3]*r[4] }
				# poor man's sort, keep the smallest rect to the top
				if rects and pixels <= rects[0]['pixels']:
					rects.insert(0,spec)
				else:
					rects.append(spec)
			tpls.append({ 'name':l, 't':t, 'i':i, 'r':rects, 'cond':inv, 'search':search })
		except Exception,e:
			print traceback.format_exc()
			return None
	return tpls

    def check_waiter(self,waiter,debug=False):
	""" check a single waiter (templates) """
	try:
		tpls = waiter['templates']
	except KeyError:
		tpls = self.load_templates(waiter['t'])
		print "templates loaded",waiter['t']
		waiter['templates'] = tpls

	if not tpls:
		waiter['match'] = None
		return True

	for t in tpls:
		# Check all the templates
		if self.check_template(t,debug)==t['cond']:
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
			w['match'] = None
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

	bye = False

	def lineReceived(self, line):
		self.img = self.factory.img
		args = line.split(" ")
		ok = False
		try:
			print "cmd",args[0],args
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

	def cmd_mouse(self, x, y, click=None):
		x = int(x)
		y = int(y)
		if click is None:
			click = int(click)
		self.img.pointer(x,y,click)
		return True

	def cmd_learn(self,to):
		if not self.valid_filename.match(to):
			return False
		if to=='':
			to = 'screen-'+timestamp()
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

	def cmd_code(self,*args):
		for k in args:
			self.img.key(int(k,0))
		return True

	def cmd_exit(self):
		self.bye = True
		return True

	def cmd_next(self):
		self.pause()
		self.img.next(self.resume)
		return True

	def cmd_flush(self):
		self.img.flush()
		return True

	def cmd_check(self,*templates):
		w = {'t':templates}
		return len(templates) and self.img.check_waiter(w, True) and self.print_wait(w)

	def cmd_wait(self,*templates):
		if len(templates)<2:
			return False
		timeout = int(templates[0])
		self.pause()
		self.img.wait({'cb':self.wait_cb,'t':templates[1:],'retries':timeout})
		return True

	def print_wait(self,waiter):
		if waiter['match']:
			w = waiter['match']
			print "match",w
			if w['cond']:
				self.transport.write("found %s %s %s\n" % (w['name'], w['dx'], w['dy']))
			else:
				self.transport.write("spare %s\n" % (w['name']))
			return True
		else:
			print "timeout"
			self.transport.write("timeout\n")
			return False

	def wait_cb(self,waiter):
		self.print_wait(waiter)
		self.resume()

	def resume(self):
		try:
			self.transport.resumeProducing()
		except:
			# may have gone away in the meantime
			print "gone away"

	def pause(self):
		self.transport.pauseProducing()

	def ping(self):
		self.sendLine("PONG");

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
	img = rfbImg("RFB image writer")
	if img.loop:
		createControl(".sock", img)
	img.run()

