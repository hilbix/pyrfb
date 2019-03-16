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

header("Content-type: text/plain");
header("Pragma: no-cache");
header("Expires: -1");

$targ = intval(substr($_SERVER["PATH_INFO"],1));

$fd = fsockopen("unix://../sub/$targ/sock");
if (!$fd) die("cannot open $targ");

socket_set_blocking($fd,0);
$o="";
$s="";
if (isset($_GET["c"]))
  {
    $a = intval($_GET["c"], 0);
    $o = sprintf("code %d", $a);
    $s = sprintf("code 0x%04x\n", $a);
  }
elseif (isset($_GET["t"]))
  {
    $a = explode("\n",$_GET["t"]);
#    $s = "key ".$a[count($a)-1];
    for ($i=count($a); --$i>=0; ) {
      $s = "key ".$a[$i]."\n$s";
      if ($i)
        $s = "code 10\n$s";
    }
  }
elseif (isset($_GET["x"]))
  {
    $s = sprintf("mouse %d %d", $_GET["x"], $_GET["y"]);
    if (isset($_GET["b"]))
      {
        $b = $_GET["b"];
        if ($b&65536)
          $o = sprintf("%s %d", $s, $b&65535);
        else
          $o = sprintf("%s\n%s %d\n%s", $s, $s, $b, $s);
      }
  }
elseif (isset($_GET["l"]))
  {
    $a = explode("\n",$_GET["l"]);
    $s = "learn ".$a[0];
  }
if ($o=="") $o = $s;
fwrite($fd,"$o\n");
fflush($fd);
fclose($fd);
echo $s;
flush();

