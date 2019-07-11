<?php
# Send a PING (or some easy commands) to the backend,
# should output PONG (or the command output).
#
# default:	Checks backend alive.
# c=exit:	Lets backend exit (it comes back) for resynchronization
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

header("Content-type: text/plain");
header("Pragma: no-cache");
header("Expires: -1");

#foreach ($_SERVER as $k=>$v)
#  printf("%20s = %s\n", $k, json_encode($v,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

$pi = explode('/', $_SERVER["PATH_INFO"]);
$targ = intval($pi[1]);

$name = "../sub/$targ/sock";
#$name = "sock:-1 (basic shuttle outflop)\n";
$pwd  = getcwd();
$fd = fsockopen("unix://$name");
$err = json_encode(error_get_last(),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
if (!$fd) die("cannot open $targ"); # ($name) ($pwd) ($err)");

switch (isset($pi[2]) ? $pi[2] : '')
{
  case 'stop':	$cmd	= 'stop'; break;
  default:	$cmd	= 'ping'; break;
}

socket_set_blocking($fd,1);
fwrite($fd,"$cmd\n");		# ping/exit
fflush($fd);
echo fread($fd,4096);
fclose($fd);
flush();

