# Claude plays Rogue

The goal of this repo is to enable Claude to play the classic game Rogue.

It uses a modified version of the Rogue Collection that can be found here: [https://github.com/iwhalen/Rogue-Collection](https://github.com/iwhalen/claude-plays-rogue)

## Quickstart

> [!Warning]
> This code has only been tested on WSL2 Ubuntu 24.04. 

To get Rogue running, run the following:

``` bash
make install
make build-rogue
make run-rogue
```

This should open a window wher you can play Rogue!

## AI mode

TODO


## Human mode

Originally made for testing, you can also play from your terminal with "human" mode.

``` bash
uv run cpr --player human
```

You should see something like this, which means you're ready to play!

``` bash 
╭───────────────────────────────────── Rogue ──────────────────────────────────────╮
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                            --------------------+----                             │
│                            |...............@.......+                             │
│                            +/......................|                             │
│                            ------------+------------                             │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│                                                                                  │
│ Level: 1  Gold: 0      Hp: 12(12)  Str: 16(16)  Arm: 4   Exp: 1/0                │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

This is no different than regular old Rogue from the GUI. 

To exit, sent a CTRL+C signal.
