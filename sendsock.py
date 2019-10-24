#!/usr/bin/env python3
#
# Send cmd to socket
# ./sendsock.py socketnr
# ./sendsock.py socketnr lines..
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

import sys
import os
import socket

OKPATTERN="---------------------------------------[[[OK]]]----------------------------------------"
KOPATTERN="---------------------------------------[[[KO]]]----------------------------------------"

def unixsocket(name):
	sock = socket.socket(socket.AF_UNIX)
	sock.connect(name)
	return sock

def get(err):
	sock.flush()
	while True:
		s = sock.readline()
		if not s:
			if err:
				print('EOF')
				sys.exit(err)
			return
		if s==KOPATTERN+'\n':
			sys.exit(err)
		if s==OKPATTERN+'\n':
			return
		sys.stdout.write(s)
		sys.stdout.flush()

sock = None
def send(s):
	sock.write("%s\n" % s)
	get(1)
	sys.stdout.flush()

if __name__=='__main__':
	sock = unixsocket('sub/'+sys.argv[1]+'/sock').makefile(mode='rw')
	send("success "+OKPATTERN)
	send("failure "+KOPATTERN)
	if len(sys.argv)==2:
		while True:
			arg	= sys.stdin.readline()	# interactively/unbuffered line by line
			if not arg: break
			send(arg.strip())
	else:
		for arg in sys.argv[2:]:
			send(arg)
	send("exit")
	get(0)

