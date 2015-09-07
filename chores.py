#!/usr/bin/env python

"""chores.py

Usage:
  chores.py [<path/to/config_file.yaml>]
  chores.py (-h | --help)
  chores.py --version
  chores.py --config-skeleton

Options:
  -h --help                 Show this screen.
  --version                 Show version.
  path/to/config_file.yaml  Where preferences are stored [DEFAULT: "~/.config/choresrc.yaml"]
  --config-skeleton         Print out contents of a reasonable config file.
"""

import bottle
import requests
import json
import datetime
from datetime import timedelta
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
import urllib
import urlparse
import qrcode
import os
import yaml
from docopt import docopt
from furl import furl
import chores_controller
import generic_functions

########
# HTML #
########


def chore_form(user, dt=None):
  """
  Generator yielding a form containing new chores to claim
  `user` has done at datetime `dt`.
  """
  if not dt:
    dt = datetime.datetime.now()
  yield '<form method="POST" action="./" id="impatient_chore_form">'
  yield '''<label for="new_done_chore_chore_id_user_{0}" class="select">Chore for {1}</label>
<select name="new_done_chore_chore_id" id="new_done_chore_chore_id_user_{0}" data-mini="true" data-inline="true">'''.format(
    user['rowid'],
    user['name']
  )
  for chore in controller.chores():
    yield '<option name="{0}" value="{0}">{1} ({2})</option>'.format(chore['rowid'], chore['name'], chore['worth'])
  yield '</select>'
  yield '<input type="text" name="new_done_chore_user_id" value="{}" style="visibility:hidden;width:2px;height:2px;"/>'.format(
    user['rowid']
  )
  yield '<input type="text" name="new_done_chore_date" value="{}" style="visibility:hidden;width:2px;height:2px;"/>'.format(
    dt.strftime('%Y-%m-%d')
  )
  yield '<input type="text" name="new_done_chore_time" value="{}" style="visibility:hidden;width:2px;height:2px;"/>'.format(
    dt.strftime('%H:%M:%S')
  )
  yield '<input type="submit" style="width:100%;font-size:96px;height:250px;" value="Add"/>'
  yield '</form>'


def done_chores_list_html(user):
  """Generator yielding the done chores with popups for deletion"""
  for done_chore in controller.done_chores(user_id=user['rowid'], reverse=True):
    yield '<li data-icon="delete">{0} {2}<a href="/#done_chore_{1}_popup" data-rel="popup"  data-transition="pop"></a></li>'.format(
      controller.chore_name(done_chore['chore_id']), done_chore['rowid'],
      done_chore['datetime'].strftime('%a %-m/%-d'),
    )
    yield """
      <div data-role="popup" id="done_chore_{0}_popup" data-overlay-theme="b" data-theme="b" data-dismissible="false">
        <div data-role="header" data-theme="a">
          <h1>Delete chore</h1>
        </div>
        <div role="main" class="ui-content">
          <h3 class="ui-title">Are you sure you want to delete this chore?</h3>
          <a href="#" class="ui-btn ui-corner-all ui-shadow ui-btn-inline ui-btn-b" data-rel="back">Cancel</a>
          <a href="/?delete_done_chore_id={0}" class="ui-btn ui-corner-all ui-shadow ui-btn-inline ui-btn-b" data-transition="flow">Delete</a>
        </div>
      </div>""".format(done_chore['rowid'])

