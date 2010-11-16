// $Header$
//
// partly stolen at http://snippets.dzone.com/posts/show/2025
// Rest portion:
// This Works is placed under the terms of the Copyright Less License,
// see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
//
// $Log$
// Revision 1.1  2010/11/16 07:47:27  tino
// Web part added
//
// Revision 1.1  2008-12-29 19:18:39  tino
// Added
//

function $$$(e,s){$(e).innerHTML=s};
function $$(e){return $(e).innerHTML};
function $(e){if(typeof e=='string')e=document.getElementById(e);return e};

ajax={};
ajax.collect=function(a,f){var n=[];for(var i=0;i<a.length;i++){var v=f(a[i]);if(v!=null)n.push(v)}return n};
ajax.x=function(){try{return new ActiveXObject('Msxml2.XMLHTTP')}catch(e){try{return new ActiveXObject('Microsoft.XMLHTTP')}catch(e){return new XMLHttpRequest()}}};
ajax.send=function(u,f,m,a){var x=ajax.x();x.open(m,u,true);x.onreadystatechange=function(){if(x.readyState==4)f(x.responseText)};if(m=='POST')x.setRequestHeader('Content-type','application/x-www-form-urlencoded');x.send(a)};
ajax.get=function(url,func){ajax.send(url,func,'GET')};
//ajax.serialize=function(f){var g=function(n){return f.getElementsByTagName(n)};var nv=function(e){if(e.name)return encodeURIComponent(e.name)+'='+encodeURIComponent(e.value);else return ''};var i=ajax.collect(g('input'),function(i){if((i.type!='radio'&&i.type!='checkbox')||i.checked)return nv(i)});var s=ajax.collect(g('select'),nv);var t=ajax.collect(g('textarea'),nv);return i.concat(s).concat(t).join('&');};
//ajax.gets=function(url){var x=ajax.x();x.open('GET',url,false);x.send(null);return x.responseText};
//ajax.post=function(url,func,args){ajax.send(url,func,'POST',args)};
//ajax.update=function(url,elm){var e=$(elm);var f=function(r){e.innerHTML=r};ajax.get(url,f)};
//ajax.submit=function(url,elm,frm){var e=$(elm);var f=function(r){e.innerHTML=r};ajax.post(url,f,ajax.serialize(frm))};

