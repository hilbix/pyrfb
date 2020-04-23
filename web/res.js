"use strict";
function init()
{
  out('init failed');

  emit.init();
  emit.register('err', function (e,...a){ xLOG('err',e,e.stack,...a); out('err: '+e+' '+a); out('stack: '+e.stack); alert(e+' '+a+'\n'+e.stack) });
  req.init();
  runs.init();

  layout();

  out('ok');
}

onready(init);

