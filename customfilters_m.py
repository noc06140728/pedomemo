#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import datetime
from google.appengine.ext import webapp

register = webapp.template.create_template_register()

def sjis(body):
	return body.encode('Shift_JIS')

register.filter(sjis)

