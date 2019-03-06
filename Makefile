# Makefiles not war
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

SCREENS=3	# this is an example

.PHONY: all
all:
	autostart/.setup $(SCREENS)

clean:
	rm -f *.pyc
	autostart/.setup 0

debian:
	sudo apt-get install python-twisted python-pil

