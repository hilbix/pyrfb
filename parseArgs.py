#
# Easy Args Parser

# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# Usage:
#
#

import sys

# Why is option processing always so complex?
# Why is there no easy and extremely simple to use standard?
#	python rfbimg.py [0|1|2 [filename [type [quality]]]]
class parseArgs(object):
	"""
args = parseArgs(Null, [ argumentdef ], "Usage-text")

# Or for more complex parsing needs:

class MyArgs(parseArgs):
	usage = "Usage-Text"
	opts = [ argumentdef ]
	
	def parse_TYPE(self, arg, rest, args):
		if rest is None:
			self.arg[arg] = args[1]	# consumed next arg
			return 1
		self.arg[arg] = rest
		return 0	# consumed nothing else

args = MyArgs()

# You then get the arguments dict as:
	args.get_dict("name1 name2 name3")
# or as array:
	args.get_list("name1 name2 name3")

# adugmentdef is a comma separated list of strings as follows:

'name'		binary option, False by default
'name?'		ternary: None (default), True, False
'name='		option, default=None
'name=default'	option with given default
'name,TYPE'	use parse_TYPE() function, default=None
'name,TYPE,def'	use parse_TYPE() function, given default

Predefined types, replace ',TYPE,':

'#'		numeric (integer)
'##'		numeric (floating point)
':'		'host:port'

	"""
	def __init__(self, args=None):

		if args is None:
			args = sys.argv
		self.arg0 = args[0]

class parseRfbArgs(parseArgs):
	opts = [ 'host:', 'loop=.sock', 'img=rfbimg.jpg', 'type', 'quality#', 'mouse' ];

if __name__=='__main__':
	opts = parseRfbArgs()
        
	img = rfbImg(sys.argv[1:], "RFB image writer")
	if img.loop:
		createControl(".sock", img)
	img.run()

