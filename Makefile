# Makefiles not war
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

.PHONY: all
all:	web/c web/e web/learn

web/c web/e:
	mkdir -m 1777 $@

web/learn:
	mkdir -m 775 web/learn

clean:
	rm -f *.pyc

debian:
	sudo apt-get install python-twisted python-pil

