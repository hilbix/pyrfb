#!/bin/bash

list()
{
dirlist todo
}

run()
{
now=""
while	[ -z "$now" ] || [ ".$now" != ".$was" ] && ! keypressed && echo && echo "RETRY" && echo
do
	was="$now"
	./todo.sh
	now="`list`"
done
true
}

while	! keypressed
do
	run
	echo "WAITING"
	while	[ ".$now" = ".$was" ] && ! keypressed 120000 && echo -n .
	do
		now="`list`"
	done
done

