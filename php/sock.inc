<?php
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

function plain()
{
  header("Content-type: text/plain");
  header("Pragma: no-cache");
  header("Expires: -1");
}

function get_POST_data()
{
  # fetch arguments from POST data
  return file_get_contents("php://input");
}

function send($s)
{
  GLOBAL $targ, $sock;

  $fd = fsockopen("unix://$sock");
#  $pwd	= getcwd();
#  $err = json_encode(error_get_last(),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
  if ($fd===FALSE) die("cannot open $targ");	# ($name) ($pwd) ($err)");

  socket_set_blocking($fd, 1);
  fwrite($fd,"$s\n");
  fflush($fd);
#  socket_shutdown($fd, 1);	# does not work with fsockopen()

  return $fd;
}

function send_receive($s)
{
  $fd	= send($s);

  while (!feof($fd) && !ferror($fd))
    {
      $s = fread($fd,4096);
      if ($s === FALSE)
        die("read error on $targ");
      echo $s;
    }
  fclose($fd);

  flush();
}

function args($n,$m)
{
  GLOBAL $cnt;

  if ($cnt<$n || ($m>=0 && $cnt>$m))
    die("wrong number of path arguments: $cnt (allowed $n-$m)");
}

$pi	= explode('/', $_SERVER["PATH_INFO"]);
$targ	= intval($pi[1]);
$sock	= "../sub/$targ/sock";
#$sock	= "sock:-1 (basic shuttle outflop)\n";

$root	= $_SERVER["DOCUMENT_ROOT"];
$script	= $_SERVER["SCRIPT_NAME"];      // this must be relative to document root
$base	= "$root/".dirname($script)."/$targ";
if (!is_dir($base)) die("wrong $targ");

$cnt	 = count($pi);

