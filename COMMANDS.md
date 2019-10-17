# rfbimg command interface

To send a single command sequence:

	./sendsock.py NR 'cmd1 args' 'cmd2 args' .. && echo all commands OK || echo something failed

To access the command interface:

	socat unix:sub/NR/sock -
	prompt

## Commands

Not all commands are explained here in detail.  A full list can be found via `help`:

- `help` to list all available commands
- `help command` to give some command help
- `mouse`, `key`, `code` to send things to RFB, see `help`

## Variables

In prompt mode and in macros (see below) you have variables.
Variables replace the string `{varname}` by their value.

- `set` to list all known variables
- `set var value` to set a variable
- `echo {var}` to show the variable contents

## Conditionals

- `if cmd args..` remembers the state of `cmd`, fails only on errors seen
  - fail means, the macro is terminated
- `then cmd args..` is executed, if if-state was success
- `else cmd args..` is executed, if if-state was failure
- `err cmd args..` is executed, if if-state was error
  - usually cannot happen as the macro terminates if `if` fails

## Macro

- `do MACRO arg..` runs the MACRO (see `sub/NR/web/o/MACRO.macro`)
  - this sets the variables `{1}`, `{2}` and so on to the first, second etc. argument
  - this is like `gosub` in Basic
  - Macros terminate at the first failure.  Use `if` to catch failures.
  - use `exit` to return from macro prematurely
  - macro fails if it does not end on `exit`
- `run macro arg..` as before, but also `exit`s automatically.
  - this is like `goto` in Basic

## Learning

- `learn NAME` writes file to `sub/NR/l/NAME.png`

	send keystroke with key NNNN

- `check template..` checks for a match of the given template.
  - Use `edit.html` to create templates.
- `state template..` as before, wirtes `sub/NR/s/TEMPLATE.png` on match

