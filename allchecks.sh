#!/bin/bash

[ -n "$*" ] || set -- e/*.tpl

for a
do
	b="${a#*/}"
	b="${b%.tpl}"
	./sendsock.py "check $b" >/dev/null &&
	echo -n " $b"
done
echo
