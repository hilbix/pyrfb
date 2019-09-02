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

import easyrfb
import json

import os
import io
import re

import sys
import time
import random
import traceback
import functools

import PIL.Image
import PIL.ImageStat
import PIL.ImageChops
import PIL.ImageDraw

# We definitively want to become independent
# if this in future
#
# For now easyrfb depends on this
# so we depend on this, too.
#
# however everything of this dependency
# MUST
# be moved into easyrfb
#
# Below mark twistedisms with (this is on column 89)					# TWISTED
# to replace them with easyrfbisms.
# Note that I might have missed things.
import twisted

LEARNDIR='l/'
STATEDIR='s/'
IMGEXT='.png'
TEMPLATEDIR='e/'
TEMPLATEEXT='.tpl'
MACRODIR='o/'
MACROEXT='.macro'

# Dots are disallowed for a good reason
valid_filename = re.compile('^[_a-zA-Z0-9][-_a-zA-Z0-9]*$')

log	= None

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

def rand(x):
        "return a random integer from 0 to x-1"
        return random.randrange(x)

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
        self._timer = twisted.internet.task.LoopingCall(self.timer)			# TWISTED
        self._timer.start(self.TICKS, now=False)					# TWISTED

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
#       self.rect = [ x,y,width,height ]

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
#       self.forcing = 2

        # First release, then move
        # If you want to move with button pressed:
        # Move with button, then release button.
        if click is None:
                click	= self.lm_c
        elif self.lm_c and not click:
                self.event_add(self.myVNC.pointerEvent, self.lm_x, self.lm_y, 0)

        self.lm_c	= click
        if x is not None:	self.lm_x	= x
        if y is not None:	self.lm_y	= y

        self.event_add(self.myVNC.pointerEvent, self.lm_x, self.lm_y, self.lm_c)
        self.log('mouse', self.lm_x, self.lm_y, click)

    def key(self,k):
#       self.forcing = 2
#       self.count += self.width*self.height
        self.event_add(self.myVNC.keyEvent,k,1)
        self.event_add(self.myVNC.keyEvent,k,0)

