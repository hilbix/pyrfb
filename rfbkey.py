#!/usr/bin/env python
#
# $Header$
#
# Send keyboard input
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# Usage:
#	python rfbkey.py "string" "string" ...

from __future__ import print_function

import easyrfb

import sys
import os

def keyval(s):
        if s[0]=='\\':
                return False
        n = easyrfb.getKey(s)
        if n:
                return n
        if s[0]!='=':
                return False
        try:
                return int(s[1:],0)
        except:
                return False

class rfbKey(easyrfb.client):

    def __init__(self, argv):
        easyrfb.client.__init__(self)
        self.sequence	= []
        for a in argv:
                mode	= '_'
                if a[0] in '_+-':
                        mode	= a[0]
                        a	= a[1:]
                keys	= keyval(a)
                if keys==False:
                        if a[0]=='\\':
                                a	= a[1:]
                        keys	= []
                        for b in a:
                                keys.append(ord(b))
                else:
                        keys	= [keys]
                for b in keys:
                        if mode in '_+':
                                self.sequence.append((b,1))
                        if mode in '_-':
                                self.sequence.append((b,0))

    def connectionMade(self, vnc):
        print("connection made")

    def vncConnectionMade(self, vnc):
        for a,b in self.sequence:
                print("typing 0x%02x %d" % (a, b))
                vnc.keyEvent(a,b)
        vnc.framebufferUpdateRequest()

    def beginUpdate(self, vnc):
        print("done")
        self.halt()

if __name__=='__main__':
        if len(sys.argv)==1:
                print("Usage: %s key.." % (sys.argv[0]))
                print("\t+key for press, -key for release, _key for both.")
                print("\t=key to send the given key number")
                print("\t\\key for literal key if ambiguous (use \\\\ for \\)")
                print("\tSpecial keys:", end='')
                for a in sorted(easyrfb.getKeys()):
                        print('', a, end='')
                print('')
                sys.exit(1)
        rfbKey(sys.argv[1:]).run()

