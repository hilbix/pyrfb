#!/usr/bin/env python2
# coding=utf-8
#
# Save RFB framebuffer to a file
# or run in a loop and also send commands to VNC through socket
#
# Needs python-imaging (PIL)
# Needs json
# Tested for python 2.7
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# Usage:
#	SETTING=VALUE SETTING=VALUE python rfbimg.py
# where:
#	RFBIMGLOOP=0	oneshot (default)
#	RFBIMGLOOP=1	loop mode, creates RFBIMGSOCK for automation
#	RFBIMGSOCK=	name of the control socket for RFBIMGLOOP=1, default: .sock
#	RFBIMGMOUSE=0	try not to include mouse in oneshot
#	RFBIMGMOUSE=1	include mouse in oneshot
#	RFBIMGNAME=rfbimg.jpg	name of the file written
#	RFBIMGTYPE=	JPEG, BMP, etc.  Default (empty): autodetect
#	RFBIMGQUALITY=	image quality in percent.  Default (empty): default quality
#	RFBIMGVIZ=0	do not vizualize changes (default)
#	RFBIMGVIZ=1	vizualize changes
#	EASYRFBHOST=	VNC IP to connect to, default 127.0.0.1
#	EASYRFBPORT=	VNC port to connect to, default 5900
#	EASYRFBSHARED=0	do not use shared session
#	EASYRFBSHARED=1	use shared session (default)
#	EASYRFBPASS=	VNC password, default: no password (Untested with passwords)

MAXSTACK	= 10000
MAXMACROS	= 100000

import easyrfb
import json

import os
import io
import re

import sys
import time
import errno
import random
import inspect
import functools
import traceback

import PIL.Image
import PIL.ImageDraw
import PIL.ImageStat
import PIL.ImageChops

