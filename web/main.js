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

function clicks(e, click) { e=$(e); e.onclick=click; return e }
function TEXT(x) { return document.createTextNode(x); }
function TEXTe(x) { return typeof x=='string' ? TEXT(x) : x; }
function DOMs(sel)	{ return document.querySelectorAll(sel) }
function DOMe(e, child, attr)
{
  e = document.createElement(e);
  if (child)
    for (let x of mkArray(child))
      e.appendChild(TEXTe(x));
  if (attr)
    for (let x in attr)
      e.setAttribute(x, attr[x]);
  return help(e);
}

function DIV(inner, attr) { return DOMe('div', inner, attr) }
function BUTTON(inner, click, attr) { return clicks(DOMe('button', inner, attr), click) }

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
  let t;

  try { t=JSON.stringify(s); } catch (e) {}
  s = String(s);
  if (s==t || t===undefined)
    return s;
  const g = quote(s);
  const q = '"'+g+'"';
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
    let e = $(this.el);
    if (e) e.innerText = this.hist.join('\n');
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

function strCut(s, at) { const n = s.length-at.length; return n>=0 && s.substr(n)==at ? s.substring(0,n) : s }	// remove last
function strCutAt(s, at) { const n = s.indexOf(at); return n>=0 ? s.substring(0,n) : s }			// remove upto first
function strTail(s, at) { const n = s.lastIndexOf(at); return n>=0 ? s.substring(n+1) : s }			// remove until last

function BUG(x) { const f=function () { alert(x); return false; }; f(); return f }

function dump(x)
{
  let s="";
  for (let n in x) { const v=x[n]; if (typeof(v)=="function") continue; s+=n+"="+x[n]+"\n"; }
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
  if (!e) return e;
  e=$(e);
  while (e.firstChild)
    e.removeChild(e.firstChild);
  if (c)
    e.appendChild(c);
  return e;
}

// IMG(URL): create image from URL
// If URL is a function it is called and the return is taken as URL
// If URL is a string, this is set as the IMG.src
// Else the URL is taken as is (it must be an IMG)
function IMG(url)
{
  const img = DOMe('img');

  if (typeof url == 'function')
    url	= url(img);

  if (typeof url == 'string')
    {
      LOG('img', url);
      img.src	= url;
      return img;
    }

  return url.tagName == 'IMG' ? url : void 0;
}

// IMGp: Create a Promise which resolves when the image is loaded
// IMGp(img).then(img => { success }, img => { fail }).then(...)
// Why not something like bfred-it/image-promise?  Because it cannot do functions ..
// See: https://github.com/bfred-it/image-promise/blob/master/index.js
function IMGp(url)
{
  const img	= IMG(url);

  if (!img) return Promise.reject();

  const ret = new Promise((ok,ko) =>
    {
      const done = () =>
        {
          img.removeEventListener('load', done);
          img.removeEventListener('error', done);
          if (img.naturalWidth) { LOG('img ok',img.src); ok(img) } else { LOG('img err', img.src); ko(img) }
        };

      img.addEventListener('load', done);
      img.addEventListener('error', done);
      if (img.complete)
        done();
    });

  ret.img	= img;
  return ret;
}

function clone(e)
{
  const o = e.cloneNode(true);

  o.onload	= e.onload;
  o.onerror	= e.onerror;
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
// capture=true:	Receives event in capture phase
// passive=true:	Function never calls preventDefault()
function EVP(e, ons, fn)
{
  if (!e) return e;
  e = $(e);
  for (let l of mkArray(ons))
    e.addEventListener(l, CLOSURE(fn, l), {passive:true, capture:true});
  return e;
}

// Register active Event
// capture=false:	Receives event in bubbling phase
// passive=false:	Function may call preventDefault()
function EVT(e, ons, fn)
{
  if (!e) return e;
  e = $(e);
  for (let l of mkArray(ons))
    e.addEventListener(l, CLOSURE(fn, l), {passive:false, capture:false});
  return e;
}

function hover(e, t)
{
  if (!e) return e;
  e = $(e);
  EVP(e, 'mouseover', CLOSURE(t => out.tmp(true,  t), t));
  EVP(e, 'mouseout',  CLOSURE(t => out.tmp(false, t), t));
  return e;
}

function help(e)
{
  e = $(e);
  if (e.title)
    hover(hover(e, e.title).getAttribute('for'), e.title);
  return e;
}

function ArrayToggle(arr, val)
{
  xLOG("toggle", val, arr);
  for (let i=arr.length; --i>=0; )
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
      for (let f of this.emits[what])
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
    const f = (...b) => { if (cb(...a,...b)===this.STOP) this.emits[what].remove(f) };
    this.emits[what].push(f);
    return this;
  }
};