def users_list_div(now, rollover_day, rollover_time):
  """Div containing the list of users"""
  max_weekly_score = max(controller.weekly_score(
      user['rowid'], now, rollover_day, rollover_time)
      for user in controller.users())
  max_width_percent = 50
  for user in controller.users():

    user_weekly_score = controller.weekly_score(user['rowid'], now, rollover_day,
        rollover_time)
    if max_weekly_score > 0:
      bar_width = max_width_percent * float(user_weekly_score) / float(max_weekly_score)
    else:
      bar_width = max_width_percent / 20

    yield '<div data-role="collapsible">'
    yield '  <h2><span style="width:30%;display:inline-block;">{0}: </span><div class="animated slideInRight" style="width:{2}%;border-style:solid;border-width:3px;display:inline-block;text-align:right;background:#99ffff;padding-right:.5em;"> {1}</div></h2>'.format(
        user['name'], user_weekly_score, bar_width)
    yield '''
      <ul data-role="listview">
      <li>Enter new chore<a href="#new_done_chore_popup_user_{0}" data-rel="popup" data-position-to="window" class="ui-btn ui-corner-all ui-shadow ui-btn-inline ui-icon-check ui-btn-icon-left ui-btn-a" data-transition="pop"></a></li>
      <div data-role="popup" id="new_done_chore_popup_user_{0}" data-theme="a" class="ui-corner-all">
    '''.format(user['rowid'])
    for formline in chore_form(user):
      yield formline
    yield '</div>'
    for line in done_chores_list_html(user):
      yield line
    yield "</ul></div>"

def users_choose_div():
  """Div containing the list of users for setting a cookie"""
  for user in controller.users():
    yield "<div>"
    yield '<p><a href="/?set_user_id_cookie={1}" class="ui-btn ui-shadow ui-corner-all">{0}</a></p>'.format(user['name'], user['rowid'])
    yield "</div>"

def main_page(now):
  """Generator yielding the html for the "main page" part of the
  monolithic jquerymobile page.
  """
  rollover_day = 'Friday'
  rollover_time =  datetime.time(6, 0)
  date_range = generic_functions.containing_date_range(now, rollover_day, rollover_time)
  previous_date_range = {
      'begin': date_range['begin'] - relativedelta(weeks=1),
      'end': date_range['end'] - relativedelta(weeks=1),
  }
  yield """
    <div data-role="page" id="main_page">
      <div data-role="collapsibleset">
        <p><a href="#chores_management_page" class="ui-btn ui-shadow ui-corner-all"><i class="fa fa-cog"></i> Manage Chores</a></p>
  """
  date_format = '%a %-m/%-d %-I:%M%P'
  last_week = now - relativedelta(weeks=1)
  next_week = now + relativedelta(weeks=1)
  last_weeks_winner = controller.winner(last_week, rollover_day, rollover_time)
  yield '<p>Last weeks winner: {0} with {1} points</p>'.format(
      last_weeks_winner['name'], last_weeks_winner['score'])
  yield '<p>{0} - {1}</p>'.format(date_range['begin'].strftime(date_format),
      date_range['end'].strftime(date_format))
  for line in users_list_div(now, rollover_day, rollover_time):
    yield line

  # Navigate buttons for prev/next week
  prev_week_url = furl(bottle.request.url)
  prev_week_url.args['datetime'] = last_week.strftime('%Y-%m-%d %H:%M:%S')
  prev_week_url = prev_week_url.url
  next_week_url = furl(bottle.request.url)
  next_week_url.args['datetime'] = next_week.strftime('%Y-%m-%d %H:%M:%S')
  next_week_url = next_week_url.url
  yield '<a href="{0}" data-role="button" data-icon="arrow-l">Previous Week</a>'.format(prev_week_url)
  yield '<a href="{0}" data-role="button" data-icon="arrow-r" data-iconpos="right">Next Week</a>'.format(next_week_url)
  yield """
      </div>
    </div><!-- /content -->
  </div><!-- /page -->
  """

def chore_url(chore_id):
  return urlparse.urljoin(bottle.request.url, '/postget/?new_done_chore_chore_id={0}'.format(chore_id))

def chore_qrcode_url(chore_id):
  return '/qrcodes/{0}.png'.format(chore_id)

