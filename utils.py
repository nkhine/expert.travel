# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime
from operator import itemgetter
from string import Template

# Import from itools
from itools.i18n import format_datetime
from itools.stl import stl
from itools.web import get_context
from itools.datatypes import XMLAttribute
from itools.cms.base import Handler
from itools.xml import Parser

namespaces = {
    None: 'http://www.w3.org/1999/xhtml',
    'stl': 'http://xml.itools.org/namespaces/stl'}

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

def get_sort_name(name):
    """ 
    Return a tuple for ex. ('page', 4) for 'page4', and 
    and (1, 'a') for '1a' used for sort by id
    """
    name = name.strip()
    if not name:
        return ()
    # Split the name in sequences of digits and non-digits
    last = name[0]
    result = [last]
    for i in name[1:]:
        if last.isdigit() is i.isdigit():
            result[-1] += i
        else:
            result.append(i)
        last = i
    # Cast to int the digit segments
    result = [ x.isdigit() and int(x) or x for x in result ]

    return tuple(result)

def t1(uri, start, size, total, gettext=Handler.gettext,
          msgs=(u"There is 1 object.", u"There are ${n} objects.")):
    # Plural forms (XXX do it the gettext way)
    if total == 1:
        msg1 = gettext(msgs[0])
    else:
        msg1 = gettext(msgs[1])
        msg1 = Template(msg1).substitute(n=total)
    msg1 = msg1.encode('utf-8')

    # Calculate end
    end = min(start + size, total)

    # Previous
    previous = None
    if start > 0:
        previous = max(start - size, 0)
        previous = str(previous)
        previous = uri.replace(t1=previous)
        previous = str(previous)
        previous = XMLAttribute.encode(previous)
        previous = '<a href="%s" title="%s">&lt;&lt;</a>' \
                   % (previous, gettext(u'Previous'))
    # Next
    next = None
    if end < total:
        next = str(end)
        next = uri.replace(t1=next)
        next = str(next)
        next = XMLAttribute.encode(next)
        next = '<a href="%s" title="%s">&gt;&gt;</a>' \
               % (next, gettext(u'Next'))

    # Output
    if previous is None and next is None:
        msg = msg1
    else:
        # View more
        if previous is None:
            link = next
        elif next is None:
            link = previous
        else:
            link = '%s %s' % (previous, next)

        msg2 = gettext(u"View from ${start} to ${end} (${link}):")
        msg2 = Template(msg2)
        msg2 = msg2.substitute(start=(start+1), end=end, link=link)
        msg2 = msg2.encode('utf-8')

        msg = '%s %s' % (msg1, msg2)

    # Wrap around a paragraph
    return Parser('<p class="batchcontrol">%s</p>' % msg, namespaces)

def t2(uri, start, size, total, gettext=Handler.gettext,
          msgs=(u"There is 1 object.", u"There are ${n} objects.")):
    # Plural forms (XXX do it the gettext way)
    if total == 1:
        msg1 = gettext(msgs[0])
    else:
        msg1 = gettext(msgs[1])
        msg1 = Template(msg1).substitute(n=total)
    msg1 = msg1.encode('utf-8')

    # Calculate end
    end = min(start + size, total)

    # Previous
    previous = None
    if start > 0:
        previous = max(start - size, 0)
        previous = str(previous)
        previous = uri.replace(t2=previous)
        previous = str(previous)
        previous = XMLAttribute.encode(previous)
        previous = '<a href="%s" title="%s">&lt;&lt;</a>' \
                   % (previous, gettext(u'Previous'))
    # Next
    next = None
    if end < total:
        next = str(end)
        next = uri.replace(t2=next)
        next = str(next)
        next = XMLAttribute.encode(next)
        next = '<a href="%s" title="%s">&gt;&gt;</a>' \
               % (next, gettext(u'Next'))

    # Output
    if previous is None and next is None:
        msg = msg1
    else:
        # View more
        if previous is None:
            link = next
        elif next is None:
            link = previous
        else:
            link = '%s %s' % (previous, next)

        msg2 = gettext(u"View from ${start} to ${end} (${link}):")
        msg2 = Template(msg2)
        msg2 = msg2.substitute(start=(start+1), end=end, link=link)
        msg2 = msg2.encode('utf-8')

        msg = '%s %s' % (msg1, msg2)

    # Wrap around a paragraph
    return Parser('<p class="batchcontrol">%s</p>' % msg, namespaces)

