"use strict;"

// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

JSON.encode=JSON.stringify;

var config = (function (n) { return (
  {
    targ: ""+n+"",
    dir: ""+n+"/",
    exec: "exec.php/"+n,
  });
})(parseInt(window.location.search.substr(1)));

function sub(s) { return config.dir+s }


///////////////////////////////////////////////////////////////////////
// Old stuff
///////////////////////////////////////////////////////////////////////


var decache;

function dump(x)
{
try {
var s="";
for (var n in x) { var v=x[n]; if (typeof(v)=="function") continue; s+=n+"="+x[n]+"\n"; }
return s;
} catch (e) {
  return e+": "+x;
}
}
function peek(x)
{
out(dump(x));
return x;
}
var editmode=false;
var kbprocessing=true;
var currentregion;
var blinker=0;
function timer()
{
if (!editmode || !currentregion)
  return;
switch (++blinker)
  {
  case 1:
    currentregion.regiondiv.style.opacity = 0.5;
    currentregion.regiondiv.style.background = "red";
    break;
  case 2:
    currentregion.regiondiv.style.background = "blue";
    break;
  default:
    currentregion.regiondiv.style.opacity = 1;
    currentregion.regiondiv.style.background = "transparent";
    blinker = 0;
    break;
  }
}
var text;
function err(s)
{
var e=$("out");
e.className = "err";
e.innerHTML = s;
}
function out(s)
{
$("out").innerHTML = s;
text = s;
}
function start(s)
{
$("out").className = "ok";
out(s);
}
function done(s)
{
out(text + "<br>"+s);
}
function evok(e)
{
  if (e)
    {
      e.cancelBubble = true;
      if (e.stopPropagation)
        e.stopPropagation();
      if (e.preventDefault)
        e.preventDefault();
    }
  return false;
}
function moveregion(d)
{
  var i = current + d;
  if (i<0 || i>=edit.r.length)
    return;
  var o = edit.r[current];
  edit.r[current]	= edit.r[i];
  edit.r[i]		= o;
  regions(d);
}

