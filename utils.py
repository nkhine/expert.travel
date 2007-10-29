# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime
from operator import itemgetter

# Import from itools
from itools.i18n import format_datetime
from itools.stl import stl
from itools.web import get_context



def title_to_name(title):
    title = title.encode('ascii', 'replace')
    title = title.lower()
    name = title.replace('/', '-').replace('?', '-')
    for c in '.,&()':
        name = name.replace(c, '')
    return '-'.join(name.split())

def get_new_id(self, prefix=''):
    ids = []
    for name in self.get_handler_names():
        if name.endswith('.metadata'):
            continue
        if prefix:
            if not name.startswith(prefix):
                continue
            name = name[len(prefix):]
        try:
            id = int(name)
        except ValueError:
            continue
        ids.append(id)

    if ids:
        ids.sort()
        return prefix + str(ids[-1] + 1)
    
    return prefix + '0'

class VersioningAware(object):

    def commit_revision(self):
        context = get_context()
        username = ''
        if context is not None:
            user = context.user
            if user is not None:
                username = user.name

        property = {
            (None, 'user'): username,
            ('dc', 'date'): datetime.now(),
        }

        self.set_property('ikaaro:history', property)


    def get_revisions(self, context):
        accept = context.get_accept_language()
        revisions = []

        for revision in self.get_property('ikaaro:history'):
            username = revision[(None, 'user')]
            date = revision[('dc', 'date')]
            revisions.append({
                'username': username,
                'date': format_datetime(date, accept=accept),
                'sort_date': date})

        revisions.sort(key=itemgetter('sort_date'), reverse=True)
        return revisions


    ########################################################################
    # User Interface
    ########################################################################
    history_form__access__ = 'is_allowed_to_view'
    history_form__label__ = u'History'
    def history_form(self, context):
        namespace = {}

        namespace['revisions'] = self.get_revisions(context)

        handler = self.get_handler('/ui/abakuc/history.xml')
        return stl(handler, namespace)


