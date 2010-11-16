<?
header("Content-type: text/plain");

$fd = fsockopen("unix://.sock");
socket_set_blocking($fd,0);
$o="";
$s="";
if ($_GET["c"]!="")
  {
    $o = sprintf("code %d", $_GET["c"]);
    $s = sprintf("code 0x%04x\n", $_GET["c"]);
  }
elseif ($_GET["t"]!="")
  {
    $a = explode("\n",$_GET["t"]);
#    $s = "key ".$a[count($a)-1];
    for ($i=count($a); --$i>=0; ) {
      $s = "key ".$a[$i]."\n$s";
      if ($i)
        $s = "code 10\n$s";
    }
  }
elseif ($_GET["x"])
  {
    $s = "mouse ".$_GET["x"]." ".$_GET["y"];
    $o = "$s\n$s 0\n$s";
  }
elseif ($_GET["l"])
  {
    $s = "learn ".$_GET["l"];
  }
if ($o=="") $o = $s;
fwrite($fd,"$o\n");
fflush($fd);
fclose($fd);
echo $s;
flush();
?>
