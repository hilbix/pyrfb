"use strict";
//window.setTimeout(function () { poller.stop() }, 10000);

// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

// index.html?NR (NR must be numeric)
// NR/l/ ("learned") are images saved via backend
// NR/s/ ("state") are state images saved via backend
// NR/e/ ("edit" web writable) are the edits (JSON templates referencing "learned" files)
// NR/o/ ("operation" web writable) are processed by the backend (JSON files referencing "edit"s)

// These functions should go into a lib

function Doms(sel) { return document.querySelectorAll(sel) }
function Dome(e)  { return document.createElement(e) }

function DIV(inner)
{
  return $$$(Dome('div'), inner);
}

function BUTTON(inner, click)
{
  var b = $$$(Dome('button'), inner);
  b.onclick = click;
  return b;
}

function quote(s)
{
  return String(s)
    .replace(/\\/g, '\\\\')
    .replace(/\f/g, '\\f')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t')
    .replace(/\v/g, '\\v')
    .replace(/\'/g, '\\\'')
    .replace(/[\x00-\x1f]/g,
             function (c) { return '\\x'+('0'+c.charCodeAt().toString(16)).slice(-2) }
            );
}

function dumpstring(s)
{
  var t;

  try { t=JSON.stringify(s); } catch (e) {}
  s = String(s);
  if (s==t || t===undefined)
    return s;
  var g = quote(s);
  var q = '"'+g+'"';
  if (q==t)
    return g==s ? s : t;
  return g==t ? s : s+t;
}

var DEBUG =
{ el:		'debug'
, hist:		[]
, timing:	30000
, timer:	0
, log:		function (...args)
  {
    this.hist.push(args.map(x => dumpstring(x)).join(' '));
    this.show();
  }
, show:		function ()
  {
    $(this.el).innerText = this.hist.join('\n');
    if (this.hist.length>0)
      {
        if (this.timer)
          clearTimeout(this.timer);
        this.timer = setTimeout(() => { this.timer=0; this.hist.shift(); this.show() }, this.timing/this.hist.length);
      }
  }
};

function xLOG(...args)
{
  DEBUG.log(...args);
  LOG(...args);
}

// https://stackoverflow.com/a/17772086/490291
['Arguments', 'Function', 'String', 'Number', 'Date', 'RegExp'].forEach(
  n => window[`is${n}`] = o => toString.call(o) == `[object ${n}]`
);

function later(fn, ...a) { setTimeout(() => fn(...a)) }

function strCut(s, at) { var n = s.length-at.length; return n>=0 && s.substr(n)==at ? s.substring(0,n) : s }	// remove last
function strCutAt(s, at) { var n = s.indexOf(at); return n>=0 ? s.substring(0,n) : s }				// remove upto first
function strTail(s, at) { var n = s.lastIndexOf(at); return n>=0 ? s.substring(n+1) : s }			// remove until last

function BUG(x) { var f=function () { alert(x); return false; }; f(); return f }

function dump(x)
{
  var s="";
  for (var n in x) { var v=x[n]; if (typeof(v)=="function") continue; s+=n+"="+x[n]+"\n"; }
  return s;
}

function stamp() { return new Date().getTime() }
function LOG(...a)
{
  console.log(...a)
}

function out(s) { out._out=s; $$$('out', out._tmp===undefined ? out._out : out._tmp) }
out.tmp = function (flag, s) { this._tmp = flag ? s : this._tmp==s ? undefined : this._tmp; out(this._out) }

function OUT(s) { out(JSON.stringify(s)) }

function clear(e,c)
{
  e=$(e);
  while (e.firstChild)
    e.removeChild(e.firstChild);
  if (c)
    e.appendChild(c);
  return e;
}

// IMG: Promise to create an image
// IMG(img).then(img => { success }, img => { fail }).then(...)
// imgs can be image, URL(string), function img => URL
// Why not something like bfred-it/image-promise?  Because it cannot do function ..
// See also: https://github.com/bfred-it/image-promise/blob/master/index.js
function IMG(url)
{
  var img	= Dome('img');

  if (typeof url == 'function')
    url	= url(img);
  if (typeof url == 'string')
    {
      LOG('img', url);
      img.src	= url;
    }
  else
    img		= url;

  if (!img || img.tagName !== 'IMG') return Promise.reject();

  var ret = new Promise((res,rej) =>
    {
      var ok = () =>
        {
          img.removeEventListener('load', ok);
          img.removeEventListener('error', ok);
          if (img.naturalWidth) { LOG('img ok',img.src); res(img) } else { LOG('img err', img.src); rej(img) }
        };

      img.addEventListener('load', ok);
      img.addEventListener('error', ok);
      if (img.complete)
        ok();
    });

  ret.img	= img;
  return ret;
}

