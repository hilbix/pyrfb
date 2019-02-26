// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

JSON.encode=JSON.stringify;

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
var blink=false;
var kbprocessing=true;
var currentregion;
var blinker=0;
function timer()
{
if (!blink || !kbprocessing || !currentregion)
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
    }
  return false;
}
function keyboard(e)
{
if (!kbprocessing)
  return;
if (!e)
  e = window.event;

x=0;
y=0;
d=0;
switch (e.keyCode)
  {
    default:
      $$$("out",e.keyCode);
      return;

    case 109: orderregion(-1); return evok(e);
    case 107: orderregion(+1); return evok(e);

    case 8: abortit(); return evok(e);

    case 37: x=-1; break;
    case 38: y=-1; break;
    case 39: x=1; break;
    case 40: y=1; break;

    case 81: d=1; break;
    case 87: d=10; break;
    case 69: d=100; break;
    case 82: d=1000; break;
    case 84: d=10000; break;
    case 90: d=100000; break;
    case 85: d=1000000; break;
    case 73: d=10000000; break;
    case 79: d=100000000; break;

    case 65: d=-1; break;
    case 83: d=-10; break;
    case 68: d=-100; break;
    case 70: d=-1000; break;
    case 71: d=-10000; break;
    case 72: d=-100000; break;
    case 74: d=-1000000; break;
    case 75: d=-10000000; break;
    case 76: d=-100000000; break;
  }
if (!e.ctrlKey)
  {
    x *= 16;
    y *= 16;
  }
var r = edit.r[current];
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
r[0] = Math.max(0,r[0]+d);
dirt();
fixregion(currentregion);
return evok(e);
}
function modder(mod)
{
blink = mod=="e";
var el=document.getElementsByName("mod");
for (var i=el.length; --i>=0; )
  if (el[i].getAttribute("mod")==mod)
    show(el[i]);
  else
    hide(el[i]);
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
  var i = t.regionnr;
  var e = t.regiondiv;
  var r = edit.r[i];

  e.style.left = r[1]+'px';
  e.style.top = r[2]+'px';
  e.style.width = r[3]+'px';
  e.style.height = r[4]+'px';
  e.style.borderColor = '#'+colors[r[0]];
  $$$(t,r);
}
var edit;
var current;
var colors=['000000','ff0000','00ff00','0000ff'];
function regions()
{
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
$("filename").value = edit.name;
movesel(edit.img);
regions();
}
function dirt()
{
edit.dirt = new Date().getTime();
}
function newrect()
{
current = edit.r.length;
edit.r.push([0,0,0,10,10]);
dirt();
regions();
}
function stamp()
{
return new Date().getTime();
}
function exe(r,cb)
{
ajax.get("exec.php?decache="+stamp()+"&r="+r,function(e){cb(e)});
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
    if (s==200)
      {
        done("saved "+n+": "+t);
        if (ob.dirt==stamp)
          ob.dirt = 0;
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
ajax.post("exec.php?r=save&f="+escape(edit.name),saved(edit),JSON.encode(edit));
}
var dispi, dispsrc;
function dispok(e)
{
this.style.opacity = 1;
}
function dispimg(i)
{
var e=$("show");
if (e.src!=dispsrc || i!=dispi)
  {
    e.style.opacity = 0.5;
    e.onload = dispok;
    e.src="learn/"+i+'?decache='+decache;
  }
dispi = i;
dispsrc = e.src;
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
ajax.get('e/'+e.tag+"?decache="+decache,function(d,x,s){if(s!=200)return;e.loadcache=parse(d);cb(e)});
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
l=l.split("\n");
l.sort();
var x=[];
for (var i=0; i<l.length; i++)
  {
    if (l[i]=="")
      continue;
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
l=l.split("\n");
l.sort();
var x=[];
for (var i=0; i<l.length; i++)
  if (l[i]!="")
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
exe("dir",dir);
}
function refreshimgs()
{
exe("learn",learns);
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

function init()
{
  refreshall();
  modder("m");

  window.setInterval(timer,500);
  window.onkeydown = keyboard;

  var el = document.getElementsByName("focus");
  for (var i=el.length; --i>=0; )
    {
      el[i].onfocus = gotfocus;
      el[i].onblur = lostfocus;
    }
}

onready(init);

