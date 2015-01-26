pypkjs
======

PebbleKit JS in Python!

Setup
-----

To get started clone the repo and submodules:

    git clone git@github.com:pebble/pypkjs.git
    git submodule update --init --recursive

Set up a virtualenv and install everything

    virtualenv .env
    source .env/bin/activate
    pip install -r requirements.txt

Running
-------

You'll need to get [QEMU](https://github.com/pebble/qemu) running and find some pbws.
Then invoke jskit like this:

    ./jskit.py localhost:12344 app1.pbw app2.pbw ...

It'll connect to the running QEMU instance (assuming it's serving bluetooth on port 12344,
as is the default) and provide JavaScript for the given PBWs.

You can also run it like this:

    ./phonesim.py

Then you can use the standard `pebble` command, giving `--phone localhost`, like so:

    pebble install --phone localhost --logs

Configuration Pages
-------------------

Configuration pages are supported, but the pages must be modified. We cannot catch the
`pebble://close` link, so instead we add a `return_to` query param. Your configuration
page should check for the presence of `return_to` and, if present, use it in place of
`pebble://close#`. In its absence, it should behave as before (to support the real
mobile apps).

To open a configuration page using the command-line runner (`jskit.py`), send the running
process `SIGUSR1` (e.g. using `kill -SIGUSR1 somepid`). Configuration pages are not
currently supported using the phonesim setup.

Platforms
-------

Mac OS (10.10) and Linux are tested. Windows won't work.