function clone(i)
{
  var o = i.cloneNode(true);

  o.onload	= i.onload;
  o.onerror	= i.onerror;
  return o;
}

function mkArray(a)
{
  return Array.isArray(a) ? a : [a];
}

function CLOSURE_(fn, a)
{
  return a.length ? function (...b) { return fn.call(this, ...a, ...b) } : fn;
}

function CLOSURE(fn, ...a)
{
  return CLOSURE_(fn, a);
}

function SELFCALLwithTHIS(self, name, ...a)
{
  return function (...b) { return self[name].call(self, ...a, this, ...b) }
}

// Register passive Event
function EVP(e, ons, fn)
{
  for (var l of mkArray(ons))
    $(e).addEventListener(l, CLOSURE(fn, l), {passive:true, capture:true});
}

// Register active Event
function EVT(e, ons, fn)
{
  for (var l of mkArray(ons))
    $(e).addEventListener(l, CLOSURE(fn, l), {passive:false, capture:false});
}

function ArrayToggle(arr, val)
{
  xLOG("toggle", val, arr);
  for (var i=arr.length; --i>=0; )
    if (arr[i]==val)
      {
        xLOG("del");
        arr.splice(i,1);
        return arr
      }
  xLOG("add");
  arr.push(val);
  return arr;
}

//
// Config
//

if (!document.location.search && document.referrer && document.referrer.startsWith(document.location.href))
  document.location.replace(document.location.href+'?'+parseInt(document.referrer.substr(document.location.href.length)));

var conf = {}

conf.n		= parseInt(window.location.search.substr(1));
conf.quick	= 100;		// count
conf.quickmode	= 10;		// initial quick
conf.poll	= 200;		// ms
conf.maxwait	= 1000000;	// ms
conf.holdpolls	= 3;		// nr of images when hold mode
conf.sleep	= 6;
conf.targ	= ''+conf.n+'';
conf.dir	= conf.targ+'/';

function subdir(s) { return conf.dir+s }


//
// Base classes
//

// emit class
//
// emit some state or whatever such that others can react on it
//
// currently only used for displaying things.

var emit =
{ STOP:	['STOP']
, init:		function ()
  {
    this.emits	= {};
  }
, emit:		function (what, ...a)
  {
    if (what in this.emits)
      for (var f of this.emits[what])
        f(...a);
    return this;
  }
// register emitter callback function with given args
// callback will be called with given args followed by the emitted args
// if it returns emit.STOP the callback will be deregistered
, register:	function (what, cb, ...a)
  {
    if (!(what in this.emits))
      this.emits[what]	= [];
    var f = (...b) => { if (cb(...a,...b)===this.STOP) this.emits[what].remove(f) };
    this.emits[what].push(f);
    return this;
  }
};


//
// Backend-Calls
//

