<?php
# Macro management
#
# GET	macro.php/{V}/{M}	run {M}
# POST	macro.php/{V}/{M}	run {M} {POSTDATA}
#
# {V} is the VNC number
# {POSTDATA} must not contain special (nonprinting) characters
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

require 'sock.inc';

plain();
args(3,3);

$t = '';
# There is only 1 .. for now
for ($i=1; ++$i<$cnt; )
  {
    $f = $pi[$i];
    if ($f==='') die("missing filename: $i");
    if (!file_exists("$base/o/$f.macro")) die("missing file: $i");
    $t .= " $f";
  }

#if (isset($_GET['refresh']))
#  header("Refresh: ".min(20, intVal($_GET['refresh'])));

# fetch arguments from POST data
$r = preg_replace('/[\x00-\x1F\x7F]/u', '', get_POST_data());
if ($r!=='')
  $t .= " $r";

send_receive("run$t");