def chores_management_page():
  """Generator yielding the html for the "chores management page"
  part of the monolithic jquerymobile page.
  """
  yield """
    <div data-role="page" id="chores_management_page">
    <div data-role="collapsibleset">
    <p><a href="#main_page" class="ui-btn ui-shadow ui-corner-all"><i class="fa fa-arrow-left"></i> Back to Main Page</a></p>
  """
  for chore in controller.chores():
    yield """<div data-role="collapsible">
          <h2>{0}</h2>
          <form method="POST" action="./">
            <ul data-role="listview" data-divider-theme="b">
              <li class="ui-field-contain">
                  <label for="name2">New Name</label>
                  <input name="update_chore_name" id="name2" value="{0}" data-clear-btn="true" type="text">
                  <input type="submit" ui-btn-inline" value="Rename"/>
<div><a href="{3}"><img src="{3}" style="width:200px;border-width:2px;border-style:solid;"/></a></div>
              </li>
              <li class="ui-field-contain">
                  <label for="name2">New Worth</label>
                  <input name="update_chore_worth" id="name2" value="{2}" data-clear-btn="true" type="text">
                  <input style="visibility:hidden;" name="update_chore_id" value="{1}" type="text">
                  <input type="submit" style="ui-btn-inline" value="Change Worth"/>
              </li>
            </ul>
          </form>
        </div>
    """.format(chore['name'], chore['rowid'], chore['worth'], chore_qrcode_url(chore['rowid']))
  yield """
          <h2>Add New Chore</h2>
          <form method="POST" action="./">
            <ul data-role="listview" data-divider-theme="b">
              <li class="ui-field-contain">
                  <label for="name2">New Name</label>
                  <input name="new_chore_name" id="name2" value="" data-clear-btn="true" type="text">
              </li>
              <li class="ui-field-contain">
                  <label for="name2">New Worth</label>
                  <input name="new_chore_worth" id="name2" value="" data-clear-btn="true" type="text">
                  <input type="submit" style="ui-btn-inline" value="Submit"/>
              </li>
            </ul>
          </form>
</div>
</div><!-- /content -->
</div><!-- /page -->
  """

def cookie_setting_page():
  """Generator yielding the html for the "identify device" part of the
  monolithic jquerymobile page.
  """
  yield """
    <div data-role="page" id="identify_device">
      <div data-role="collapsibleset">
  """
  yield '<h1>Who are you?</h1>'
  for line in users_choose_div():
    yield line
  yield """
      </div>
    </div><!-- /content -->
  </div><!-- /page -->
  """


def complete_page(now):
  yield """
    <!doctype html>
    <html>
    <head>
    <title>Chores</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="http://code.jquery.com/mobile/1.2.0/jquery.mobile-1.2.0.min.css">
    <link rel="stylesheet" href="animate.min.css">
    <script src="http://code.jquery.com/jquery-1.8.2.min.js"></script>
    <script src="http://code.jquery.com/mobile/1.2.0/jquery.mobile-1.2.0.min.js"></script>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css">
    </head>
    <body>
  """
  for line in main_page(now):
    yield line
  for line in chores_management_page():
    yield line
  for line in cookie_setting_page():
    yield line
  yield """
</body>
</html>
  """


@bottle.get('/')
def get_whole_page():
  # Try to make this not cache so that the same chore can be loaded twice in succession
  bottle.response.set_header('Cache-Control', 'max-age=1')
  if bottle.request.query.get('delete_done_chore_id'):
    controller.delete_done_chore(chore_id=bottle.request.query.get('delete_done_chore_id'))
  if bottle.request.query.get('delete_user_id'):
    delete_user(user_id=bottle.request.query.get('delete_user_id'))
  if bottle.request.query.get('delete_chore_id'):
    delete_chore(chore_id=bottle.request.query.get('delete_chore_id'))
  if bottle.request.query.get('set_user_id_cookie'):
    set_user_id_cookie(bottle.response, int(bottle.request.query.get('set_user_id_cookie')))
  if bottle.request.query.get('datetime'):
    return '\n'.join(list(complete_page(
        datetime.datetime.strptime(bottle.request.query.get('datetime'),
            "%Y-%m-%d %H:%M:%S"))))
  else:
    return '\n'.join(list(complete_page(
        datetime.datetime.now())))


