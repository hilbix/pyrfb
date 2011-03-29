#!/bin/bash
# $Header$
#
# $Log$
# Revision 1.4  2011/03/29 21:02:35  tino
# Generic version independent of scripts
#
# Revision 1.3  2011-03-23 09:59:06  tino
# much better but not independent of the target currently
#
# Revision 1.2  2011-03-16 20:18:20  tino
# Added parameter support

set_exit()
{
atexit="$*"
}

exe()
{
. script/X
. "script/$script"
}

d()
{
[ -z "$1" ] && return
echo -n " .."

snapshot=
echo -n " $1"

script="$1"
exe $2

if [ -n "$snapshot" ]
then
	cp test.jpg "c/$snapshot.jpg"
	echo -n " $snapshot.jpg"
fi
}

run()
{
atexit=""
while	read -ru3 cmd args
do
	d "$cmd" "$args"
done

[ -n "$atexit" ] && d $atexit
}

d restart

tim=1
while
	if	read -rt$tim cmd args
	then
		[ -n "$cmd" ] || exit
		case "$cmd" in
		\!*)	cmd="${cmd:1}"
			set -x;;
		esac
		d "$cmd" "$args"
		set +x
		echo
		tim=1
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

	echo -n "RUN"
	run 3<"todo/$next"
	echo -n " "
	rm -vf "todo/$next"
done

