#!/usr/bin/env python
#
# $Header$
#
# Send keyboard input
#
# Usage:
#	python rfbkey.py "string" "string" ...
#
# $Log$
# Revision 1.1  2011/03/16 11:53:29  tino
# __() ___()
#

import easyrfb

import sys
import os

def intval(s):
	try:
		return int(s,0)
	except:
		return False

class rfbKey(easyrfb.client):

    def __init__(self, argv):
	easyrfb.client.__init__(self)
	self.sequence = []
	for a in argv[1:]:
		if a[0]=="_" and intval(a[1:]):
			self.sequence.append(intval(a[1:]))
		else:
			for b in a:
				self.sequence.append(ord(b))

    def connectionMade(self, vnc):
	print "connection made"

    def vncConnectionMade(self, vnc):
	for a in self.sequence:
		vnc.keyEvent(a,1)
		vnc.keyEvent(a,0)
	vnc.framebufferUpdateRequest()

    def beginUpdate(self, vnc):
	self.halt()

if __name__=='__main__':
	rfbKey(sys.argv).run()

