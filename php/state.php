<?php
# Send state check to backend
#
# state.php/targ/tpl/tpl..
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

require 'sock.inc';

plain();
args(2,-1);

for ($i=1; ++$i<$cnt; )
  {
    $f = $pi[$i];
    if ($f==='') die("missing filename: $i");
    if (!file_exists("$base/e/$f.tpl")) die("missing file: $i");
    $t = " $f";
  }

send_receive("if state$t\nthen echo ok\nelse echo ko\nexit");