# WTF?!? What a bunch of hyper ugly code!  Just for some dead old POSIX locks ..
# See https://stackoverflow.com/a/46407326/490291
# Wrap this in a class as we do not want to pollute the global namespace even more
try:
	import	fcntl
	class LOCK:
		@classmethod
		def lock_file(klass, io, exclusive=True):
			fcntl.lockf(io, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
		@classmethod
		def unlock_file(klass, io):
			fcntl.lockf(io, fcntl.LOCK_UN)
except ImportError:
	import msvcrt
	# Well, no, this probably isn't Windows compatible at all
	class LOCK:
		@classmethod
		def filesize(klass, io):
			pos	= io.tell()
			io.seek(0, os.SEEK_END)
			ret	= io.tell()
			io.seek(pos, os.SEEK_SET)
			return ret
		@classmethod
		def lock_file(klass, io, exclusive=Treu):
			msvcrt.locking(io.fileno(), msvcrt.LK_LOCK if exclusive else msvcrt.LK_RLOCK, klass.filesize(f))
		@classmethod
		def unlock_file(klass, n):
			msvcrt.locking(io.fileno(), msvcrt.LK_UNLCK, klass.filesize(f))

# WTF why does io.open() does not allow locking semantics?
# That's a crucial feature!
# with Open() as file: ..
nropen	= 0
class Open:
	# https://stackoverflow.com/a/40635301/490291 WTF!?!
	def __init__(self, name, write=False, append=False, binary=False, lock=False, utf8=False):
		global	nropen

		if append:
			omode	= os.O_CREAT|os.O_RDWR|os.O_APPEND
			mode	= 'a+'	# this is always read/write while write==append
			write	= True
		elif write:
			omode	= os.O_CREAT|os.O_RDWR
			mode	= 'r+'	# this is always read/write
		else:
			omode	= os.O_RDONLY
			mode	= 'r'
		if binary:
			mode	+= 'b'
		else:
			mode	+= 't'
			if utf8:
				kw['encoding']	= kw.get('encoding', 'utf-8')

		self.file	= os.fdopen(os.open(name, omode), mode)
		nropen	+= 1
		if lock:
			LOCK.lock_file(self.file, write)
		self.lock	= lock

	def __enter__(self):
		return self.file

	def __exit__(self, exc_type=None, exc_value=None, traceback=None):
		global	nropen
		if self.lock:
			LOCK.unlock_file(self.file)
		self.file.close()
		nropen	-= 1
		return exc_type is None

LEARNDIR='l/'
STATEDIR='s/'
IMGEXT='.png'
TEMPLATEDIR='e/'
TEMPLATEEXT='.tpl'
MACRODIR='o/'
MACROEXT='.macro'
GLOBALSFILE='globals.json'

# Because of https://bugs.python.org/issue13769#msg229882 json.dump() is completely useless.
# Because of missing parse_string, json.load() is completely useless.
# Hence we have to re-invent the wheel, again and again and again and again,
# and instead of using some sane, quick, easy, memory efficient way,
# we have to do it error-prone, slow, complex, memory inefficient way.
# WTF, why was that done so badly?
#
# And why was the old bullshit taken over into Python3 instead of replacing it by something more sane?
# (I would expect an easy to wrap python class for decoding.)
#
# Das kommt mir doch alles sehr lateinisch vor ..
# encoding='latin1' -> der Default steht total sinnfrei auf UTF-8, wodurch str-Typen nicht encodiert werden können!
def ioJSONu(io, **kw):	return io.write(unicode(toJSON(o, **kw)))
def ioJSON(io, **kw):	return io.write(toJSON(o, **kw))
def toJSON(o, **kw):	return json.dumps(o, encoding='latin1', **kw)
def toJSONu(o, **kw):	return unicode(toJSON(o, **kw))				# USE THIS! JSON must return unicode
def toU(s):		return unicode(s, endcoding='latin')			# USE THIS! str -> unicode
def fromU(u):		return u.encode('latin')				# USE THIS! unicode -> str
def fromJSON(j):	return json.loads(j, 'latin1')
def fromJSONio(io):	return json.load(io, 'latin1')
def fixJSON(j):		return fixed(fromJSON(j))				# USE THIS!
def fixJSONio(io):	return fixed(fromJSONio(io))				# USE THIS!

# Because json.load() is missing parse_string, and json.loads(), too,
# we have to fix it by re-inventing the wheel to be able to call
# fix_uni() for all and everything:
def fixed_dict(d):	return { fixed(k):fixed(v) for k,v in d.iteritems() }
def fixed_list(l):	return [fixed(a) for a in l]
def fixed_uni(u):
	"""
	return (str) if possible, (unicode) else
	"""
	try:
		return fromU(u);
	except:
		return u
def fixed(o):
	if isinstance(o, dict):		return fixed_dict(o);
	if isinstance(o, list):		return fixed_list(o);
	if isinstance(o, unicode):	return fixed_uni(o);
	return o

# Dots are disallowed for a good reason
valid_filename = re.compile('^[,_a-zA-Z0-9][-,_a-zA-Z0-9]*$')

log	= None

# WTF, why isn't there a standard function for this?
def updateDict(o, *args, **kw):
	o.update(*args, **kw)
	return o

def timestamp():
	t = time.gmtime()
	return "%04d%02d%02d-%02d%02d%02d" % ( t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

cachedimages = {}
def cacheimage(path, mode='RGB'):
	"""
	cache an image, re-reads if file modification time has changed.

	Note that this possibly converts the cached image to the given mode.
	Be sure to cache only compatible modes!
	"""
	mtime	= os.stat(path).st_mtime
	try:
		if cachedimages[path][0]==mtime:
			return cachedimages[path][1] if cachedimages[path][2]==mode else cachedimages[path][1].convert(mode)
	except KeyError:
		pass
	cachedimages[path] = (mtime,PIL.Image.open(path).convert(mode),mode)
	return cachedimages[path][1]

def Image(path, mode):
	return PIL.Image.open(path).convert(mode)

__CACHE	= {}
def cached(factory, path, *args, **kw):
	"""
	cache a file, re-read if file modification time has changed.
	The first argument is the factory, the 2nd is the path, additional parameters might follow.
	factory is the function/class to create path, it gets passed all following args.
	arg/kw are used for caching, too, so they need to be JSON serializable.
	"""
	mtime	= os.stat(path).st_mtime
	a	= json.dumps((args, kw), sort_keys=True, encoding='latin1') if args or kw else ''
	c	= __CACHE.get(path)
	if c:
		if c[0]==mtime:
			r	= c[1].get(a)
			if r:
				return r
		else:
			c	= None
	if c is None:
		c		= [mtime, {}]
		__CACHE[path]	= c
	r	= factory(path, *args, **kw)
	c[1][a]	= r
	return r

def cachedImage(path, mode='RGB'):
	return cached(Image, path, mode)

def cachedTemplate(name):
	if not valid_filename.match(name):
		raise RuntimeError('invalid filename: '+repr(name))
	return cached(Template, TEMPLATEDIR+name+TEMPLATEEXT, name)

def rand(x):
	"return a random integer from 0 to x-1"
	return random.randrange(x) if x>0 else 0

def D(*args, **kw):
	print(" ".join(tuple(str(v) for v in args)+tuple(str(n)+"="+repr(v) for n,v in sorted(kw.iteritems()))))

def myrepr(v):
	if inspect.isgenerator(v):
		return 'gen('+v.__name__+')'
	return repr(v)

def ordered_repr(d):
	return ' '.join(str(x)+'='+myrepr(d[x]) for x in sorted(dict(**d).keys()))

class Template:
	"""
	Searches are regions which are 0 width or 0 height.  Just a dot resets search.
	- The left top corner of the next region is moved along the given axis
	- The following regions then are checked relative to the found displacement
	If 'delta' is negated, search is done opposite direction.
	"""
	def __init__(self, path, name):
		"""
		Load a single template and extract the searches
		"""
		self.path	= path
		self.name	= name
		with Open(path) as f:
			self.tpl	= json.load(f)
		self.parsed	= False
		self.n		= None
		self.i		= None
		self.p		= None
		self.r		= None
		self.lf		= None

	def getName(self):
		return self.name

	def getTpl(self):
		return self.tpl

	def getRect(self, n):
		if not self.parsed:	self.parse()
#		D(n, r=self.r, find=self.lf)
		if n not in self.r:
			return None
		r	= self.r[n]
		p	= r['p']
		part	= self.p[p]
		off	= self.lf[p] if part['c']>1 else 0
		dx	= part['x'] * off
		dy	= part['y'] * off
		x	= r['x'] + dx
		y	= r['y'] + dy
		w	= r['w'] - x
		h	= r['h'] - y
		d	= r['d']
#		D(d=d, x=x, y=y, w=w, h=h)
		return (d, x, y, w, h)

	def parse(self):
		if self.parsed:
			return self

		t	= self.tpl
		self.n	= t['img']
		self.i	= cacheimage(LEARNDIR+self.n)
		self.p	= []
		self.r	= {}		# WTF?  No sparse lists?

		sf	= False
		sx	= 0
		sy	= 0
		dx	= 0
		dy	= 0
		cnt	= 0
		part	= []

		def put():
			if part: self.p.append(dict(n=len(self.p), x=dx, y=dy, c=cnt+1, p=part))

		for n,r in enumerate(t['r'], start=1):
			if r[3]==0 or r[4]==0:
				put()
				part	= []
				sf	= True
				sx	= r[1]
				sy	= r[2]
				d	= -1 if r[0]<0 else 1
				if r[3]!=0:
					cnt	= r[3]
					dx	= d
					dy	= 0
					if d<0: x += cnt	# cnt == 1 means look for 2 positions
				elif r[4]!=0:
					cnt	= r[4]
					dx	= 0
					dy	= d
					if d<0: y += cnt	# cnt == 1 means look for 2 positions
				else:
					sx	= 0
					sy	= 0
					cnt	= 0
					sf	= False
				continue

			if sf:
				sf	= False
				sx	-= r[1]
				sy	-= r[2]
			i	= self.i.crop((r[1],r[2],r[1]+r[3],r[2]+r[4])).convert('RGB')
			# cnt == 1 means look for 2 positions
			v	= dict(n=n, p=len(self.p), x=r[1]+sx, y=r[2]+sy, w=r[1]+r[3]+sx, h=r[2]+r[4]+sy, i=i, d=r[0], px=r[3]*r[4])
			self.r[n]	= v
			part.append(v)
		put()

		self.parsed	= True
		return self

	def match(self, img, debug=False):
		"""
		check if img matches this template

		returns list of found offsets, or None if mismatch

		debug is a debugging function which receives keyword arguments
		"""
		if not self.parsed:	self.parse()

		finds	= []
		for p in self.p:
			offset	= self.part(p, img, debug)
			if offset is None:
				if debug: debug(Template=self.name, _part=p['n'], found=None)
				return None
			finds.append(offset)
			if debug: debug(Template=self.name, _part=p['n'], offset=offset)
		if debug: debug(Template=self, found=finds)
		self.lf	= finds
		return finds

	def part(self, p, img, debug=False):
		"""
		check for a matching part (internal routine)

		returns found offset (integer) or None if none
		"""
		# p is { 'x':dx, 'y':dy, 'c':cnt+1, 'p':part }
		dx	= p['x']
		dy	= p['y']
		x	= 0
		y	= 0
		if debug: debug(Template=self.name, _part=p['n'], r=p['p'][0], c=p['c'])
		for i in range(p['c']):
			r	= p['p']
			# r is [{ 'x':x, 'y', 'w', 'h', 'i':img, 'm':abs(r[0]), 'px':r[3]*r[4] }]
			if self.check(r[0], x, y, img, False):
				# We got a match, check the remaining rects
				if debug: debug(Template=self.name, _part=p['n'], x=x, y=y)
				for r in r[1:]:
					if not self.check(r, x, y, img, debug):
#						if debug: debug(Template=self.name, _part=p['n'], mismatch=r)
						# Fail early in case they do not match
						return None
				# Success!  Return the offset/searches done
				return i
			x += dx
			y += dy
		# Fail, as we did not find anything
		return None

	def check(self, r, dx, dy, img, debug):
		"""
		check for a rectanlge to match (internal routine)

		returns True if match, false otherwise
		"""
		# r is { 'x':x, 'y', 'w', 'h', 'i':img, 'm':abs(r[0]), 'px':r[3]*r[4] }
		# IC.difference apparently does not work on RGBX, so we have to convert to RGB first
		rect	= (r['x']+dx, r['y']+dy, r['w']+dx, r['h']+dy)
		di	= PIL.ImageChops.difference(r['i'], img.crop(rect).convert('RGB'))
		bb	= di.getbbox()
		if bb is None:
			if debug: debug(Template=self.name, check=True, rect=rect)
			return True
		if not r['d'] and not debug:
			return False

		st	= PIL.ImageStat.Stat(di.crop(bb))
		delta	= reduce(lambda x,y:x+y, st.sum2)
		if delta <= abs(r['d']):
			if debug: debug(Template=self.name, check=True, rect=rect, delta=delta)
			return True
		if debug: debug(Template=self.name, check=False, rect=rect, delta=delta)
		return False

	def __str__(self):
		return '<template {} parsed={} img={}>'.format(self.name, self.parsed, self.n)

	def __repr__(self):
		return '<template {} {}>'.format(self.name, self.tpl)

class rfbImg(easyrfb.client):

	valid_filename	= valid_filename

	TICKS	= 0.1	# timer resolution in seconds
	SLEEP_TIME	= 3	# in TICKS = 0.3s
	DIRT_LEVEL	= 40	# in TICKS = 4.0s
	tick	= 0	# monotone tick counter (TICKS resolution)

	count	= 0	# Count the number of pixels changed so far
	fuzz	= 0	# Additional dirt added by timer to flush from time to time
	forcing	= 0	# Force update in given count of timers
	changed	= 0	# Changed pixel count in batch
	delta	= 0	# Max delta seen so far before update
	dirt	= 0	# Dirty counter, if too high then force flush
	dirty	= False	# dirty flag (when count!=0 or forcing)
	sleep	= 0	# Sleep counter, delay update if recently flushed
	skips	= 0	# Number of skipped (==unchanged) frames received in this update

	def __init__(self, appname, loop=None, mouse=None, name=None, type=None, quality=None, viz=None, **kw):
		super(rfbImg, self).__init__(appname, **kw)
		self.logging()

		if loop is None:	loop	= self._preset("RFBIMGLOOP",    '0') != '0'
		if mouse is None:	mouse	= self._preset("RFBIMGMOUSE",   '1') != '0'
		if name is None:	name	= self._preset("RFBIMGNAME",    'rfbimg.jpg');
		if type is None:	type	= self._preset("RFBIMGTYPE",    None);
		if quality is None:	quality	= self._preset("RFBIMGQUALITY", None);
		if viz is None:		viz	= self._preset("RFBIMGVIZ",     '0') != '0';

		if quality is not None:	quality = int(quality)

		self.log("init", loop=loop, mouse=mouse, name=name, type=type, qual=quality)

		# Start the timer
		self._timer = twisted.internet.task.LoopingCall(self.timer)		#TWISTED
		self._timer.start(self.TICKS, now=False)				#TWISTED

		# Remember the args
		self.loop	= loop
		self.mouse	= mouse
		self.name	= name
		self.type	= type
		self.quality	= quality

		self.viz	= None
		self.vizualize	= viz

		# we haven't seen the mouse and do not know where it is
		self.lm_c	= 0
		self.lm_x	= 0
		self.lm_y	= 0

	# This is really black magic, sorry
	def timer(self):
		"""Called each 0.1 seconds when idle"""

		self.tick	+= 1

		# has something changed?
		if self.dirty:
			self.dirt	+= 1		# TICKS how long we are dirty
			self.sleep	-= 1		# TICKS we have to wait after the last flush

			# This is something we should adjust in future
			# perhaps base this on the count seen so far or whatever
			self.fuzz += self.width/10

			# Are we delaying, then skip a flush
			if self.sleep<0:
				# If we are dirty (.dirt) longer then DIRT_LEVEL (4s)
				# OR we are .forcing and .forcing has reached 1 (==this tick)
				# OR the dirty region (.count) is just too much
				if self.dirt>self.DIRT_LEVEL or self.forcing==1 or self.width * self.height < self.count * 50 + self.fuzz:
					self.force_flush()
			else:
				self.forcing += 1	# HACK to NOT decrement self.forcing below

		# See HACK above, this works as follows, which is intended:
		# If self.forcing is set, it is usually set to 2 such that it
		# does not force on the direct next tick (which can be right now).
		# However if we are forcing and nothing changed we still want
		# to write out the picture - perhaps some filesystem trigger waits.
		if self.forcing:
			self.forcing	-= 1
			self.dirty	= True

		self.autonext(False)

	def flush(self, fast):
		"""
		Force a flush after the next tick (0.1s to 0.2s).

		Set fast, if it should be on the next tick (0.s to 0.1s).
		If you really need immediate, then use .force_flush()
		"""
		if self.forcing!=1:
			self.forcing	= 2
		if fast:
			self.dirty	= True
			self.count	+= self.width*self.height	# HACK to refresh on next timer

	# Called when the image must be written to disk
	def force_flush(self):
		"""
		Immediately write image to disk.
		The target is overwritten atomically by rename()

		This should not be called directly,
		because it might flush() unneccessarily.
		Use .flush() instead
		"""

		self.sleep = self.SLEEP_TIME

		# Do not flush if nothing changed
		if self.count or self.changed:
			self.save_img(self.name, self.type)

		self.count	= 0
		self.fuzz	= 0
		self.delta	= 0
		self.dirt	= 0
		self.skips	= 0
		self.dirty	= False

	def save_img(self,name, type=None, quality=None):
		tmp = os.path.splitext(name)
		tmp = tmp[0]+".tmp"+tmp[1]

		img	= self.img
		if self.viz:
			img	= self.img.copy()
			img.paste(self.viz, (0,0), self.viz)

		if self.vizualize:
			old		= self.viz
			self.viz	= PIL.Image.new('RGBA',(self.width,self.height),(0,0,0,0))
			if old:
				self.viz	= PIL.Image.blend(self.viz, old, alpha=.75)
			self.vizdraw	= PIL.ImageDraw.Draw(self.viz)

		if quality is None:
			quality	= self.quality
		if quality is None:
			img.convert('RGB').save(tmp, type)
		else:
			img.convert('RGB').save(tmp, type, quality=quality)
		os.rename(tmp,name)

		img	= None
		self.log("out", name=name, skips=self.skips, count=self.count, fuzz=self.fuzz, delta=self.delta, dirt=self.dirt)

	def connectionMade(self, vnc):
		self.log("connection made")
		self.myVNC = vnc

	def vncConnectionMade(self, vnc):
		super(rfbImg, self).vncConnectionMade(vnc)

		self.width = vnc.width
		self.height = vnc.height

		# According to PIL docs:
		# 1x1 1 is b/w
		# 1x8 L is grayscale
		# 2x8 LA is L with alpha (limited support, really alpha and not transparency mask?)
		# 1x8 P is palette
		# 3x8 RGB is red/creen/blue
		# 4x8 RGBA is 4x8 RGB with transpacency mask
		# 4x8 RGBX is RGB with padding (limited support)
		# 4x8 RGBa is RGB with pre-multiplied alpha channel (limited support)
		# 4x8 CMYK Cyan/Magenta/Yellow/Black substractive color separation
		# 3x8 YCbCr JPEG based video format
		# 3x8 LAB L*a*b
		# 3x8 HSV Hue, Saturation, Value
		# 1x32 I signed integer pixels
		# 1x32 F floating point pixels
		#
		# We use RGBX here, because that is the VNC data format used
		#
		# PIL.Image.new(mode, (w,h), color)  missing color==0:black, None:uninitialized
		self.img = PIL.Image.new('RGBX',(self.width,self.height),None)

	def updateRectangle(self, vnc, x, y, width, height, data):
		#print "%s %s %s %s" % (x, y, width, height)
		img = PIL.Image.frombuffer('RGBX',(width,height),data,'raw','RGBX',0,1)
		if x==0 and y==0 and width==self.width and height==self.height:
			# Optimization on complete screen refresh
			self.img = img
		elif self.loop or self.mouse:
			# If not looping this apparently updates the mouse cursor
			bb	= PIL.ImageChops.difference(img,self.img.crop((x,y,x+width,y+height)))

			if self.viz:
				outline=(255,0,0,255)			# major changes are marked red
				st	= PIL.ImageStat.Stat(bb)
				if reduce(lambda x,y:x+y, st.sum2) < 100*width*height:
					outline=(0,0,255,255)		# minor changes are marked black
				self.vizdraw.rectangle((x,y,x+width,y+height),outline=outline)

			# Skip update if region is really unchanged
			if not bb.getbbox():
				# Can this actually happen with RFB?
				self.skips	+= 1
				return

			self.img.paste(img,(x,y))

		self.dirty	= True
		self.changed	+= width*height
#		self.rect = [ x,y,width,height ]

	def beginUpdate(self, vnc):
		self.changed = 0

	def commitUpdate(self, vnc, rectangles=None):
		#print "commit %d %s %s" % ( self.count, len(rectangles), self.rect )

		# remember the biggest batch
		if self.changed > self.delta:
			self.delta = self.changed
		self.changed = 0

		# Increment by the biggest batch seen so far
		self.count += self.delta

		# If one-shot then we are ready
		if not self.loop:
			self.force_flush()
			self.stop()	# This is asynchronous
			#self.halt()	# I really have no idea why this is not needed

		self.autonext(True)
		vnc.framebufferUpdateRequest(incremental=1)

	def pointer(self,x,y,click=None):
		"""
		Then moves the mouse pointer to the given coordinate
		and applies the button click.

		If all buttons are released, they are released before movement.

		If click is not given, use the same button mask as before (drag etc.)
		"""
#		self.forcing = 2

		# First release, then move
		# If you want to move with button pressed:
		# Move with button, then release button.
		if click is None:
			click	= self.lm_c
		elif self.lm_c and not click:
			self.event_add(self.myVNC.pointerEvent, self.lm_x, self.lm_y, 0)

		self.lm_c	= click
		if x is not None:	self.lm_x	= max(0,x)
		if y is not None:	self.lm_y	= max(0,y)

		self.event_add(self.myVNC.pointerEvent, self.lm_x, self.lm_y, self.lm_c)
		self.log('mouse', self.lm_x, self.lm_y, click)

	def key(self,k):
#		self.forcing = 2
#		self.count += self.width*self.height
		self.event_add(self.myVNC.keyEvent,k,1)
		self.event_add(self.myVNC.keyEvent,k,0)

#	def todo(self,*
#	def todo(self, cb, *args, **kw):
#		self.event_add(*args, **kw)






# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[
# NEEDS REWRITE START[

# Sorry in German, because this for me until this got rewritten:
#
# Das Ganze hier ist ein einziger grosser gigantischer Misthaufen
# der nicht nur übel stinkt sondern auch noch dazu große
# environmentale Probleme bereitet.
#
# Das ist nicht nur hackish sondern komplett fehldesigned.
#
# Was ich brauche ist ein ordentliches System mit dem man etwas
# nebenläufig ablaufen lassen kann.
# Das Halte und Startproblem (pause, resume) darf hier nicht rein
# sondern kann meinetwegen in einer Zwischenklasse implementiert werden.
#
# Das Ganze muss wohl mit Callbacks organisiert sein.
# Callbacks funktionieren mit allen Varianten,
# egal ob AsyncIO, Threads, Twisted oder sonstwas.
# Ich will da nicht von irgendeinem Framewürg abhängig bleiben,
# sprich, das hängt dann technisch nur von easyrfb ab.
#
# Ja, eigentlich sollte das in EasyRFB rein.  Issesabernich.
# Noch nicht.  Also bleibt das erst einmal vorerst hier.
# Aber sollte da hin verschoben werden können,
# schließlich erbt es dann diese Klasse hier.

	# next management
	#
	# force==False:
	# Timer is asynchronous.  Hence it may hit too early.
	# So we need to delay the next invocation for the next timer.
	# This gives the picture at least 0.1s time to update properly
	# before rechecking.
	#
	# force==True:
	# Synchronous at the end of a round.
	# As we have a current picture, invoke everything now.
	#
	# cmd "next" needs to wait for the next update to happen
	# which is asynchronous.
	#
	# cmd "wait" waits for a certain picture content
	#
	# "evt" wants to send some events in a controlled fashion
	delaynext = False
	def autonext(self, force):
		self.delaynext	= self.event_next(force, self.delaynext)

		if not force and not self.delaynext:
			self.delaynext = self.waiting or self.nexting
			return

		self.check_waiting()
		if force:
			self.notify()

		self.delaynext = self.waiting or self.nexting

	# This is upcoming rewrite of next/notify/etc. below
	# (I need some proper idea and time to do so)
	# Therefor the excess arguments which are not needed now
	#
	# For now this only runs the next event, not all
	#
	# In future will have following types of events:
	# queued events:	processed one after the other (else in parallel)
	# timed events:	processed on force=false
	# next events:	processed on force=true
	# repeated events:	not removed if callback returns false
	def event_next(self, force, delaynext):
		# For now this is just queued+timed event
		if not self.evting or force:
			return delaynext

		cb,args,kw	= self.evting.pop(0)
		#print('evt', cb,args,kw)
		cb(*args, **kw)

		return delaynext

	evting	= []
	def event_add(self, cb, *args, **kw):
		queued	= kw.pop('queued', True)
		timed	= kw.pop('timed', True)
		next	= kw.pop('next', False)
		# for now only queued and timed event are supported
		#print('add', cb,args,kw)
		self.evting.append((cb, args, kw))

	nexting	= []
	def next(self, cb):
		self.nexting.append(cb)

	def notify(self):
		tmp = self.nexting
		self.nexting = []
		for cb in tmp:
			cb()

	waiting = []
	def wait(self, **waiter):
		self.waiting.append(waiter)

# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]
# NEEDS REWRITE END]

	def prep_templates(self,templates):
		"""
		Load a bunch of templates for comparision/searching
		and extract the condition on each template based on the prefixing `!`
		"""
		tpls = []
		for l in templates:
			if l=="": continue
			# template	check if template matches
			# !template	check if template does not match
			# I am not happy with following:
			# !!template	check if !template does not match
			# !!!template	check if !template matches
			# !!!!template	check if !!template matches
			# !!!!!template	check if !!!template matches
			# and so on
			# JUST DO NOT USE TEMPLATE NAMES STARTING WITH !
			f = l
			cond = l[0]!='!'
			if not cond:	# !??xxxxx
				# template	-> cond=true  template
				# !template	-> cond=false template
				# !!template	-> cond=false !template
				# !!!template	-> cond=true  !template
				# !!!!template	-> cond=true  !!template
				# !!!!!template	-> cond=true  !!!template
				cond = l[1]=='!' and l[2]=='!'
				f = l[(cond and 2 or 1):]
			try:
				tpls.append(dict(t=cachedTemplate(f).parse(), cond=cond))
			except Exception,e:
				twisted.python.log.err(None, "load")			#TWISTED
				return None
		return tpls

	def check_waiter(self,waiter,debug=False):
		""" check a single waiter (templates) """
		try:
			tpls = waiter['templates']
		except KeyError:
			tpls = self.prep_templates(waiter['t'])
			self.log("templates loaded",waiter['t'])
			waiter['templates'] = tpls

		if not tpls:
			waiter['match'] = None
			return True

#		if debug: debug = lambda **kw: self.diag(**kw)

		for t in tpls:
			# Check all the templates
			f	= t['t'].match(self.img, debug)
			if (f is None) == (not t['cond']):
				waiter['match'] = (t, f)
				if 'img' in waiter:
					waiter['img'] = self.img.convert('RGB')
				return True
		return False

	# I do not like that.
	# "waiting" should contain classes which contain the code
	# This then is far more flexible
	# This way evt, next and wait can become a single thing
	def check_waiting(self):
		for i,w in enumerate(self.waiting):
			if self.check_waiter(w):
				# We found something
				# Remove from list and notify the waiting task
				del self.waiting[i]	# safe, as we return afterwards
				w['cb'](**w)
				# We must return here, else i gets out of sync
				return
			w['retries'] -= 1
			if w['retries']<0:
				del self.waiting[i]	# safe, as we return afterwards
				w['match'] = None
				w['cb'](**w)
				return

def try_link(from_, to):
	try:
		os.link(from_, to)
		return True
	except OSError,e:
		if e.errno != errno.EEXIST:
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

# Why isn't that the standard of l.append(v, v, v)?
def Append(l, *a):
	l.extend(a)
	return l

# Why isn't that the standard of l.extend(a, a, a)?
def Extend(l, *a):
	for b in a:
		l.extend(b)
	return l

# This now is deterministic O(n)
# and no more possibly endless recursive/iterative
def var_expand(o, *d):
	"""
	return o with '{var}' sequences replaced by vars given in dicts *d
	first dict wins.  If var is missing, '{var}' is just not replaced.
	Also: {} is an escape preventing expansion at this stage.
	You can nest it with: {{}} which will replace to {}
	"""
	maxarg	= None
	for a in d:
		if a:
			maxarg	= a.get('#')
			if maxarg is not None:
				break
	maxarg	= int(maxarg) if maxarg else 0

	r	= []
	t	= []
	s	= str(o)
	p	= 0
	inhibit	= False
	for i in range(len(s)):
		if s[i]=='{':
			r.append(s[p:i])
			t.append(r)
#			print('stack', t)
			r	= []
			p	= i+1
		if s[i]=='}' and t:
			r.append(s[p:i])
			v	= ''.join(r)
			r	= t.pop()
#			print('unstack', r, v)
			p	= i+1
			if v=='':
				# {} special case
				# Regardless how deep it shows up,
				# it inhibits further expansion,
				# but only a single time.
				# {{}} is your friend ..
				inhibit	= True
				# But it replaces to nothing at this level.
				# Notes for degenerate cases a='b', b='', c='x':
				# '{c{{a}}}' => '{c{b}}' => '{c}' gives 'x'
				# '{c{{b}}}' => '{c{}}' gives '{c}', as further expansion is inhibited
				continue
			# We must check for {} first and then for inhibit:
			# '{{}someting{}}' expands to '{something}'.
			# but inhibiting above starts after '{{}' has been seen already
			# so it would inhibit '{}}', so the '{}' still needs to replace to nothing.
			# For '{{}something{}}' we are at
			# STACK('{') INHIBIT('{}') 'something' INHIBIT('{}') YOU_ARE_HERE('}')
			# giving '{something}' and resets inhibit if we are at top level again.
			# hence '{{}}'  is replaced to '{}', which is exactly what we want.
			if inhibit:
				r.append('{'+v+'}')
				# inhibit stops when we are on top level again
				inhibit	= len(r)>0
				continue

			# {X}
			# {X:N}
			# {X:N:N}
			sep	= v.rsplit(':', 2)
			v	= sep[0]
			y	= int(sep[1]) if len(sep)>1 and sep[1] else -1
			z	= int(sep[2]) if len(sep)>2 and sep[2] else -1
			if v=='' or len(sep)>1 and v.isdigit():
				# {[start]:[end]}
				# {[start]:[end]:[step]}
				x	= int(v) if v else 0
				if x<1: x=1
				if y<0 or y>maxarg: y=maxarg
				if z<1: z=1
				l	= []
				while x<=y:
					v	= str(x)
					for c in d:
						if c and v in c:
							l.append(c[v])
							break
					x += z
				# XXX TODO XXX
				# you cannot detect the difference between
				# empty argument {3:3}
				# and missing argument {3:2}
				# both are empty.  Is there some solution?
				r.append(' '.join(l))
				continue

			# {var}
			# {var:start}
			# {var:start:end}
			for a in d:
				if a and v in a:
					x	= a[v]
					if y<0:	y=0
					if z<0:	z=len(x)
					r.append(x[y:z])
					break
			else:
				# executed if not found (no 'break' above)
				r.append('{'+v+'}')
	# append the remaining part (everything after the last '}'
	if p<len(s):
		r.append(s[p:])
	# now works up the strack backwards open braces seen which have missing closing braces
	# There are no errors here
#	print('r', r)
#	print('t', t)
	while t:
		# or r	= Append(t.pop(), *r)
		# or r	= Extend(t.pop(), r)
		v	= ''.join(r)
		r	= t.pop()
		r.append('{'+v)
#	print('r', r)
	return ''.join(r)

#	a	= {}
#	for i in d:
#		a.update(i)
#	for i in range(100):
#		tmp	= s
#		for k,v in a.iteritems():
#			tmp = tmp.replace(k,v)
#		if tmp == s:
#			return s
#		s	= tmp
#
#	raise RuntimeError('instable expansion, too many recursions: '+repr(o))

def restore_property(prop):
	def decorate(fn):
		@functools.wraps(fn)
		def wrap(self, *args, **kw):
			old	= getattr(self, prop)
			try:
				return fn(self, *args, **kw)
			finally:
				setattr(self, prop, old)
		return wrap
	return decorate

def WRAP(fn, *args, **kw):
	def x():
		return fn(*args, **kw)
	return x

def bool2str(b):
	return b and '1' or '0'

# We should have a speeding curve from 0..n
# but a linear move must do for now
def curve(end, start, pos, steps, rnd=5):
	return rand(rnd+rnd+1)-rnd + end + pos * (start - end) / steps

class Val(object):
	def __init__(self, val):
		self.__val	= val

	def val(self):
		return self.__val

	def __repr__(self):
		return self.__class__.__name__+'('+repr(self.__val)+')'

class Return(Val):	pass
class Bye(Val):		pass

class RfbCommander(object):
	valid_filename	= valid_filename

	MODE_SPC	= ' '
	MODE_TAB	= "\t"

	__Nothing	= {}		# some Dummy

	def __init__(self, io):
		self.io		= io

		# HACK:
		# I do not like that global "self.bye" thingie yet.
		# There should be some "bye" object,
		# which allows to be passed with additional flags, like
		# "I need to do just a return from macro" or
		# "I need to exit from input loop, as well"
		# But I haven't found a good idea yet.
		#
		# Example: "prompt" "run macro" should exit if "macro" exists, but not if not
		# Currently I cannot really express this easily.
		self.bye	= False
		self._prompt	= None
		self.globals	= None
		self.repl	= {}
		self.args	= {}
		self.autovars	= False
		self.success	= None
		self.failure	= 'ko'
		self.state	= None
		self.prevstate	= None
		#self.rfb	= io.factory.rfb	# not set yet
		self.quiet	= False
		self.verbose	= False
		self.debugging	= False
		self.tracing	= False
		self.mode	= self.MODE_SPC
		self.paused	= True
		self.stack	= [self.topLevelInput()]
		self.lines	= []
		#self.max	= 0
		self.macnt	= 0
		self.scheduler()

	def queueLine(self, rfb, line):
		self.rfb	= rfb
		self.lines.append(line)
		self.log('got', line)
		if not self.paused:	# readLine is waiting for data
			# assert that TOS is generator of lineInput?
			self.scheduler()

#	def setmax(self, max):
#		if self.max < max:
#			self.max	= max
#			self.log('depth', max)

	def scheduler(self, v=None, error=None):
		self.trace(Sched=len(self.stack), ____________________v=v, _error=error, B=self.bye)
		while self.stack:
			g	= self.stack[len(self.stack)-1]
			try:
				err	= error
				if err:
					error	= None
					# keep v if next gives StopIteration
					self.trace(Sched=len(self.stack), _throw=g, _v=err, B=self.bye)
					v	= g.throw(err)
				else:
					self.trace(Sched=len(self.stack), _send=g, _v=v, B=self.bye)
					v	= g.send(v)
			except StopIteration:
				self.trace(Sched=len(self.stack), _stop=g, B=self.bye)
				self.stack.pop()
				if not err:		# StopIteration on .throw() is OK
					self.log(warn='Return() was not used', generator=g)
				continue
			except Exception, e:
				self.trace(Sched=len(self.stack), _g=g, _exc=e, B=self.bye)
				if not err:		# skip error sequences, just tell the head
					self.io.log_err(None, 'scheduler exception from '+repr(g))
				error	= e
				self.stack.pop()
				continue

			# In Python3.3 we could use "return generator()" instead of "yield generator(); return"
			# But scheduler() will first fully execute "generator()" until the "return" is done.
			# Workaround is to use "yield Return(generator()); return" which is not all too bad
			while isinstance(v, Return):
				v	= v.val()
				g	= self.stack.pop()
				try:
					self.trace(Sched=len(self.stack), _return=g, B=self.bye)
					g.send(None)
					self.trace(Sched=len(self.stack), _return=g, bug='no return after Return()', B=self.bye)
					# Must not come here
					self.throw(v, 'Return() not followed by return:', repr(g))
					# never reached

				except StopIteration:
					self.trace(Sched=len(self.stack), _returned=g, B=self.bye)

			if v is self.__Nothing:
				# We are delaying (waiting for event etc.)
				# This is why we see __Nothing
				# (perhaps we should get a callback or something .. but)
				self.trace(Sched=len(self.stack), _waiting=g, B=self.bye)
				return

			if inspect.isgenerator(v):
				# We got passed something to do
				# Push it onto the stack and run it next iteration

				if len(self.stack)>=MAXSTACK:
					error	= RuntimeError('stackoverflow, too many recursions: '+str(len(self.stack)))
					self.io.log_err(error, 'scheduler exception')
					self.trace(Sched=len(self.stack), _macro=v, stackoverflow=len(self.stack), B=self.bye)
				else:
					self.trace(Sched=len(self.stack), _macro=v, B=self.bye)
					self.stack.append(v)
					v	= None
			else:
				self.trace(Sched=len(self.stack), _val=v, B=self.bye)

			# Postpone the next iteration.
			# XXX TODO XXX do not use 'sleep' here
			self.io.sleep(0, self.scheduler, v, error)
			return

		self.trace(Sched=len(self.stack), _end=True, v=v, error=error, B=self.bye)
		self.io.end()
		if error:
			raise error

	def topLevelInput(self):
		return self.lineInput(True)
		#self.log('bye')
		#self.io.end() is in scheduler()

	def lineInput(self, prompt=False):
		self.paused	= True						# disable queueLine() sending to us
		hold		= False
		ret		= True
		try:
			while not self.bye:
				if not self.lines:
					if hold:
						hold	= False
						if self.io.resume():		# Enable factory, as we are available again
							continue		# this possibly pulls in new lines
						self.log('gone away')
						self.bye	= True
						ret		= False		# going away unexpectedly is an error
						break

					if prompt:
						yield self.prompt()		# send prompt if something needed
						if self.lines:	continue	# this might reveal some more lines

					# The next 3 commands must be in exactly this sequence to avoid races
					self.paused	= False			# enable queueLine() directly sending to us
					yield self.__Nothing			# wait for next line
					self.paused	= True			# disable queueLine() sending until allowed again
					continue

				if not hold:
					hold	= True
					self.io.pause()				# Stop factory, we are busy

				line		= self.lines.pop(0)
				v		= yield self.readLine(line, self._prompt and prompt)
				self.log(Done=line, Ret=v, B=self.bye)
		finally:
			if hold:
				self.io.resume()				# Enable factory, as we are available again

		yield Return(ret)						# this is what we expect, a clean self.bye (due to 'exit')

	#
	# Direct IO Helpers
	#

	def write(self, s):
		self.io.write(s)

	def writeLine(self, s):
		self.io.writeLine(s)

	def readLine(self, line, prompt):
		if prompt and line.strip()=='':
			# hack: Do not error on empty lines when prompting
			# hack: and do the autoset which usually is done in .processLine
			self.autoset()
			st	= self.ok()
		else:
			self.log(line=line)
			self.macnt	= 0							# reset macro counter on each line processed
			st		= None
			try:
				v	= self.processLine(line, prompt)			# only expand on prompts
				self.trace(Line=line, _yield=v, B=self.bye)
				v	= yield v
				self.trace(Line=line, _got=v, B=self.bye)
				st	= self.get_bye(v)
			except Exception,e:
				self.trace(Line=line, ex=e, B=self.bye)
				self.io.log_err(e, 'exception in readline')
				self.bye		= True	# Really?
				if prompt:
					self.bye	= False
					self.writeLine(traceback.format_exc())
			self.trace(Line=line, _status=st, prompt=prompt, B=self.bye)
			if st:
				self.out(self.success, st, line)
			else:
				self.fail(self.failure, st, line)
				if prompt and self.macnt>0:
					self.bye	= False

		# quiesce scheduler() warning about missing Return()
		yield Return(st)

	def expand(self, s):
		return var_expand(s, self.args, self.repl, self.globals)

	def prompt(self):
		if not self._prompt:
			yield Return(False)
			return

		# TODO XXX TODO print some stats here
		self.write(self.expand(self._prompt))
		yield Return(True)			# push output to user

	#
	# Variables
	#

	def autoset(self):
		self.autovars	= True
		r		= self.repl

		r['mouse.x']		= str(self.rfb.lm_x)
		r['mouse.y']		= str(self.rfb.lm_y)
		r['mouse.b']		= str(self.rfb.lm_c)

		r['flag.verbose']	= bool2str(self.verbose)
		r['flag.quiet']		= bool2str(self.quiet)
		r['flag.debug']		= bool2str(self.quiet)
		r['flag.trace']		= bool2str(self.quiet)

		r['sys.tick']		= str(self.rfb.tick)
		r['sys.macros']		= str(self.macnt)
		r['sys.depth']		= str(len(self.stack))

		tm			= time.gmtime()
		r['date.y']		= str(tm.tm_year)
		r['date.m']		= str(tm.tm_mon)
		r['date.mm']		= str(tm.tm_mon).zfill(2)
		r['date.d']		= str(tm.tm_mday)
		r['date.dd']		= str(tm.tm_mday).zfill(2)
#		r['date.w']		= str(tm.tm_week)		# 1-52
#		r['date.ww']		= str(tm.tm_week).zfill(2)	# /1-52
		r['date.wd']		= str(tm.tm_wday+1)		# 1-7 where 7=sun
		r['date.yd']		= str(tm.tm_yday)		# 1-366
		r['date.ydd']		= str(tm.tm_yday).zfill(3)
		r['time.h']		= str(tm.tm_hour)
		r['time.hh']		= str(tm.tm_hour).zfill(2)
		r['time.m']		= str(tm.tm_min)
		r['time.mm']		= str(tm.tm_min).zfill(2)
		r['time.s']		= str(tm.tm_sec)
		r['time.ss']		= str(tm.tm_sec).zfill(2)

# this was for debugging saves to JSON
#		r['all']		= ''.join([chr(x) for x in range(256)])

		# XXX TODO XXX add more replacements

		return r

	#
	# Output helpers
	#

	def send(self, s):
		if not self.quiet:
			self.writeLine(s)
		return True

	def diag(self, **kw):
		if self.verbose:
			self.send(ordered_repr(kw))
		return True

	def trace(self, **kw):
		if self.tracing:
			r	= ordered_repr(kw)
			self.log('trace', r)
			self.send(r)
		return True

	def debug(self, **kw):
		if self.debugging:
			r	= ordered_repr(kw)
			self.log('debug', r)
			self.send(r)
		return True

	def debugFn(self):
		def debug(**kw):
			self.debug(**kw)
		return debug

	def log(self, *args, **kw):
		D(*args, **kw)
		return self

	def out(self, s, *args, **kw):
		if s is not None:
			self.send(s)
		return self.log(s, *args,**kw)

	#
	# Return values of commands
	#

	def ok(self, *args, **kw):
		if args:
			self.send(args[0])
		if kw or len(args)>1:
			self.log(*args, **kw)
		return True			# default return value for "success"

	def fail(self, *args, **kw):
		if args:
			self.out(*args, **kw)
		return False			# default return value for "failure"

	def err(self, *args, **kw):
		if args:
			self.out(*args, **kw)
		return None			# default return value for "error"

	#
	# Line processor
	#

	def processLine(self, line, expand=False):
		if expand:
			line	= self.expand(line)
#		print('process', line)
		return self.processArgs(line.split(self.mode))

	def processArgs(self, args):
		"""
		process an argument array
		returns True  on success
		returns False on failure
		returns None  on error (exception) and set terminaton (bye)
		"""
		self.log("cmd",args)
		self.trace(proc=args)
		return getattr(self,'cmd_'+args[0], self.unknown)(*args[1:])

	#
	# all cmd_* are supposed to return
	# True  on success
	# False on failure
	# None  on error (exception)
	#

	def unknown(self, *args):
		if not self._prompt:
			self.bye	= True
		return self.err('unknown cmd, try: help')

	def cmd_prompt(self,*args):
		"""
		prompt: set prompt and do not terminate on errors (can no more switched off)
		.
		This also makes {var}s usable, see: set
		And it fundamentally changes how "unknown" commands are processed.
		Without prompt they set exit state, while with prompt they don't and just fail.
		"""
		self._prompt = ' '.join(args) if args else '> '
		self.repl['prompt']=self._prompt
		self.send(__file__ + ' ' + sys.version.split('\n',1)[0].strip())
		return self.ok()

	def cmd_success(self,*args):
		"""
		success string: set or suppresses the success string.  Default suppressed
		"""
		self.success = args and ' '.join(args) or None
		return self.ok()

	def cmd_quiet(self,*args):
		"""
		Suppress normal output of cmd
		Commandline see 'verbose'.  'verbose' and 'quiet' are independent.
		"""
		return self.onoff('quiet', *args)

	def cmd_verbose(self,*args):
		"""
		verbose: get verbose status
		verbose on: enable verbose
		verbose off: disable verbose
		verbose cmd: verbose output of cmd (see: dump)
		"""
		return self.onoff('verbose', *args)

	def cmd_debug(self, *args):
		"""
		Enable debugging output.
		Commandline see 'verbose'.  'verbose' and 'quiet' are independent.
		"""
		return self.onoff('debugging', *args)

	def cmd_trace(self, *args):
		"""
		Enable scheduler tracing.
		Commandline see 'verbose'.  'verbose' and 'quiet' are independent.
		"""
		return self.onoff('tracing', *args)

	def onoff(self, prop, *args):
		old	= getattr(self, prop)
		if len(args)==1:
			st	= args[0]=='on'
			if st or args[0]=='off':
				if not st:
					self.debug(**{prop:st})
				setattr(self, prop, st)
				if st:
					self.debug(**{prop:st})
				args	= []
		if not args:
			yield Return(old); return

		setattr(self, prop, True)
		self.debug(**{prop:True})
		try:
			v	= yield self.processArgs(args)
		finally:
			self.debug(**{prop:old})
			setattr(self, prop, old)
		yield Return(v)

	def cmd_failure(self,*args):
		"""
		failure string: set or suppresses the failure string.  Default: ko
		"""
		self.failure = args and ' '.join(args) or None
		return self.ok()

	def cmd_ok(self,*arg):
		"""
		ok: dummy command, ignores args, always succeeds
		"""
		return self.ok()

	def cmd_fail(self,*arg):
		"""
		fail: dummy command, ignores args, always fails
		.
		Also used as "unknown command"
		"""
		return self.fail()

	def cmd_fatal(self, *args):
		"""
		Raise Python RuntimeError (for debugging purpose only)
		"""
		raise RuntimeError(args and ' '.join(args) or None)

	def cmd_bug(self,*arg):
		"""
		bug: dummy command, ignores args, always errors
		"""
		return self.err()

	def cmd_help(self, cmd=None):
		"""
		help: list known commands
		help command: show help of command
		.
		Note that this application is single threaded,
		hence lengthy calculations block other things.
		"""
		if cmd is None:
			all	= []
			for a in dir(self):
				if a.startswith('cmd_'):
					all.append(a[4:])
			return self.ok('known commands: '+', '.join(all))

		fn = getattr(self, 'cmd_'+cmd)
		for a in fn.__doc__.split('\n'):
			a	= a.strip()
			if len(a):
				if a=='.': a=''
				self.writeLine(' '+a)
		return self.ok()

	def var(self, k):
		for d in [self.args, self.repl, self.globals]:
			if d:
				v	= d.get(k)
				if v is not None:
					return v
		return None

	def nvar(self, k):
		v	= self.var(k)
		try:
			return int(v)
		except TypeError:
			return 0

	def let(self, k, fn, *args):
		v	= self.nvar(k)
		ret	= v != 0
		for a in args:
			try:
				v	= fn(v, int(a))
				ret	= v != 0
			except:
				ret	= self.err()
				break
		self.repl[k]	= str(v)
		return ret

	def true(self, v, fn, *args):
		for a in args:
			try:
				v	= fn(v, a)
				if not v:
					break
			except:
				return self.err()
		# if no args then the initial v defines the return value
		return self.ok() if v else self.fail()

	def cmd_let(self, v, *args):
		"""
		let var N..:	set var to the last numeric value N, stops at the first nonnumeric one
		- errors if some N is non-numeric
		- fails if var is 0 afterwards
		- else succeeds
		- undef/empty/nonnumeric variables are silently changed to 0 first
		.
		let var:	makes var 0 if it is undefined, empty or nonnumeric
		let var a:	as before, but errors
		let var 0:	makes var 0 and fails
		let var 0 a:	makes var 0 and errors
		let var 0 1:	makes var 1 and succeeds
		let var 0 1 a:	makes var 1 and errors
		"""
		return self.let(v, lambda x,y: y, *args)

	def cmd_add(self, v, *args):
		"""
		add var N..:	add all the N to var
		- the return value is the same as in "let"
		"""
		return self.let(v, lambda x,y: x+y, *args)

	def cmd_sub(self, v, *args):
		"""
		sub var N..:	like add, but subtracs
		"""
		return self.let(v, lambda x,y: x-y, *args)

	def cmd_mul(self, v, *args):
		"""
		mul var N..:	like add, but multiplies
		"""
		return self.let(v, lambda x,y: x*y, *args)

	def cmd_div(self, v, *args):
		"""
		div var N..:	like add, but divides
		- if N is 0 this errors
		"""
		return self.let(v, lambda x,y: x/y, *args)

	def cmd_mod(self, v, *args):
		"""
		mod var N..:	like div, but does the remainder
		"""
		return self.let(v, lambda x,y: x%y, *args)

	def cmd_nat(self, *args):
		"""
		nat var..:	return true if all vars are natural numbers
		- errors if some var is undef/empty/nonnumeric
		- fails if any number is <= 0
		- success if all vars are numbers and higher than 0
		"""
		return self.true(true, lambda x,y: int(self.var(y))>0, *args)

	def cmd_cmp(self, v, *args):
		"""
		cmp val var..: compare the given variables against the given val
		- errors if any var is unset or no var is given
		- fails if any var is not the given value
		- succeeds if all vars are the given value
		"""
		def cmp(x,y):
			k	= self.var(y)
			if k is None:
				raise KeyError(y)
			return k == v
		return self.true(False, cmp, *args)

	def cmd_equal(self, v, *args):
		"""
		equal var..: success if all variables exist and are all equal
		"""
		if not args:
			return self.err()
		v	= self.var(v)
		if v is None:
			return self.fail()
		for a in args:
			if self.var(a) != v:
				return self.fail()
		return self.ok()

	def cmd_empty(self, *args):
		"""
		empty var..: checks variables for emptieness
		- fails if a variable is nonempty
		- errors if no arguments
		- else success (all variables are empty or do not exist)
		This works in sequence
		"""
		if not args:
			return self.err()
		for a in args:
			v	= self.var(a)
			if v is not None and v != '':
				return self.fail()
		return self.ok()

	def cmd_set(self, var=None, *args):
		"""
		set: list all known {var}s
		set var: check if {var} is known
		set var val: set {var} to val.
		.
		Replacements only work in macros or when promp is active.
		However the sequence in what {...} is replaced first
		is random and implementation dependent.
		.
		You cannot override macro parameters like {0}, {:3}, {3:}, {:} or {#} etc.
		To see all variables, do "prompt" followed by "load" followed by "set"
		.
		There is a subtle detail:
		'set a ' <- note: trailing blank -- sets {a} to the empty string
		'set a' <- note: no blank        -- checks if {a} is known and
		'set  b' <- note: two blanks     -- sets {} to b
		.
		Example:
		.
		if set myvar
		else set myvar default
		"""
		if not var:
			flag	= False
			if self.globals is not None:
				for k,v in sorted(self.globals.iteritems()):
					self.writeLine('g{'+k+'} '+repr(v))
					if k in self.repl and v!=self.repl[k]:
						flag	= True
			else:
				self.writeLine('use "load" to load globals')
			if not self.autovars:
				self.writeLine('use "prompt" to get automatic vars')
			if flag:
				self.writeLine('note: vars override globals, use "save" to save globals')
			for k,v in sorted(self.repl.iteritems()):
				self.writeLine('v{'+k+'} '+repr(v))
			for k,v in sorted(self.args.iteritems()):
				self.writeLine('m{'+k+'} '+repr(v))
		elif not args:
			# must return bool, never None
			return self.var(var) is not None
		else:
			self.repl[var]	= ' '.join(args)
		return self.ok()

	def cmd_unset(self, *args):
		"""
		unset var..: unset replacements {var}s
		.
		this fails for the first {var} missing
		"""
		for var in args:
			del self.repl[var]
		return self.ok()

	def fillstate(self, v, ok=[], fail=[], err=[], **kw):
		return self.err(*err, **kw) if v==None else self.fail(*fail, **kw) if v=='' else self.ok(*ok, **kw)

	def cmd_expand(self, var, *args):
		"""
		expand var:		echo the expanded value of the variable
		- errors if var is undef
		expand var val..:	expand the value and set it to var.
		- succeeds if expansion is nonempty, else fails
		"""
		if args:
			v	= self.expand(' '.join(args))
			self.repl[var]	= v
		else:
			v	= self.var(var)
			if v is not None:
				v	= self.expand(v)
				self.writeLine(v)
		return self.fillstate(v)

	def globs(self, globs):
		# fix possibly buggy things
#		print('before', repr(globs))
		kick	= []
		fix	= []
		for a in globs.iterkeys():
			if a.startswith('global.'): continue
			if 'global.'+a not in globs:
				# if 'a' and 'global.a' exist in GLOBALSFILE, then ignore 'a'
				fix.append(a)
			kick.append(a)	# unsafe: del globs[a]
		for a in fix:
			globs['global.'+a]	= globs[a]
		for a in kick:
			# Deleting keys while iterate over .keys() is safe in Python2 only.
			# In Python3 this introduces subtle awful random RuntimeErrrors,
			# so we must do delayed deletion.  But now we can use .iterkeys().
			# Python3 WTF is breaking good and valid code!?!
			# However, this probably is even faster, as .iterkeys() should be faster than .keys()
			del globs[a]
#		print('after', repr(globs))
		self.globals	= globs

	def cmd_load(self, *args):
		"""
		load:		loads all globals
		load var..:	load the given gobals (again)
		.
		Automatic globals always have 'global.' as prefix.
		if you just load 'x' instead of 'global.x',
		then 'x' is not considered by 'save'
		"""
		try:
			with Open(GLOBALSFILE, lock=True) as f:
				try:
					globs	= fixJSONio(f)
				except ValueError, e:
					return self.fail('could not read: '+GLOBALSFILE, e)
		except (OSError,IOError), e:
			if e.errno != errno.ENOENT:
				raise
			return self.fail('no globals file: '+GLOBALSFILE)

		self.globs(globs)

		# transfer global to variables
		for a in args:
			self.repl[a]	= globs.get(a if a.startswith('global.') else 'global.'+a, '')

		self.send(str(len(globs))+' global(s) loaded')
		return self.ok()

	def cmd_save(self, *args):
		"""
		save:		save all automatic globals which are overridden by 'set'
		save var..:	save the given globals only.  You must 'set' them first.
		.
		'save' automatically considers variables which start with 'global.'
		To save variable '{x}' as global, use 'save x' which 'load's it as 'global.x' then
		.
		An empty global which is saved and unset in variables is removed from globals:
		'set global.x ' <- note the space, then 'save' then 'unset global.x' then 'save global.x'
		"""
		# calculate the globals which have changes
		changes	= {}
		g	= self.globals or {}
		g	= g.copy()		# need to .copy() to allow transactional behavior
		dels	= []
		if args:
			# convenience, allow to "save a" to save {a} as {global.a}
			for a in args:
				k	= a if a.startswith('global.') else 'global.'+a
				v	= self.repl.get(a)
				if v is None:
					if k!=a:
						return self.fail('variable {'+a+'} not set')
					if g.get(k)!='':
						return self.fail('cannot delete nonempty global {'+k+'}')
					dels.append(a)
					continue

				# "save a" saves global.a
				k	= a if a.startswith('global.') else 'global.'+a

				# check if global multiply given
				# like in: save a global.a
				b	= changes.get(k)
				if v == b:	continue
				if b is not None:
					return self.fail('duplicate nonmatching global given: {'+k+'}')

				# "save a" should fail if {a} and {global.a} are present and differ
				# as this might introduce very difficult to find bugs later on
				b	= self.repl.get(k)	# ==v if k==a .. (else broken computer)
				if b is not None and v!=b:
					return self.fail('variable mismatch of {'+a+'} and {'+k+'}')

				# no check for g.get(k)==v here
				# as we else would possibly miss duplicates
				changes[k]	= v

			# remove changes which do not change the global value from the last load
			kick	= []
			for k,v in changes.iteritems():
				if g.get(k)==v:
					kick.append(k)
			for a in kick:
				del changes[a]

		else:
			# just transfer every global.X variable to the globals again
			# set global.X goes into self.repl, not in self.globals!
			for k,v in self.repl.iteritems():
				if k.startswith('global.') and v!=g.get(k):
					changes[k] = v

		if not changes and not dels:
			return self.ok('nothing to save or unchanged')

		#
		# We have calculated all needed changes[] now.
		# Now do the compare + write.
		#

		with Open(GLOBALSFILE, write=True, lock=True) as f:
			# get the current global store from disk
			# It is write locked, so it cannot change until we are ready
			try:
				globs	= fixJSONio(f)
			except ValueError:
				globs	= {}

			# check, if the changes are really changes to the file
			# and that the changes are compatible to the last state from "load"
			kick	= []
			for k,v in changes.iteritems():
				a	= globs.get(k)	# value on disk
				b	= g.get(k)	# value from last load

				g[k]	= v		# remember change in our local environment

				# no global yet or our load is still valid: change is valid
				if a is None or a==b:	continue

				if a!=v:
					# We have a conflicting change.
					# a != b (disk and load differ)
					# a != v (disk and value differ)
					# b != v (load and value differ, this is from above how change[] is set up)
					# Hence our local environment is incompatible to global state
					return self.fail('Conflict: Global {'+k+'} changed while we changed it, too', glob=a, val=v, orig=g.get(k))
				# We have a compatible change.
				kick.append(k)
			for a in kick:
				del changes[a]

			kick	= []
			for a in dels:
				v	= globs.get(a)
				if v is None:	continue
				if v!='':
					return self.fail('Conflict: Global {'+a+'} not empty, cannot remove', dels=a, val=v)
				kick.append(a)

			if not changes and not kick:
				self.globs(g)	# remember the changes locally, too
				return self.ok('nothing left to save (already saved)')

			for a in kick:
				self.debug(kick=k)
				del globs[k]
			for k,v in changes.iteritems():
				self.debug(key=k, val=v)
				globs[k]	= v

			# XXX  TODO XXX UNSAFE BUG WARNING!
			#
			# If we are interrupted here, we have a problem.
			# However it is extremely difficult to do it correctly in a locking situation.
			#
			# Another task waiting for a read-lock will get the current file data after our write-lock
			# goes away.  So the data must be present there.
			#
			# However, if we write another file and only rename() it,
			# this replaces the file on disk, but not the one which already is openly waiting for lock!
			# This still refers to the original file (which is deleted now).
			#
			# The escape probably is to have a lockfile.  However this then needs two file handles,
			# one to the lockfile and one to the real file, which is bad for the general case which is good.
			# We probably want to open thousands of files (cmd 'sub'), hence doubling this number is
			# extremely bad.  Also to create some dirty second files introduces trainloads of other bug
			# possibilities, too.
			#
			# Hence we want to do it with a single FD in the general case, and only with multiple
			# files when writing, which is rare (also locked, so only max 1 write needs to have a 2nd FD):
			#
			# Read can stay easy:
			#
			# - open the file
			# - lock it for read
			# - read the file
			# - unlock and close
			#
			# In fact, we do not need locking here at all, as due to the semantics, a file does not
			# change while it is read.  Hence we can just open the file and read, without locks.
			#
			# Write is a bit more complicated:
			#
			# - Read in the old file (as it cannot change while reading, we do not need locks here)
			# - Write out a completely new file
			# - sync() the new file, so it's data and metadata is savely on disk
			# - We need to do the sync() without lock, as a sync() might take ages
			# - Open and lock the old file for write
			# - Check that the locked file still has the same metadata as the file on disk
			# - If not, drop the lock and loop to "Open and lock the old file for write".
			# - read the locked file and compare it with the data from the first step
			# - If not equal, drop the lock and loop back to the beginning.
			# - rename() the new file to the old file, which ensures atomic behavior.
			# - On the new file there is no lock, hence the write lock is dropped.
			# - And the old file now is deleted on disk
			# - However some others still might try to get a lock on the old file!
			# - Drop the lock to the old file
			# - Now others might get the lock on the old file, even that it is deleted already.
			#
			# - The next thing they do (according to this algorithm) is to get the lock
			# - and then check, that their file reference and the file on disk are the same.
			# - As this is no more true they will drop the lock and try again.
			#
			# Doing it right is *way* too complicated.  But doing it right should be the default!
			#
			# Notes:
			#
			# - This is true for things like textfiles.
			# - With copy-on-write files this could be done transactional far more easy.
			# - We must not alter the old file in the above scenario, as old data might show up
			#   after some crash with fsck().  Metadata and contents are not always in sync,
			#   if you do not enforce this.  And we only enforce it on the contents
			#   of the new file, outside all locks.
			# - If we write the old file and crash while doing it, there would be the same
			#   corruption as present here.  The goal was to get rid of exactly this possible
			#   corruption, so we must not re-introduce it!

			self.debug(glob=globs)
			s	= toJSONu(globs, sort_keys=True, separators=(",\n",': '))
			f.seek(0, io.SEEK_SET)
			f.truncate()	# unsafe!
			f.write(s)	# unsafe!

		self.globs(g)	# remember the changes locally, too
		return self.ok(str(len(changes))+' global(s) saved')

	def cmd_mode(self, mode):
		"""
		mode MODE: set command/argument mode
		Macros always start with SPC.
		Modes:
		SPC	a single space
		TAB	a single TAB
		"""
		self.mode	= getattr(self, 'MODE_'+mode)
		return self.ok()

	def sleep(self, seconds):
		self.io.sleep(seconds, self.scheduler)
		return self.__Nothing

	def cmd_sleep(self, sec):
		"""
		sleep sec: sleep the given seconds
		"""
		yield self.sleep(float(sec))
		yield Return(self.ok())

	def cmd_do(self, *args):
		"""
		do MACRO args..:
		- read file o/MACRO.macro line by line
		- returns success on "exit"
		- returns fail on EOF (possibly truncated file)
		- returns failure on the first failing command
		- returns error on error (which sets termination)
		.
		if do macro:    does not terminate on fails or errors
		.
		The macro can contain replacement sequences:
		- {N} is replaced by arg N, {*} with all args
		- {mouse.x} {mouse.y} {mouse.b} last mouse x y button
		- {sys.tick} global tick counter
		- {flag.X} where X are diverse flags
		- to see all do: "prompt" followed by "load" followed by "set"
		"""
		return self.run_do(*args)

	def run_do(self, macro, *args):
		# prevent buggy names
		if not self.valid_filename.match(macro):
			yield Return(self.fail()); return

		oldargs		= self.args
		oldmode		= self.mode
		oldstate	= self.state

		try:
			nr	= self.macnt
			if nr>=MAXMACROS:
				raise RuntimeError('macro limit exceeded:', nr)
			self.macnt	+= 1

			a		= {}
			for i in range(len(args)):
				a[str(i+1)] = args[i]
			a['#']	= str(len(args))
#			a['*']	= ' '.join(args)
			self.args	= a
			self.mode	= self.MODE_SPC
			self.diag(N=nr, _macro=macro, args=self.args)

			# read in the complete macro file
			# TODO XXX TODO decide: Move this after the hack?
			with Open(MACRODIR+macro+MACROEXT) as file:
				data	= file.readlines()

			# HACK:
			# If we are called with "bye", remember this
			# so we can set it again on leave.
			was_bye		= self.bye
			self.bye	= False

			for l in data:
				# ignore empty lines and comments
				if l.strip()=='':	continue
				if l[0]=='#':		continue

				# l is unicode and contains \n
				if l.endswith('\n'): l=l[:-1]
				# we need UTF-8
				l	= l.encode('utf8')

				# parse line
				#self.trace(Macro=macro, l=l, B=self.bye)
				st		= self.get_bye((yield self.processLine(l, True)))
				self.trace(Macro=macro, l=l, ret=st, B=self.bye)
				if not st:
					# pass on errors
					break
				if self.bye:
					# "exit" is success (st==True)
					self.bye	= False			# we have obeyed the passed "bye"
					break
			else:
				# EOF fails
				self.diag(N=nr, _macro=macro, err="EOF reached, no 'exit'")
				st	= self.fail()

			# HACK: bring back "bye" value from above.
			self.bye	= self.bye or was_bye
			self.diag(N=nr, macro=macro, ret=st)
			yield Return(st)

		finally:
			self.mode	= oldmode
			self.args	= oldargs
			self.state	= oldstate

	def cmd_run(self, *args):
		"""
		run MACRO args..: same as "if do MACRO", but followed by "return"
		"""
		return Bye(self.run_do(*args))

	def get_bye(self, v):
		while isinstance(v, Bye):
			v	= v.val()
			self.bye= True
		return v

	def cmd_not(self, *args):
		"""
		not cmd args..: fails on success, else succeeds (even on error)
		- resets exit state (like 'if' does, too)
		- does not record the STATE (use 'if' for this)
		.
		not return:	returns the inverse STATE (error/fail become success)
		"""
		st		= self.get_bye((yield self.processArgs(args)))
		self.bye	= False
		yield Return(self.fail() if st else self.ok())

	def cmd_if(self, *args):
		"""
		if command args..:
		- resets exit state (like 'not' does)
		- record success/failure of command as STATE
		- returns failure on error (this usually terminates a macro and let it return failure)
		- else returns success
		.
		if exit: just success (the "exit" has no effect else than returning success)
		if return command args..: This does not return, the "return" just is redundant
		if unknown: returns failure, sets err STATE, but does not exit (unlike "unknown" does)
		- note that "unknown" only exits if no "prompt" is active
		if if command args..: always succeeds
		- "then" executed if command has success or failure
		- "else" executed if command errored
		- "err" cannot be executed afterwards
		if command args..
		if return
		- technically the same as before
		"""
		st		= self.get_bye((yield self.processArgs(args)))
		self.bye	= False
		self.prevstate	= self.state
		self.state	= st
		yield Return(self.fail() if st is None else self.ok())

	def cmd_then(self, *args):
		"""
		then command args..: run command only when STATE (see: if) is success
		- returns state of command, succeeds when no command is executed
		"""
		return self.processArgs(args) if self.state else self.ok()

	def cmd_else(self, *args):
		"""
		else command args..: run command only when STATE (see: if) is failure
		- returns state of command, succeeds when no command is executed
		"""
		return self.processArgs(args) if (self.state == False) else self.ok()

	def cmd_err(self, *args):
		"""
		err command args..: run command only when STATE (see: if) is error
		- returns state of command, succeeds when no command is executed
		"""
		return self.processArgs(args) if (self.state is None) else self.ok()

	def cmd_echo(self, *args):
		"""
		echo args..: echo the given args with a linefeed.  Always succeeds.
		"""
		self.writeLine(' '.join(args) if args else '')
		return self.ok()

	def cmd_print(self, *args):
		"""
		print args..: like echo, but outputs no linefeed.  Always succeeds.
		"""
		if args:
			self.write(' '.join(args))
		return self.ok()

	def cmd_dump(self, *args):
		"""
		dump args..: print python repr of args
		- needs "verbose" like in: verbose dump something
		"""
		return self.diag(args=args)

	def cmd_mouse(self, x, y=None, click=None):
		"""
		mouse x y: jump mouse to the coordinates with the current button setting (dragging etc.)
		mouse x y buttons: release if all released, jump mouse, then apply buttons
		mouse template N [buttons]: move mouse in N steps to first region of e/template.tpl and performs action
		mouse template.# N [buttons]: use region n, n=1 is first
		.
		To release all buttons, you must give 0 as buttons!
		buttons are 1(left) 2(middle) 4(right) 8 and so on for further buttons.
		To press multiple buttons add their numbers.
		.
		Template based mouse movement should set the button before execution like:
		mouse template 5 0
		mouse template 0 1
		mouse template 0 0
		"""
		if click is not None:
			click = int(click)
		try:
			a = None if x=='' else int(x)
			b = None if y=='' else int(y)
		except Exception,e:
			a,b	= yield self.templatemouse(x, y, click)

		self.rfb.pointer(a,b,click)
		yield Return(self.drain(False))

	def drain(self, refresh):
		self.log("drain",refresh)
		def drained(**kw):
			self.rfb.flush(refresh)		# XXX TODO XXX WTF HACK WTF!
			self.scheduler()
		self.rfb.event_add(drained)
		yield self.__Nothing
		yield Return(True)

	def templatemouse(self, t, n, click):
		tpl	= self.template(t)
		if not tpl:
			return

		try:
			n	= int(t.split('.',1)[1])
		except Exception,e:
			n	= 0
		if not n:	n=1
		d,x,y,w,h	= tpl.getRect(n)

		lx		= self.rfb.lm_x
		ly		= self.rfb.lm_y

		# Mouse button release
		if not click and x < lx < x+w-1 and y < ly < y+h-1:
			# jitter 1 pixel
			yield Return((lx+rand(3)-1, ly+rand(3)-1)); return

		x	+= rand(w);
		y	+= rand(h);

#		self.diag(x=x, y=y, lx=lx, ly=ly)
		# move mouse in n pieces
		try:
			# We should move relative to a random spline,
			# but this must do for now
			n	= min(int(n), (abs(lx-x)+abs(ly-y))/20)
			k	= n-1
			while k>0:
				k	= k-1
				tx	= curve(x, lx, k, n)
				ty	= curve(y, ly, k, n)
				self.rfb.pointer(tx, ty)
				yield this.sleep(0.01 + 0.01 * rand(10))
		except Exception,e:
			pass

		# return the real position
		yield Return((x,y))

	def cmd_learn(self,to):
		"""
		learn NAME: save screen to l/NAME.png
		"""
		if not self.valid_filename.match(to):
			return self.fail()
		tmp = 'learn.png'
		try:
			os.unlink(tmp)
		except Exception,e:
			pass
		self.rfb.img.convert('RGBA').save(tmp)
		out = LEARNDIR+to
		if os.path.exists(out+IMGEXT):
			rename_away(out, IMGEXT)
		self.log("tmp", tmp, "out", out)
		os.rename(tmp, out+IMGEXT)
		return self.ok()

	def cmd_key(self,*args):
		"""
		key string: Type the given string
		Note: This is buggy with characters which use Shift or Control
		"""
		for k in " ".join(args):
			self.rfb.key(ord(k))
		yield Return(self.drain(True))

	def cmd_code(self,*args):
		"""
		code code code..: Send keykodes, code can be numbers or names
		"""
		for k in args:
			v	= easyrfb.getKey(k)
			if v == False:
				v	= int(k, base=0)
			self.rfb.key(v)
		yield Return(self.drain(True))

	def cmd_exit(self):
		"""
		exit: end conversation / return from macro
		"""
		return Bye(self.ok())

	def cmd_return(self, *args):
		"""
		return: like 'exit', but returns the current if-STATE (not always success)
		return cmd [args..]: unlike `if cmd args..` followed by `return`
		"""
		return Bye(self.processArgs(args) if len(args) else self.state)

	def cmd_next(self):
		"""
		next: Wait for next picture flushed out
		.
		It delays reception of next command until the next image is written out.
		.
		Usually followed by: exit
		"""
		self.rfb.next(self.scheduler)
		yield self.__Nothing
		yield Return(self.ok())

	def cmd_flush(self):
		"""
		flush: Force next picture to be flushed

		This is asynchronous, so in MACROs it probably does NOT do what what you expect.

		Usually followed by: next
		"""
		self.rfb.force_flush()
		return self.ok()

	def checker(self, **kw):
		w	= dict(**kw)
		r	= len(w['t']) and self.rfb.check_waiter(w, self.debugFn()) and self.print_wait(w)
		self.diag(check=w)
		return r
		
	def cmd_check(self, *templates):
		"""
		check template..:
		- check if template matches
		- fails if no template matches
		- prints first matching template
		"""
		return self.checker(t=templates)

	def cmd_state(self,*templates):
		"""
		state template..: like check, but writes the state (picture) to s/TEMPLATE.img
		"""
		return self.checker(t=templates, img=1)

	def cmd_wait(self,timeout,*templates):
		"""
		wait count template..: wait count screen updates for one of the given templates to show up
		.
		If count is negative, it saves state picture (like 'state' command)
		.
		Note: This waits count frames, not a defined time
		"""
		if not templates:
			yield Return(self.fail()); return

		def result(**waiter):
			self.diag(wait=waiter)
			self.scheduler(self.print_wait(waiter))

		timeout = int(timeout)
		self.rfb.wait(cb=result, t=templates, retries=abs(timeout), img=timeout<0)
		yield Return(self.__Nothing)
		# return value see result()

	def print_wait(self,waiter):
		m	= waiter.get('match')
		if not m:
			return self.fail('timeout')
		m,f	= m
		t	= m['t']
		cond	= m['cond']

		self.log("match",f,cond,t)
		if cond:
			self.send('found %s %s' % (t.getName(), str(f)))
		else:
			self.send('spare %s' % (t.getName()))
		if 'img' in waiter:
			waiter['img'].save(STATEDIR+t.getName()+IMGEXT)
		return self.ok()

	def cmd_ping(self):
		"""
		ping: Outputs "pong"
		"""
		self.send("pong");
		return self.ok()

	def cmd_stop(self):
		"""
		stop: Terminate rfbimg.  Use sparingly!
		"""
		self.send("stopping");
		self.rfb.stop()
		return self.ok()

	def cmd_send(self, channel, *args):
		"""
		send channel data..: send to channel, waiting
		- This waits until somebody has read the data
		- Data delivery is in-sequence
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		v	= ' '.join(args)
		if not c.put(v):
			c.put(v, self.scheduler)
			yield self.__Nothing
		yield Return(self.ok())

	def cmd_push(self, channel, *args):
		"""
		push channel data..: append data to channel, nonwaiting
		- This appends data to a channel, not waiting for delivery
		- Data delivery is in-sequence
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		v	= ' '.join(args)
		return self.ok() if c.put(v, False) else self.fail()

	def cmd_rep(self, channel, *args):
		"""
		rep channel data..: send data to a channel, directly and exclusively
		- This succeeds if data is delivered
		- This fails if nobody waiting on the channel
		- This errors if channel is not empty (somebody other does send/push)
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		if c.has_put():
			return self.err()
		v	= ' '.join(args)
		return self.ok() if c.put(v) else self.fail()

	def cmd_recv(self, channel, k):
		"""
		recv channel var: receive data from channel, waiting
		- This waits until somebody sends data
		- Data receipt is in-sequence
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		v	= c.get(self.scheduler)
		if v is None:
			v	= yield self.__Nothing
		self.repl[k]	= v
		yield Return(self.ok())

	def cmd_pull(self, channel, k):
		"""
		pull channel var: receive data from channel, nonwaiting
		- Fails if there is no data on the channel
		- Data receipt is in-sequence
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		v	= c.get()
		if v is None:
			return self.fail()
		self.repl[k]	= v
		return self.ok()

	def cmd_req(self, channel, k):
		"""
		req channel var: receive data from channel, exclusively
		- This fails if somebody else is waiting for data, too
		- Else this waits until somebody sends data
		this waits for something to arrive on the channel
		see also: send/recv, req/rep, push/pull
		"""
		c	= Channel(channel)
		if c.has_get():
			yield Return(self.fail())
			return
		v	= c.get(self.scheduler)
		if v is None:
			v	= yield self.__Nothing
		self.repl[k]	= v
		yield Return(self.ok())

	def template(self, name, prefix=''):
		"""
		load and returns the template named after
		prefix plus name up to the first underscore
		"""

		try:
			return cachedTemplate(prefix+(name.split('.',1)[0]))
		except:
			self.fail('template error', name=name, prefix=prefix)
			return None

	def cmd_extract(self, name, *img):
		"""
		extract template images..:
		.
		Extract all the regions of each state image given
		and save it as the state image of the first parameter.
		.
		The template used is 'extract' followed by name up to the first underscore.
		.
		A 0 with/heigth region (just a short line)
		defines the placement of the following regions
		within the same picture.
		This line then is moved along the other axis
		by the difference parameter if given, if it is 0
		according to widht/height of the placed region.
		.
		If more such lines follow, they are used for the
		placement of following pictures accordingly.
		This way you can create multiple column layouts.
		"""
		tpl	= self.template(name, 'extract')
		if not tpl:
			return self.fail()

		# XXX TODO XXX move this into the Template class
		# we do not want structural dependencies here ..
		reg	= tpl.getTpl()['r']

		class V:
			ruler	= [0,0,0,1,0]	# implicite ruler
			rulen	= -1
			xy	= [0,0]
			dir	= 0
			had	= None

		# poor man's nonlocal:
		v = V()

		def jumprule():
			"""
			move the ruler according to distance/had
			"""
			if v.had:
				d	= v.ruler[0]
				if not d:
					d	= v.had[1-v.dir]
				v.ruler[2-v.dir]	+= d

			# start a new round
			v.xy	= v.ruler[1:3]
			v.dir	= v.ruler[3]==0 and 1 or 0
			v.had	= None

		# this must only be called if there are rulers
		def nextrule():
			"""
			find next ruler
			"""

			# find next ruler
			while True:
				v.rulen	+= 1
				if v.rulen > len(reg):
					v.rulen	= 0
				nr	= reg[v.rulen]
				if nr[3]==0 or nr[4]==0:
					break

			# end the old ruler
			jumprule()
			# now: v.had == None

			# jump to the new ruler
			v.ruler	= nr
			jumprule()

		out	= None
		for i in img:
			im	= cacheimage(STATEDIR+i+IMGEXT)
			if not out:
				out	= PIL.Image.new('RGB',im.size)

			for r in reg:
				self.debug(img=i, r=r, xy=v.xy, dir=v.dir, ruler=v.ruler, had=v.had)

				if r[3]==0 or r[4]==0:
					nextrule()
					continue

				# handle overflow by extending the picture?
				# XXX TODO XXX

				# paste and advance along the axis
				# WTF why does .paste modify xy?
				out.paste(im.crop((r[1],r[2],r[1]+r[3],r[2]+r[4])), list(v.xy))
				v.xy[v.dir] += r[3+v.dir]

				# calculate minimal offsets to jump (min == max of pastes)
				v.had = (max(v.had and v.had[0] or 0, r[3]), max(v.had and v.had[1] or 0, r[4]))

			# now move the ruler to the next position
			jumprule()

		out.save(STATEDIR+name+IMGEXT)
		return self.ok('written '+name)

	def cmd_collage(self, name, *img):
		"""
		NOT YET IMPLEMENTED
		.
		collage template images..:
		.
		Create a collage from the given state images
		and save it as the state image of the first parameter.
		.
		The template used is 'collage' followed by name up to the first underscore.
		.
		The regions are taken from each next picture
		and placed at the same location on the template.
		.
		The difference parameter (the first number of each template) is RRGGBBTT
		RRGGBB are RGB values (color) and TT is transparency.
		00 is min and 99 is max
		"""
		t	= self.template(name, 'collage')
		if not t:
			return self.fail()
		r	= t['r']
		return self.fail()
		return self.ok()

class Channel():
	chan	= {}

	def __init__(self, name):
		self.c	= self.__class__.chan.get(name)
		if self.c is None:
			self.c	= self
			self.p	= []	# waiting for put
			self.g	= []	# waiting for get
			self.__class__.chan[name]	= self

	def has_put(self):		return self.c.p and True
	def has_get(self):		return self.c.g and True

	def put(self, data, cb=None):	return self.c._put(data, cb)
	def get(self, cb=None):		return self.c._get(cb)

	def _get(self, cb):
		while self.p:
			# self.g == []
			r,p	= self.p.pop(0)
			if p:
				p()
			if r is not None:
				return r
		# self.p == []
		if cb:
			self.g.append(cb)
		return None

	def _put(self, data, cb):
		if self.g:
			# self.p == []
			self.g.pop(0)(data)
			return True
		# self.g == []
		if cb is None:
			return False
		self.p.append((data,cb))
		return True

# Following are twisted wrappers, implementing an abstract interface to the classes above
#
# For now easyrfb depends on twisted, so we depend on this, too.
# We definitively want to become independent of this in future
#
# however everything of following dependency
# MUST
# be moved into easyrfb, else it is not "easy".
#
# Below mark twistedisms with (this is on column 89)					#TWISTED
# to replace them with easyrfbisms.
# Note that I might have missed things.
import twisted										#TWISTED

import twisted.protocols.basic								#TWISTED
class CorrectedLineReceiver(twisted.protocols.basic.LineReceiver):			#TWISTED
	def sendRaw(self, s):
		"""
		send raw data to other side

		Why is this missing in twisted.protocols.basic.LineReceiver?
		"""
		self.transport.write(s)

class ControlProtocol(CorrectedLineReceiver):
	delimiter='\n'									#TWISTED black magic, DO NOT REMOVE

	ID	= 0

	@classmethod
	def getid(klass):
		klass.ID	+= 1
		return klass.ID

	# Called from factory, but no self.factory here!
	def __init__(self):
		# self.factory not present at this time
		self.cmd	= RfbCommander(self)
		self.__id	= self.getid()

	def connectionMade(self):
		print("OPEN", self.__id)

	def connectionLost(self, *args):
		print('CLOSE', self.__id, args)

	# Called by LineReceiver
	# Note that this does not honor pause()
	# due to what I consider that are twisted bugs.
	def lineReceived(self, line):							#TWISTED
		self.cmd.queueLine(self.factory.rfb, line)				#TWISTED black magic, hand over rfb here
		# We are not allowed to return something else than None here
		# due to how lineReceived() works

	def log_err(self, e, cause):
		twisted.python.log.err(e, cause)					#TWISTED

	def writeLine(self, s):
		try:
			self.sendLine(s.encode('utf-8'))				#TWISTED
		except:
			print('writeLine exception', s)
			# Ignore dead other sides
			# perhaps it just disconnected early and did not care
			pass

	def write(self, s):
		try:
			# WTF?  Why is self.sendRaw() missing?
			self.sendRaw(s)							#TWISTED
		except:
			# perhaps it just disconnected early and did not care
			pass

	def pause(self):
		try:
			self.pauseProducing()						#TWISTED
			return True
		except:
			return False

	def resume(self):
		try:
			self.resumeProducing()						#TWISTED
			return True
		except:
			return False

	def end(self):
		try:
			self.stopProducing()						#TWISTED
			#self.transport.loseConnection()				#TWISTED
		except:
			pass

	def sleep(self, secs, cb, *args, **kw):
		twisted.internet.reactor.callLater(secs, cb, *args, **kw)		#TWISTED


class CreateControl(twisted.internet.protocol.Factory):					#TWISTED
	protocol = ControlProtocol							#TWISTED black magic, DO NOT REMOVE

	def __init__(self, sockname, rfb):
		self.rfb = rfb		# becomes ControlProtocol.factory.rfb eventually
		try:
			os.unlink(sockname)
		except:
			pass
		twisted.internet.reactor.listenUNIX(sockname,self)			#TWISTED

if __name__=='__main__':
	rfb	= rfbImg("RFB image writer")
	if rfb.loop:
		CreateControl(rfb._preset("RFBIMGSOCK", '.sock'), rfb)			#TWISTED

	rfb.run()
	print('came back, bye')

