# PyRFB

Wrappers around python-vnc-viewer to be used from shell level

Prerequisites:

- Python 2.7
- Probably some of my tools, see https://github.com/hilbix/src
- Linux (perhaps it works with CygWin)


## Usage

```bash
git clone https://github.com/hilbix/pyrfb.git
cd pyrfb
git submodule update --init
vim conf.inc
make
```

- Export directory `web/` to your web root which is PHP enabled.  For example to make it available under http://127.0.0.1/vnc/ you can try: `sudo ln --relative -s web /var/www/html/vnc`


## Contact

Eventually I notice communication on GitHub via:

- Issues: https://github.com/hilbix/pyrfb/issues
- Pull requests: https://github.com/hilbix/pyrfb/pulls

To reach me directly you can try my Pager:

https://hydra.geht.net/pager.php

(Note: Messages, which are marked "important" but are not important for me, are usually undestood as SPAM and hence will be ignored.)



## OLD text

This is the old text.  It might be wrong or worse:

```
Change into a secure directory and copy everything there.  Then do:
	mkdir learn c e
	chmod 1777 e

Create a PHP web directory:
	mkdir /var/www/vnc

Link all neccessary things there:
	for a in .sock *.js *.php learn *.html test.jpg
	do
		ln -s "`realpath "$a"`" /var/www/vnc/
	done

Start a local VNC server:
	Xvnc4 :0 -desktop "`hostname -f`" -localhost -nolisten tcp -rfbwait 30000 -nopn -SecurityTypes None -geometry 1000x1100 :0

Start image grabber, this currently is hardwired to 127.0.0.1:5900:
	nice -99 ./rfbimg.py 1 test.jpg JPEG 18
	# If this does not work look into easyrfb.py to see what it needs

Open run.html in your browser:
	echo http://`hostname -f`/vnc/run.html
	firefox http://www.example.com/vnc/run.html

If you want to do more:
	Look into rfbmove.py

License:
	All work without Copyright is CLL, if not otherwise stated.
	CLL is PD disallowing Copyrights.  See COPYRIGHT.CLL
```
