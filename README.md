# PyRFB

Wrappers around `python-vnc-viewer` to be used from shell level
to dump/control RFB connections.

Prerequisites:

- Python 2.7 or later
- Probably some of my tools, see https://github.com/hilbix/src
- Linux (perhaps it works with CygWin)


## Usage

```bash
git clone https://github.com/hilbix/pyrfb.git
cd pyrfb
git submodule update --init
make
```
- Export directory `web/` to your web root which is PHP enabled.  
  For example to make it available under `http://127.0.0.1/vnc/` try:  
  `sudo ln --relative -s web /var/www/html/vnc`

- Start `Xvnc` or similar:

	Xvnc4 :0 -desktop "`hostname -f`" -localhost -nolisten tcp -rfbwait 30000 -nopn -SecurityTypes None -geometry 1000x1100 :1

- Run image grabber and control service (for all parameters see header comment in `rfbimg.py`):

	RFBIMGLOOP=1 RFBIMGVIZ=1 RFBIMGQUAL=18 EASYRFBPORT=5900 nice -99 ./rfbimg.py

	  Note that this must run permanently.  See `autostart/` for details.



## License

This Works is placed under the terms of the Copyright Less License,
see file COPYRIGHT.CLL.  USE AT OWN RISK, ABSOLUTELY NO WARRANTY.

Read: This is free as in free beer, free speech and freely born baby.

Note that some parts have a different license.

## FAQ

How to contact you?

- Eventually I notice communication on GitHub via:  
  Issues: https://github.com/hilbix/pyrfb/issues  
  Pull requests: https://github.com/hilbix/pyrfb/pulls

Debian Requisites?

- `make debian`

