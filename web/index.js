// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

function dump(x)
{
var s="";
for (var n in x) { var v=x[n]; if (typeof(v)=="function") continue; s+=n+"="+x[n]+"\n"; }
alert(s);
}
function stamp()
{
return new Date().getTime();
}
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

var shown;
function disp2()
{
show("show"+shown);
if (shown!=0) hide("show0");
if (shown!=1) hide("show1");
if (shown!=2) hide("show2");
}

function disp(n)
{
shown=n;
window.setTimeout(disp2,10);
}

var newi=0;
var loadn=0;
function loadi()
{
waiti=0;
$("show"+loadn).style.opacity=1;
if (shown<2)
  disp(loadn);
loadn=1-loadn;
$$$("refcnt", newi+"x");
}
function greyi()
{
if (!$("uihelper").checked)
  $("show"+(1-loadn)).style.opacity=0.5;
}

var sleeps = 0;
var sleeper = 0;
var pendi = false;
var defsleep = 6;
var maxsleep = defsleep;
var defrun = 100;
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
  lm=l;
if(!l || s==304)
  {
    lmc++;
    $$$("lms",s+": "+lm+" @ "+lmc);
    waiti = 0;
  }
else
  {
    lmc=0;
    $$$("lms",s+": "+l);

    $$$("refcnt", ++newi+"*");
    $("show"+loadn).src = "test.jpg?"+stamp();

    waiti=100;
  }
pendi=false;
sleeper++;
if (maxrun && maxsleep && sleeper>maxsleep)
  {
    if (!--maxrun)
      $("qrun").value = "q";
    sleeper = maxsleep;
  }
sleeps=0;
nextrefresh();
}
function dorefresh()
{
waiti = 100;
$$$("check","*");
ajax.head("test.jpg",checkrefresh,lm);
}
function quick()
{
pendi=true;
maxsleep = maxsleep && maxrun ? 0 : defsleep;
$("qrun").value = maxsleep ? "r" : "q";
maxrun = defrun;
}

var reqrun=false;
var reqs=[];
function reqdone(r)
{

out("done: "+r);
reqrun = false;
sleeps=0;
sleeper=0;
dorefresh();
reqnext();
}
function reqnext()
{
if (reqrun)
  return;
try {
var r = reqs.shift();
} catch (e) {
  return;
}
if (r===undefined)
  return;
reqrun = true;
greyi();
ajax.get("click.php?decache="+stamp()+"&"+r,function(e){reqdone(r)});
nr++;
out("do: "+r);
}
function req(r)
{
reqs.push(r);
reqnext();
}
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
function movei(ev)
{
xy = elxy(this,ev);
$$$("pos","x="+xy[0]+" y="+xy[1]);
}
function send(id,t)
{
if (!t) t="t";
req(t+"="+escape($(id).value));
return false;
}
function code(c)
{
req("c="+escape(c));
}
function ovr()
{
if (this.height<40)
  return;

var c = this.cloneNode(true);
c.id = "show2";
c.style.width = "";
hide(c);

// This is a hack as replaceChild has a bad visual impact
shown = 1-loadn;
disp2();

var s = $("shower");
s.replaceChild(c,s.lastChild);

shown = 2;
disp2();

this.style.opacity=0.5;
}
function novr()
{
this.style.opacity=1;
disp(1-loadn);
}
function init()
{
for (var a=2; --a>=0; )
  {
    var o=$("show"+a);
    o.onclick = clicki;
    o.onload  = loadi;
    o.onmousemove  = movei;
  }
disp(0);
window.setInterval(timer,500);
dorefresh();
out("running");
var cnt=1;
for (var i=$("cit").firstChild; i; i=i.nextSibling)
  if (i.src)
    {
      cnt++;
      i.mycnt = cnt;
      i.onmouseover = ovr;
      i.onmouseout  = novr;
      i.style.width = "100px";
//      i.style.border= "1px dotted white";
    }
}
