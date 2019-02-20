"use strict;"

// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

// These functions should go into a lib

function dump(x)
{
  var s="";
  for (var n in x) { var v=x[n]; if (typeof(v)=="function") continue; s+=n+"="+x[n]+"\n"; }
  alert(s);
}

function stamp() { return new Date().getTime() }

// run an object if it is ok or error
function run(o) { var r=o.runner; if (r && (o.err || o.ok)) { o.runner=undefined; r.call(o) } }
function runit(o, r) { o.run = r; run(o) }

// create an Image which tracks it's state
function image(url)
{
  var i		= document.createElement('img');

  i.run		= undefined;
  i.onload	= function () { this.ok=1;  run(this) }
  i.onerror	= function () { this.err=1; run(this) }
  i.run		= function (fn) { var l=this.runner; this.runner=(l ? function() { l(); fn() } : fn); run(this) }
  i.src		= sub(url);

  return i;
}

//
// Config
//

var n = parseInt(window.location.search.substr(1));
var config =
  {
    run: 100,
    sleep: 6,
    targ: ""+n+"",
    dir: ""+n+"/",
  };

function sub(s) { return config.dir+s }





























//
// Things below should be reworked
//


var runcnt = 0;
var waiti = 0;

function timer(e)
{
  runcnt++;
  //$$$("run",runcnt);
  if (waiti)
    {
      if (!--waiti)
        dorefresh();
    }
  nextrefresh();
}

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

var newi=0;
var loadn=0;

// Image is loaded, show it if it is still shown
function loadi()
{
  if (this.err)
    return;

  waiti	= 0;
  this.style.opacity	= 1;
  if (this === shown)
    show();
  $$$("refcnt", newi+"x");
}

function greyi()
{
  if ($("uihelper").checked)
    return;

  var	e = $("show");

  if (e.firstChild)
    e.firstChild.style.opacity = 0.5;
}

var sleeps = 0;
var sleeper = 0;
var pendi = false;
var defsleep = config.sleep;
var maxsleep = defsleep;
var defrun = config.run;
var maxrun = defrun;

function nextrefresh()
{
  if (sleeps<0)
    sleeps = sleeper;
  if (!--sleeps)
    pendi = true;
  if (pendi && !waiti)
    dorefresh();
}

var lm, lmc;

// req.text, req, req.status, req.IfModifiedSince
function checkrefresh(e,x,s,l)
{
  $$$("check","");
  if (l)
    lm = l;
  if(!l || s==304)
    {
      lmc++;
      $$$("lms",s+": "+lm+" @ "+lmc);
      waiti	= 0;
    }
  else
    {
      lmc	= 0;
      $$$("lms",s+": "+l);

      $$$("refcnt", ++newi+"*");

      show(image("test.jpg?"+stamp()));

      waiti	= 100;
    }
  pendi	= false;
  sleeper++;
  if (maxrun && maxsleep && sleeper>maxsleep)
    {
      maxrun--;
      sleeper	= maxsleep;
      updquick();
    }
  sleeps	= 0;
  nextrefresh();
}

function dorefresh()
{
  waiti = 100;
  $$$("check","*");
  ajax.head(sub("test.jpg"), checkrefresh, lm);
}

function updquick()
{
  if (maxrun && maxsleep)
    $("qrun").value = maxrun;
  else
    $("qrun").value = "0";
}

function quick()
{
  pendi=true;
  maxsleep = maxsleep && maxrun ? 0 : defsleep;
  maxrun = defrun;
  updquick()
}

var reqrun=false;
var reqs=[];

function reqdone(r)
{
  out("done: "+r);

  reqrun	= false;
  sleeps	= 0;
  sleeper	= 0;

  dorefresh();
  reqnext();
}

function reqnext()
{
  var r;

  if (reqrun)
    return;

  try {
    r = reqs.shift();
  } catch (e) {
    return;
  }

  if (r===undefined)
    return reqnext();

  reqrun	= true;
  greyi();

  ajax.get("click.php/"+config.targ+"?decache="+stamp()+"&"+r, function(e) { reqdone(r) });

  nr++;
  out("do: "+r);
}

function req(r) { reqs.push(r); reqnext() }

function clicki(ev)
{
  var mb = document.getElementsByName("mb");
  var b=0;
  for (var i=mb.length; --i>=0; )
    if (mb[i].checked)
      b |= parseInt(mb[i].value);
  var xy = elxy(this,ev);
  req("x="+xy[0]+"&y="+xy[1]+"&b="+b);
}

function movei(ev) { xy = elxy(this,ev); $$$("pos","x="+xy[0]+" y="+xy[1]) }
function send(id,t) { if (!t) t="t"; req(t+"="+escape($(id).value)); return false }
function code(c) { req("c="+escape(c)); return false }

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
      return;
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

  this.style.opacity = 0.5;
  was	= shown;
  show(this.cloneNode(true));
}

function init()
{
  window.setInterval(timer,500);
  dorefresh();
  updquick();

  $('lref').href = sub('l/');

  var o = $('cit');
  for (var a=0; a<30; a++)
    {
      var i	= image('e/'+a.toString(16)+'.jpg');

//    i.mycnt	= a;
//    i.style.border	= "1px dotted white";
      i.style.width	= "100px";
      i.onmouseover	= ovr;
      i.onmouseout	= function () { this.style.opacity=1; if (shown==this) show(was); }

      o.appendChild(i);
    }

  out("running");
}

