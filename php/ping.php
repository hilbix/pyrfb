<?php
# Send a PING (or some easy commands) to the backend,
# should output PONG (or the command output).
#
# GET	ping.php/${V}		send "ping", expects "pong"
# GET	ping.php/${V}/		send "ping", expects "pong"
# GET	ping.php/${V}/ping	send "ping", expects "pong"
# GET	ping.php/${V}/stop	send "stop", expects "pong"
# GET	ping.php/${V}/${other}	currently: "ping"
#
# ${V} is the VNC number
#
# default:	Checks backend alive.
# c=exit:	Lets backend exit (it comes back) for resynchronization
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

require 'sock.inc';

plain();
args(2,3);

#foreach ($_SERVER as $k=>$v)
#  printf("%20s = %s\n", $k, json_encode($v,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

switch (isset($pi[2]) ? $pi[2] : '')
{
  case 'stop':	$cmd	= 'stop'; break;
  default:	$cmd	= 'ping'; break;
}

send_receive($cmd);

