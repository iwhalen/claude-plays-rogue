# Rogomatic for LLMs

![VHS gif of rogomatic-llm](static/demo.gif)

> Make your own animations like this with [VHS](https://github.com/charmbracelet/vhs). 

The goal of this repo is to play Rogue with LLMs.

It uses a modified version of the Rogue Collection that can be found [here](https://github.com/iwhalen/Rogue-Collection).

## Quickstart

> [!Warning]
> This code has only been tested on WSL2 Ubuntu 24.04. 

First, clone the repo recursively to pull in the custom version of Rogue Collection.

``` bash
git clone --recursive https://github.com/iwhalen/rogomatic-llm.git
cd rogomatic-llm
```

To get Rogue running, run the following:

``` bash
make install
make build-rogue
make run-rogue
```

This should open a window where you can play Rogue!

## AI mode

First, create a `.env` with your API key in it:

``` bash
cp .env.sample .env
```

By default, this works with Sonnet-4.6.

``` bash
uv run rogomatic-llm
```

Once running, you should see output like the `.gif` above.

## Human mode

Originally made for testing, you can also play from your terminal with "human" mode.

``` bash
uv run rogomatic-llm --player human
```

You should see something like this, which means you're ready to play.

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

This is no different from regular old Rogue from the GUI (i.e., with `make run-rogue`). 

To exit, send a CTRL+C signal.

You won't be able to save, resize, or do anything else. So, if you only want to play Rogue, run `make run-rogue` instead.

## CLI

For more options in the CLI, run `uv run rogomatic-llm --help`:


``` bash                                                                             
 Usage: rogomatic-llm [OPTIONS]                                                    
                                                                                   
 Main typer application. Starts the play session with the given options.           
                                                                                   
╭─ Options ───────────────────────────────────────────────────────────────────────╮
│ --player                    [human|llm]               Type of player.           │
│                                                       [default: llm]            │
│ --rogue-path                PATH                      Path to the rogue         │
│                                                       executable.               │
│                                                       [default:                 │
│                                                       rogue-collection/build/r… │
│ --rogue-version             [unix rogue 3.6.3|unix    Rogue version to play.    │
│                             rogue 5.2.1|unix rogue    [default: Unix Rogue      │
│                             5.3|unix rogue 5.4.2]     5.4.2]                    │
│ --model                     TEXT                      PydanticAI compatible     │
│                                                       Agent model string.       │
│                                                       [default:                 │
│                                                       anthropic:claude-sonnet-… │
│ --max-history               INTEGER                   Number of recent          │
│                                                       action/result pairs to    │
│                                                       retain in AI context.     │
│                                                       [default: 25]             │
│ --action-delay              FLOAT                     Seconds to wait between   │
│                                                       actions in LLM mode.      │
│                                                       [default: 0.5]            │
│ --install-completion                                  Install completion for    │
│                                                       the current shell.        │
│ --show-completion                                     Show completion for the   │
│                                                       current shell, to copy it │
│                                                       or customize the          │
│                                                       installation.             │
│ --help                                                Show this message and     │
│                                                       exit.                     │
╰─────────────────────────────────────────────────────────────────────────────────╯

```

## Development

The dev setup for this repo is quite minimal. The two commands worth running are:

``` bash
make lint
make test
```

The test suite is quite minimal. Not much is actually tested.