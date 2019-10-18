<?php
# Macro management
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

require 'sock.inc';

plain();
args(3,3);

# There is only 1 .. for now
for ($i=1; ++$i<$cnt; )
  {
    $f = $pi[$i];
    if ($f==='') die("missing filename: $i");
    if (!file_exists("$base/o/$f.macro")) die("missing file: $i");
    $t .= " $f";
  }

# fetch arguments from POST data
$r = get_POST_data();
if (ctype_print($r))
  $t .= " $r";

send_receive("run$t");