// req.get(url, query-string, callback, callback-args)
//	runs callback(response, callback-args)
//	failure: response is undefined
// req.ext(url, path, query-string, callback, callback-args)
//	same as req.get but extended.  path does not need first slash
//
// req.send(element-id, type)	click.php type=element-contents, type defaults to "t"
// req.code(charcode)		click.php character-code
// req.key(key)			click.php special-key
// req.req(query)		click.php with given query
// req.idle(query)		click.php query when idle (last one wins).  This is just before emit(fin)
// req.next()			(internal) process next request if no other is active
// req.done()			(internal) process finished request (even on error)
var req =
{ url:		'click.php'
, init:		function ()
  {
    this.reqs	= [];
    this.active	= false;
    this.cnt	= { req:0 };
    return this;
  }
, send:		function (id,t)	{ return this.req((t?t:'t')+'='+escape($(id).value)) }
, code:		function (c)	{ return this.req(         'c='+escape(c)) }
, key:		function (k)	{ return this.req(         'k='+escape(k)) }
, req:		function (s)	{ return this.get(this.url, s) }
, idle:		function (s)	{ this.idle_ = s; return this.next() }
, get:		function (u,r,cb,...a)   { this.reqs.push({u:mkArray(u), r:r, cb:cb, a:a}); return this.next() }
, post:		function (u,r,p,cb,...a) { this.reqs.push({u:mkArray(u), r:r, cb:cb, a:a, post:p}); return this.next() }
, next:		function ()
  {
    var r;

    if (this.active)
      return this;

    do
      {
        if (this.reqs.length)
          r		= this.reqs.shift();
        else
          {
            r		= this.idle_;
            this.idle_	= void 0;
            if (r === void 0)
              {
                emit.emit('fin');
                return;
              }
            r		= { u:this.url, r:r };
          }
      } while (!r);

    this.active	= r;
    this.cnt.req++;
    emit.emit('act', r);
    // ajax callback is: text, XMLHttpRequest-object, status, last-modified-header
    var u	= Array.from(r.u);
    if (u[0]=='')
      u[0]	= conf.targ;
    else
      u.splice(1, 0, conf.targ);
    if (r.post)
      ajax.push(u.join('/')+'?nocache='+stamp()+(r.r?'&'+r.r:''), (t,x,s) => this.done(r, t, s), r.post);
    else
      ajax.get(u.join('/')+'?nocache='+stamp()+(r.r?'&'+r.r:''), (t,x,s) => this.done(r, t, s));
    return this;
  }
, done:		function (r, t, s)
  {
    this.active	= false;
    emit.emit('done', r, t, s);
    if (r.cb)
      r.cb(s==200 ? t : null, ...r.a, s, t);
    return this.next();
  }
, P:		function (u, r, post) { return new Promise((ok,ko) =>
  {
    var cb=(t,s,o) => { if (s==200) ok(o); else ko(o) };
    if (post)
      this.post(u,r,post,cb);
    else
      this.get (u,r,     cb);
  })}
};

//
// Dom helper
//
var Dom =
{ dummy: 1
, sel:	function (tag, sel, ...args)
  {
//    xLOG('dom.sel1', tag, sel, args);

    var m = Doms('[data-'+tag+']');
    var current = 0, togo=-1;

    for (var i=m.length; --i>=0; )
      {
        if (!m[i].classList.contains('hide'))
          current	= i;
        if (sel && m[i].getAttribute('data-sel') == sel)
          togo		= i;
        else
          m[i].classList.add('hide');
      }
//    xLOG('dom.sel2', current, togo);
    if (sel==+1 || sel==-1)
      togo	= current+sel;
    else if (togo==-1)
      togo	= current+1;
    if (togo<0)
      togo	= m.length-1;
    if (togo>=m.length)
      togo	= 0;
    m[togo].classList.remove('hide');
    var sel = m[togo].getAttribute('data-sel');
//    xLOG('dom.sel3', tag, current, togo, sel, args);
    emit.emit('sel', tag, current, togo, sel, ...args);
    emit.emit('sel-'+tag, current, togo, sel, ...args);
  }
};

//
// DOM click handling
//

var runs =
{ attribute:	'runs'
, init:		function (attrib)
  {
    if (!attrib) attrib = this.attribute;
    for (var e of Doms('['+attrib+']'))
      e.onclick = this.click(e.getAttribute(attrib));
  }
, click:	function (str)
  {
    var w = (''+str).split(' ');
    var i = 'run_'+w.shift();
    if (i in this)	return CLOSURE_(this[i], [w]);

    i	= parseInt(str);
    if (i>0)	return () => { req.code(i); return false };
    if (str.substr(0,1)=='K') return () => { req.key(str.substr(1)); return false };
    if ($(str))	return () => { req.send(str); return false };

    return BUG('bug: undefined functionality: '+str);
  }
, run_sel:	function (args, ev) { Dom.sel(args[0], args[1], ev); }
, run_reload:	reload
, run_cmd:	function (args) { req.get(['ping.php', args[0]], ''); }
, run_quick:	function () { poller.quick(poller.state.quick>0 ? 0 : poller.state.quick<0 ? conf.quick : -1) }
, run_learn:	function () { req.send('learn', 'l'); return false }
, run_mnew:	function (...a) { macro.mnew(...a) }
, run_msave:	function (...a) { macro.msave(...a) }
, run_mdel:	function (...a) { macro.mdel(...a) }
, run_mrun:	function (...a) { macro.mrun(...a) }
};


