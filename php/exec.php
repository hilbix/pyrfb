<?php
# Simple edit wrapper.
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

header("Content-type: text/plain");
header("Expires: -1");
header("Pragma: no-cache");

$targ = intval(substr($_SERVER["PATH_INFO"],1));
$root = $_SERVER["DOCUMENT_ROOT"];
$script = $_SERVER["SCRIPT_NAME"];	// this must be relative to document root
$base = "$root/".dirname($script)."/$targ";
if (!is_dir($base)) die("wrong $targ");

$r = $_GET['r'];
if ($r=="dir" || $r=="learn")
  {
    $d = dir("$base/".($r=="dir" ? 'e' : 'l'));
    while (false !== ($e=$d->read()))
      {
        if ($e=='.' || $e=='..') continue;
        echo htmlentities($e);
        echo "\n";
      }
  }
elseif ($r=="save")
  {
    $name = $_GET['f'];
    $pi = pathinfo($name);
    if ($name!=$pi['filename'] || $name=='')
      die("wrong name (parameter f)");
    $name = "$base/e/$name.tpl";
    $done = "created";
    if (file_exists($name))
      for ($i=0;; $i++)
        {
          $to = "$name.tpl.~$i~";
          if (!file_exists($to))
            {
              rename($name,$to);
              $done = "replaced";
              break;
            }
        }
    if (copy('php://input', $name))
      echo $done;
    else
      header("HTTP:/1.0 500 copy failed");
  }
else
  die("wrong param r");

