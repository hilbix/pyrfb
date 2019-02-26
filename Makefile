# Makefiles not war
#
# This Works is placed under the terms of the Copyright Less License,
# see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

DIRS=sub/1 sub/2 sub/3

.PHONY: all
all:	$(DIRS)

$(DIRS):
	ln -nsf '../$@/web' "web/`basename -- '$@'`"
	ln -nsf .pyrfb "autostart/pyrfb-`basename -- '$@'`.sh"
	mkdir -pm 775 sub
	mkdir -m 775 '$@' '$@/web' '$@/web/l'
	mkdir -m 1777 '$@/web/c' '$@/web/e'

clean:
	rm -f *.pyc

debian:
	sudo apt-get install python-twisted python-pil

