#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import wsgiref.handlers

from google.appengine.ext import webapp

from pedomemo import *

class CountStepsWorker(webapp.RequestHandler):
    def get(self):
        start_date = parseDate(self.request.get('start'))
        end_date = parseDate(self.request.get('end'))
        StepSummary.countStepRecords(Term(start_date, end_date))
#        ym = self.request.get('ym')
#        if len(ym) <> 6:
#            raise ApplicationError('Invarid specified year-month(ym).')
#        year = ym[0:4]
#        month = ym[4:6]
#        StepSummary.countStepRecords(Term(year, month))
#        StepSummary.countStepRecords(Term.getCampaignTerm(year))
        self.response.out.write('Calculate steps complate.')

application = webapp.WSGIApplication([
  ('/admin/count', CountStepsWorker)
], debug=False)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
