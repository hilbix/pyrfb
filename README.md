> It works, but is in it's very early stages.
>
> TODOs:
>
> - Python 3 compatibility (`python-vnc-viewer` currently is Python 2 only)
> - Better experience
> - More easy install
> - Integrate noVNC, such that you can use it as you like
> - A lot of improvements (99% to come over the years)


# PyRFB

Wrappers around `python-vnc-viewer` to create a web based VNC control.

> There is a [JavaScript/WebSocket driven VNC client](https://github.com/novnc/).
> However this is meant for online connections which allow high bandwidth (100 KB/s and above)
>
> This here is meant to control VNC via smallband (<8 KB/s):
>
> - download a picture
> - send command sequences to the VNC (clicks, keypresses, etc.)
> - download a picture again to see the progress/outcome

Prerequisites:

- Python 2.7 and Python 3.x (transitioning to Python 3 slowly)
- Some of my tools, see https://github.com/hilbix/src
- Linux (perhaps it works with CygWin)
- NginX with PHP-FPM


## Usage

	git clone https://github.com/hilbix/pyrfb.git
	cd pyrfb
	git submodule update --init
	make

- Export directory `web/` to your web root.
  For example to make it available under `http://127.0.0.1/vnc/` try:  
  `sudo ln --relative -s web /var/www/html/vnc`

- Serve PHP files from the `php/` directory.  
  If your web root is PHP enabled, you can do  
  `ln --relative -s php/* web`

- Be sure to restrict access to the web directory, as else anybody can send commands.

- Start `Xvnc` or similar:

	Xvnc4 :0 -desktop "`hostname -f`" -localhost -nolisten tcp -rfbwait 30000 -nopn -SecurityTypes None -geometry 1000x1100 :1

- Run image grabber and control service (for all parameters see header comment in `rfbimg.py`):

	RFBIMGLOOP=1 RFBIMGVIZ=1 RFBIMGQUAL=18 EASYRFBPORT=5900 nice -99 ./rfbimg.py

Note that this must run permanently.  [See `autostart/` for details](autostart/.readme.md).


## License

Note that some parts have a different license.
For the most parts, following "license" applies:

This Works is placed under the terms of the Copyright Less License,
see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

Read: This is free as in free beer, free speech and freely born baby.


## FAQ

How to contact you?

- Eventually I notice communication on GitHub via:  
  Issues: https://github.com/hilbix/pyrfb/issues  
  Pull requests: https://github.com/hilbix/pyrfb/pulls

Debian Requisites?

- `make debian`

