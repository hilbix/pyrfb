#!/bin/bash
# $Header$
#
# $Log$
# Revision 1.7  2011/04/30 22:12:58  tino
# ls command added, initial timeout is 3 seconds to be able to do something (rm)
#
# Revision 1.6  2011-04-24 22:37:43  tino
# direct commands on the input, no more ./in needed
#
# Revision 1.5  2011-03-30 21:30:06  tino
# moved common functions here and fix for snapshotting
#
# Revision 1.4  2011-03-29 21:02:35  tino
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

die()
{
send "learn OOPS"
echo "ERROR: $*" >&2
date >&2
exit 1
}

assert()
{
"$@" || die "cannot $*"
}

IN()
{
./in "$@"
}

exe()
{
. script/X
. "script/$script"
}

send()
{
sendresult="`./sendsock.py "$@"`"
}

key()
{
for k
do
        case "$k" in
        _*)     echo "code ${k#_}";;
        *)      echo "key $k";;
        esac
done |
send - ||
die "cannot send key sequence: $*"
}

d()
{
if	$needrestart
then
	needrestart=false
	d restart
fi

[ -z "$1" ] && return
echo -n " .."

snapshot=
echo -n " $1"

script="$1"
exe $2

if [ -n "$snapshot" ]
then
	send flush
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

d2()
{
scr="$1"
shift
[ -f "script/$scr" ] || return 1
d "$scr" "$*"
return 0
}

d1()
{
for cc
do
	[ -s "script/LINKS/$cc" ] && read -r cc < "script/LINKS/$cc"
	cc="${cc//:/ }"
	d2 $cc || return
done
}

needrestart=:

tim=3
while
	if	read -rt$tim cmd
	then
		[ -n "$cmd" ] || exit
		tim=1
		case "$cmd" in
		\!*)	cmd="${cmd:1}"
			set -x
			;;
		[0-9]*)	./in $cmd
			continue
			;;
		todo/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9])	rm -vf "$cmd"; continue;;
		ls)	./list; continue;;
		esac
		d1 $cmd
		set +x
		echo
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