//
// Backend-Calls
//
// url = [ prefix, path, path ];
//
// req.P(url, query)		Promise for req.get, resolves when got
// req.P(url, query, postdata)	Promise for req.get, resolves when got
//
// req.get(url, query-string, callback, callback-args)
//	runs callback(response, callback-args)
//	failure: response is undefined
// req.post(url, query-string, postdata, callback, callback-args)
//	same as req.get but uses POST
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
    if (this.active)
      return this;

    let r;
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

    const q	= ['nocache='+stamp()];
    const u	= Array.from(r.u);
    if (u[0]=='')
      u[0]	= conf.targ;
    else if (u[0].slice(-1) != '?')
      u.splice(1, 0, conf.targ);

    if (r.r)
      q.push.apply(q, mkArray(r.r));

    let p	= u.join('/');
    if (q)
      p += '?'+q.join('&');

    if (r.post)
      ajax.push(p, (t,x,s) => this.done(r, t, s), r.post);
    else
      ajax.get(p, (t,x,s) => this.done(r, t, s));
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
    const cb=(t,s,o) => { if (s==200) ok(o); else ko(o) };
    if (post)
      this.post(u,r,post,cb);
    else
      this.get (u,r,     cb);
  })}
};

//
// Dom helper
//
// XXX TODO SMELL: var refactoring
//
var Dom =
{ dummy: 1
, sel:	function (tag, sel, ...args)
  {
    xLOG('dom.sel1', tag, sel, args);

    var att = 'data-sel-'+tag;
    var m = DOMs('['+att+']');
    var current = 0, togo=-1;

    for (let i=m.length; --i>=0; )
      {
        if (!m[i].classList.contains('hide'))
          current	= i;
        if (sel && m[i].getAttribute(att) == sel)
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

    sel = m[togo].getAttribute(att);
//    xLOG('dom.sel3', tag, current, togo, sel, args);

    var att = 'data-xsel-'+tag;
    var m = DOMs('['+att+']');
    for (let i=m.length; --i>=0; )
      {
        if (m[i].getAttribute(att) == sel)
          m[i].classList.add('sel');
        else
          m[i].classList.remove('sel');
      }

    emit.emit('sel', tag, sel, current, togo, ...args);
    emit.emit('sel-'+tag, sel, current, togo, ...args);

    return m[current].getAttribute(att);
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
    for (let e of DOMs('['+attrib+']'))
      e.onclick = this.click(e.getAttribute(attrib));
  }
, click:	function (str)
  {
    const w = (''+str).split(' ');
    {
    const i = 'run_'+w.shift();
    if (i in this)	return CLOSURE_(this[i], [w]);
    }
    {
    const i	= parseInt(str);
    if (i>0)	return () => { req.code(i); return false };
    }
    if (str.substr(0,1)=='K') return () => { req.key(str.substr(1)); return false };
    if ($(str))	return () => { req.send(str); return false };

    return BUG('bug: undefined functionality: '+str);
  }
, run_sel:	function (args, ev) { Dom.sel(args[0], args[1], ev); }
, run_reload:	reload
, run_cmd:	function (args) { req.get(['ping.php', args[0]], ''); }
, run_quick:	function () { poller.quick(poller.state.quick>0 ? -1 : poller.state.quick<0 ? 0 : conf.quick) }
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
    const etag = r.getResponseHeader('etag');
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
    const t = this.name+'?'+stamp();
    IMGp(subdir(t)).then(i =>
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
    if (!e) e = window.event;
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
    const xy = mouse.xy_from_event(e);
    return [ xy[0]-o.offsetLeft, xy[1]-o.offsetTop ];
  }
, move:		function (t, ev)
  {
    const xy = mouse.relative(this,ev);
    $$$('pos',xy[0]+" "+xy[1]);
    if ($('ma').checked)
      req.idle("x="+xy[0]+"&y="+xy[1]);
  }
, click:	function (t, ev)
  {
    const xy = mouse.relative(this,ev);
    const mb = document.getElementsByName('mb');
    let b=0;
    for (let i=mb.length; --i>=0; )
      if (mb[i].checked)
        b |= parseInt(mb[i].value);
    req.req("x="+xy[0]+"&y="+xy[1]+"&b="+b);
  }
};


//
// Canvas
//

// const show .. cannot be used, as "show" already referenced in poller
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
    let need = true;
    let old = this.current;
    const current = (keep) =>
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

    IMGp(i).then(img => { if (current(true)) { this.orig_ = img; this.draw() } });
  }
