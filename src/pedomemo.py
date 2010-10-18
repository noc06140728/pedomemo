#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import datetime
import wsgiref.handlers
import os
import hashlib
import re

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

webapp.template.register_template_library('customfilters_m')

class ApplicationError(Exception):
    pass

def parseUserId(struserid):
    if not re.compile('^[0-9A-Za-z._-]{1,16}$').match(struserid):
        raise ApplicationError(u'ユーザIDは、半角英数字16文字以内で入力してください。')
    return struserid

def parseProfile(strprofile):
    if len(strprofile) > 64:
        raise ApplicationError(u'プロフィールは64文字以内で入力してください。')
    return strprofile

def parseDate(strdate):
    try:
        intdate = int(strdate)
        if intdate < 19800101 or intdate > 20991231:
            raise ApplicationError(u'日付には西暦の年月日を数字8桁で入力してください。')
        return datetime.date(intdate / 10000, (intdate % 10000) / 100, intdate % 100)
    except:
        raise ApplicationError(u'日付には西暦の年月日を数字8桁で入力してください。')
    
def parseSteps(strsteps):
    try:
        intsteps = int(strsteps)
        if intsteps < 0:
            raise ApplicationError(u'歩数には0以上の整数値を入力してください。')
        return int(strsteps)
    except ValueError:
        raise ApplicationError(u'歩数には0以上の整数値を入力してください。')

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
        user = cls.gql('WHERE accesskey=:1', accesskey).get()
        if user is None:
            raise ApplicationError(u'該当するユーザが見つかりませんでした。ユーザ登録しなおしてください。')
        return user

    def getStepRecord(self, date):
        return StepRecord.gql('WHERE user=:1 AND date=:2', self, date).get()

    def getStepRecords(self, term):
        return StepRecord.gql('WHERE user=:1 AND date>=:2 AND date<=:3', self, term.start, term.end)

    def getStepSummary(self, term):
        memkey = '%s:%s' % (self.userid, term)
        steps = memcache.get(memkey, namespace='steps')
        if steps is None:
            steps = 0
            for record in self.getStepRecords(term):
                steps += record.steps
            memcache.set(memkey, steps, namespace='steps')
        return steps

"""    def getRank(self, term):
        memkey = '%s:%s' % (self.userid, term)
        rank = memcache.get(memkey, namespace='rank')
        if rank is None:
            steps = self.getStepSummary(term)
            rank = 1
            for other in User.all():
                if other.getStepSummary(term) > steps:
                    rank += 1
            memcache.set(memkey, rank, namespace='rank')
        return rank
"""
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

    def __str__(self):
        return '%s~%s' % (self.start, self.end)

class RankItem:
    def __init__(self, rank, user, steps):
        self.rank = rank
        self.user = user
        self.steps = steps

class Ranking:
    def __init__(self, term):
        self.term = term
        memkey = str(term)
        self.rank_list = memcache.get(memkey, namespace='rank_list')
        if self.rank_list is None:
            self.rank_list = []
            rank = 1
            rank_index = 1
            pre_steps = 0
            for user in sorted(User.all(), key=lambda u: u.getStepSummary(term), reverse=True):
                steps = user.getStepSummary(term)
                if pre_steps <> steps:
                    rank = rank_index
                self.rank_list.append(RankItem(rank, user, steps))
                pre_steps = steps
                rank_index += 1
            memcache.set(memkey, self.rank_list, namespace='rank_list')

    def getRank(self, user):
        for item in self.rank_list:
            if item.user.userid == user.userid:
               return item.rank
        return None

class BaseHandler(webapp.RequestHandler):
    def write_response_template(self, values):
        self.response.headers['Content-Type'] = 'text/html; charset=Shift_JIS'
        path = os.path.join(os.path.dirname(__file__), 'templates', self.__class__.__name__ + '.html')
        self.response.out.write(template.render(path, values))

    def handle_exception(self, exception, debug_mode):
        if debug_mode:
            super(BaseHandler, self).handle_exception(exception, debug_mode)
        else:
            self.response.headers['Content-Type'] = 'text/html; charset=Shift_JIS'
            path = os.path.join(os.path.dirname(__file__), 'templates', 'ErrorPage.html')
            error_message = exception.args[0].encode('Shift_JIS')
            self.response.out.write(template.render(path, {'error_message': error_message}))

class SignupPage(BaseHandler):
    def get(self):
        self.write_response_template({})

    def post(self):
        self.request.charset = 'Shift_JIS'
        userid = parseUserId(self.request.get('userid'))
        if User.gql("WHERE userid=:1", userid).count() > 0:
            raise ApplicationError(u'ユーザID "%s" は、既に登録されています。別のユーザIDを指定してください。' % userid)
        user = User()
        user.userid = userid
        user.profile = parseProfile(self.request.get('profile'))
        user.accesskey = hashlib.sha512(userid + str(datetime.datetime.today())).hexdigest()
        user.put()
        self.redirect('/menu?key=%s' % user.accesskey)

class MenuPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        self.write_response_template({'user': user})
    
class InputPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        strdate = self.request.get('date')
        date = parseDate(strdate) if strdate else datetime.date.today()
        record = user.getStepRecord(date)
        if not record:
            record = StepRecord()
            record.date = date
        self.write_response_template({'user': user, 'record': record})

    def post(self):
        user = User.getByAccessKey(self.request.get('key'))
        date = parseDate(self.request.get('date'))
        record = user.getStepRecord(date)
        if not record:
            record = StepRecord()
        record.user = user
        record.date = date
        record.steps = parseSteps(self.request.get('steps'))
        record.comment = "TODO"
        record.put()
        memcache.flush_all()
        self.redirect('/history?key=%s' % user.accesskey)

class HistoryPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        records = StepRecord.gql("WHERE user=:user ORDER BY date DESC", user=user).fetch(30)
        monthly_term = Term()
        monthly_steps = user.getStepSummary(monthly_term)
        monthly_rank = Ranking(monthly_term).getRank(user)
        campaign_term = Term(datetime.date(2010, 10, 1), datetime.date(2010, 11, 30)) #TODO
        campaign_steps = user.getStepSummary(campaign_term)
        campaign_rank = Ranking(campaign_term).getRank(user)
        users_count = User.all().count()
        self.write_response_template({'user': user, 'records': records, 'monthly_steps': monthly_steps, 'monthly_rank': monthly_rank, 'campaign_steps': campaign_steps, 'campaign_rank': campaign_rank, 'users_count': users_count})

class RankingPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        ranking = Ranking(Term())
        self.write_response_template({'user': user, 'ranking': ranking})

class ProfilePage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        self.write_response_template({'user': user, 'profile': user.profile.encode('Shift-JIS')})

application = webapp.WSGIApplication([
  ('/', SignupPage),
  ('/menu', MenuPage),
  ('/input', InputPage),
  ('/history', HistoryPage),
  ('/ranking', RankingPage),
  ('/profile', ProfilePage)
], debug=False)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()