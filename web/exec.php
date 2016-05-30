<?php
# Simple edit wrapper.
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

header("Content-type: text/plain");
header("Expires: -1");
header("Pragma: no-cache");

$r = $_GET['r'];
if ($r=="dir" || $r=="learn")
  {
    $d = dir($r=="dir" ? 'e' : 'learn');
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
       die("illegal name f");
    $name = "e/$name.tpl";
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
