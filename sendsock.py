#!/usr/bin/env python
#
# $Header$
#
# Send cmd to socket
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# $Log$
# Revision 1.3  2011/08/07 18:24:36  tino
# CLL
#
# Revision 1.2  2011-03-29 21:01:16  tino
# Working version with stdin support
#
# Revision 1.1  2011-01-21 16:23:02  tino
# Just a quick and dirty thing to send commands to the rfbimg.py .sock

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
	sock = unixsocket(".sock").makefile()
	if len(sys.argv)==2 and sys.argv[1]=='-':
		for arg in sys.stdin.readlines():
			send(arg.strip())
	else:
		for arg in sys.argv[1:]:
			send(arg)
	send("exit")
	get(0)

