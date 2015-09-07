import sqlalchemy
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, \
    desc, asc, text, ForeignKey
from sqlalchemy.sql import select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import generic_functions

class chores_controller():
  def __init__(self, path_to_database):
    self.session = chores_db_session(path_to_database)

  def chores(self):
    """
    Return list of chores

      [{'rowid': rowid, 'name': name, 'worth': worth}, ...]

    ordered by worth (highest to lowest) from `session`
    """
    return [
      {'rowid': x.rowid, 'name': x.name, 'worth': x.worth}
      for x in self.session.query(Chore).order_by(desc(Chore.worth)).all()
    ]

  def done_chores(self, user_id=None, reverse=False):
    """
    Return list of done chores from `session`
      [{'rowid': rowid, 'chore_id': chore_id, 'user_id': user_id, 'datetime': datetime}, ...
    ordered by datetime (choronological if (not `reverse`) else anti-chronological)
    """
    results = self.session.query(Done_chore)
    if user_id:
      results = results.filter_by(user_id=user_id)
    if reverse:
      results = results.order_by(desc(Done_chore.datetime))
    else:
      results = results.order_by(asc(Done_chore.datetime))
    return [
      {'rowid': row.rowid, 'datetime': row.datetime, 'chore_id': row.chore_id, 'user_id': row.user_id}
      for row in results.all()
    ]

  def chore_name(self, rowid):
    """Return name corresponding to `rowid` from `session`"""
    results = self.session.query(Chore.name).filter_by(rowid=rowid)
    return results.one()[0]

  def weekly_score(self, user_id, now, rollover_day, rollover_time):
    """Return the total score from the current week for `user_id`"""

    date_range = generic_functions.containing_date_range(now, rollover_day, rollover_time)

    query_string = """
      SELECT sum(chores.worth)
      FROM
        done_chores, chores
      WHERE
        done_chores.user_id = {0}
      AND
        done_chores.chore_id = chores.rowid
      AND
        done_chores.datetime >= "{1}"
      AND
        done_chores.datetime < "{2}"
      ;
    """.format(user_id, date_range['begin'], date_range['end'])

    results = self.session.query("sum(chores.worth)").from_statement(text(query_string));
    if results.all()[0][0] is None:
      return 0
    else:
      return results.all()[0][0]

  def winner(self, now, rollover_day, rollover_time):
    scores = [
      {
        'user_id': user['rowid'],
        'week_score': self.weekly_score(user['rowid'], now, rollover_day, rollover_time)
      }
      for user in self.users()
    ]

    # Find maximum scoring user_id
    win = scores[0]
    for score in scores:
      if score['week_score'] > win['week_score']:
        win = score

    return {
        'name': self.user_name(win['user_id']), 'score': win['week_score']
    }

  def users(self):
    """Return list of users

      [{'rowid': rowid, 'name': name, 'score': total score}, ...]

    ordered by total score highest to lowest
    """
    # TODO Use the ORM for this, not a raw SQL statement
    # The ones in the done_chores table
    # i.e. they've done a chore
    results = self.session.query("rowid", "name", "sum(chores.worth)").from_statement(text("""
      SELECT
        users.rowid, users.name, sum(chores.worth)
      FROM
        done_chores, chores, users
      WHERE
        done_chores.user_id = users.rowid
      AND
        done_chores.chore_id = chores.rowid
      GROUP BY
        users.name
      ;
    """))
    hard_workers = results.all()
    # The ones who've done nothing yet
    results = self.session.query("rowid", "name").from_statement(text("SELECT rowid, name, 0 FROM users WHERE rowid NOT IN (SELECT user_id FROM done_chores);"))
    return list(reversed(sorted(list(
      {'rowid': x[0], 'name': x[1], 'score': x[2]}
      for x in hard_workers + [(x[0], x[1], 0) for x in results.all()]
    ), cmp=lambda a,b: cmp(a['score'], b['score']))))

  def rowid(self, name, table_type):
    """Return rowid corresponding to `name` in `table_type`"""
    if table_type == 'user':
      table = User
    elif table_type == 'chore':
      table = Chore
    else:
      raise RuntimeError("Unknown table type " + table_type)
    return session.query(table.rowid).filter_by(name=name).one()[0]

  def user_name(self, rowid):
    """Return name corresponding to `rowid`"""
    return self.session.query(User.name).filter_by(rowid=rowid).one()[0]

  def delete_done_chore(self, chore_id):
    self.session.delete(self.session.query(Done_chore).filter_by(rowid=chore_id).one())
    self.session.commit()

  def new_chore(self, name, worth):
    self.session.add(Chore(name=name, worth=worth))
    self.session.commit()

  def new_user(self, name):
    self.session.add(User(name=name))
    self.session.commit()

  def new_done_chore(self, user_id, chore_id, dt):
    self.session.add(Done_chore(user_id=user_id, chore_id=chore_id, datetime=dt))
    self.session.commit()

  def delete_user(self, user_id):
    self.session.delete(self.session.query(User).filter_by(rowid=user_id).one())
    self.session.commit()

  def delete_chore(self, chore_id):
    self.session.delete(self.session.query(Chore).filter_by(rowid=chore_id).one())
    self.session.commit()