//
// Poller
//
// This polls for image updates,
// with some linear backoff.

var poller =
{ init:		function (ms)
  {
    this.name	= 'test.jpg';
    this.cnt	= { run:0, check:0, imgs:0 };
    this.state	= { nomod:0, noimg:0, holdpolls:conf.holdpolls };
    this.set	= {};
    this.speed(ms);
    this.reset();
    this.start();
    emit.register('fin', this.reset.bind(this));
    return this;
  }
, speed:	function (ms)
  {
    // Set the speed
    this.set.ms		= ms;
    this.set.maxwait	= conf.maxwait / ms;
    return this;
  }
, reset:	function ()
  {
    // reset the linear waiting
    // so we immediately do a poll again
    // (if timer is started)
    this.state.wait	= 0;
    this.state.backoff	= 0;
    emit.emit('wait', this.state.wait, this.state.backoff);
    if (!this.state.ticking)
      this.tick();
    return this;
  }
, start:	function ()
  {
    // start the timer
    this.state.stopped	= false;
    if (this.state.started) return;
    this.tick();
    return this;
  }
, stop:		function ()
  {
    // stop the timer
    if (this.state.started)
      {
        window.clearTimeout(this.state.started);
        this.state.started	= false;
      }
    this.state.stopped	= true;
    return this;
  }
, tick:		function ()
  {
    // The timer
    this.state.ticking	= false;
    if (this.state.stopped)
      {
        this.state.started	= false;
        return;
      }
    if (this.state.quick<0 && this.state.backoff>this.state.holdpolls)
      return;
    this.state.ticking	= true;
    this.cnt.run++;
    this.poll();
    this.state.started	= window.setTimeout(() => { this.tick() }, this.set.ms);
  }
, retry:	function ()
  {
    // retry next time it is time to poll
    this.state.backoff	= 0;
  }
, quick:	function (nr)
  {
    this.state.quick	= nr<0 ? -1 : nr>0 ? (this.state.wait=0, nr) : 0;
    emit.emit('quick', this.state.quick);
    if (!this.state.ticking)
      this.tick();
  }
, poll:	function ()
  {
//    LOG('backoff', this.state.backoff);
    if (this.state.backoff)
      {
        if (--this.state.backoff > this.state.wait)
          this.state.backoff	= this.state.wait;
        emit.emit('backoff', this.state.backoff);
        return;
      }
    $$$("check",++this.cnt.check + '*');
    ajax.head(subdir(this.name), (...a) => this.check(...a), this.state.last_modified);

    if (++this.state.wait > this.set.maxwait)
      this.state.wait = this.set.maxwait;
    this.state.backoff = this.state.wait;
    emit.emit('wait', this.state.wait);
    emit.emit('backoff', this.state.backoff);
  }
, check:	function (txt, r, stat, l_m)
  {
    var etag = r.getResponseHeader('etag');
    $$$("check", this.cnt.check + '_');
    if (stat==304 && etag == this.state.etag)
      {
        // not modified
        // if we are in quick mode, do the next poll immediately
        // else at the next backoff interval.
        if (this.state.quick>0)
          {
            this.state.wait	= 0;
            // zu unruhig: emit.emit('wait', this.state.wait);
          }
        $$$('lms', stat+'@'+ ++this.state.nomod);
        return;
      }
    if (!l_m)
      {
        // error
        $$$('lms', stat+'?'+ ++this.state.noimg);
        return;
      }
    this.state.etag		= etag;
    this.state.last_modified	= l_m;
    this.state.noimg		= 0;
    this.state.nomod		= 0;

    $$$('lms', stat);
    $$$('refcnt', ++this.cnt.imgs+'*');
    var t = this.name+'?'+stamp();
    IMG(subdir(t)).then(i =>
      {
        show.load(i);
        if (this.state.quick > 0)
          this.quick(this.state.quick-1);
        $$$('refcnt', this.cnt.imgs+'x');
      })

    this.state.backoff++;	// give additional cycle backoff to load pic
    emit.emit('backoff', this.state.backoff);
  }
}

//
// Mouse
//

