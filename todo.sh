#!/bin/bash
# $Header$
#
# $Log$
# Revision 1.3  2011/03/23 09:59:06  tino
# much better but not independent of the target currently
#
# Revision 1.2  2011-03-16 20:18:20  tino
# Added parameter support
#

STDWAIT=12

exe()
{
(
. script/X
script="$1"
shift
. "$script"
) >/dev/null
}

d()
{
echo -n " .."
case "$2" in
save)	j="$c"; return;;
-)	c=; return;;
esac

keypressed "${1:-$STDWAIT}000" && exit

if [ -n "$j" ]
then
	cp test.jpg "c/c$j.jpg"
	echo -n " c$j.jpg"
	j=''
fi
[ -z "$2" ] && return

have=:
echo -n " $2"
exe "script/$2" $3

j=
case "$2" in
city)	j="$c";;
bau)	j="b$c";;
dom)	c=1; city="$2";;
tank)	c=2; city="$2";;
spat)	c=3; city="$2";;
gral)	c=4; city="$2";;
bust)	c=5; city="$2";;
wanne)	c=6; city="$2";;
bank)	c=7; city="$2";;
mimo)	c=8; city="$2";;
L)	j=9;;
mil)	j=a;;
sci)	j=b;;
diplo)	j=c;;
info)	j=d;;
esac
}

run()
{
read -ru3 city || return

j=
c=

d 1 "$city"
if [ -n "$c" ]
then
	d 5 city
	d 5 "$city"
	d 5 city
fi

have=false
while	read -ru3 cmd args
do
	d '' "$cmd" "$args"
done

[ -n "$c" ] && $have && d '' city
[ -n "$j" ] && d
}

tim=0
while
	if	read -rt$tim cmd args
	then
		[ -n "$cmd" ] || exit
		d 0 "$cmd" "$args"
		echo
		tim=0
		continue
	fi

	now="$(date +%Y%m%d-%H%M%S)"
	next="$(dirlist todo | sort | head -1)"

	echo -n "$now $next "

do
	tim=12

	case "$next" in
	'')		continue;;
	[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9])	;;
	*)		echo -n " OOPS"; continue;;
	esac

#	[ ".$next" = ".$last" ] || [ -z "$last" ] || echo
	last="$next"
	expr ":$next" \< ":$now" >/dev/null || continue

	exec 3<"todo/$next"
	echo -n "RUN"
	run
	echo -n " "
	rm -vf "todo/$next"
	exec 3<&-
done

