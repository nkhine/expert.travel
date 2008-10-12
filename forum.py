# -*- coding: UTF-8 -*-
# Copyright (C) 2004-2005 Luis Arturo Belmar-Letelier <luis@itaapy.com>
# Copyright (C) 2006-2007 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2007 Sylvain Taverne <sylvain@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from operator import itemgetter
from datetime import datetime

# Import from itools
from itools.datatypes import FileName, Unicode
from itools.i18n import format_datetime
from itools.stl import stl
from itools.xml import Parser
from itools.xhtml import sanitize_stream, xhtml_uri
from itools.html import Parser as HTMLParser
from itools.rest import checkid
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.registry import register_object_class
from itools.cms.html import XHTMLFile
from itools.cms.text import Text


def add_forum_style(context):
    style = context.root.get_handler('ui/forum/forum.css')
    context.styles.append(context.handler.get_pathto(style))


def get_forum_handler(container, handler_name):
    """Used for retro-compatibility with Itools 0.16.3 and anterior versions"""
    #XXX To remove in 0.17
    xhtml_document = '%s.xhtml' % handler_name
    if container.has_handler(xhtml_document):
        return container.get_handler(xhtml_document)
    else:
        return container.get_handler('%s.txt' % handler_name)



class Message(XHTMLFile):

    class_id = 'ForumMessage'
    class_title = u"Message"
    class_description = u"Message in a thread"
    class_views = [['edit_form'], ['history_form']]


    def new(self, data):
        data = HTMLParser(data)
        self.events = sanitize_stream(data)


    def _load_state_from_file(self, file): 
        data = file.read()
        stream = Parser(data, {None: xhtml_uri})
        self.events = list(stream)


    # Remove from searches
    def to_text(self):
        return u''


    def edit_form(self, context):
        """WYSIWYG editor for HTML documents."""
        # Edit with a rich text editor
        namespace = {}
        # Epoz expects HTML
        namespace['timestamp'] = datetime.now()
        namespace['rte'] = self.get_rte(context, 'data', self.events)

        handler = self.get_handler('/ui/html/edit.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_admin'
    def edit(self, context):
        data = context.get_form_value('data')
        data = HTMLParser(data)
        self.events = sanitize_stream(data)
        self.set_changed()

        return context.come_back(MSG_CHANGES_SAVED, goto='../;view')


    def get_epoz_data(self):
        return self.events


class Thread(Folder):

    class_id = 'ForumThread'
    class_title = u"Thread"
    class_description = u"A thread to discuss"
    class_views = [['view'], ['edit_metadata_form']]

    message_class = Message


    def new(self, data=u''):
        Folder.new(self)
        cache = self.cache
        message = self.message_class(data=data)
        cache['0.xhtml'] = message
        cache['0.xhtml.metadata'] = message.build_metadata()


    def to_text(self):
        text = []

        # index messages in order (XXX necessary?)
        for id in ([0] + self.get_replies()):
            message = get_forum_handler(self, id)
            text.append(message.to_text())

        return u'\n'.join(text)


    def get_document_types(self):
        return [self.message_class]


    def get_replies(self):
        #XXX To remove in 0.17
        replies = self.search_handlers(handler_class=(XHTMLFile, Text))
        posts = [int(FileName.decode(x.name)[0]) for x in replies]
        posts.sort()

        # deduce original post
        return posts[1:]


    def get_last_post(self):
        replies = self.get_replies()
        if replies:
            last = replies[-1]
        else:
            last = 0

        return get_forum_handler(self, last)


    def get_message_namespace(self, context):
        user = context.user
        username = user and user.name
        namespace = []
        users = self.get_handler('/users')
        ac = self.get_access_control()
        accept_language = context.get_accept_language()
        for i, id in enumerate([0] + self.get_replies()):
            message = get_forum_handler(self, id)
            author_id = message.get_property('owner')
            metadata = users.get_handler('%s.metadata' % author_id)
            namespace.append({
                'author': (metadata.get_property('dc:title') or
                    metadata.get_property('ikaaro:email')),
                'mtime': format_datetime(message.get_mtime(), accept_language),
                'body': message.events,
                'editable': ac.is_admin(user, message),
                'edit_form': '%s/;edit_form' % message.name,
            })

        return namespace


    view__access__ = 'is_allowed_to_view'
    view__label__ = u"View"
    def view(self, context):
        namespace = {}

        namespace['title'] = self.get_title()
        namespace['description'] = self.get_property('dc:description')
        namespace['messages'] = self.get_message_namespace(context)
        namespace['rte'] = self.get_rte(context, 'data', None)
        add_forum_style(context)

        handler = self.get_handler('/ui/abakuc/forum/thread/view.xml')
        return stl(handler, namespace)


    new_reply__access__ = 'is_allowed_to_edit'
    def new_reply(self, context):
        replies = self.get_replies()
        if replies:
            last_reply = max(replies)
        else:
            last_reply = 0

        next_reply = str(last_reply + 1)
        name = FileName.encode((next_reply, 'xhtml', None))

        data = context.get_form_value('data')
        reply = self.message_class(data=data)
        self.set_object(name, reply)

        return context.come_back(u"Reply Posted.", goto='#new_reply')


    def get_epoz_data(self):
        return None


class Forum(Folder):

    class_id = 'Forum'
    class_title = u'Forum'
    class_description = u'A forum'
    class_icon48 = 'images/Forum48.png'
    class_icon16 = 'images/Forum16.png'
    class_views = [['view'], ['new_thread_form'], ['edit_metadata_form']]

    thread_class = Thread


    def get_document_types(self):
        return [self.thread_class]


    def get_thread_namespace(self, context):
        accept_language = context.get_accept_language()
        namespace = []
        users = self.get_handler('/users')
        # XXX Retrocompatibility (For 0.17 -> only search xhtml Documents)
        from itools.cms.text import Text
        thread_txt = list(self.search_handlers(handler_class=Text))
        threads = list(self.search_handlers(handler_class=self.thread_class))
        threads += thread_txt

        for thread in threads:
            first = get_forum_handler(thread, '0')
            first_author_id = first.get_property('owner')
            first_metadata = users.get_handler('%s.metadata' % first_author_id)
            last = thread.get_last_post()
            last_author_id = last.get_property('owner')
            last_metadata = users.get_handler('%s.metadata' % last_author_id)
            namespace.append({
                'name': thread.name,
                'title': thread.get_title(),
                'description': thread.get_property('dc:description'),
                'author': (first_metadata.get_property('dc:title') or
                    first_metadata.get_property('ikaaro:email')),
                'replies': len(thread.get_replies()),
                'last_date': format_datetime(last.get_mtime(), accept_language),
                'last_author': (last_metadata.get_property('dc:title') or
                    last_metadata.get_property('ikaaro:email')),
            })

        namespace.sort(key=itemgetter('last_date'), reverse=True)

        return namespace

    #def is_branch_manager(self, user, object):
    #    if not user:
    #        return False
    #    # Is global admin
    #    root = object.get_root()
    #    if root.is_admin(user, self):
    #        return True
    #    # Is reviewer or member
    #    return self.has_user_role(user.name, 'abakuc:branch_manager')


    #def is_travel_agent(self, user, object):
    #    if user is None:
    #        return False

    #    # TEST 015
    #    return self.has_user_role(user.name, 'abakuc:branch_member')

    #def is_allowed_to_edit(self, user, object):
    #    root = object.get_site_root()
    #    return root.is_branch_manager(user, object)


    view__access__ = True 
    view__label__ = u"Forum"
    def view(self, context):
        namespace = {}

        namespace['title'] = self.get_title()
        namespace['description'] = self.get_property('dc:description')
        namespace['threads'] = self.get_thread_namespace(context)
        #namespace['is_allowed_to_edit'] = self.is_allowed_to_edit(context)
        #print namespace['is_allowed_to_edit'] 

        add_forum_style(context)

        handler = self.get_handler('/ui/abakuc/forum/view.xml')
        return stl(handler, namespace)


    new_thread_form__access__ = 'is_allowed_to_edit'
    new_thread_form__label__ = u"New Thread"
    def new_thread_form(self, context):
        namespace = {}
        namespace['rte'] =  self.get_rte(context, 'data', None)
        add_forum_style(context)
        handler = self.get_handler('/ui/abakuc/forum/thread/new_thread.xml')
        return stl(handler, namespace)


    new_thread__access__ = 'is_allowed_to_edit'
    def new_thread(self, context):
        title = context.get_form_value('dc:title').strip()
        if not title:
            return context.come_back(u"No title given.")

        name = checkid(title)
        if name is None:
            return context.come_back(u"Invalid title.")

        if self.has_handler(name):
            return context.come_back(u"This thread already exists.")

        root = context.root
        website_languages = root.get_property('ikaaro:website_languages')
        default_language = website_languages[0]

        data = context.get_form_value('data')
        thread = self.thread_class(data=data)
        thread, metadata = self.set_object(name, thread)
        thread.set_property('dc:title', title, language=default_language)

        return context.come_back(u"Thread Created.", goto=name)


    def get_epoz_data(self):
        return None


register_object_class(Forum)
register_object_class(Thread)
register_object_class(Message)