# Serve the css necessary for the date and time pickers
# TODO Just do this with a static file directive
@bottle.get('/lib/themes/<a_css_file>')
def return_css_file(a_css_file):
  if a_css_file in ("default.css", "default.date.css", "default.time.css"):
    local_file = "picker/compressed/themes/{}".format(a_css_file)
    with open(local_file) as f:
      return f.read()

@bottle.get('/qrcodes/<chore_id>.png')
def return_qrcode_png(chore_id):
  rel_path_to_image = os.path.join('qrcodes', '{0}.png'.format(chore_id))
  if not os.path.isfile(rel_path_to_image):
    qr = qrcode.QRCode()
    qr.add_data(chore_url(chore_id))
    qr.make()
    im = qr.make_image()
    im.save(rel_path_to_image)
  return bottle.static_file(rel_path_to_image, root='')

@bottle.post('/')
def post_whole_page():
  # Try to make this not cache so that the same chore can be loaded twice in succession
  bottle.response.set_header('Cache-Control', 'max-age=1')
  # Add a new chore
  if bottle.request.forms.get('new_chore_name') and bottle.request.forms.get('new_chore_worth'):
    controller.new_chore(name=bottle.request.forms.get('new_chore_name'), worth=bottle.request.forms.get('new_chore_worth'))
  # Add a new user
  if bottle.request.forms.get('new_user_name'):
    new_user(name=bottle.request.forms.get('new_user_name').strip())
  # Add a new done chore
  gets = []
  for get in ('new_done_chore_user_id', 'new_done_chore_date', 'new_done_chore_time', 'new_done_chore_chore_id'):
    gets.append(bottle.request.forms.get(get))
  if gets[0] and gets[1] and gets[2] and gets[3]:
    controller.new_done_chore(
      user_id=gets[0],
      chore_id=gets[3],
      dt=datetime.datetime.strptime(
        "{} {}".format(gets[1], gets[2]),
        "%Y-%m-%d %H:%M:%S"
      )
    )
  # Update an existing chore
  gets = []
  for get in ('update_chore_name', 'update_chore_worth', 'update_chore_id'):
    gets.append(bottle.request.forms.get(get))
  if all(gets):
    controller.change_chore(
        chore_id=int(gets[2]), name=gets[0],
        worth=gets[1]
    )
  return '\n'.join(list(complete_page(datetime.datetime.now())))


# GET version of what REST says should be a POST so that chores can be submitted by a URL
# e.g. from a QR Code
@bottle.get('/postget/')
def post_get():
  # Try to make this not cache so that the same chore can be loaded twice in succession
  bottle.response.set_header('Cache-Control', 'max-age=1')
  # Add a new done chore
  gotten = {}
  possible_GETs = ('new_done_chore_user_id', 'new_done_chore_date', 'new_done_chore_time', 'new_done_chore_chore_id')
  for getvar in possible_GETs:
    if getvar in bottle.request.query:
      gotten[getvar] = bottle.request.query[getvar]
  if 'new_done_chore_date' in gotten:
    datey = gotten['new_done_chore_date']
  else:
    datey = datetime.datetime.now().strftime('%Y-%m-%d')
  if 'new_done_chore_time' in gotten:
    timey = gotten['new_done_chore_time']
  else:
    timey = datetime.datetime.now().strftime('%H:%M:%S')
  if ('new_done_chore_user_id' in gotten) and ('new_done_chore_chore_id' in gotten):
    controller.new_done_chore(
      user_id=gotten['new_done_chore_user_id'],
      chore_id=gotten['new_done_chore_chore_id'],
      dt=datetime.datetime.strptime("{} {}".format(datey, timey), "%Y-%m-%d %H:%M:%S")
    )
    return '\n'.join(list(complete_page(datetime.datetime.now())))
  # If no user_id given in GET, but they've got a cookie with their user_id, use that
  elif 'new_done_chore_chore_id' in gotten:
    user_id = user_id_from_cookie(bottle.request.cookies)
    if user_id:
      controller.new_done_chore(
        user_id=user_id,
        chore_id=gotten['new_done_chore_chore_id'],
        dt=datetime.datetime.strptime("{} {}".format(datey, timey), "%Y-%m-%d %H:%M:%S")
      )
      return '\n'.join(list(complete_page(datetime.datetime.now())))
    # If no cookie found with a valid id, demand user identify themselves
    bottle.redirect("/#identify_device")


