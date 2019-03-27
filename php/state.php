<?php
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
for ($i=1; ++$i<$l; )
  {
    $f = $pi[$i];
    if ($f==='') die("missing filename: $i");
    if (!file_exists("$base/e/$f.tpl")) die("missing file: $i");
    $t .= " $f";
  }

$fd = fsockopen("unix://../sub/$targ/sock");
if (!$fd) die("cannot open $targ");
socket_set_blocking($fd,1);
fwrite($fd,"state$t\n");
if ($s)
  fwrite($fd,"check$t\n");
fwrite($fd, "exit\n");
fflush($fd);
echo fread($fd,4096);
fclose($fd);
flush();

