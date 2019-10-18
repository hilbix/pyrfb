#!/bin/bash
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

MIN=5
FAST=30
SLOW=60
DELAY=1000

cd "$(dirname "$(readlink -e "$0")")/.." || exit
ID="`basename -- "$0" .sh`" || exit
ID="${ID##*[^0-9]}"

t=1
while	! [ -f INHIBIT ] && ! read -t$t t && printf '%(%Y%m%d-%H%M%S)T '
do
	v="$(./sendsock.py "${1:-$ID}" 'run trig')"
	ret=$?
	printf '%q: %q\n' "$ret" "$v"
	let t=MIN+RANDOM%FAST
	[ 0 = $ret ] || let t=SLOW+RANDOM%DELAY
done