var mouse =
{ xy_from_event:	e =>
  {
    if (!e) var e = window.event;
    if (e.pageX || e.pageY)
      return [ e.pageX, e.pageY ];
    if (e.clientX || e.clientY)
      return [ e.clientX + document.body.scrollLeft + document.documentElement.scrollLeft,
               e.clientY + document.body.scrollTop  + document.documentElement.scrollTop
             ];
    return [ 0,0 ]
  }
, relative:	(o,e) =>
  {
    var xy = mouse.xy_from_event(e);
    return [ xy[0]-o.offsetLeft, xy[1]-o.offsetTop ];
  }
, move:		function (t, ev)
  {
    var xy = mouse.relative(this,ev);
    $$$('pos',xy[0]+" "+xy[1]);
    if ($('ma').checked)
      req.idle("x="+xy[0]+"&y="+xy[1]);
  }
, click:	function (t, ev)
  {
    var xy = mouse.relative(this,ev);
    var mb = document.getElementsByName('mb');
    var b=0;
    for (var i=mb.length; --i>=0; )
      if (mb[i].checked)
        b |= parseInt(mb[i].value);
    req.req("x="+xy[0]+"&y="+xy[1]+"&b="+b);
  }
};


//
// Canvas
//

var show =
{ init:		function (id)
  {
    this.id	= id;
    this.canvas	= $(id);
    this.orig_	= void 0;
    this.tmp_	= void 0;
    this.greyout= $('greyout');
    EVT(this.canvas, 'click',     mouse.click);
    EVT(this.canvas, 'mousemove', mouse.move);
  }
, load:		function (i)
  {
    var need = true;
    var old = this.current;
    var current = (keep) =>
      {
        if (!need)
          return false;
        if (!keep)
          i.src = '';	// abort request
        if (this.current === current)
          this.current = void 0;
        need = false;
        // cancel out older pictures which are still loading
        if (old) old(false);
        old = void 0;
        return true;
      };
    this.current = current;

    IMG(i).then(img => { if (current(true)) { this.orig_ = img; this.draw() } });
  }
, draw:		function ()
  {
    var	i = this.tmp_ || this.orig_;
    this.canvas.width	= i.naturalWidth;
    this.canvas.height	= i.naturalHeight;
    this.canvas.style.opacity = 1;
    this.canvas.getContext("2d").drawImage(i,0,0);
  }
, grey:		function ()
  {
    if (this.greyout && this.greyout.checked)
      this.canvas.style.opacity = 0.5;
  }
, tmp:		function (flag,i)
  {
    if (flag)
      {
        this.tmp_ = i;
        this.draw();
      }
    else if (this.tmp_ === i)
      {
        this.tmp_ = void 0;
        this.draw();
      }
  }
};

function insertTab(ev)
{
//  xLOG(ev.code);
  if (ev.code != 'Tab' || ev.shiftKey || ev.ctrlKey || ev.altKey)
    return true;

  var p	= this.scrollTop;
  var s	= this.selectionStart;
  var e	= this.selectionEnd;

  this.value = this.value.substr(0,s)+"\t"+this.value.substr(e);
  this.setSelectionRange(s+1,s+1);
  this.focus();

  this.scrolTop	= p;
  ev.preventDefault();
  return false;
}

//
// Macros
//

