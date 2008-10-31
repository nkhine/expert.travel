# -*- coding: UTF-8 -*-

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
from itools.cms.widgets import batch

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


    edit_form__access__ = 'is_admin'
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
        forum = self.parent
        for i, id in enumerate([0] + self.get_replies()):
            message = get_forum_handler(self, id)
            author_id = message.get_property('owner')
            metadata = users.get_handler('%s.metadata' % author_id)
            namespace.append({
                'author': (users.get_handler(author_id).get_title() or
                    metadata.get_property('dc:title') or
                    metadata.get_property('ikaaro:email')),
                'registered': metadata.get_property('abakuc:registration_date'),
                'mtime': format_datetime(message.get_mtime(), accept_language),
                'url': '/%s/%s/' % (forum.name, message),
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
        messages = self.get_message_namespace(context)
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 8
        batch_total = len(messages)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        messages = messages[batch_start:batch_fin]
         # Namespace
        if messages:
            messages_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=(u"There is 1 message.",
                                    u"There are ${n} messages."))
            msg = None
        else:
            messages_batch = None
            msg = u"Appologies, currently we don't have any messages in this forum"
        namespace['batch'] = messages_batch
        namespace['msg'] = msg

        namespace['messages'] = messages

        #user = context.user
        #username = user and user.name
        #if username:
        #    namespace['rte'] = self.get_rte(context, 'data', None)
        #else:
        #    namespace['rte'] = None
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
        forum_name = self.name
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
                'author': (users.get_handler(first_author_id).get_title() or
                    first_metadata.get_property('dc:title') or
                    first_metadata.get_property('ikaaro:email')),
                'replies': len(thread.get_replies()),
                'last_date': format_datetime(last.get_mtime(), accept_language),
                'last_author': (users.get_handler(last_author_id).get_title() or
                    last_metadata.get_property('dc:title') or
                    last_metadata.get_property('ikaaro:email')),
            })

        namespace.sort(key=itemgetter('last_date'), reverse=True)

        return namespace

    view__access__ = True 
    view__label__ = u"Forum"
    def view(self, context):
        namespace = {}
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')

        namespace['title'] = self.get_title()
        namespace['description'] = self.get_property('dc:description')
        threads = self.get_thread_namespace(context)
        # Get the top 5 most replied to threads
        most_popular = []
        for item in threads:
            if item['replies'] >= 4:
                most_popular.append(item)
        result = sorted(most_popular, key=itemgetter('replies'), reverse=True)
        namespace['most_popular'] = result[:5]
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 8
        batch_total = len(most_popular)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        most_popular = most_popular[batch_start:batch_fin]
         # Namespace
        if most_popular:
            most_popular = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=(u"There is 1 thread.",
                                    u"There are ${n} threads."))
            msg = None
        else:
            most_popular = None
            msg = u"Appologies, currently there are no threads."
        namespace['batch'] = most_popular
        namespace['msg'] = msg
        namespace['threads'] = threads

        add_forum_style(context)
        handler = self.get_handler('/ui/abakuc/forum/view.xml')
        return stl(handler, namespace)


    new_thread_form__access__ = 'is_allowed_to_edit'
    new_thread_form__label__ = u"New Thread"
    def new_thread_form(self, context):
        namespace = {}
        user = context.user
        #types = ['question', 'announcment']
        #print types
        #namespace['types'] = types
        #print namespace['types']
        # Is global admin
        ac = self.get_access_control()
        from training import Training
        if isinstance(ac, Training):
            namespace['is_admin'] = ac.is_training_manager(user, self)
        else:
            namespace['is_admin'] = ac.is_admin(user, self)
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

        #if self.has_handler(name):
        #    return context.come_back(u"This thread already exists.")
        # Generate the name(id)
        x = self.search_handlers(handler_class=Thread)
        y =  str(len(list(x))+1)
        name = 'thread%s' % y
        while self.has_handler(name):
              try:
                  names = name.split('-')
                  if len(names) > 1:
                      name = '-'.join(names[:-1])
                      number = str(int(names[-1]) + 1)
                      name = [name, number]
                      name = '-'.join(name)
                  else:
                      name = '-'.join(names) + '-1'
              except:
                  name = '-'.join(names) + '-1'

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