function keyboard_edit(e)
{
  var r = edit.r[current];

  x=0;
  y=0;
  d=0;
  switch (e.code)
    {
    default:
      return;

    case 'PageUp':		moveregion(-1); return evok(e);
    case 'PageDown':		moveregion(+1); return evok(e);

    case 'NumpadSubtract':	regions(-1); return evok(e);
    case 'NumpadAdd':		regions(+1); return evok(e);

    case 'Return':		newrect(); return evok(e);

    case 'ArrowLeft':	x= -1; break;
    case 'ArrowUp':	y= -1; break;
    case 'ArrowRight':	x= +1; break;
    case 'ArrowDown':	y= +1; break;
    case 'NumPad7':	x= -1; y= -1; break;
    case 'NumPad8':	x=  0; y= -1; break;
    case 'NumPad9':	x= +1; y= -1; break;
    case 'NumPad4':	x= -1; y=  0; break;
    case 'NumPad7':	x= +1; y=  0; break;
    case 'NumPad1':	x= -1; y= +1; break;
    case 'NumPad2':	x=  0; y= +1; break;
    case 'NumPad3':	x= +1; y= +1; break;

    case 'Backspace':	d= -r[0]; break;

    case 'KeyQ':	d= +1; break;
    case 'KeyW':	d= +10; break;
    case 'KeyE':	d= +100; break;
    case 'KeyR':	d= +1000; break;
    case 'KeyT':	d= +10000; break;
    case 'KeyY':	d= +100000; break;
    case 'KeyU':	d= +1000000; break;
    case 'KeyI':	d= +10000000; break;
    case 'KeyO':	d= +100000000; break;

    case 'KeyA':	d= -1; break;
    case 'KeyS':	d= -10; break;
    case 'KeyD':	d= -100; break;
    case 'KeyF':	d= -1000; break;
    case 'KeyG':	d= -10000; break;
    case 'KeyH':	d= -100000; break;
    case 'KeyJ':	d= -1000000; break;
    case 'KeyK':	d= -10000000; break;
    case 'KeyL':	d= -100000000; break;
    }
  if (!e.ctrlKey)
    {
      x *= 16;
      y *= 16;
    }
  else if (!x && !y)
    return;	// unknown CTRL combination

  if (e.shiftKey)
    {
      r[3] = Math.max(0,r[3]+x);
      r[4] = Math.max(0,r[4]+y);
    }
  else
    {
      r[1] = Math.max(0,r[1]+x);
      r[2] = Math.max(0,r[2]+y);
    }
  r[0] += d;
  dirt();
  fixregion(currentregion);
  return evok(e);
}
function modder(mod)
{
editmode = mod=="e";
for (var e of document.querySelectorAll('[show]'))
  if (e.getAttribute("show")==mod)
    show(e);
  else
    hide(e);
}
function hilight()
{
this.style.color = "blue";
}
function lolight()
{
this.style.color = "white";
}
function selregion()
{
current = this.regionnr;
regions();
}
function fixregion(t)
{
  if (!t)
    return;

  var i = t.regionnr;
  var e = t.regiondiv;
  var r = edit.r[i];

  e.style.left = r[1]+'px';
  e.style.top = r[2]+'px';
  e.style.width = r[3]+'px';
  e.style.height = r[4]+'px';
//  e.style.borderColor = '#'+colors[r[0]];
  $$$(t,r);
}
var edit;
var current = 0;
//var colors=['000000','ff0000','00ff00','0000ff'];
function regions(d)
{
if (d && (d+=current)>=0 && d<edit.r.length)
  current = d;
currentregion = null;
if (!edit.r)
  edit.r = [];
var x=[], y=[];
for (var i=0; i<edit.r.length; i++)
  {

    var e = __("div");
    e.className = "region";

    var t = __("span");
    t.regiondiv = e;
    t.regionnr = i;

    if (i==current)
      {
        currentregion = t;
        t.style.color = "red";
      }
    else
      {
        t.onclick = selregion;
        t.onmouseover = hilight;
        t.onmouseout = lolight;
      }
    fixregion(t);
    x.push(e);
    a = _a_('#',mkdelregion(i),___("X"));
    y.push(__("li",___("[ ",a," ] ",t)));
  }
clear("regions",__("div",x));
clear("regionlist",__("ul",y));
}
function mkdelregion(i)
{
  return function(e){return delregion(i,e)}
}
function delregion(r,e)
{
edit.r.splice(r,1)
dirt();
regions();
return evok(e);
}
function ed(e)
{
if (edit && edit.dirt && edit!==e)
  if (!confirm(edit.name+" not saved, leave?"))
    return;
edit = e;
modder("e");
setname(edit.name);
movesel(edit.img);
regions();
}
function dirt()
{
edit.dirt = new Date().getTime();
}
function newrect()
{
var r = [0,0,0,10,10];
if (edit.r[current])
  r = edit.r[current].slice(0);
current = edit.r.length;
edit.r.push(r);
dirt();
regions();
}
function stamp()
{
return new Date().getTime();
}
function files(r,cb)
{
ajax.get(config.exec+"?decache="+stamp()+"&r=dir&d="+r,function(d,x,s){if (s==200) cb(d); else err('failed '+r+' ('+s+'): '+d)});
}
function clear(e,c)
{
e=$(e);
while (e.firstChild)
  e.removeChild(e.firstChild);
if (c)
  e.appendChild(c);
}
function newit()
{
ed({ name:'new' });
}
function saved(ob)
{
var n = ob.name;
var stamp = ob.dirt;
start("saving "+n);
return function(t,x,s)
  {
    if (s==200 && t!='')
      {
        done("saved "+n+": "+t);
        setname(null);
        if (ob.dirt==stamp)
          ob.dirt = 0;
        refreshdir();
      }
    else
      err("save error "+n+": "+s+": "+t);
  }
}
function saveit()
{
if (!edit)
  return;
var n=$('filename').value;
edit.img = currentsel();
edit.name = $('filename').value;
ajax.post(config.exec+"?d=ed&r=save&f="+escape(edit.name),saved(edit),JSON.encode(edit));
}