############
# Database #
############

Base = declarative_base()
class User(Base):
  """row of sqlalchemy users Table object"""
  __tablename__ = 'users'
  rowid = Column(Integer, primary_key=True)
  name = Column(String)
class Chore(Base):
  """row of sqlalchemy chores Table object"""
  __tablename__ = 'chores'
  rowid = Column(Integer, primary_key=True)
  name = Column(String)
  worth = Column(Integer)
class Done_chore(Base):
  """row of sqlalchemy done_chores Table"""
  __tablename__ = 'done_chores'
  rowid = Column(Integer, primary_key=True)
  chore_id = Column(Integer, ForeignKey('chores.rowid'))
  user_id = Column(Integer, ForeignKey('users.rowid'))
  datetime = Column(DateTime)



def chores_db_session(path_to_database):
  engine = sqlalchemy.create_engine(
      'sqlite:///{0}'.format(path_to_database))
  Session = sessionmaker(bind=engine)
  return Session()

def get_chore(name, cursor):
  query = "SELECT name, worth, rowid FROM chores WHERE name='{}';"
  cursor.execute(query.format(name))
  first_row = cursor.fetchall()[0]
  if len(first_row) >= 3:
    return {'name': first_row[0], 'worth': first_row[1],
      'rowid': first_row[2]}
  return {}

def sparks(user, cursor):
  cursor.execute("""
    SELECT
      date(done_chores.datetime),
      sum(chores.worth)
    FROM
      done_chores, chores
    WHERE
      done_chores.chore=chores.name
    AND
      done_chores.user='John'
    GROUP BY
      date(done_chores.datetime)
    ;
  """)
  dates_with_work = dict(cursor.fetchall())
  return dates_with_work
  # for a_date in (
    # datetime.datetime.strptime(min(a), '%Y-%m-%d') + datetime.timedelta(n) for n in range(7)
  # ):
# ...   print a_date
# ...
# 2014-09-05 00:00:00
# 2014-09-06 00:00:00
  # return 

def save_chore(name, cursor, connection):
  cursor.execute("INSERT OR REPLACE INTO chores (name, worth) VALUES (?, ?)", (name, int(bottle.request.forms.get('worth'))))
  connection.commit()

def show_user(name, cursor):
  cursor.execute("SELECT datetime, chore FROM done_chores, users WHERE done_chores.user_id = users.rowid AND users.name=?;", (name,))
  return dict(cursor.fetchall())

def save_user(name, cursor, connection):
  cursor.execute("INSERT OR REPLACE INTO users (name) VALUES (?)", (name,))
  connection.commit()

def change_chore(chore_id, session, **kwargs):
  """Update name and/or worth of chore `chore_id`

  kwargs can contain name= and/or worth=
  """
  # if ('name' in kwargs) or ('worth' in kwargs):
  to_update = {
    key: value
    for key, value in kwargs.iteritems()
    if key in ('worth', 'name')
  }
  if to_update:
    session.query(Chore).filter_by(rowid=chore_id).update(
      to_update)
    session.commit()


