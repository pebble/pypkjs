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
    pip install -r requirements

Running
-------

You'll need to get [QEMU](https://github.com/pebble/qemu) running and find some pbws.
Then invoke jskit like this:

    ./jskit.py localhost:12344 app1.pbw app2.pbw ...

It'll connect to the running QEMU instance (assuming it's serving bluetooth on port 12344,
as is the default) and provide JavaScript for the given PBWs. If one is already running,
you will have to leave and restart it.

Platforms
-------

Mac OS (10.10) is tested. Linux is expected to work, but is untested. Windows won't work.
