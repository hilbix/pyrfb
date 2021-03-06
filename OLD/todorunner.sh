#!/bin/bash
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# For used tools see:
#	http://www.scylla-charybdis.com/tool.php/keypressed
#	http://www.scylla-charybdis.com/tool.php/dirlist

list()
{
dirlist todo
}

run()
{
now="."
old="."
while	[ -z "$now" ] || [ ".$now.$now" != ".$was.$old" ] && ! keypressed && echo && echo "RETRY" && echo
do
	old="$was"
	was="$now"
	./todo.sh
	now="`list`"
done
true
}

while	! keypressed
do
	run
	echo WARN waiting > /tmp/poststat.ok.10000.service.easyrfb
	echo "WAITING"
	while	[ ".$now" = ".$was" ] && ! keypressed 5000 && echo -n .
	do
		now="`list`"
	done
done

