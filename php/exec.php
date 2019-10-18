<?php
# Directory and file management
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

require 'sock.inc';

plain();
args(2, 2);

$dirs = [ 'ed'=>'e',   'learn'=>'l',   'stat'=>'s',   'oper'=>'o' ];
$exts = [ 'ed'=>'tpl', 'learn'=>'png', 'stat'=>'png', 'oper'=>'macro' ];

function getname($flag)
{
  GLOBAL $base, $ext;

  $name = $_GET[$flag];
  $pi = pathinfo($name);
  if ($name != $pi['filename'] || $name=='')
    die("wrong name (parameter $flag)");
  return "$base/$name.$ext";
}

function renamer($name)
{
  GLOBAL $ext;

  if (!file_exists($name))
    return 0;
  for ($i=0;; $i++)
    {
      $to = "$name.~$i~";
      if (!file_exists($to))
        {
          rename($name,$to);
          return 1;
        }
    }
}

function fail($reason)
{
  header("HTTP/1.0 500 $reason");
}

$d = $_GET['d'];
if (!isset($dirs[$d]))
  die('wrong param d');

$base	= "$base/".$dirs[$d];
$ext	= $exts[$d];

$r = $_GET['r'];
if ($r=='dir')
  {
    $d = dir($base);
    while (false !== ($e=$d->read()))
      {
        if ($e=='.' || $e=='..') continue;
        echo htmlentities($e);
        echo "\n";
      }
  }
elseif ($r=='kick')
  {
    $name	= getname('f');
    if (renamer($name))
      echo 'kicked';
    else
      fail('unknown');
  }
elseif ($r=='save')
  {
    $name	= getname('f');
    $done	= renamer($name) ? 'renamed' : 'created';
    if (copy('php://input', $name))
      echo $done;
    else
      fail('copy failed');
  }
else
  die('wrong param r');