var macro =
{ id:		'mac'
, selclass:	'sel'
, match:	/^([A-Za-z0-9_].*)\.macro(.*)$/
, ext:		'.macro'
, query:	'r=dir&d=oper'
, init:		function ()
  {
    $('mdef').onkeydown	= insertTab;
    this.was	= '';
    this.wasurl	= '';
    this.sel	= {};
    this.mode	= null;
    emit.register('sel-m', (x,y,s) => this.setup(s));
    this.setup('run');	// assumed, perhaps later we can fix this
  }
, reload:	function ()
  {
    xLOG('mreload');
    this.macros	= {};
    var m = clear(this.id);
    return req.P('exec.php', this.query
    ).then(t =>
      {
        var a = t.split('\n');
        xLOG('mreloaded', a.length);
        var k;
        a.sort();
        for (var u of a)
          if (validfile(u) && (k = this.match.exec(u)))
            {
              var n	= k[1]+k[2];
              var b	= BUTTON(n, SELFCALLwithTHIS(this, 'macroclick'));
              b.realurl = u;
              this.selbutton(b);
              this.macros[n] = b;
              m.appendChild(b);
            }
        return t;
      }
    )
  }
, setup:	function (what)
  {
    xLOG('mset', what);
    if (!('click_'+what in this))
      return BUG('unknown macro function '+what);
    this.mode	= what;
    return this.select();
  }
, click_run:	function (m) { this.toggle(1, m); }
, click_ed:	function (m) { this.toggle(1, m); this.load(m) }
, click_new:	function (m) { this.toggle(1, m); this.load(m) }
, click_del:	function (m) { this.toggle(0, m); }
, getsel:	function (m) { return this.mode=='new' ? 'ed' : this.mode; }
, toggle:	function (radio, id)
  {
    var	s, m=this.getsel(m);

    if (radio || !(s=this.sel[m]))
      s	= [id];
    else
      s	= ArrayToggle(s, id);
    this.sel[m]	= s;
    xLOG('mtoggle', id, s);
    this.select();
  }
, select:	function ()
  {
    for (var b=$(this.id).firstChild; b; b=b.nextSibling)
      this.selbutton(b);
  }
, selbutton:	function (b)
  {
    var m = this.getsel();
    var s = this.sel[m];
    b.classList.toggle(this.selclass, s!=void 0 && s.includes(b.realurl));
//    xLOG('selb', b.realurl, b.classList);
  }
, macroclick: function (button, mouse_ev, ...args)
  {
    xLOG('mc', this.mode, ...args);
    return this['click_'+this.mode].call(this, button.realurl);
  }
, load:		function (url)
  {
    xLOG('mload', url);
    var o = $('mdef');
    return req.P(['','o',url])
    .then(t =>
      {
        if (o.value != t)
          {
            if (o.value != this.was && !confirm('overwrite edit?'))
              return Promise.reject(t);
            o.value	= t;
          }
        return t;
      })
    .then(this.saved.bind(this, url))
  }
, saved:	function (url, data, ...args)
  {
    xLOG('msaved', url, ...args);
    if (url)
      {
        this.wasurl		= url;
        $('mloaded').value	= url;
      }
    if (data)
      this.was	= data;
    return data;
  }
, save:		function (id)
  {
    var name = $(id).value.trim();
    var	k = this.match.exec(name);
    if (k[1]) name	= k[1];

    var data = $('mdef').value;
    xLOG('msave', id, name);
    if (!name)
      cause	= 'no name';
    else if (!data.trim())
      cause	= 'no data';
    else if (this.was == data && name == this.wasurl)
      cause	= 'unchanged';
    else
      return req.P('exec.php', 'r=save&d=oper&f='+escape(name), data)
      .then(this.saved.bind(this, name+this.ext, data))
    out('not saved: '+cause+'!');
    return Promise.reject();
  }
, msave:	function () { this.save('mloaded'); }
, mnew:		function () { this.save('mname').then(this.reload.bind(this)).then(t => Dom.sel('m', 'ed')) }
, mrun:		function (...a) { xLOG('mrun', ...a); }
, mdel:		function ()
  {
    xLOG('mdel:', this.sel['del']);
    var p = [];
    for (var i=this.sel['del'].length; --i>=0; )
      {
        var nam	= this.sel['del'][i];
        var k	= this.match.exec(nam);
        if (!k[1] || k[2]) continue;
        var deleted = (k,n) => t => { xLOG('mdel', k, n, t); return t };
        p[i] = req.P('exec.php', 'r=kick&d=oper&f='+escape(k[1]))
               .then(deleted(k[1], nam));
      }
    return Promise.all(p).then(() => { out('deleted'), this.reload() });
  }
}


//
// Initialization
//

function isSlowMobile()
{
  return navigator && navigator.connection && navigator.connection.effectiveType && navigator.connection.effectiveType<'4g';
}

function init()
{
  out('init failed');

  $('lref').href = subdir('l/');
  $('edit').href = "edit.html?"+conf.targ;

  show.init('show');

  emit.init();
  emit.register('quick', function (v)   { $$$('qrun', v) });
  emit.register('done',  function (r,t,s) { out((s==200 ? 'done' : 'fail'+s)+': '+r.r+' '+t) });
  emit.register('act',   function (r)   { if (!r.cb) show.grey(); out('do: '+r.r) });
  emit.register('wait',  function (w)   { $$$('wait', w) });

  req.init();
  runs.init();
  poller.init(conf.poll).quick(isSlowMobile() ? -1 : conf.quickmode);
  macro.init();

  // improve hoverness
  for (var e of Doms('[title]'))
    {
      var t = e.title;
      EVP(e, 'mouseover', CLOSURE(t => out.tmp(true,  t), t));
      EVP(e, 'mouseout',  CLOSURE(t => out.tmp(false, t), t));
      var f = e.getAttribute('for');
      if (!f) continue;
      EVP(f, 'mouseover', CLOSURE(t => out.tmp(true,  t), t));
      EVP(f, 'mouseout',  CLOSURE(t => out.tmp(false, t), t));
    }

  reload(false);

  out('ok');
}

