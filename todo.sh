#!/bin/bash
# $Header$
#
# $Log$
# Revision 1.1  2011/03/16 11:53:29  tino
# __() ___()
#

d()
{
echo -n " .."
case "$1" in
save)	j="$c"; return;;
-)	c=; return;;
esac

sleep ${2:-12}

[ -n "$j" ] && cp test.jpg c/c$j.jpg
[ -z "$1" ] && return

have=:
echo -n " $1"
export city
./".$1" >/dev/null

j=
case "$1" in
city)	j="$c";;
bau)	j="b$c";;
dom)	c=1;;
tank)	c=2;;
spat)	c=3;;
gral)	c=4;;
bust)	c=5;;
wanne)	c=6;;
bank)	c=7;;
mimo)	c=8;;
L)	j=9;;
mil)	j=a;;
sci)	j=b;;
diplo)	j=c;;
info)	j=d;;
esac
}

run()
{
echo -n " RUN"
read -ru3 city || return

j=
c=

d "$city" 1
if [ -n "$c" ]
then
	d city 5
	d "$city" 5
	d city 5
fi

have=false
while	read -ru3 cmd
do
	d "$cmd"
done

[ -n "$c" ] && $have && d city
[ -n "$j" ] && d
}

while	! keypressed 12345
do
	next="$(dirlist todo | sort | head -1)"

	now="$(date +%Y%m%d-%H%M%S)"
	echo -n "$now $next" || break
	case "$next" in
	'')		continue;;
	[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9])	;;
	*)		echo -n " OOPS"; continue;;
	esac

#	[ ".$next" = ".$last" ] || [ -z "$last" ] || echo
	last="$next"
	expr ":$next" \< ":$now" >/dev/null || continue

	exec 3<"todo/$next"
	run
	echo -n " "
	rm -vf "todo/$next"
	exec 3<&-
done

