#!/bin/bash
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

[ -n "$*" ] || set -- e/*.tpl

for a
do
	b="${a#*/}"
	b="${b%.tpl}"
	./sendsock.py "check $b" >/dev/null &&
	echo -n " $b"
done
echo
