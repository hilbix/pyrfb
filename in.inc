#!/bin/bash
#
# Create entries in todo/
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# For used tools see:
#       http://www.scylla-charybdis.com/tool.php/mvatom


cd "`dirname "$0"`" || exit

OOPS()
{
echo "OOPS $*" >&2
exit 1
}

mins="$1"
case "$mins" in
*:*)	hours="${mins%%:*}"
	mins="${mins##*:}"
	let mins=hours*60+mins
	;;
esac

case "$mins" in
0)	;;
*)	let ++mins || OOPS "nonnumeric $mins";;
esac

secs=0
while	then="`date -d "+$mins min +$secs sec" +%Y%m%d-%H%M%S`" || OOPS invalid date
	! mvatom "$2" "todo/$then"
do
	let secs++
done

dump()
{
while read -r a
do
	echo -n " -- $a"
done < "$1"
echo
}

echo "`date +%Y%m%d-%H%M%S` $then`dump "todo/$then"`" >> log/IN.log

exit 0

