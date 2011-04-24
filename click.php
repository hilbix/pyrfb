<?
# $Header$
#
# Simple PHP wrapper to forward commands to rfbimg.py socket.
# THIS IS INHERENTLY INSECURE IF EXPOSED TO THE WORLD.
# So protect it with BasicAuth and HTTPS, you have been warned.
#
# $Log$
# Revision 1.4  2011/04/24 22:36:31  tino
# saner run (less warnings)
#
# Revision 1.3  2011-03-23 10:01:03  tino
# Mouse button select
#
# Revision 1.2  2010-11-16 08:08:51  tino
# README added

header("Content-type: text/plain");
header("Pragma: no-cache");
header("Expires: -1");

$fd = fsockopen("unix://.sock");
socket_set_blocking($fd,0);
$o="";
$s="";
if (isset($_GET["c"]))
  {
    $o = sprintf("code %d", $_GET["c"]);
    $s = sprintf("code 0x%04x\n", $_GET["c"]);
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
?>