// chi.nr must be present.
// It is sorted according to that
function placeChild(ob, chi)
{
  for (var n of ob.children)
    if (!('nr' in n) || chi.nr<n.nr)
      {
         ob.insertBefore(chi, n);
         return;
      }
  ob.appendChild(chi);
}

var Assets =
{
  learn: (...a) => Assets.img(...a),
  stat:  (...a) => Assets.img(...a),
  ed:    (...a) => Assets.template(...a),

  img:	(ctx, u) =>
    {
      IMG(i => { i.nr = ++ctx.nr; i.main = ctx.f+'/'+u; ctx.loading(i); return subdir(i.main) })
      .then(i =>
        {
          LOG('asset', ctx.name, i.nr, i.src);
          ctx.loaded(i);
          if (!ctx.current)
            return;

          i.style.border	= "1px dotted white";
          i.style.width		= "100px";

          placeChild(ctx.o, i);

          i.onmouseover	= function () { this.style.opacity=0.5; show.tmp(true,  this); out.tmp(true,  i.nr+' '+i.main) }
          i.onmouseout	= function () { this.style.opacity=1;   show.tmp(false, this); out.tmp(false, i.nr+' '+i.main) }
          i.onclick	= function () { $('learn').value = strCut(u, '.png') }
        });
    },

  template:	(ctx, u) =>
    {
      u = strCut(u, '.tpl');

      LOG('template', ctx.name, u);

      var b = BUTTON(u, e => upd());
      b.setAttribute('class', 'no');

      function upd(quiet)
        {
          req.get(['state.php', u], '', t =>
            {
              t = strCut(t, '\n');
              if (!quiet)
                OUT(t);
              t = strTail(t, '\n');
              b.setAttribute('class', t=='ok' ? 'ok' : 'ko');
            });
        };

      ctx.o.appendChild(b);
      upd(1);
    },
};

class CTX
  {
  constructor(o, name, props)
    {
      this.nr	= 0;
      this.o	= o;
      this.gen	= new Date();
      this._l	= 0;
      this.name	= name;
      this.p	= props;

      if (props && !isString(props))
        for (var p in props)
          this[p] = props[p];

      o.gen	= this.gen;
    }

  get current() { return this.gen === this.o.gen }

  loading(ob)
    {
      if (this._l++ || !this.current) return;
      this._o = DIV('load...');
      this.o.appendChild(this._o);
      xLOG('loading', this.name);
    }

  loaded(ob)
    {
      if (--this._l || !this.current) return;
      this.o.removeChild(this._o);
      delete this._o;
      xLOG('loaded', this.name);
    }

  load(dir)
    {
      this.loading(dir);
      return req.P('exec.php', 'r=dir&d='+dir)
             .then(t => { later(t => this.loaded(dir)); return t })
    }
  }

var $showdel;

function reload(ev)
{
  var assets = { l:'learn', s:'stat', t:'ed' };

  $showdel	= $('showdel');
  macro.reload();

  var f = $$('reload');
  if (ev=='next')
    {
      var t = f;
      f = null;
      for (var x in assets)
        {
          if (t==x)
            {
              t	= null;
              continue;
            }
          if (!t)
            {
              f	= x;
              break;
            }
          if (!f)
            f	= x;
        }
      $$$('reload', f);
    }

  var a = assets[f];
  var ctx = new CTX(clear('cit'), a, {f:f});

  ctx.load(a).then(t =>
    {
      var s = t.split('\n');
      s.sort();
      for (var u of s)
        if (validfile(u))
          Assets[a](ctx, u);
    }
  );

}

function validfile(u)
{
  if (!u) return false;
  return u.indexOf('~')<0 ? true : $showdel.checked;
}

onready(init);

