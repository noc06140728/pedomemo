#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import webapp2
from google.appengine.api import taskqueue

import logging
from pedomemo import *

class CountStepsWorker(webapp2.RequestHandler):
    def get(self):
        logging.info('CountStepsWorker started.')
        start_date = parseDate(self.request.get('start'))
        end_date = parseDate(self.request.get('end'))
        StepSummary.countStepRecords(Term(start_date, end_date))
        logging.info('Calculate steps complate.')

class CountTaskWorker(webapp2.RequestHandler):
    def get(self):
        logging.info('CountTaskWorker started.')
        for task in CountTask.all():
            taskqueue.add(url='/admin/count', method='GET',
                          params={'start': task.start_date.strftime('%Y%m%d'),
                                  'end': task.end_date.strftime('%Y%m%d')})
            task.delete()
        logging.info('Task added.')

app = webapp2.WSGIApplication([
  ('/admin/count', CountStepsWorker),
  ('/admin/task', CountTaskWorker)
], debug=True)
