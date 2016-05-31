#
# Easy Args Parser

# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.
#
# Usage:
#
#

import sys
from __future__ import print_function

# Why is option processing always so complex?
# Why is there no easy and extremely simple to use standard?
#	python rfbimg.py [0|1|2 [filename [type [quality]]]]
class parseArgs(object):
	"""
args = parseArgs(Null, [ argumentdef ], "Usage-text")

# Or for more complex parsing needs:

class MyArgs(parseArgs):
	usage = "Usage-Text"
	args = [ argumentdef ]
	
	def parse_TYPE(self, arg, rest, args):
		if rest is None:
			self.arg[arg] = args[1]	# consumed next arg
			return 1
		self.arg[arg] = rest
		return 0	# consumed nothing else

args = MyArgs()

# Get arguments as array:
	args.get_list("name1 name2 name3")
# or as dict:
	args.get_dict("name1 name2 name3")
# or as dict with renaming:
	args.get_dict("name1:nameA name2:nameB name3:nameC")

# argumentdef is a comma separated list of strings, as follows:

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

Additional variants you can set:

	parseArgs.delim='--'
	parseArgs.first=['-','--']	# use '' for DD type args
	parseArgs.assing=['=']
	"""

	slef
	def __init__(self, argv=None, args=None, usage=None):

		if argv is None:
			argv = sys.argv
		self.arg0 = argv[0]

		if args is None:  args  = self.args
		if usage is None: usage = self.usage

		

	def usage(self):
		print("Usage: {0}", self.arg0)
		sys.exit(42)

