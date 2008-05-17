# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath, get_version
from itools.cms.registry import register_object_class
from itools.cms.skins import register_skin

# Import from abakuc
from root import Root
from skins import countries, trainings, websites
import document
import exam
import marketing
import metadata
import news
import training
import users

__version__ = get_version(globals())

# Register the skins
path = get_abspath(globals(), 'ui')
register_skin('abakuc', path)

base = get_abspath(globals(), 'skins')
for name, cls in websites.items():
    path = base + '/' + name
    register_skin(name, cls(path))

country = get_abspath(globals(), 'skins/countries')
for name, cls in countries.items():
    path = country + '/' + name
    register_skin(name, cls(path))

training = get_abspath(globals(), 'skins/training')
for name, cls in trainings.items():
    path = training + '/' + name
    register_skin(name, cls(path))

for handler_class in [document.Document, exam.Exam,
                      marketing.Marketing, news.News,
                      users.UserFolder, users.User]:
    register_object_class(handler_class)