#############
# Functions #
#############


def user_id_from_cookie(cookies):
  """
  `cookies` will be bottle.request.cookies
  """
  if 'chores_id' in cookies:
    purported_user_id = int(cookies['chores_id'])
    if purported_user_id in (user['rowid'] for user in controller.users()):
      return purported_user_id
  return None

def set_user_id_cookie(response, user_id):
  """
  `response` should be bottle.response
  """
  response.set_cookie("chores_id", str(user_id), expires=datetime.datetime.strptime("3030-01-01", "%Y-%m-%d"))


# Data fetching functions with RESTful interface via bottle decorators as needed
# Try to only implement RESTful things as they are needed by javascript

# Have not removed superfluous bottle REST stuff from below

@bottle.get('/chores/<name>')
def get_chore(name):
  chores_controller.get_chore(name, cursor)

@bottle.get('/sparks/<user>')
def sparks(user):
  chores_controller.sparks(user, cursor)

# Using post for new
@bottle.post('/chores/<name>')
def save_chore(name):
  chores_controller.save_chore(name, cursor, connection)

@bottle.get('/users/<name>')
def show_user(name):
  chores_controller.show_user(name, cursor)

@bottle.put('/users/<name>')
def save_user(name):
  chores_controller.save_user(name, cursor, connection)

@bottle.get('/done_chores/<name>')
def show_user(name):
  return chores_controller.show_user(name, cursor)

def default_config_dir():
  return os.path.join(os.path.expanduser("~"), ".config")

def default_config_filename():
  return os.path.join(default_config_dir(), "choresrc.yaml")

def config_skeleton():
  return """path_to_database: {0}
host_name: localhost
port: 8090
debug_mode: True""".format(
    os.path.join(os.path.abspath('.'), 'default_chores.sql'))

def config_file_variables(config_dir, config_filename):
  # If `config_dir`/`config_filename` doesn't exist yet,
  # create one with default content.
  if not os.path.exists(config_filename):
    print("{} doesn't exist so creating and populating " \
      "with defaults.".format(config_filename))
    if not os.path.exists(config_dir):
      os.makedirs(config_dir)
    with open(config_filename, 'w') as config_file:
      config_file.write(config_skeleton())

  # Read variables in from config file
  with open(config_filename) as config_file:
    config = yaml.load(config_file)
    to_return = {
        item: config[item]
        for item in
        ('path_to_database', 'host_name', 'port', 'debug_mode')
    }
  
  return to_return

# Static route to animate.css
@bottle.get('/<filename:re:.*\.css>')
def stylesheets(filename):
  return bottle.static_file(filename, root='static/css')

if __name__ == '__main__':

  arguments = docopt(__doc__, version='1.0.0')

  if arguments['--config-skeleton']:
    print config_skeleton()
    exit(0)

  if arguments['<path/to/config_file.yaml>'] is None:
    config_filename = default_config_filename()
    config_dir = default_config_dir()
  else:
    config_filename = os.path.abspath(arguments['<path/to/config_file.yaml>'])
    config_dir = os.path.dirname(config_filename)

  # Fetch variables from config file
  # (or create one if none exists yet)
  conf_vars = config_file_variables(config_dir, config_filename)

  # Database
  controller = chores_controller.chores_controller(
      conf_vars['path_to_database'])
  bottle.run(host=conf_vars['host_name'],
      port=conf_vars['port'], debug=conf_vars['debug_mode'])