var showel;
function presentit(e)
{
showel=e;
dispimg(e.loadcache.img);
out(JSON.encode(e.loadcache));
}
function parse(d)
{
var t=JSON.parse(d);
t.dirt=0;
return t;
}
function pullit(e,cb)
{
ajax.get(sub('e/')+e.tag+"?decache="+decache,function(d,x,s){if(s!=200)return;e.loadcache=parse(d);cb(e)});
}
function _showit(e)
{
if (e.loadcache)
  presentit(e);
else
  pullit(e,_showit);
}
function _editit(e)
{
if (e.loadcache)
  ed(e.loadcache);
else
  pullit(e,_editit);
}
function showit(e)
{
  this.style.color = "blue";
  _showit(this);
}
function showdef(e)
{
  this.style.color = "white";
if (showel!==this)
  return;
selimg(e);
showel = 0;
}
function editit(e)
{
  _editit(this);
}
function dir(l)
{
var tilde = $('tilde').checked;

l=l.split("\n");
l.sort();
var x=[];
for (var i=0; i<l.length; i++)
  {
    if (l[i]=="")
      continue;
    if (!tilde && l[i].indexOf('~')>=0) continue;
    var o = __("span",___(l[i]));
    o.tag = l[i];
    o.loadcache = null;
    o.onclick = editit;
    o.onmouseover = showit;
    o.onmouseout = showdef;
    x.push(__("li",o));
  }
clear("list",__('ul',x));
done("templates loaded");
}
function movesel(n)
{
//done("movesel "+n);
var e=$("learns").firstChild.options;
for (var i=e.length; --i>=0; )
  if (e[i].value == n)
    {
//      done("found "+i);
      e[i].selected = true;
    }
}
function currentsel()
{
var e=$("learns").firstChild;
return e.options[e.selectedIndex].value;
}
function selimg(e)
{
dispimg(currentsel());
}
function learns(l)
{
imgcache={};
var tilde = $('tilde').checked;

l=l.split("\n");
l.sort();
var x=[];
for (var i=0; i<l.length; i++)
  if (l[i]!="" && (tilde || l[i].indexOf('~')<0))
    x.push(__('option',___(l[i])));
var e = __('select',x);
e.onchange = selimg;
e.onkeyup = selimg;
var was="";
try {
  was = currentsel();
} catch (_e) {}
clear("learns",e);
movesel(was);
selimg();
done("images loaded");
}
function refreshdir()
{
files("ed",dir);
}
function refreshimgs()
{
files("learn",learns);
}
function refreshall()
{
decache=stamp();
start("reloading");
refreshdir();
refreshimgs();
}
function abortit()
{
modder("m");
}
function editagain()
{
if (edit)
  modder("e");
}
var focuselement;
function gotfocus()
{
  focuselement = this;
  kbprocessing = false;
}
function lostfocus()
{
  if (this==focuselement)
    kbprocessing = true;
}

///////////////////////////////////////////////////////////////////////
// Newer stuff
///////////////////////////////////////////////////////////////////////

function keyboard(e)
{
  $$$("out",e.key+' '+e.code);

  if (!kbprocessing)
    return;

  if (e.ctrlKey)
    switch (e.code)
      {
      case 'KeyR':	refreshall(); return evok(e);
      }
  else
    switch (e.code)
      {
      case 'Escape':	abortit(); return evok(e);
      case 'Space':	editagain(); return evok(e);
      }

  if (edit && editmode && keyboard_edit(e))
    return evok(e);
}

var dispi;
var imgcache={};

function dispok(e)
{
  this.haveload	 = 1;
  dispimg(dispi);
  done(Object.keys(imgcache).length + ' images cached');
}

function dispimg(i)
{
  var e=$('show');
  var c;

  dispi	= i;
  if (i in imgcache)
    c			= imgcache[i];
  else
    {
      c			= new Image();
      c.src		= sub('l/')+i+'?decache='+decache;
      c.onload		= dispok;
      c.dispi		= i;
      c.haveload	= 0;
      imgcache[i]	= c;
    }
  if (e.src != c.src)
    e.src		= c.src;
  e.style.opacity	= c.haveload ? 1 : 0.5;
}

function setname(name)
{
  var e = $('filename');

  if (name!==null)
    e.value = name;
  checkname.call(e);
}

function checkname()
{
  $('killer').disabled = !edit || this.value != edit.name;
}

function killer()
{
  var e = edit;

  if (!e)
    return;

  if ($("filename").value != e.name)
    return;

  start("killing "+e.name);

  ajax.post(config.exec+"?d=ed&r=kick&f="+escape(edit.name), function (t,x,s)
    {
      if (s==200 && t!='')
        {
          done('killed '+e.name+': '+t);
          refreshdir();
          return;
        }
      err('kill error '+e.name+': '+s+': '+t);
    });
}

var clickmap =
{ editagain:	editagain
, abortit:	abortit
, refreshall:	refreshall
, newit:	newit
, saveit:	saveit
, newrect: 	newrect
, killer: 	killer
};

function clickproxy(e)
{
  var r = this.getAttribute('runs');

  if (clickmap[r])
    return clickmap[r].call(this, e);

  out('UNKNOWN '+r);
  return false;
}

function init()
{
  for (var e of document.querySelectorAll('[runs]'))
    {
      console.log(e);
      e.onclick = clickproxy;
    }

  refreshall();
  modder("m");

  window.setInterval(timer,200);
  window.onkeydown = keyboard;

  e = $('filename');
  e.onkeyup = checkname;
  e.onchange = checkname;

  var el = document.getElementsByName("focus");
  for (var i=el.length; --i>=0; )
    {
      el[i].onfocus = gotfocus;
      el[i].onblur = lostfocus;
    }
}

onready(init);

