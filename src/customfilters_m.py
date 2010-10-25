#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import datetime
import re
from google.appengine.ext import webapp

register = webapp.template.create_template_register()

def sjis(body):
	return body.encode('Shift_JIS')

def commafmt(value):
    return re.compile(r'(\d)(?=(?:\d{3})+$)').sub(r'\1,', str(value))

register.filter(sjis)
register.filter(commafmt)


