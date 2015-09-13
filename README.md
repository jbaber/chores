# chores

These modules let members of your household register that they have
done chores by visiting a site running on your LAN (e.g. on a
raspberry pi in a cabinet somewhere on your Wifi) with their
phones or desktop computers.  A running weekly score is kept
with a weekly winner recorded à la fitbit.  Gamify the dishes.

QR Codes are provided that let chore registration happen by
just snapping a picture.  You can also use the QR code addresses
to make tapping an NFC tag register a done chore.

# TO RUN

- `python -Bm chores_api.chores_api` starts the webserver that talks to the database.  By default, it listens on port 8190.
- `python -Bm clients.web.chores_web_server` starts the webserver that hosts the web interface for updating chores.  By default, it listens on port 8180.

# This is still a very rough draft.

# Issues

In ubuntu 14.04 LTS (Trusty Tahr), the version of `six` that comes
with python is not recent enough for `furl` to work and running `chores_webpage_server.py`
gets you

```
AttributeError: 'Module_six_moves_urllib_parse' object has no attribute 'SplitResult'
```

You must

```sudo apt-get purge python-six```

then

```sudo pip install six```

to get a later version installed.
