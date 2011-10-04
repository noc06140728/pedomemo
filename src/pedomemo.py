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

def parseComment(strcomment):
    if len(strcomment.encode('SHIFT_JIS')) > 40:
        raise ApplicationError(u'コメントは20文字以内で入力してください。')
    return strcomment

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

    @classmethod
    def getUser(cls, userid):
        user = User.gql("WHERE userid=:1", (userid)).get()
        if user is None:
            raise ApplicationError(u'該当するユーザが見つかりませんでした。')
        return user

    def getStepRecord(self, date):
        return StepRecord.gql('WHERE user=:1 AND date=:2', self, date).get()

    def getStepRecords(self, term):
        return StepRecord.gql('WHERE user=:1 AND date>=:2 AND date<=:3 ORDER BY date',
                              self, term.start_date, term.end_date)

    def getStepSummary(self, term):
        return StepSummary.getSummaryStep(self, term)

class StepRecord(db.Model):
    user = db.ReferenceProperty(User)
    date = db.DateProperty()
    steps = db.IntegerProperty()
    comment = db.StringProperty()
    entrydate = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def getRecentStepRecords(cls, count):
        records = []
        for record in StepRecord.gql('ORDER BY entrydate DESC'):
            if (record.comment <> '') and (record.comment <> 'TODO'):
                records.append(record)
            if len(records) >= count: break
        return records

class StepSummary(db.Model):
    user = db.ReferenceProperty(User)
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    steps = db.IntegerProperty()
    rank = db.IntegerProperty()
    entrydate = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def countStepRecords(cls, term):
        count_steps = {}
        for record in StepRecord.gql('WHERE date>=:1 AND date<=:2',
                                     term.start_date, term.end_date):
            if count_steps.has_key(record.user.userid):
                count_steps[record.user.userid] += record.steps
            else:
                count_steps[record.user.userid] = record.steps

        for userid, steps in count_steps.items():
            step_sum = StepSummary.get_or_insert('%s/%s' % (userid, term))
            step_sum.user = User.getUser(userid)
            step_sum.start_date = term.start_date
            step_sum.end_date = term.end_date
            step_sum.steps = steps
            step_sum.put()

        rank = 1
        rank_index = 1
        pre_steps = 0
        for step_sum in StepSummary.getRankList(term):
            if pre_steps <> step_sum.steps:
                rank = rank_index
            step_sum.rank = rank
            step_sum.put()
            pre_steps = step_sum.steps
            rank_index += 1

    @classmethod
    def getSummaryStep(cls, user, term):
        return StepSummary.get_by_key_name('%s/%s' % (user.userid, term))

    @classmethod
    def getRankList(cls, term):
        return StepSummary.gql('WHERE start_date = :1 AND end_date = :2 ORDER BY steps DESC',
                               term.start_date, term.end_date)

class CountTask(db.Model):
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    entrydate = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def putTask(cls, term):
        task = CountTask.get_or_insert(str(term))
        task.start_date = term.start_date
        task.end_date = term.end_date
        task.put()

    @classmethod
    def registTask(cls, date):
        term = Term.getTerm(date.year, date.month)
        CountTask.putTask(term)

        if Term.inCampaignTerm(date):
            term = Term.getCampaignTerm(date.year)
            CountTask.putTask(term)

class Term:
    def __init__(self, start_date=None, end_date=None):
        today = datetime.date.today()
        self.start_date = start_date if start_date else datetime.date(today.year, today.month, 1)
        self.end_date = end_date if end_date else getLastDate(self.start_date)

    def __str__(self):
        return '%s~%s' % (self.start_date, self.end_date)

    @classmethod
    def getCampaignTerm(cls, year=None):
        if year is None:
            year = datetime.date.today().year
        return Term(datetime.date(year, 10, 1), datetime.date(year, 11, 30))

    @classmethod
    def getTerm(cls, year, month):
        if not(1 <= month <= 12):
            raise ApplicationError('Invarid month.')
        start_date = datetime.date(year, month, 1)
        return Term(start_date, getLastDate(start_date))

    @classmethod
    def inCampaignTerm(cls, date):
        term = Term.getCampaignTerm(date.year)
        return (term.start_date <= date <= term.end_date)

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
            error_message = exception.args[0]
            self.response.out.write(template.render(path, {'error_message': error_message}))

