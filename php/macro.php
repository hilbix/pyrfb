<?php
# Macro management
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
header("Content-type: text/plain");
header("Pragma: no-cache");
header("Expires: -1");

$pi = explode('/', $_SERVER["PATH_INFO"]);
$targ = intval($pi[1]);

$root = $_SERVER["DOCUMENT_ROOT"];
$script = $_SERVER["SCRIPT_NAME"];      // this must be relative to document root
$base = "$root/".dirname($script)."/$targ";
if (!is_dir($base)) die("wrong $targ");

$l = count($pi);
if ($l!=3) die("too many macros: $l");

# There is only 1 .. for now
for ($i=1; ++$i<$l; )
  {
    $f = $pi[$i];
    if ($f==='') die("missing filename: $i");
    if (!file_exists("$base/o/$f.macro")) die("missing file: $i");
    $t .= " $f";
  }

# fetch arguments from POST data
$r = file_get_contents("php://input");
if (ctype_print($r))
  $t .= " $r";

$fd = fsockopen("unix://../sub/$targ/sock");
if (!$fd) die("cannot open $targ");
socket_set_blocking($fd,1);
fwrite($fd,"run$t\n");		# run (macro)
fflush($fd);
echo fread($fd,4096);
fclose($fd);
flush();