#    def todo(self,*
#    def todo(self, cb, *args, **kw):
#       self.event_add(*args, **kw)









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
# egal onb AsyncIO, Threads, Twisted oder sonstwas.
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






    def check_rect(self,template,r,rect,debug,trace):
        # IC.difference apparently does not work on RGBX, so we have to convert to RGB first
        bb = PIL.ImageChops.difference(r['img'], self.img.crop(rect).convert('RGB'))
        st = PIL.ImageStat.Stat(bb)
        delta = reduce(lambda x,y:x+y, st.sum2)		# /(bb.size[0]*bb.size[1])
        if delta<=r['max']:
                if trace:
                        self.log("same",template['name'],rect,delta)
                return True

        # We have a difference
        if debug:
                bb.save('_debug.png')
                self.log("diff",template['name'],rect,delta,bb.getbbox())
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
                self.log("search",template['name'],s)
                for i in range(s[2]):
                        x += dx
                        y += dy
                        if self.check_rects(template,x,y,False,debug):
                                if debug:
                                        self.log("found",template['name'],"offset",x,y)
                                template['dx'] = x
                                template['dy'] = y
                                return True
        return False

    def load_template(self,template):
        """
        Just load a single template
        """
        if not self.valid_filename.match(template):
                raise RuntimeError('invalid filename: '+repr(template))
        return json.load(io.open(TEMPLATEDIR+template+TEMPLATEEXT))

    def prep_templates(self,templates):
        """
        Load a bunch of templates for comparision/searching.
        - it loads the template's image contents for comparision
        - it extracts the searches
        - it calculates the condition (!template)
        - it tries to optimize rectangle order for faster compare
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
                        cond = l[1]=='!' and l[2]=='!'
                        f = l[(cond and 2 or 1):]
                try:
                        t = self.load_template(f)
                        n = t['img']
                        i = cacheimage(LEARNDIR+n)
                        rects = []
                        search = []
                        for r in t['r']:
                                if r[3]==0 or r[4]==0:
                                        # Special search, if distance parameter is odd search backwards
                                        if r[3]==0:
                                                search.append((0, (r[0]&1) and -1 or 1, r[4]))
                                        else:
                                                search.append(((r[0]&1) and -1 or 1, 0, r[3]))
                                        continue

                                rect = (r[1],r[2],r[1]+r[3],r[2]+r[4])
                                pixels = r[3]*r[4]
                                spec = { 'r':r, 'name':n, 'img':i.crop(rect), 'rect':rect, 'max':r[0], 'pixels':r[3]*r[4] }
                                # poor man's sort, keep the smallest rect to the top
                                # (probable speed improvement)
                                if rects and pixels <= rects[0]['pixels']:
                                        rects.insert(0,spec)
                                else:
                                        rects.append(spec)
                        tpls.append({ 'name':l, 't':t, 'i':i, 'r':rects, 'cond':cond, 'search':search })
                except Exception,e:
                        twisted.python.log.err(None, "load")				# TWISTED
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

        for t in tpls:
                # Check all the templates
                if self.check_template(t,debug)==t['cond']:
                        waiter['match'] = t
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
                        del self.waiting[i]
                        w['cb'](**w)
                        # We must return here, else i gets out of sync
                        return
                w['retries'] -= 1
                if w['retries']<0:
                        del self.waiting[i]
                        w['match'] = None
                        w['cb'](**w)
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

def mass_replace(o, d):
        """
        mass replace string s
        by key,value of dict d
        until string no more changes
        """
        s	= str(o)
        for i in range(100):
                tmp	= s
                for k,v in d.iteritems():
                        tmp = tmp.replace(k,v)
                if tmp == s:
                        return s
                s	= tmp

        raise RuntimeError('instable expansion, too many recursions: '+repr(o))

def WRAP(fn, *args, **kw):
        def x():
                return fn(*args, **kw)
        return x

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

import twisted.protocols.basic
class controlProtocol(twisted.protocols.basic.LineReceiver):				# TWISTED
        delimiter='\n'									# TWISTED black magic, DO NOT REMOVE

        valid_filename	= valid_filename

        MODE_SPC	= ' '
        MODE_TAB	= "\t"

        # Called from factory, but no self.factory here!
        def __init__(self):
                self.bye	= False
                self.prompt	= None
                self.repl	= {}
                self.success	= None
                self.failure	= 'ko'
                self.state	= None
                self.prevstate	= None
                #self.rfb	= self.factory.rfb	no self.factory here
                self.quiet	= False
                self.verbose	= False
                self.mode	= self.MODE_SPC
                self.pausing	= []

        # Called by LineReceiver
        def lineReceived(self, line):							# TWISTED
                self.log("lR1")
                self.rfb	= self.factory.rfb

                if self.prompt and line.strip()=='':
                        # hack: Do not error on empty lines when prompting
                        self.autoset()
                else:
                        st	= self.processLine(line, self.prompt)
                        if st:
                                self.log("lR1 ok")
                                self.out(self.success, st, line)
                        else:
                                self.log("lR1 fail")
                                self.fail(self.failure, st, line)

                self.log("lR1 mid")
                if self.bye:
                        self.log("bye")
                        self.stopProducing()
                        #self.transport.loseConnection()
                elif self.prompt:
                        # TODO XXX TODO print some stats here
                        self.log("lR1 A")
                        self.transport.write(mass_replace(self.prompt, self.repl))
                        self.log("lR1 B")
                else:
                        self.log("lR1 end")
#                self.transport.resumeProducing()


        def autoset(self):
                r	= self.repl

                r['{mx}']	= str(self.rfb.lm_x)
                r['{my}']	= str(self.rfb.lm_y)
                r['{mb}']	= str(self.rfb.lm_c)
                r['{tick}']	= str(self.rfb.tick)
                # XXX TODO XXX add more replacements

                return r

        def send(self, s):
                if not self.quiet:
                        self.sendLine(s)
                return True

        def diag(self, **kw):
                if self.verbose:
                        self.send(repr(kw))
                return True

        def log(self, *args, **kw):
                print(" ".join(tuple(str(v) for v in args)+tuple(str(n)+"="+str(v) for n,v in kw.iteritems())))
                return self

        def out(self, s, *args, **kw):
                if s is not None:
                        self.send(s)
                self.log(s, *args,**kw)
                return self

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

        def processLine(self, line, expand=False):
                if expand:
                        line	= mass_replace(line, self.autoset())
                return self.processArgs(line.split(self.mode))

        def processArgs(self, args):
                """
                process an argument array
                returns True  on success
                returns False on failure
                returns None  on error (exception) and set terminaton (bye)
                """
                try:
                        self.log("cmd",args)
                        self.diag(proc=args)
                        return getattr(self,'cmd_'+args[0], self.unknown)(*args[1:])
                except Exception,e:
                        twisted.python.log.err(None, "line")				# TWISTED
                        if self.prompt:
                                self.sendLine(traceback.format_exc())
                        else:
                                self.bye	= True
                        return None

        # all cmd_* are supposed to return
        # True  on success
        # False on failure
        # None  on error (exception)

        def unknown(self, *args):
                if not self.prompt:
                        self.bye	= True
                return self.err('unknown cmd, try: help')

        def cmd_prompt(self,*args):
                """
                prompt: set prompt and do not terminate on errors (can no more switched off)
                """
                self.prompt = ' '.join(args)+'> '
                self.send(__file__ + ' ' + sys.version.split('\n',1)[0].strip())
                return self.ok()

        def cmd_success(self,*args):
                """
                success string: set or suppresses the success string.  Default suppressed
                """
                self.success = args and ' '.join(args) or None
                return self.ok()

        @restore_property('quiet')
        def cmd_quiet(self,*args):
                """
                quiet cmd: suppress normal output of cmd
                """
                self.quiet	= True
                return self.processArgs(args)

        @restore_property('verbose')
        def cmd_verbose(self,*args):
                """
                verbose cmd: verbose output of cmd
                """
                self.verbose	= True
                return self.processArgs(args)

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

                Also used as "unknown command"
                """
                return self.fail()

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
                                self.sendLine(' '+a)
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
                You can set even macro parameters {0} and so on.
                .
                There is a subtle detail:
                'set a ' <- note the blank
                sets {a} to the empty string while
                'set a' <- note the missing blank
                checks if {a} is known and
                'set  b' sets {} to b
                .
                Example:
                .
                if set myvar
                else set myvar default
                """
                if not var:
                        for k,v in self.repl.iteritems():
                                self.sendLine(' '+k+' '+repr(v))
                        return self.ok()

                if not args:
                        return '{'+var+'}' in self.repl

                self.repl['{'+var+'}']	= ' '.join(args)
                return self.ok()

        def cmd_unset(self, *args):
                """
                unset var..: unset replacements {var}s
                .
                this fails for the first {var} missing
                """
                for var in args:
                        del self.repl['{'+var+'}']
                return self.ok()

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

        # FALSCH IMPLEMENTIERT
        def cmd_sleep(self, sec):
                """
                sleep sec: sleep the given seconds
                """
                time.sleep(float(sec))
                return self.ok()

        # FALSCH IMPLEMENTIERT
        @restore_property('mode')
        def cmd_sub(self, macro, *args):
                """
                sub MACRO args..:
                - read file o/MACRO.macro line by line
                - returns success on "exit"
                - returns fail on EOF (possibly truncated file)
                - returns failure on the first failing command
                - returns error on error (which sets termination)
                .
                if sub macro:    do not fail on fails
                if if sub macro: do not fail on errors
                .
                The macro can contain replacement sequences:
                - {N} is replaced by arg N
                - {mx} {my} {mb} last mouse x y button
                - {tick} global tick counter
                - more replacements might show up in future
                - see also: set
                """

                self.mode	= self.MODE_SPC

                repl	= dict(self.repl)
                for i in range(len(args)):
                        repl['{'+str(i+1)+'}'] = args[i]

                # prevent buggy names
                if not self.valid_filename.match(macro):
                        return self.fail()

                # read the macro file
                for l in io.open(MACRODIR+macro+MACROEXT):
                        # ignore empty lines and comments
                        if l.strip()=='':	continue
                        if l[0]=='#':		continue

                        # l is unicode and contains \n
                        if l.endswith('\n'): l=l[:-1]
                        # we need UTF-8
                        l	= l.encode('utf8')

                        # parse result
                        st		= self.processLine(l, True)
                        if not st:
                                # pass on errors
                                return st
                        if self.bye:
                                self.bye	= False
                                # exit is success
                                return self.ok()

                # EOF fails
                self.diag(macro=macro, err="EOF reached, no 'exit'")
                return self.fail()

        # FALSCH IMPLEMENTIERT
        def cmd_run(self, macro, *args):
                """
                run MACRO args..: same as "sub MACRO", but followed by "exit"
                .
                This is different from "sub MACRO" "exit" in that it can return failure
                (exit cannot).
                """

                # XXX TODO XXX how to do tail recursion here so this becomes "goto"?
                st		= cmd_sub(macro, *args)
                self.bye	= True
                return st

        def cmd_if(self, *args):
                """
                if command args..:
                - record success/failure of command as STATE
                - returns failure on error
                - else returns success
                .
                if if command args..: record error state, error is failure everything else is success
                """
                st		= self.processArgs(args)
                self.prevstate	= self.state
                self.state	= st
                if st is None:
                        self.bye	= False
                        return self.fail()
                return self.ok()

        def cmd_then(self, *args):
                """
                then command args..: run command only of STATE (see: if) is success
                """
                return self.processArgs(args) if self.state else self.ok()

        def cmd_else(self, *args):
                """
                else command args..: run command only of STATE (see: if) is failure
                """
                return self.processArgs(args) if (self.state == False) else self.ok()

        def cmd_err(self, *args):
                """
                err command args..: run command only of STATE (see: if) is error
                """
                return self.processArgs(args) if (self.state is None) else self.ok()

        def cmd_echo(self, *args):
                """
                echo args..: echo the given args
                """
                if args:
                        self.sendLine(' '.join(args))
                return self.ok()

        def cmd_dump(self, *args):
                """
                dump args..: print repr of args
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
                        x = int(x)
                        y = int(y)
                except Exception,e:
                        x,y	= self.templatemouse(x, y, click)

                self.rfb.pointer(x,y,click)
                return self.event_drain(False)

        def event_drain(self, refresh):
                self.log("drain",refresh)
                def drained():
                        self.rfb.flush(refresh)		# XXX TODO XXX WTF HACK WTF!
                        self.resume()
                self.pause(drained)
                self.rfb.event_add(self.resume)
                return True

        def templatemouse(self, x, n, click):
                tpl	= self.rfb.load_template(x.split('.',1)[0])
                r	= tpl['r']
                try:
                        n	= int(x.split('.',1)[1])
                except Exception,e:
                        n	= 0
                n	= min(n, len(r))
                r	= r[max(0,n-1)]

                # Mouse button release
                if not click and r[1] < self.rfb.lm_x < r[1]+r[3]-1 and r[2] < self.rfb.lm_y < r[2]+r[4]-1:
                        # jitter 1 pixel
                        return self.rfb.lm_x+rand(3)-1, self.rfb.lm_y+rand(3)-1

                x	= r[1]+rand(r[3]);
                y	= r[2]+rand(r[4]);

                # move mouse in n pieces
                try:
                        # We should move relative to a random spline,
                        # but this must do for now
                        n	= min(int(n), (abs(self.rfb.lm_x-x)+abs(self.rfb.lm_y-y))/20)
                        # We should have a speeding curve from 0..n
                        # but a linear move must do for now
                        while n>0:
                                n	= n-1
                                tx	= rand(11)-5 + (x-self.rfb.lm_x)/(n+2)
                                ty	= rand(11)-5 + (y-self.rfb.lm_y)/(n+2)
                                self.rfb.pointer(tx, ty)
                                time.sleep(0.01 + 0.01 * rand(10))
                except Exception,e:
                        pass

                # return the real position
                return x,y

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
                return self.event_drain(True)

        def cmd_code(self,*args):
                """
                code code code..: Send keykodes, code can be numbers or names
                """
                for k in args:
                        v	= easyrfb.getKey(k)
                        if v == False:
                                v	= int(k, base=0)
                        self.rfb.key(v)
                return self.event_drain(True)

        def cmd_exit(self):
                """
                exit: end conversation / return from sub or macro
                """
                self.bye = True
                return self.ok()

        def cmd_next(self):
                """
                next: Wait for next picture flushed out

                This is asynchronous, so does NOT work in MACROs.
                It delays reception of next command until the next image is written out.

                Usually followed by: exit
                """
                self.pause()
                self.rfb.next(self.resume)
                return self.ok()

        def cmd_flush(self):
                """
                flush: Force next picture to be flushed

                This is asynchronous, so in MACROs it probably does NOT do what what you expect.

                Usually followed by: next
                """
                self.rfb.force_flush()
                return self.ok()

        def cmd_check(self,*templates):
                """
                check template..:
                - check if template matches
                - fails if no template matches
                - prints first matching template
                """
                w = {'t':templates}
                return len(templates) and self.rfb.check_waiter(w, True) and self.print_wait(w)

        def cmd_state(self,*templates):
                """
                state template..: like check, but writes the state (picture) to s/TEMPLATE.img
                """
                w = {'t':templates, 'img':1}
                return len(templates) and self.rfb.check_waiter(w, True) and self.print_wait(w)

        def cmd_wait(self,*templates):
                """
                wait count template..: wait count screen updates for one of the given templates to show up

                This is asynchronous, so does NOT work in MACROs.
                It delays reception of next command until the next image is written out.

                Note: This waits count frames, not a defined time
                """
                if len(templates)<2:
                        return self.fail()
                timeout = int(templates[0])
                self.pause()
                self.rfb.wait(cb=self.wait_cb, t=templates[1:], retries=timeout)
                return self.ok()

        def print_wait(self,waiter):
                if waiter['match']:
                        w = waiter['match']
                        self.log("match",w)
                        if w['cond']:
                                self.send('found %s %s %s' % (w['name'], w['dx'], w['dy']))
                        else:
                                self.send('spare %s' % (w['name']))
                        if 'img' in waiter:
                                waiter['img'].save(STATEDIR+w['name']+IMGEXT)
                        return self.ok()
                else:
                        self.log("timeout")
                        self.send('timeout')
                        return self.fail()

        def wait_cb(self,**waiter):
                self.print_wait(waiter)
                self.resume()

        def resume(self):
                self.log('resume', self.pausing)
                if self.pausing:
                        return (self.pausing.pop())()
                try:
                        self.transport.resumeProducing()
                except:
                        # may have gone away in the meantime
                        self.log("gone away")
                        self.bye	= True
                        return False
                return True

        def pause(self, fn=None):
                self.log('pause')
                if fn:
                        self.pausing.append(fn)
                self.transport.pauseProducing()
                return self

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

        def template(self, prefix, name):
                """
                load and returns the template named after
                prefix plus name up to the first underscore
                """
                t	= name.split('.',1)[0]
                if t and self.valid_filename.match(t):
                        return self.rfb.load_template(prefix+t)

                self.fail('wrong name', name=name, prefix=prefix, t=t)
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
                tpl	= self.template('extract', name)
                if not tpl:
                        return self.fail()

                reg	= tpl['r']

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
                                self.diag(img=i, r=r, xy=v.xy, dir=v.dir, ruler=v.ruler, had=v.had)

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
                collage template images..:

                Create a collage from the given state images
                and save it as the state image of the first parameter.

                The template used is 'collage' followed by name up to the first underscore.
                The template used has 'collage' plush name up to the first dot.

                Each template is taken from the next picture
                and placed at the same location on the template.

                The difference parameter is RRGGBBTT
                RRGGBB are RGB values (color) and TT is transparency.
                00 is min and 99 is max
                """
                t	= self.template('collage', name)
                r	= t['r']
                return self.fail()
                return self.ok()


class createControl(twisted.internet.protocol.Factory):					# TWISTED
        protocol = controlProtocol							# TWISTED black magic, DO NOT REMOVE

        def __init__(self, sockname, rfb):
                self.rfb = rfb
                try:
                        os.unlink(sockname)
                except:
                        pass
                twisted.internet.reactor.listenUNIX(sockname,self)			# TWISTED

if __name__=='__main__':
        rfb	= rfbImg("RFB image writer")
        if rfb.loop:
                createControl(rfb._preset("RFBIMGSOCK", '.sock'), rfb)			# TWISTED

        rfb.run()

