<?php
# Send a PING to the backend, should output PONG
# (Checks backend alive.)
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

header("Content-type: text/plain");
header("Pragma: no-cache");
header("Expires: -1");

$targ = int(substr($_SERVER["PATH_INFO"],1));

$fd = fsockopen("unix://../$targ/sock");
socket_set_blocking($fd,0);
fwrite($fd,"ping\n");
fflush($fd);
echo fread($fd,4096);
fclose($fd);
flush();