, draw:		function ()
  {
    const	i = this.tmp_ || this.orig_;
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

  const p	= this.scrollTop;
  const s	= this.selectionStart;
  const e	= this.selectionEnd;

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
, match:	/^([,A-Za-z0-9_].*)\.macro(.*)$/
, ext:		'.macro'
, query:	'r=dir&d=oper'
, init:		function ()
  {
    $('mdef').onkeydown	= insertTab;
    this.was	= '';
    this.wasurl	= '';
    this.sel	= {};
    this.args	= {};
    this.mode	= null;
    emit.register('sel-m', s => this.setup(s));
    this.setup('run');	// assumed, perhaps later we can fix this
  }
, reload:	function ()
  {
    xLOG('mreload');
    const ctx	= new CTX(clear(this.id), 'macros');
    ctx.load('exec.php', this.query)
    .then(t =>
      {
        this.macros = {};

        const	a = t.split('\n');
        xLOG('mreloaded', a.length);
        a.sort();

        let k;
        for (let u of a)
          if (validfile(u) && (k = this.match.exec(u)))
            {
              const b	= BUTTON(k[1]+k[2], SELFCALLwithTHIS(this, 'macroclick'), {title:u});
              b.realurl	= u;
              this.macros[u] = b;
              ctx.child(b);
            }

        this.select();
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
, click_run:	function (m)
  {
    const old = this.toggle(1, m)[0];
    const now = this.sel['run'][0];
    if (old && now && old!=now)
      {
        const e = $('mrun');
        this.args[old]	= e.value;
        e.value		= this.args[now] || '';
      }
  }
, click_ed:	function (m) { this.toggle(1, m); this.load(m) }
, click_new:	function (m) { this.toggle(1, m); this.load(m) }
, click_del:	function (m) { this.toggle(0, m); }
, getsel:	function () { return this.mode=='new' ? 'ed' : this.mode; }
, toggle:	function (radio, id)
  {
    const m	= this.getsel();
    const old	= this.sel[m];
    const s	= (radio && old && old[0]!=id) ? [id] : ArrayToggle(old, id);

    this.sel[m]	= s;
    xLOG('mtoggle', id, s);
    this.select();
    return old;		// only returns old with radio
  }
, select:	function ()
  {
    // Remove unknown macros from selection
    const	m = this.getsel();
    const	s = this.sel[m];
    const	t = [];
    if (s)
      for (let u of s)
        if (u in this.macros)
          t.push(u);
    this.sel[m]	 = t;

    // Highlight selection again
    for (let b=$(this.id).firstChild; b; b=b.nextSibling)
      b.classList.toggle(this.selclass, t && t.includes(b.realurl));
  }
, macroclick: function (button, mouse_ev, ...args)
  {
    xLOG('mc', this.mode, ...args);
    return this['click_'+this.mode].call(this, button.realurl);
  }
, load:		function (url)
  {
    xLOG('mload', url);
    const o = $('mdef');
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
, getname:	function (n) { n=n.trim(); const k = this.match.exec(n); return k && k[1] ? k[1] : n; }
, save:		function (id)
  {
    const name = this.getname($(id).value);
    const data = $('mdef').value;

    xLOG('msave', id, name);
    let	cause;
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
, mrun:		function ()
  {
    const u	= this.getname(this.sel['run'][0]);
    xLOG('run',u);
    return req
      .P(['macro.php', u], '', $('mrun').value)
      .then(t => { xLOG('ran',u,t); out('macro',u,t); return t; })
      .then(t => { if (poller.state.quick>=0 && poller.state.quick<conf.quickmode) poller.quick(conf.quickmode); return t })
  }
, mdel:		function ()
  {
    xLOG('mdel:', this.sel['del']);
    const p = [];
    for (let i=this.sel['del'].length; --i>=0; )
      {
        const nam	= this.sel['del'][i];
        const k		= this.match.exec(nam);
        if (!k[1] || k[2]) continue;

        const deleted	= (k,n) => t => { xLOG('mdel', k, n, t); return t };

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

function href(el, dest)
{
  const e	= $(el);

  e.href	= dest;
  e.target	= el+'-'+conf.targ;
}

var Assets =
{
  generation: 0,

  learn: (...a) => Assets.img(...a),
  stat:  (...a) => Assets.img(...a),
  ed:    (...a) => Assets.template(...a),

  mouseover:	function() { this.style.opacity=0.5; show.tmp(true,  this); out.tmp(true,  this.main) },
  mouseout:	function() { this.style.opacity=1;   show.tmp(false, this); out.tmp(false, this.main) },
  click:	function() { $('learn').value = this.u },

  img:	function(ctx, u)
    {
      if (!ctx.current)
        return;

      const nr	= ctx.nr;
      const l	= ctx.loading(nr);

      // XXX TODO BUG #Asset.generation does not work in Chrome
      // The idea now is to:
      // - create the image
      // - refresh the image using iframe trick https://stackoverflow.com/a/40032192/490291
      IMGp(i => { i.u = strCut(u, '.png'); i.main = ctx.f+'/'+u; return subdir(i.main)+'#'+ ++Assets.generation })
      .then(i =>
        {
          LOG('asset', ctx.name, nr, i.src);

          i.style.border	= "1px dotted white";
          i.style.width		= "100px";
          i.onmouseover	= this.mouseover;
          i.onmouseout	= this.mouseout;
          i.onclick	= this.click;

          ctx.child(i, nr);
        })
      .finally(i => ctx.loaded(l));
    },

  template:	(ctx, u) =>
    {
      if (!ctx.current)
        return;

      u = strCut(u, '.tpl');

      LOG('template', ctx.name, u);

      var b = BUTTON(u, e => upd(), {'class':'no'});

      function upd(quiet)
        {
          b.setAttribute('class', 'no');
          ctx.load(['state.php', u])
            .then(t =>
              {
                t = strCut(t, '\n');
                if (!quiet)
                  OUT(t);
                t = strTail(t, '\n');
                b.setAttribute('class', t=='ok' ? 'ok' : 'ko');
              });
        };

      ctx.child(b)
      upd(1);
    },
};

/* CTX: asynchronously update ordered children of elements
 *
 * There can only be one context on an element!
 * (The most current context takes the element.)
 *
 * ctx = CTX(element, name, properties);
 * ctx.load() triggers "loading"
 * ctx.load(...args-of-req.P)
 *    .then(result => { ctx.child(child(result), ctx.nr) }
 *
 * slot = ctx.loading()
 * do_the_load();
 * ctx.loaded(slot);
 *
 * You can order children based on the number or anything else.
 * You can do DOM manipulations.
 *
 * Also I found something which I think is a bug:
 * WekMap() does not work with DOM object.
 */
const $mapkey = '_ctx';

class CTX
  {
  constructor(o, name, props)
    {
      this._nr	= 0;
      this._l	= 0;
      this._o	= o;
      this._q	= Promise.resolve();
      this.gen	= new Date();
      this.name	= name;
      this.p	= props;

      if (props && !isString(props))
        for (let p in props)
          this[p] = props[p];

      o.gen	= this.gen;
    }

  get current() { return this.gen === this._o.gen }
  get nr() { return ++this._nr }

  // Child is sorted on nr, which can be anything except undefined
  // IF NR Is left away (undefined), the next ctx.nr is used
  // ==> nr assigned to the child
  child(chi, nr)
    {
      if (nr === void 0)
        nr	= this.nr;
      chi[$mapkey]	= nr;
      if (!this.current || this._o.contains(chi))
        {
          xLOG('chi-nope', nr)
          return nr;
        }

      let last;

      for (let n of this._o.children)
        {
          const k = n[$mapkey];
          if (k === nr)
            {
              this._o.replaceChild(chi, n);
              return nr;
            }
          if (k !== void 0 && nr < k)
            {
              last = n;
              break;
            }
        }

//      LOG('chib', nr, last ? last[$mapkey] : void 0);
      this._o.insertBefore(chi, last);
      return nr;
    }

  loading(what)
    {
      if (this._l++ || !this.current || this._o.contains(this._hint)) return void 0;

      this._hint	= DIV('...loading...');
      this._o.appendChild(this._hint);
      xLOG('loading', this.name);
      return 1;
    }

  loaded(idx)
    {
      // idx currently ignored
      if (--this._l || !this.current) return void 0;
      later(() =>
        {
          if (this._l || !this._hint) return;
          this._o.removeChild(this._hint);
          delete this._hint;
          xLOG('loaded', this.name);
        });
    }

  load(...args)
    {
      const slot	= this.loading();
      return req.P(...args)
             .then(t => { this.loaded(slot); return this.current ? t : Promise.reject('no more current') })
    }
  }

function next_in(is, a)
{
  let def;

  def	= void 0;
  for (let x in a)
    {
      if (def === void 0)
        def	= x;		// preset first into f
      if (is === x)
        is	= void 0;	// trigger set of next (or return first)
      else if (is === void 0)
        return x;
    }
  return def;
}

function next_of(is, a)
{
  let def;

  def	= void 0;
  for (let x of a)
    {
      if (def === void 0)
        def	= x;		// preset first into f
      if (is === x)
        is	= void 0;	// trigger set of next (or return first)
      else if (is === void 0)
        return x;
    }
  return def;
}

let $showdel;

function reload(ev)
{
  const assets = { l:'learn', s:'stat', t:'ed' };

  $showdel	= $('showdel');
  macro.reload();

  let f = $$('reload');
  if (ev=='next')
    f = next_in(f, assets);
  $$$('reload', f);

  var a = assets[f];
  var ctx = new CTX(clear('cit'), a, {f});

  ctx.load('exec.php', 'r=dir&d='+a)
   .then(t =>
     {
       let s = t.split('\n');
       s.sort();
       for (let u of s)
         if (validfile(u))
           Assets[a](ctx, u);
     }
   );
  layout();
}

function layout()
{
  return req.P('layout.json?')
   .then(j => JSON.parse(j))
   .then(o =>
     {
//       var was = Dom.sel('b', 'x');
       // XXX TODO SMELL
       new Layout('b').clear(o);
//       Dom.sel('b', was);
     })
   .catch(e => { emit.emit('err','layout', e, e.stack) })
}

function deep_replace(arr, str, val)
{
  function step(arr)
    {
      let t = typeof arr;

      if (t == 'string')
        return arr.split(str).join(val);
      if (Array.isArray(arr))
        {
          t = [];
          for (let e of arr)
            t.push(step(e));
          return t;
        }
      if (t !== 'object')
        return t;
      else
        {
          t = {};
          for (let e in arr)
            t[step(e)]=step(arr[e]);
          return t;
        }
    }
  return step(arr);
}

class Layout
{
  constructor(layout)
    {
      this.layout	= layout;
      this.b		= $('layout-'+layout);
      this.e		= $('layout_'+layout);
    }

  // XXX TODO SMELL
  clear(o) { clear(this.b); clear(this.e); this.add(o); globals() }

  add(o)
    {
      for (var a of o)
        {
          var t = a[0];
          if (this.b)
             this.b.appendChild(BUTTON(t, runs.click('sel '+this.layout+' '+t), {['data-xsel-'+this.layout]: t, title:a[1]}));
          var f = 'l_'+a[2];
          if (! f in this)
            throw 'Layout '+f+' is missing';
          this.e.appendChild(DIV(this[f](a.slice(3)), {['data-sel-'+this.layout]:t}));
          if (!this.b)
            break;
        }
    }

  l_table(o)
    {
      var rows = [];
      function mkRow(row)
        {
          let cols = [];
          for (let col of row)
            {
              let attr = void 0;
              if (typeof col!='string')
                {
                  attr = {}
                  if ('v' in col) attr['data-var'] = String(col['v']);
                  if ('m' in col) attr['data-var-m'] = String(col['m']);
                  if ('s' in col) attr['data-var-s'] = String(col['s']);
                  col='?';
                }
              cols.push(DOMe('td', col, attr));
            }
          rows.push(DOMe('tr', cols, {'class':'hi'}));
        }
      for (let row of o)
        if (Array.isArray(row))
          mkRow(row);
        else
          for (let i of row['i'])
            {
              const x = deep_replace(row['t'], row['k'], i);
              //console.log(x);
              mkRow(x);
            }
      return DOMe('table', rows, {'class':'b1'});
    }
}

function globals()
{
  return req.P(['','globals.json'])
    .then(j => JSON.parse(j))
    .then(o => new Globals(o))
    .then(o => emit.emit('globals', o))
    .then(o => 'ok')
    .catch(e => { emit.emit('err','globals', e, e.stack); return 'err' })
    .then(o => xLOG('globals loaded', o))
}

class Globals
{
  constructor(g)
    {
      this.g	= g;
      this.p	= Promise.resolve();
      for (let d of DOMs('[data-var]'))
        {
          const f = d.getAttribute('data-var-m');
          const i = d.getAttribute('data-var-i');
          const s = d.getAttribute('data-var-s');
          let n = d.getAttribute('data-var');
          let v = g['global.'+n];
          if (s)
            {
              n = s.replace(/[{][?][}]/g, v);
              v = g['global.'+n];
              if (!v)
                v = '?';
            }
          const m = `v_${f}`;
          if (!f)
            clear(d, hover(DIV(v), n));
          else if (m in this)
            this[m](d, v, n);
          else
            throw 'missing globals handling >'+f+'<';
        }
    }

  v_if(d, v, n)
    {
      if (v)
        {
          clear(d, hover(DIV(v), n));
          d.parentElement.classList.remove('hide');
        }
      else
        d.parentElement.classList.add('hide');
    }

  v_pm(d, v, n)
    {
      var self = this;

      clear(d, EVT(hover(DIV(v, {'class':'hi2'}), 'l/m/r=inc/0/dec shift=10 '+n),
        ['contextmenu', 'mousedown', 'mouseup'],
        function (m,e)
          {
            e.preventDefault();
            if (m!='mouseup')
              return;

//            xLOG('incdec', e.button, n, this.innerText, String(e));
            self.p = self.p.finally(() =>
              {
                var c = parseInt(this.innerText);
                if (!c) c=0;
                var [i,k] = e.shiftKey ? [10,10] : [1, c ? 0 : 1];
                switch (e.button)
                  {
                  default: return;
                  case 0:	k = c+i; break;
                  case 2:	k = c-i; break;
                  case 1:	break;
                  }
                if (k<0) k=0;
                xLOG('incdec', e.button, n, c, k);
                return req
                  .P(['macro.php', 'glob'], '', `global.${n} ${c} ${k}`)
                  .then(t =>
                    {
                      t = t.trim();
                      let x = parseInt(t);
                      if (t != `${x}`)
                        throw 'wrong response: '+t;
                      this.innerText = t;
                      xLOG('incdec', e.button, n, c, k, 'ok', x);
                    })
                  .catch(r => xLOG('incdec', e.button, n, c, k, 'error', r))
              });
          }));
    }
}

function validfile(u)
{
  if (!u) return false;
  return u.indexOf('~')<0 ? true : $showdel.checked;
}

