#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.api import taskqueue

import logging
from pedomemo import *

class CountStepsWorker(webapp.RequestHandler):
    def get(self):
        logging.info('CountStepsWorker started.')
        start_date = parseDate(self.request.get('start'))
        end_date = parseDate(self.request.get('end'))
        StepSummary.countStepRecords(Term(start_date, end_date))
        logging.info('Calculate steps complate.')

class CountTaskWorker(webapp.RequestHandler):
    def get(self):
        logging.info('CountTaskWorker started.')
        for task in CountTask.all():
            taskqueue.add(url='/admin/count', method='GET',
                          params={'start': task.start_date.strftime('%Y%m%d'),
                                  'end': task.end_date.strftime('%Y%m%d')})
            task.delete()
        logging.info('Task added.')

application = webapp.WSGIApplication([
  ('/admin/count', CountStepsWorker),
  ('/admin/task', CountTaskWorker)
], debug=False)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
