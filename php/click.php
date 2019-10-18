<?php
# Simple PHP wrapper to forward commands to rfbimg.py socket.
# THIS IS INHERENTLY INSECURE IF EXPOSED TO THE WORLD.
# So protect it with BasicAuth and HTTPS, you have been warned.
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# send charcode:	c=charcode
# send text:		t=lines-of-text
# move mouse:		x=xcoord&y=ycoord
# mouse click:		x=xcoord&y=ycoord&b=mousebuttons
# mouse drag:		x=xcoord&y=ycoord&b=$[mousebuttons+65536]
# learn (save) image:	l=name
#
# mousebuttons are a bitmask of pressed buttons
# if name is empty on learn, a default name (screen-TIMESTAMP) us used

require 'sock.inc';

plain();
args(2, 2);

$o="";
$s="";
if (isset($_GET["c"]))
  {
    $a = intval($_GET["c"], 0);
    if ($a == 0 && $_GET["c"]!=='0') die("c?");
    $o = sprintf("code %d", $a);
    $s = sprintf("code 0x%04x\n", $a);
  }
else if (isset($_GET["k"]))
  {
    $a = $_GET["k"];
    if (!ctype_graph($a)) die("k?");
    $o = sprintf("code %s", $a);
    $s = sprintf("key %s\n", $a);
  }
elseif (isset($_GET["t"]))
  {
    $a = explode("\n",$_GET["t"]);
#    $s = "key ".$a[count($a)-1];
    for ($i=count($a); --$i>=0; ) {
      $s = "key ".$a[$i]."\n$s";
      if ($i)
        $s = "code Return\n$s";
    }
  }
elseif (isset($_GET["x"]) || isset($_GET["X"]))
  {
    if (isset($_GET["X"]))
      $s	= sprintf('mouse %s %d', $_GET['X'], (isset($_GET['y']) ? $_GET['y'] : 100));
    else
      $s	= sprintf("mouse %d %d", $_GET["x"], $_GET["y"]);
    if (isset($_GET["b"]))
      {
        $b = $_GET["b"];
        if ($b&65536)
          $o = sprintf("%s %d", $s, $b&65535);			# drag
        else
          $o = sprintf("%s 0\n%s %d\n%s 0", $s, $s, $b, $s);	# click
      }
  }
elseif (isset($_GET["l"]))
  {
    $a = explode("\n",$_GET["l"]);
    $s = "learn ".$a[0];
  }
else
  die('wrong request');

fclose(send($o=="" ? $s : $o));
echo $s;
flush();