class SignupPage(BaseHandler):
    def get(self):
        import useragent_m
        userAgent = useragent_m.UserAgent()
        userAgent.setUserAgent(self.request.headers['User-Agent'])
        self.write_response_template({'userAgent': userAgent})

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
        import useragent_m
        userAgent = useragent_m.UserAgent()
        userAgent.setUserAgent(self.request.headers['User-Agent'])
        user = User.getByAccessKey(self.request.get('key'))
        strdate = self.request.get('date')
        date = parseDate(strdate) if strdate else datetime.date.today()
        record = user.getStepRecord(date)
        if not record:
            record = StepRecord()
            record.date = date
            record.comment = ''
        self.write_response_template({'user': user, 'record': record, 'userAgent': userAgent})

    def post(self):
        self.request.charset = 'Shift_JIS'
        user = User.getByAccessKey(self.request.get('key'))
        date = parseDate(self.request.get('date'))
        record = user.getStepRecord(date)
        if not record:
            record = StepRecord()
        record.user = user
        record.date = date
        record.steps = parseSteps(self.request.get('steps'))
        record.comment = parseComment(self.request.get('comment'))
        record.put()
        CountTask.registTask(date)
        self.redirect('/history?key=%s' % user.accesskey)

class HistoryPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        records = StepRecord.gql("WHERE user=:user ORDER BY date DESC", user=user).fetch(30)
        monthly_term = Term()
        monthly_sum = user.getStepSummary(monthly_term)
        monthly_count = StepSummary.getRankList(monthly_term).count()
        campaign_term = Term.getCampaignTerm()
        campaign_sum = user.getStepSummary(campaign_term)
        campaign_count = StepSummary.getRankList(campaign_term).count()
        step_count = user.getStepRecords(campaign_term).count()
        self.write_response_template({
            'user': user, 'records': records,
            'monthly_sum': monthly_sum, 'monthly_count': monthly_count,
            'campaign_sum': campaign_sum, 'campaign_count': campaign_count,
            'average': campaign_sum.steps/step_count if campaign_sum and step_count else 0})

class RankingPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        if self.request.get('term') == 'campaign':
            term = Term.getCampaignTerm()
            isCampaignTerm = True
        else:
            term = Term()
            isCampaignTerm = False
        rank_list = StepSummary.getRankList(term)
        self.write_response_template({'user': user, 'term': term, 'rank_list': rank_list,
                                      'isCampaignTerm': isCampaignTerm})

class ProfilePage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        profile_user = User.getUser(parseUserId(self.request.get('userid')))
        self.write_response_template({'user': user, 'profile_user': profile_user})

class MyProfilePage(BaseHandler):
    def get(self):
        import useragent_m
        userAgent = useragent_m.UserAgent()
        userAgent.setUserAgent(self.request.headers['User-Agent'])
        user = User.getByAccessKey(self.request.get('key'))
        self.write_response_template({'user': user, 'userAgent': userAgent})

    def post(self):
        self.request.charset = 'Shift_JIS'
        user = User.getByAccessKey(self.request.get('key'))
        user.profile = parseProfile(self.request.get('profile'))
        user.put()
        self.redirect('/menu?key=%s' % user.accesskey)

class CommentsPage(BaseHandler):
    def get(self):
        user = User.getByAccessKey(self.request.get('key'))
        steps = StepRecord.getRecentStepRecords(10)
        COLOR_LIST = ["#d43333", "#d45500", "#556680", "#668000"]
        SPEED_LIST = [2, 3, 4, 5]
        self.write_response_template({'user': user, 'steps': steps, 'colors': COLOR_LIST, 'speeds': SPEED_LIST})

class ReportPage(BaseHandler):
    def get(self):
        import useragent_m
        userAgent = useragent_m.UserAgent()
        userAgent.setUserAgent(self.request.headers['User-Agent'])
        user = User.getByAccessKey(self.request.get('key'))
        report = {}
        step_sum = 0
        steps = user.getStepRecords(Term.getCampaignTerm())
        for step in steps:
            step_sum += step.steps
            report[step.date.month * 100 + step.date.day] = {'steps': step.steps, 'sum': step_sum}
        self.write_response_template({'user': user, 'report': report, 'userAgent': userAgent})

application = webapp.WSGIApplication([
  ('/', SignupPage),
  ('/menu', MenuPage),
  ('/input', InputPage),
  ('/history', HistoryPage),
  ('/ranking', RankingPage),
  ('/profile', ProfilePage),
  ('/myprofile', MyProfilePage),
  ('/comments', CommentsPage),
  ('/report', ReportPage)
], debug=False)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
