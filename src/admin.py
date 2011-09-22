#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import wsgiref.handlers

from google.appengine.ext import webapp

from pedomemo import *

class CountStepsWorker(webapp.RequestHandler):
    def get(self):
        import logging
        logging.info('test.')
        StepSummary.countStepRecords(Term())
        StepSummary.countStepRecords(Term.getCampaignTerm())
        self.response.out.write('fin.')

application = webapp.WSGIApplication([
  ('/admin/count', CountStepsWorker)
], debug=False)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
