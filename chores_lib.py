import datetime
from datetime import timedelta
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
import requests
import json
import os
import yaml

api_url = 'http://localhost:8190'
datetime_conversion_string = "%Y-%m-%d %H:%M:%S.%f"

def containing_date_range(now, rollover_day_of_week, rollover_time):

  # Find next rollover_day_of_week by just adding days until you get there.
  next_rollover = now.replace(hour=rollover_time.hour,
      minute=rollover_time.minute)
  days_forward = 0
  while next_rollover.strftime('%A') != rollover_day_of_week:
    next_rollover += datetime.timedelta(days=1)
    days_forward += 1
    if days_forward > 8:
      raise ValueError

  # Time replacement in the first line might have pushed this a week
  # backward
  if now > next_rollover:
    next_rollover += datetime.timedelta(weeks=1)

  prev_rollover = next_rollover - relativedelta(weeks=1)
  return {'begin': prev_rollover, 'end': next_rollover}

def chores():
  return requests.get(api_url + '/chores').json()['chores']

def done_chores(user_id, reverse):
  url = api_url + '/done_chores/' + str(user_id)
  if reverse:
    url += '?reverse=true'
  to_return = requests.get(url).json()['done_chores']
  
  # Change datetimes from JSON strings to actual datetime
  # objects
  for done_chore in to_return:
    done_chore['datetime'] = string_to_datetime(done_chore['datetime'])
  return to_return

def chore_name(chore_id):
  return requests.get(
      api_url + '/chore_name/' + str(chore_id)).json()['name']

def users():
  return requests.get(api_url + '/users').json()['users']

def weekly_score(user_id, now, rollover_day, rollover_time):
  url = '/'.join((api_url, 'weekly_score', str(user_id),
      datetime_to_string(now), rollover_day,
      rollover_time.strftime('%H:%M')))
  return requests.get(url).json()['weekly_score']

def winner(now, rollover_day, rollover_time):
  url = '/'.join((api_url, 'winner', datetime_to_string(now),
      rollover_day, rollover_time.strftime('%H:%M')))
  return requests.get(url).json()['winner']

def change_chore(chore_id, **kwargs):
  request_body = {}
  if 'name' in kwargs:
    request_body['name'] = kwargs['name']
  if 'worth' in kwargs:
    request_body['worth'] = kwargs['worth']
  if request_body != {}:
    url = '/'.join([api_url, 'chores', str(chore_id)])
    requests.patch(url=url, data=json.dumps(request_body))

def delete_done_chore(chore_id):
  url = '/'.join([api_url, 'chores', chore_id])
  requests.delete(url)

def new_chore(name, worth):
  url = '/'.join([api_url, 'chores', name, worth])
  requests.put(url)

def new_done_chore(user_id, chore_id, dt):
  url = '/'.join([api_url, 'done_chores', user_id, chore_id, datetime_to_string(dt)])
  requests.put(url)

# .isoformat() can't be easily converted back to a datetime
# object!
def datetime_to_string(dt):
  return dt.strftime(datetime_conversion_string)
def string_to_datetime(s):
  return datetime.datetime.strptime(s, datetime_conversion_string)
# Interpret "13:23" as the corresponding time
def string_to_time(t):
  pieces = [int(piece) for piece in t.split(':')]
  return datetime.time(pieces[0], pieces[1])

def config_file_variables(config_filename,
    default_config_skeleton):
  """
  Helper for reading from yaml config files.

  If `config_filename` doesn't exist yet, create one with
  default content in `default_config_skeleton`.
  """
  if not os.path.exists(config_filename):
    print("{} doesn't exist so creating and populating " \
      "with defaults.".format(config_filename))
    config_dir = os.path.dirname(config_filename)
    if not os.path.exists(config_dir):
      os.makedirs(config_dir)
    with open(config_filename, 'w') as config_file:
      config_file.write(default_config_skeleton)

  # Read variables in from config file
  with open(config_filename) as config_file:
    return yaml.load(config_file)
