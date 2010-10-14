#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import cgi
import datetime
import wsgiref.handlers
import os
import hashlib
import datetime

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

def strtodate(strdate):
  intdate = int(strdate)
  return datetime.date(intdate / 10000, (intdate % 10000) / 100, intdate % 100)

def getLastDate(date):
  import time
  lastday = time.mktime((date.year, date.month + 1, 1, 0, 0, 0, 0, 0, 0)) - 1
  return datetime.date.fromtimestamp(lastday)

class User(db.Model):
  userid = db.StringProperty()
  profile = db.StringProperty(multiline=True)
  accesskey = db.StringProperty()

  @classmethod
  def getByAccessKey(cls, accesskey):
    return cls.gql('WHERE accesskey=:1', accesskey).get()

  def getStepRecord(self, date):
    return StepRecord.gql('WHERE user=:1 AND date=:2', self, date).get()

  def getStepRecords(self, term):
    return StepRecord.gql('WHERE user=:1 AND date>=:2 AND date<=:3', self, term.start, term.end)

  def getStepSummary(self, term):
    steps = 0
    for record in self.getStepRecords(term):
      steps += record.steps
    return steps

  def getRank(self, term):
    steps = self.getStepSummary(term)
    rank = 1
    for other in User.all():
      if other.getStepSummary(term) > steps:
        rank += 1
    return rank

class StepRecord(db.Model):
  user = db.ReferenceProperty(User)
  date = db.DateProperty()
  steps = db.IntegerProperty()
  comment = db.StringProperty()
  entrydate = db.DateTimeProperty(auto_now_add=True)


class Term:
  def __init__(self, start=None, end=None):
    today = datetime.date.today()
    self.start = start if start else datetime.date(today.year, today.month, 1)
    self.end = end if end else getLastDate(today)

class BasePage(webapp.RequestHandler):
  def write_response_template(self, values):
    path = os.path.join(os.path.dirname(__file__), 'templates', self.__class__.__name__ + '.html')
    self.response.out.write(template.render(path, values))

class SignupPage(BasePage):
  def get(self):
    self.write_response_template({})

  def post(self):
    userid = self.request.get('userid')
    if User.gql("WHERE userid=:1", userid).count() > 0:
      raise Exception('User %s already exists.' % userid)
    user = User()
    user.userid = userid
    user.profile = self.request.get('profile')
    user.accesskey = hashlib.sha512(userid + str(datetime.datetime.today())).hexdigest()
    user.put()
    self.redirect('/menu?key=%s' % user.accesskey)

class MenuPage(BasePage):
  def get(self):
    user = User.getByAccessKey(self.request.get('key'))
    self.write_response_template({'user': user})
    
class InputPage(BasePage):
  def get(self):
    user = User.getByAccessKey(self.request.get('key'))
    strdate = self.request.get('date')
    date = strtodate(strdate) if strdate else datetime.date.today()
    record = user.getStepRecord(date)
    if not record:
      record = StepRecord()
      record.date = date
    self.write_response_template({'user': user, 'record': record})

  def post(self):
    user = User.getByAccessKey(self.request.get('key'))
    date = strtodate(self.request.get('date'))
    record = user.getStepRecord(date)
    if not record:
      record = StepRecord()
    record.user = user
    record.date = date
    record.steps = int(self.request.get('steps'))
    record.comment = "TODO"
    record.put()
    self.redirect('/history?key=%s' % user.accesskey)

class HistoryPage(BasePage):
  def get(self):
    user = User.getByAccessKey(self.request.get('key'))
    records = StepRecord.gql("WHERE user=:user ORDER BY date DESC", user=user).fetch(10)
    monthly_term = Term()
    monthly_steps = user.getStepSummary(monthly_term)
    monthly_rank = user.getRank(monthly_term)
    campaign_term = Term(datetime.date(2010, 10, 1), datetime.date(2010, 11, 30)) #TODO
    campaign_steps = user.getStepSummary(campaign_term)
    campaign_rank = user.getRank(campaign_term)
    users_count = User.all().count()
    self.write_response_template({'user': user, 'records': records, 'monthly_steps': monthly_steps, 'monthly_rank': monthly_rank, 'campaign_steps': campaign_steps, 'campaign_rank': campaign_rank, 'users_count': users_count})


application = webapp.WSGIApplication([
  ('/', SignupPage),
  ('/menu', MenuPage),
  ('/history', HistoryPage),
  ('/input', InputPage)
], debug=True)


def main():
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
