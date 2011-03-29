#!/bin/bash

for a in e/*.tpl
do
	b="${a#*/}"
	b="${b%.tpl}"
	./sendsock.py "check $b" >/dev/null &&
	echo -n " $b"
done
echo
