#!/usr/bin/env python
#
# $Header$
#
# Send cmd to socket
#
# $Log$
# Revision 1.1  2011/01/21 16:23:02  tino
# Just a quick and dirty thing to send commands to the rfbimg.py .sock
#

import sys
import os
import socket

def unixsocket(name):
	sock = socket.socket(socket.AF_UNIX)
	sock.connect(name)
	return sock

def get(err):
	while True:
		s = sock.recv(4096)
		if not s and err!=0:
			print "err EOF"
			sys.exit(err)
		if s=="ok\n" or not s:
			return
		print s,

sock = None
def send(s):
	sock.sendall("%s\n" % s)
	get(1)

if __name__=='__main__':
	sock = unixsocket(".sock")
	for arg in sys.argv[1:]:
		send(arg)
	send("exit")
	get(0)

