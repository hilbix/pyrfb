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


// https://stackoverflow.com/a/17772086/490291
['Arguments', 'Function', 'String', 'Number', 'Date', 'RegExp'].forEach(
  n => window[`is${n}`] = o => toString.call(o) == `[object ${n}]`
);

function later(fn, ...a) { setTimeout(() => fn(...a)) }

function strCut(s, at) { var n = s.length-at.length; return n>=0 && s.substr(n)==at ? s.substring(0,n) : s }
function strCutAt(s, at) { var n = s.indexOf(at); return n>=0 ? s.substring(0,n) : s }


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


//
// Config
//

if (!document.location.search && document.referrer && document.referrer.startsWith(document.location.href))
  document.location.replace(document.location.href+'?'+parseInt(document.referrer.substr(document.location.href.length)));

var conf = {}

conf.n		= parseInt(window.location.search.substr(1));
conf.quick	= 100;		// count
conf.poll	= 200;		// ms
conf.maxwait	= 1000000;	// ms
conf.sleep	= 6;
conf.targ	= ''+conf.n+'';
conf.dir	= conf.targ+'/';

function subdir(s) { return conf.dir+s }


//
// Base classes
//

// emit class

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
, register:	function (what, cb, ...a)
  {
    if (!(what in this.emits))
      this.emits[what]	= [];
    var f = (...b) => { if (cb(...a,...b)===this.STOP) this.emits[what].remove(f) };
    this.emits[what].push(f);
    return this;
  }
, bound:	function (what, that, cb, ...a)
  {
    return this.register(what, cb.bind(that), ...a);
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
, get:		function (u,r,cb,...a) { this.reqs.push({u:mkArray(u), r:r, cb:cb, a:a}); return this.next() }
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
    u.splice(1, 0, conf.targ);
    ajax.get(u.join('/')+'?nocache='+stamp()+(r.r?'&'+r.r:''), (t,x,s) => this.done(r, t, s));
    return this;
  }
, done:		function (r, t, s)
  {
    this.active	= false;
    emit.emit('done', r, t, s);
    if (r.cb)
      r.cb(t, ...r.a);
    return this.next();
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
    if (i in this)	return CLOSURE_(this[i], w);

    i	= parseInt(str);
    if (i>0)	return () => { req.code(i); return false };
    if (str.substr(0,1)=='K') return () => { req.key(str.substr(1)); return false };
    if ($(str))	return () => { req.send(str); return false };

    return BUG('bug: undefined functionality: '+str);
  }
, run_quick:	function () { poller.quick(poller.state.quick ? 0 : conf.quick) }
, run_learn:	function () { req.send('learn', 'l'); return false }
, run_reload:	reload
, run_msel:	function ()
  {
    var m = Doms('[data-msel]');
    var h = 0, s = 0;
    for (var i=m.length; --i>=0; )
      if (m[i].contains(this))
        {
          h = i;
          s = i+1;
          break;
        }
    m[h].classList.add('hide');
    m[s<m.length ? s : 0].classList.remove('hide');
  }
, run_cmd:	function (cmd)
  {
    req.get(['ping.php', cmd], '');
  }
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
    this.state	= { nomod:0, noimg:0 };
    this.set	= {};
    this.speed(ms);
    this.reset();
    this.start();
    emit.bound('fin', this, this.reset);
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
    if (this.state.stopped)
      {
        this.state.started	= false;
        return;
      }
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
    this.state.quick	= nr>0 ? (this.state.wait=0, nr) : 0;
    emit.emit('quick', this.state.quick);
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
    $$$("check", this.cnt.check + '_');
    if (stat==304)
      {
        // not modified
        // if we are in quick mode, do the next poll immediately
        // else at the next backoff interval.
        if (this.state.quick)
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
    this.state.last_modified	= l_m;
    this.state.noimg		= 0;
    this.state.nomod		= 0;

    $$$('lms', stat);
    $$$('refcnt', ++this.cnt.imgs+'*');
    var t = this.name+'?'+stamp();
    IMG(subdir(t)).then(i =>
      {
        show.load(i);
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


//
// Macros
//

var macro =
{ id:		'mac'
, query:	'r=oper'
, init:		function ()
  {
    var m = clear(this.id);
    req.get('exec.php', this.query, t =>
      {
        var a = t.split('\n');
        var r = /^([A-Z0-9].*)\.macro/;
        var k;
        a.sort();
        for (var u of a)
          if (k = r.exec(u))
            m.appendChild(BUTTON(k[1], SELFCALLwithTHIS(this, 'macroclick')))
      }
    );
  }
, macroclick: function (el, e)
  {
    ;
  }
}


//
// Initialization
//

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
  poller.init(conf.poll).quick(conf.quick);

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
  dir:   (...a) => Assets.template(...a),

  img:	(ctx, u) =>
    {
      if (u.indexOf('~')>=0) return;
      IMG(i => { i.nr = ++ctx.nr; i.main = ctx.f+'/'+u; ctx.loading(i); return subdir(i.main) })
      .then(i =>
        {
          LOG(ctx.name, i.nr, i.src);
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

      LOG(ctx.name, u);

      var b = BUTTON(u, e => upd());
      b.setAttribute('class', 'no');

      function upd(quiet)
        {
          req.get(['state.php', u], '', t =>
            {
              t = strCutAt(t, '\n');
              if (!quiet)
                OUT(t);
              b.setAttribute('class', t=='ko' ? 'ko' : 'ok');
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
      out(`loading ${this.name}`);
    }

  loaded(ob)
    {
      if (--this._l || !this.current) return;
      this.o.removeChild(this._o);
      delete this._o;
      out(`loaded ${this.name}`);
    }
  }

function reload(e)
{
  macro.init();

  var assets = { l:'learn', s:'stat', t:'dir' };

  var f = $$('reload');
  if (e)
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

  req.get('exec.php', 'r='+a, t =>
    {
      var s = t.split('\n');
      s.sort();
      for (var u of s)
        if (u)
          Assets[a](ctx, u);
    }
  );

}

onready(init);

