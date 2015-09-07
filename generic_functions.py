import datetime
from datetime import timedelta
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

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
