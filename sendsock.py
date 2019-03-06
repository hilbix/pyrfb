#!/usr/bin/env python
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

def unixsocket(name):
	sock = socket.socket(socket.AF_UNIX)
	sock.connect(name)
	return sock

def get(err):
	sock.flush()
	while True:
		s = sock.readline()
		if not s and err!=0:
			print "EOF"
			sys.exit(err)
		if s=="ko\n":
			sys.exit(err)
		if s=="ok\n" or not s:
			return
		print s,

sock = None
def send(s):
	sock.write("%s\n" % s)
	get(1)

if __name__=='__main__':
	sock = unixsocket('sub/'+sys.argv[1]+'/sock').makefile()
	if len(sys.argv)==2:
		for arg in sys.stdin.readlines():
			send(arg.strip())
	else:
		for arg in sys.argv[2:]:
			send(arg)
	send("exit")
	get(0)

