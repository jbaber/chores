#!/usr/bin/env python

"""chores_api.py

Usage:
  chores_api.py [<path/to/config_file.yaml>]
  chores_api.py (-h | --help)
  chores_api.py --version
  chores_api.py --config-skeleton

Options:
  -h --help                 Show this screen.
  --version                 Show version.
  path/to/config_file.yaml  Where preferences are stored [DEFAULT: "~/.config/chores_apirc.yaml"]
  --config-skeleton         Print out contents of a reasonable config file.
"""

version = '1.0.0'

import chores_controller
import bottle
import requests
import json
from chores_lib import datetime_to_string, \
    string_to_datetime, string_to_time, config_file_variables
import os
from docopt import docopt

@bottle.get('/chores')
def get_chores():
  # Because of CSRF, you shouldn't return a list of objects.
  return {'chores': controller.chores()}

@bottle.delete('/chores/<chore_id>')
def delete_chore(chore_id):
  controller.delete_done_chore(chore_id)

@bottle.get('/users')
def get_users():
  # Because of CSRF, you shouldn't return a list of objects.
  return {'users': controller.users()}

@bottle.put('/chores/<name>/<worth>')
def new_chore(name, worth):
  controller.new_chore(name, worth)

@bottle.route('/chores/<chore_id>', method='PATCH')
def change_chore(chore_id):
  received_values = json.loads(bottle.request.body.read())
  things_to_update = {}
  if 'worth' in received_values:
    things_to_update['worth'] = received_values['worth']
  if 'name' in received_values:
    things_to_update['name'] = received_values['name']
  if things_to_update != {}:
    controller.change_chore(chore_id, **things_to_update)

# `user_id` should be an integer
# `chore_id` should be an integer
# `done_datetime` should be formatted per datetime_to_string()
@bottle.put('/done_chores/<user_id>/<chore_id>/<done_datetime>')
def new_done_chore(user_id, chore_id, done_datetime):
  controller.new_done_chore(user_id, chore_id,
      string_to_datetime(done_datetime))

# `user_id` should be an integer
# `now_datetime` should be formatted per datetime_to_string()
# `rollover_day` should be a day fullname like 'Friday'
# `rollover_time` should be a 0-padded 24-hour time like '22:01'
@bottle.get('/weekly_score/<user_id>/<now_datetime>/<rollover_day>/<rollover_time>')
def weekly_score(user_id, now_datetime, rollover_day, rollover_time):
  return {'weekly_score': controller.weekly_score(user_id=user_id, now=string_to_datetime(now_datetime), rollover_day=rollover_day, rollover_time=string_to_time(rollover_time))}

# `now_datetime` should be formatted per datetime_to_string()
# `rollover_day` should be a day fullname like 'Friday'
# `rollover_time` should be a 0-padded 24-hour time like '22:01'
@bottle.get('/winner/<now_datetime>/<rollover_day>/<rollover_time>')
def winner(now_datetime, rollover_day, rollover_time):
  return {'winner': controller.winner(now=string_to_datetime(now_datetime), rollover_day=rollover_day, rollover_time=string_to_time(rollover_time))}

@bottle.get('/done_chores/<user_id>')
def done_chores(user_id):
  reverse = bottle.request.query.get('reverse')
  to_return = []
  if reverse and reverse.lower() == 'true':
    to_return = {'done_chores': controller.done_chores(user_id=user_id, reverse=True)}
  else:
    to_return =  {'done_chores': controller.done_chores(user_id=user_id, reverse=False)}

  # Convert datetime objects so they can be sent as JSON
  for done_chore in to_return['done_chores']:
    done_chore['datetime'] = datetime_to_string(done_chore['datetime'])

  return to_return

@bottle.get('/chore_name/<chore_id>')
def chore_name(chore_id):
  return {'name': controller.chore_name(chore_id)}


if __name__ == '__main__':

  arguments = docopt(__doc__, version=version)

  default_config_skeleton = """path_to_database: {0}
host_name: localhost
port: 8190
debug_mode: ''
path_to_database: {0}""".format(
    os.path.join(os.path.abspath('.'), 'default_chores.sql'))

  if arguments['--config-skeleton']:
    print default_config_skeleton
    exit(0)

  default_config_filename = os.path.join(
      os.path.expanduser("~"), ".config", "chores_apirc.yaml")

  if arguments['<path/to/config_file.yaml>'] is None:
    config_filename = default_config_filename
  else:
    config_filename = os.path.abspath(
        arguments['<path/to/config_file.yaml>'])

  # Fetch variables from config file (or create one if none
  # exists yet)
  conf_vars = config_file_variables(config_filename,
      default_config_skeleton)

  # Connect to the database
  controller = chores_controller.chores_controller(
      conf_vars['path_to_database'])

  # Actually serve the pages
  bottle.run(host=conf_vars['host_name'],
      port=conf_vars['port'], debug=conf_vars['debug_mode'])
