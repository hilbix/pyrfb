"use strict";

// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

// These functions should go into a lib

var STOP = [ "STOP" ];

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
  // console.log(...a)
}

// run an object if it is ok or error
function run(o) { var r=o.runner; if (r && (o.err || o.ok)) { o.runner=undefined; r.call(o) } }
function runit(o, r) { o.run = r; run(o) }

// create an Image which tracks it's state
function image(url)
{
  var i		= document.createElement('img');

  i.run		= undefined;
  i.onload	= function () { this.ok=1;  run(this); LOG('img loaded', url) }
  i.onerror	= function () { this.err=1; run(this); LOG('img error', url) }
  i.run		= function (fn) { var l=this.runner; this.runner=(l ? function() { l.call(this); fn.call(this) } : fn); run(this) }
  i.src		= sub(url);

  return i;
}

function clone(i)
{
  var o = i.cloneNode(true);

  o.onload	= i.onload;
  o.onerror	= i.onerror;
  o.run		= i.run;
  o.err		= i.err;
  o.ok		= i.ok;
  return o;
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

function sub(s) { return conf.dir+s }


//
// Base classes
//

// emit class

var emit =
{ init:		function ()
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
    var f = function (...b) { if (cb(...a,...b)===STOP) this.emits[what].remove(f) };
    this.emits[what].push(f);
    return this;
  }
, bound:	function (what, that, cb, ...a)
  {
    return this.register(what, cb.bind(that), ...a);
  }
};


//
// Initialization and global callbacks
//

function newinit()
{
  emit.init();
  emit.register('quick', function (v)   { $('qrun').value = v });
  emit.register('done',  function (r,t) { out('done: '+r+' '+t) });
  emit.register('act',   function (r)   { greyi(); out('do: '+r) });

  req.init();
  runs.init();
  poller.init(conf.poll).quick(conf.quick);
}

//
// Backend-Calls
//

var req =
{ url:		'click.php/'
, init:		function ()
  {
    this.reqs	= [];
    this.active	= false;
    this.cnt	= { req:0 };
    return this;
  }
, send:		function (id,t) { return this.req((t?t:'t')+'='+escape($(id).value)) }
, code:		function (c)    { return this.req(         'c='+escape(c)) }
, req:		function (s)    { this.reqs.push(s); return this.next(); }
, next:		function ()
  {
    if (this.active)
      return this;

    do
      {
        if (!this.reqs.length)
          {
            emit.emit('fin');
            return;
          }
        var r = this.reqs.shift();
      } while (r===void 0);

    this.active	= true;
    this.cnt.req++;
    emit.emit('act', r);
    ajax.get(this.url+'/'+conf.targ+'?decache='+stamp()+'&'+r, t => this.done(r, t));
    return this;
  }
, done:		function (...a)
  {
    this.active	= false;
    emit.emit('done', ...a);
    // sleeps = 0; sleeper = 0;
    return this.next();
  }
};


//
// Click handling
//

var runs =
{ attribute:	'runs'
, init:		function (attrib)
  {
    if (!attrib) attrib = this.attribute;
    for (var e of document.querySelectorAll('['+attrib+']'))
      e.onclick = this.click(e.getAttribute(attrib));
  }
, click:	function (str)
  {
    var i = 'run_'+str;
    if (i in this)	return this[i];

    i	= parseInt(str);
    if (i>0)	return () => { req.req("c="+escape(str)); return false };
    if ($(str))	return () => { req.send(str); return false };

    return BUG('bug: undefined functionality: '+r);
  }
, run_quick:	function () { poller.quick(poller.state.quick ? 0 : conf.quick) }
, run_learn:	function () { send('learn', 'l'); return false }
};


//
// Poller
//
// The poller logic was complex,
// so better to encapsulate,
// so source explains itself a bit better.

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
, quick:	function (value)
  {
    this.state.quick	= value>0 ? value : 0;
    emit.emit('quick', this.state.quick);
  }
, poll:	function ()
  {
    LOG('backoff', this.state.backoff);
    if (this.state.backoff)
      {
        this.state.backoff--;
        return;
      }
    $$$("check",++this.cnt.check + '*');
    ajax.head(sub(this.name), (...a) => this.check(...a), this.state.last_modified);

    if (++this.state.wait > this.set.maxwait)
      this.state.wait = this.set.maxwait;
    this.state.backoff = this.state.wait;
    LOG('wait', this.state.wait);
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
          this.state.wait	= 0;
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
    $$$("refcnt", ++this.cnt.imgs+'*');
    var t = this.name+'?'+stamp();
    LOG("show", t);
    show(image(t)).run(() => // no image(sub(t)) here
      {
        this.quick(this.state.quick-1);
        $$$("refcnt", this.cnt.imgs+'x');
      });

    this.state.backoff++;	// give additional cycle backoff to load pic
  }
}

//window.setTimeout(function () { poller.stop() }, 10000);







//
// Things below should be reworked
//



var nr=0;
function out(s)
{
  $$$("cnt",nr);
  $$$("txt",s);
}

function mousexy(e)
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

function elxy(o,e)
{
  var xy = mousexy(e);
  return [ xy[0]-o.offsetLeft, xy[1]-o.offsetTop ];
}

var loadn=0;

// Image is loaded, show it if it is still shown
function loadi()
{
  if (this.err)
    return;

  this.style.opacity	= 1;
  if (this === shown)
    show();
}

function greyi()
{
  if ($('uihelper').checked)
    return;

  var	e = $('shower');

  if (e.firstChild)
    e.firstChild.style.opacity = 0.5;
}

var sleeps = 0;
var sleeper = 0;
var defsleep = conf.sleep;
var maxsleep = defsleep;


function clicki(ev)
{
  var mb = document.getElementsByName("mb");
  var b=0;
  for (var i=mb.length; --i>=0; )
    if (mb[i].checked)
      b |= parseInt(mb[i].value);
  var xy = elxy(this,ev);
  req.req("x="+xy[0]+"&y="+xy[1]+"&b="+b);
}

function movei(ev) { var xy = elxy(this,ev); $$$("pos","x="+xy[0]+" y="+xy[1]) }

var shown;
function show(i)
{
  if (i)
    {
      i.style		= "";
      i.style.position	= "absolute";
      i.style.top	= "0px";
      i.style.left	= "0px";
      i.onclick		= clicki;
      i.onmousemove	= movei;

      shown = i;
      i.run(loadi);
      return i;
    }

  var e = $('shower');
  e.style.width		= ""+shown.width+"px";
  e.style.height	= ""+shown.height+"px";

  // avoid flicker:
  // never remove probably currently showing image in this round
  if (e.firstChild != e.lastChild)
    e.removeChild(e.firstChild);

  if (e.firstChild != shown)
    e.appendChild(shown);
}

var was;

function ovr()
{
  if (!this.ok || this.err)
    return;

  was	= shown;

  show(clone(this));

  this.style.opacity = 0.5;
}

function init()
{
  newinit();

  $('lref').href = sub('l/');
  $('edit').href = "edit.html?"+conf.targ;


  var o = $('cit');
  for (var a=0; a<30; a++)
    {
      var i	= image('l/'+a.toString(16)+'.png');

//    i.mycnt	= a;
//    i.style.border	= "1px dotted white";
      i.style.width	= "100px";
      i.onmouseover	= ovr;
      i.onmouseout	= function () { this.style.opacity=1; if (shown==this) show(was); }

      o.appendChild(i);
    }

  out("running");
}

onready(init);

