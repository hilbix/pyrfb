#!/usr/bin/env python
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

import twisted
from PIL import Image,ImageChops,ImageStat,ImageDraw

LEARNDIR='l/'
STATEDIR='s/'
IMGEXT='.png'
TEMPLATEDIR='e/'
TEMPLATEEXT='.tpl'
MACRODIR='o/'
MACROEXT='.macro'

log	= None

def timestamp():
        t = time.gmtime()
        return "%04d%02d%02d-%02d%02d%02d" % ( t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

cachedimages = {}
def cacheimage(path, mode='RGB'):
        try:
                if cachedimages[path][0]==os.stat(path).st_mtime:
                        return cachedimages[path][1]
        except KeyError:
                pass
        cachedimages[path] = (os.stat(path).st_mtime,Image.open(path).convert(mode))
        return cachedimages[path][1]

def rand(x):
        "return a random integer from 0 to x-1"
        return random.randrange(x)

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

    def __init__(self, appname, loop=None, mouse=None, name=None, type=None, quality=None, viz=None):
        super(rfbImg, self).__init__(appname)
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
        self.skips	= 0

        self.viz	= None
        self.vizualize	= viz

        self.lm_c	= 0
        self.lm_x	= 0
        self.lm_y	= 0

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

        self.save_img(self.name, self.type)

        self.count = 0
        self.fuzz = 0
        self.delta = 0
        self.dirt = 0
        self.skips = 0

    def save_img(self,name, type=None, quality=None):
        tmp = os.path.splitext(name)
        tmp = tmp[0]+".tmp"+tmp[1]

        img	= self.img
        if self.viz:
                img	= self.img.copy()
                img.paste(self.viz, (0,0), self.viz)

        if self.vizualize:
                old		= self.viz
                self.viz	= Image.new('RGBA',(self.width,self.height),(0,0,0,0))
                if old:
                        self.viz	= Image.blend(self.viz, old, alpha=.75)
                self.vizdraw	= ImageDraw.Draw(self.viz)

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
        # Image.new(mode, (w,h), color)  missing color==0:black, None:uninitialized
        self.img = Image.new('RGBX',(self.width,self.height),None)

    def updateRectangle(self, vnc, x, y, width, height, data):
        #print "%s %s %s %s" % (x, y, width, height)
        img = Image.frombuffer('RGBX',(width,height),data,'raw','RGBX',0,1)
        if x==0 and y==0 and width==self.width and height==self.height:
                # Optimization on complete screen refresh
                self.img = img
        elif self.loop or self.mouse:
                # Skip counting update if nothing changed
                st = ImageStat.Stat(ImageChops.difference(img,self.img.crop((x,y,x+width,y+height))))
                self.img.paste(img,(x,y))

                #print ImageChops.difference(img,self.img.crop((x,y,x+width,y+height))).getbbox()
                # If not looping this apparently updates the mouse cursor
                outline=(255,0,0,255)
                delta = reduce(lambda x,y:x+y, st.sum2)
                if delta<100*width*height:
                        self.skips += 1
                        outline=(0,0,255,255)
                if self.viz:
                        self.vizdraw.rectangle((x,y,x+width,y+height),outline=outline)

        self.changed	+= width*height
#	self.rect = [ x,y,width,height ]

    def beginUpdate(self, vnc):
        self.changed = 0

    def commitUpdate(self, vnc, rectangles=None):
        #print "commit %d %s %s" % ( self.count, len(rectangles), self.rect )

        # Increment by the biggest batch seen so far
        if self.changed > self.delta:
                self.delta = self.changed
        self.count += self.delta

        # If one-shot then we are ready
        if not self.loop:
                self.flush()
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
#	self.force = 2

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
#	self.force = 2
#	self.count += self.width*self.height
        self.event_add(self.myVNC.keyEvent,k,1)
        self.event_add(self.myVNC.keyEvent,k,0)

    #
    # next management
    #
    # force==False:
    # Timer is asynchronous.  Hence it may hit too early.
    # So we need to delay the next invocation for the next timer.
    # This gives the picture at least 0.1s time to update properly
    # before recheching.
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

    def event_drain(self, child, refresh):
        child.pause()
        self.event_add(self.event_drained, child, refresh);
        return True

    def event_drained(self, child, refresh):
        child.resume()
        self.force	= 2
        if refresh:
                self.count	+= self.width*self.height
        return True

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

    def check_rect(self,template,r,rect,debug,trace):
        # IC.difference apparently does not work on RGBX, so we have to convert to RGB first
        bb = ImageChops.difference(r['img'], self.img.crop(rect).convert('RGB'))
        st = ImageStat.Stat(bb)
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
                        tpls.append({ 'name':l, 't':t, 'i':i, 'r':rects, 'first':first, 'cond':cond, 'search':search })
                except Exception,e:
                        twisted.python.log.err(None, "load")
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

from twisted.protocols.basic import LineReceiver
class controlProtocol(LineReceiver):

        delimiter='\n'		# DO NOT REMOVE THIS, this black magic is needed

        # Dots are disallowed for a good reason
        valid_filename = re.compile('^[-_a-zA-Z0-9]*$')

        bye	= False
        prompt	= None

        def log(self, *args, **kw):
                print(" ".join(tuple(str(v) for v in args)+tuple(str(n)+"="+str(v) for n,v in kw.iteritems())))
                return self

        def out(self, s, *args, **kw):
                self.sendLine(s)
                self.log(s, *args,**kw)
                return self

        def ok(self, *args, **kw):
                if args:
                        self.sendLine(args[0])
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

        def lineReceived(self, line):
                self.state	= None
                self.prevstate	= None
                self.rfb	= self.factory.rfb
                if not self.prompt or line.strip()!='':
                        # Do not react on empty lines when prompting
                        if self.processLine(line):
                                self.out('ok', line)
                        else:
                                self.fail('ko', line)
                if self.bye:
                        self.stopProducing()
                        #self.transport.loseConnection()
                elif self.prompt:
                        # TODO XXX TODO print some stats here
                        self.transport.write(self.prompt)

        def processLine(self, line):
                return self.processArgs(line.split(" "))

        def processArgs(self, args):
                """
                process an argument array
                returns True  on success
                returns False on failure
                returns None  on error (exception) and set terminaton (bye)
                """
                try:
                        self.log("cmd",args)
                        return getattr(self,'cmd_'+args[0], self.unknown)(*args[1:])
                except Exception,e:
                        twisted.python.log.err(None, "line")
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
                self.prompt = ' '.join(args+('> ',))
                self.sendLine(__file__ + ' ' + sys.version.split('\n',1)[0].strip())
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
                """
                if not self.valid_filename.match(macro):
                        return self.fail()
                for l in io.open(MACRODIR+macro+MACROEXT):
                        # replace args
                        st	= processLine(self, l)
                        if not st:
                                return st
                        if self.bye:
                                self.bye	= False
                                return self.ok()
                return self.fail()

        def cmd_run(self, macro, *args):
                """
                run MACRO args..: same as "sub MACRO", but followed by "exit"
                .
                This is different from "sub MACRO" "exit" in that it can return failure
                (exit cannot).
                """
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
                return self.state if self.processArgs(args) else self.ok()

        def cmd_else(self, *args):
                """
                else command args..: run command only of STATE (see: if) is failure
                """
                if self.state == False:
                        return self.processArgs(args)
                return self.ok()

        def cmd_err(self, *args):
                """
                err command args..: run command only of STATE (see: if) is error
                """
                if self.state is None:
                        return self.processArgs(args)
                return self.ok()

        def cmd_mouse(self, x, y=None, click=None):
                """
                mouse x y: jump mouse to the coordinates with the current button setting (dragging etc.)
                mouse x y buttons: release if all released, jump mouse, then apply buttons
                mouse template N [buttons]: move mouse in N steps to first region of e/template.tpl and performs action
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
                return self.rfb.event_drain(self, False)

        def templatemouse(self, x, n, click):
                t	= self.rfb.load_template(x)
                r	= t['r'][0]
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
                if to=='':
                        to = 'screen-'+timestamp()
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
                return self.rfb.event_drain(self, True)

        def cmd_code(self,*args):
                """
                code code code..: Send keykodes, code can be numbers or names
                """
                for k in args:
                        v	= easyrfb.getKey(k)
                        if v == False:
                                v	= int(k, base=0)
                        self.rfb.key(v)
                return self.rfb.event_drain(self, True)

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
                self.rfb.flush()
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
                                self.sendLine('found %s %s %s' % (w['name'], w['dx'], w['dy']))
                        else:
                                self.sendLine('spare %s' % (w['name']))
                        if 'img' in waiter:
                                waiter['img'].save(STATEDIR+w['name']+IMGEXT)
                        return self.ok()
                else:
                        self.log("timeout")
                        self.sendLine('timeout')
                        return self.fail()

        def wait_cb(self,**waiter):
                self.print_wait(waiter)
                self.resume()

        def resume(self):
                try:
                        self.transport.resumeProducing()
                except:
                        # may have gone away in the meantime
                        self.log("gone away")

        def pause(self):
                self.transport.pauseProducing()

        def cmd_ping(self):
                """
                ping: Outputs "pong"
                """
                self.sendLine("pong");
                return self.ok()

        def cmd_stop(self):
                """
                stop: Terminate rfbimg.  Use sparingly!
                """
                self.sendLine("stopping");
                self.rfb.stop()
                return self.ok()


from twisted.internet import reactor
class createControl(twisted.internet.protocol.Factory):
        protocol = controlProtocol

        def __init__(self, sockname, rfb):
                self.rfb = rfb
                try:
                        os.unlink(sockname)
                except:
                        pass
                reactor.listenUNIX(sockname,self)

if __name__=='__main__':
        rfb	= rfbImg("RFB image writer")
        if rfb.loop:
                createControl(rfb._preset("RFBIMGSOCK", '.sock'), rfb)

        rfb.run()

