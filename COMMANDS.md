# rfbimg commands

`./sendsock.py NR 'cmd1 args' 'cmd2 args' .. && echo all commands OK || echo something failed`

none
	Default command which just prints error and terminates connection

`if cmd [args..]`
- This remembers the state of the given command.  So `if exit` sets the state to True.
- Note that this catches `exit`, so you can return early from command.
- `if` returns `True` for normal `cmd` termination (`True` or `False`) and `False` if `cmd` errors

`then cmd [args..]`
- Process cmd if state is True (command succeeded)

`else cmd [args..]`
- Process cmd if state is False (command failed)

`err cmd [args..]`
- Process cmd if state is Error (like file not found)
- Note that this cannot be reached in macros,
- as `if` returns `False` on errors, which means the `sub` terminates

`sub macro`
- Macros are files in subdirectory `o/`, which are processed line-by-line
- This shortcuts and terminates at the first command which fails.
- If you do not want this, then prefix all commands in the macro with `if`.
- This then still terminates on errors.
- If you do not want this, then prefix all commands with `if if`.

`run macro`
- same as: `sub macro` followed by `exit`

`mouse x y [click]`
- move mouse to `x` `y`
- then press the given mouse button
- 1 is the left button
- 2 is the middle button
- 4 is the right button
- and so on
- If `click` is missing or 0, the button is released
- You can press multiple buttons at once.
- You can drag by not releasing the button.

`mouse template [nr [click]]`
- move mouse to the first template region, randomnized position
- nr is the number of mouse movement events to send (0=none intermediate)
- click is as before
- Note that the mousemove is relative to the last pointer position

`learn [filename]`
- it is written to `l/filename.png`
- "learn" (write out) the current screen to the given file.
- Do not use this in parallel on several command (this currently has a race then)
- If name is missing it will be `screenshot-NUMBER` with some obsucre `NUMBER`

key String
	send the given string as keystrokes

code	NNNN
	send keystroke with key NNNN

code	KEY
	send KEY.  To list all KEYs see ./rfbkey.py
	Note that `rfbkey` can type arbitrary sequences,
	while this here can just send keystrokes.

exit
	This always must be the last command,
	else it fails.  This is implicite with `./sendsock.py`
	
next
	Waits for the next flush to happen.
	You rarely need this, but it can come handy
	to give the backend a chance to catch up with
	changes on the screen.

flush
	Forces a writeout of the current screen sample
	for the web frontend.  (You normally do not need it.)

check template..
	Check for one of the given templates.
	The first one wins and it's name is printed along with the offset found.
	Does nothing win, then this is an error.
	To create templates, see 'edit' mode on the web.
	Templates are found in `web/NR/e/*.tpl`
	Note that you can invert the match using `!`,
	so `!template` means success if the template does not match.
	(in that case it is not `found`, it is `spare`).

state template..
	Similar to check, but also
	saves the state (image) of the found TEMPLATE as s/TEMPLATE.png

wait count template..
	Wait for some given template to show up.
	This is like check but a bit more efficient than direct polling.
	Note that the count means screen updates.
	So it is neither seconds nor some time base,
	just iterations done to find the given template.
	Usually you will see 10-20 refreshs on an active screen
	while 1-3 on an idle screen.

ping
	prints pong


# Templates

Templates can be edited with the edit frontend as follows:

- Mouse selects the rectangle (use `[X]` to remove rectangle)
- Cursor moves the selected rectangle
- Shift-Cursor resizes the selected rectangle
- Ctrl switches to 1 pixel speed
- `q` `w` `e` `r` `t` increases dirt (1, 10, 100, 1000, 10000)
- `a` `s` `d` `f` `g` decreases dirt (1, 10, 100, 1000, 10000)

All rectangles in a template must match!
Dirt is the maximum delta allowed (quadratic) to mismatch in the pixels.

## horzontal/vertical displacements

If there are horizontal/vertical 0 width/height rectangles
(those would always match) these define search direction.

In that case all other rectangles will be moved along the given axis
to find a match.  (This is combinatoric and should be used sparingly.)
Note that position right/below of the middle of the screen inverts search direction.
(This is experiental and likely to change.)

The found offset is output on "check", so you can adjust accordingly.


## clicks

If a template is used to do a click, this is done on the first region of a template.
The position is randomnized on this region.