def t3(uri, start, size, total, gettext=Handler.gettext,
          msgs=(u"There is 1 object.", u"There are ${n} objects.")):
    # Plural forms (XXX do it the gettext way)
    if total == 1:
        msg1 = gettext(msgs[0])
    else:
        msg1 = gettext(msgs[1])
        msg1 = Template(msg1).substitute(n=total)
    msg1 = msg1.encode('utf-8')

    # Calculate end
    end = min(start + size, total)

    # Previous
    previous = None
    if start > 0:
        previous = max(start - size, 0)
        previous = str(previous)
        previous = uri.replace(t3=previous)
        previous = str(previous)
        previous = XMLAttribute.encode(previous)
        previous = '<a href="%s" title="%s">&lt;&lt;</a>' \
                   % (previous, gettext(u'Previous'))
    # Next
    next = None
    if end < total:
        next = str(end)
        next = uri.replace(t3=next)
        next = str(next)
        next = XMLAttribute.encode(next)
        next = '<a href="%s" title="%s">&gt;&gt;</a>' \
               % (next, gettext(u'Next'))

    # Output
    if previous is None and next is None:
        msg = msg1
    else:
        # View more
        if previous is None:
            link = next
        elif next is None:
            link = previous
        else:
            link = '%s %s' % (previous, next)

        msg2 = gettext(u"View from ${start} to ${end} (${link}):")
        msg2 = Template(msg2)
        msg2 = msg2.substitute(start=(start+1), end=end, link=link)
        msg2 = msg2.encode('utf-8')

        msg = '%s %s' % (msg1, msg2)

    # Wrap around a paragraph
    return Parser('<p class="batchcontrol">%s</p>' % msg, namespaces)

def t4(uri, start, size, total, gettext=Handler.gettext,
          msgs=(u"There is 1 object.", u"There are ${n} objects.")):
    # Plural forms (XXX do it the gettext way)
    if total == 1:
        msg1 = gettext(msgs[0])
    else:
        msg1 = gettext(msgs[1])
        msg1 = Template(msg1).substitute(n=total)
    msg1 = msg1.encode('utf-8')

    # Calculate end
    end = min(start + size, total)

    # Previous
    previous = None
    if start > 0:
        previous = max(start - size, 0)
        previous = str(previous)
        previous = uri.replace(t4=previous)
        previous = str(previous)
        previous = XMLAttribute.encode(previous)
        previous = '<a href="%s" title="%s">&lt;&lt;</a>' \
                   % (previous, gettext(u'Previous'))
    # Next
    next = None
    if end < total:
        next = str(end)
        next = uri.replace(t4=next)
        next = str(next)
        next = XMLAttribute.encode(next)
        next = '<a href="%s" title="%s">&gt;&gt;</a>' \
               % (next, gettext(u'Next'))

    # Output
    if previous is None and next is None:
        msg = msg1
    else:
        # View more
        if previous is None:
            link = next
        elif next is None:
            link = previous
        else:
            link = '%s %s' % (previous, next)

        msg2 = gettext(u"View from ${start} to ${end} (${link}):")
        msg2 = Template(msg2)
        msg2 = msg2.substitute(start=(start+1), end=end, link=link)
        msg2 = msg2.encode('utf-8')

        msg = '%s %s' % (msg1, msg2)

    # Wrap around a paragraph
    return Parser('<p class="batchcontrol">%s</p>' % msg, namespaces)
