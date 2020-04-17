<?php
# Simple PHP wrapper to forward commands to rfbimg.py socket.
# THIS IS INHERENTLY INSECURE IF EXPOSED TO THE WORLD.
# So protect it with BasicAuth and HTTPS, you have been warned.
#
# GET	click.php/{V}?c={C}		send numeric charcode {C}
# GET	click.php/{V}?k={K}		send alphanumeric key {K}
# GET	click.php/{V}?t={K}		send {K} as keys (k=) plus key Return
# GET	click.php/{V}?X={X}		mouse {X} 100	(move)
# GET	click.php/{V}?x={X}&y={Y}	mouse {X} {Y}	(move)
# GET	click.php/{V}?x={X}&y={Y}&b={B}	mouse {X} {Y} {B&0xffff}	{B&0x10000} then drag, else click
# GET	click.php/{V}?l={N}		save picture l/{N}.png
#
# BUGS:
#	- t= Uppercase does not work
#	- t= Special characts (like Linefeed) do not work
#	- l={N} uses only the first line of {N} as picture name and ignores the other lines
#
# {V} is the VNC number
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
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
    $s .= sprintf("code 0x%04x\n", $a);
  }
else if (isset($_GET["k"]))
  {
    $a = $_GET["k"];
    if (!ctype_graph($a)) die("k?");
    $o = sprintf("code %s", $a);
    $s .= sprintf("key %s\n", $a);
  }
elseif (isset($_GET["t"]))
  {
    $a = explode("\n",$_GET["t"]);
#    $s .= "key ".$a[count($a)-1]."\n";
    for ($i=count($a); --$i>=0; ) {
      $s = "key ".$a[$i]."\n$s";
      if ($i)
        $s = "code Return\n$s";
    }
  }
elseif (isset($_GET["x"]) || isset($_GET["X"]))
  {
    if (isset($_GET["X"]))
      $t	= sprintf('mouse %s %d', $_GET['X'], (isset($_GET['y']) ? $_GET['y'] : 100));
    else
      $t	= sprintf('mouse %d %d', $_GET["x"], $_GET["y"]);
    $s .= "$t\n";
    if (isset($_GET["b"]))
      {
        $b = $_GET["b"];
        if ($b&65536)
          $o = sprintf('%s %d', $t, $b&65535);			# drag
        else
          $o = sprintf("%s 0\n%s %d\n%s 0", $t, $t, $b, $t);	# click
      }
  }
elseif (isset($_GET["l"]))
  {
    $a = explode("\n",$_GET["l"]);
    $s .= "learn ".$a[0]."\n";
  }
else
  die('wrong request');

$s = trim($s);
if ($o=="") $o=$s;
fclose(send("push wait $s\n$o\n"));
echo $s;
flush();

