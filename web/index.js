"use strict";
function init()
{
  out('init failed');

  href('lref', subdir(''));
  href('edit', 'edit.html?'+conf.targ);

  show.init('show');

  emit.init();
  emit.register('quick',	function (v)	{ $$$('qrun', v) });
  emit.register('done',		function (r,t,s) { out((s==200 ? 'done' : 'fail'+s)+': '+r.r+' '+t) });
  emit.register('act',		function (r)	{ if (!r.cb) show.grey(); out('do: '+r.r) });
  emit.register('wait',		function (w)	{ $$$('wait', w) });
  emit.register('err',		function (e,...a){ xLOG('err',e,e.stack,...a); out('err: '+e+' '+a); out('stack: '+e.stack); alert(e+' '+a+'\n'+e.stack) });
  emit.register('sel-b',	function (t)	{ if (t=='t') globals(); });

  req.init();
  runs.init();
  poller.init(conf.poll).quick(isSlowMobile() ? -1 : conf.quickmode);
  macro.init();

  // improve hoverness
  for (let e of DOMs('[title]'))
    help(e);

  reload(false);

  out('ok');
}

onready(init);

