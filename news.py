# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
import time
import datetime
from string import Template
import mimetypes

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.file import File
from itools.stl import stl
from itools.vfs import vfs
from itools.web import get_context
from itools import rest
from itools.rest import to_html_events
#from itools.catalog import EqQuery, AndQuery, PhraseQuery, RangeQuery

# Import from abakuc
from base import Handler, Folder

class News(RoleAware, Folder):

    class_id = 'news'
    class_title = u'News'
    class_description = u'Add new news items'
    class_icon16 = 'abakuc/images/News16.png'
    class_icon48 = 'abakuc/images/News48.png'
    class_views = [
        ['view'],
        ['edit_metadata_form'],
        ['add_news_form']]

    new_resource_form__access__ = 'is_branch_manager_or_member'
    new_resource__access__ = 'is_branch_manager_or_member'

    ###################################################################
    ## Create a new news item
    ####

    news_fields = [
        ('dc:title', True),
        ('dc:description', True),
        ('abakuc:closing_date', True),
        ('abakuc:news_text', True)]

    @classmethod
    def new_instance_form(cls, context):
        namespace = context.build_form_namespace(cls.news_fields)
        namespace['class_id'] = News.class_id
        path = '/ui/abakuc/news/news_new_resource_form.xml'
        handler = context.root.get_handler(path)
        return stl(handler, namespace)

    @classmethod
    def new_instance(cls, container, context):
        from datetime import datetime
        username = ''
        if context is not None:
            user = context.user
            if user is not None:
                username = user.name

        # Check data
        keep = [ x for x, y in cls.news_fields ]
        error = context.check_form_input(cls.news_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        # Generate the name(id)
        x = container.search_handlers(handler_class=cls)
        y =  str(len(list(x))+1)
        name = 'news%s' % y
        while container.has_handler(name):
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

        # Job title
        title = context.get_form_value('dc:title')
        # Set properties
        handler = cls()
        metadata = handler.build_metadata()
        for key in ['dc:title' , 'dc:description', 'abakuc:news_text',
                    'abakuc:closing_date']:
            try:
                value = context.get_form_value(key)
                if not value:
                    message = (u"You have to fill all fields. You can edit"
                               u" these afterwords")
                    return context.come_back(message)
                metadata.set_property(key, context.get_form_value(key))
            except:
                message = u'Error of DataTypes.'
                return context.come_back(message)

        # Set the date the news was posted
        date = datetime.now()
        metadata.set_property('dc:date', date)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)

        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'News item has been added.'
        return context.come_back(message, goto=goto)

    add_news_form__access__ = 'is_branch_manager_or_member'
    add_news_form__label__ = u'Add news'
    def add_news_form(self, context):
        url = '../;new_resource_form?type=news'
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new news item'
        return context.come_back(message, goto=goto)


    #######################################################################
    # View news details
    ###
    view__access__ = True
    view__label__ = u'View news'
    def view(self, context):
        username = self.get_property('owner')
        users = self.get_handler('/users')
        user_exist = users.has_handler(username)
        usertitle = (user_exist and
                     users.get_handler(username).get_title() or username)
        user = (user_exist and
                     users.get_handler(username).name)
        userurl = '/users/%s/;view' % user
        company = self.parent.parent
        #date the item was posted
        date = self.get_property('dc:date')
        #namespace
        namespace = {}
        namespace['company'] = company.get_property('dc:title')
        for key in ['dc:title' , 'dc:description', 'abakuc:closing_date']:
            namespace[key] = self.get_property(key)

        news_text = to_html_events(self.get_property('abakuc:news_text'))
        namespace['abakuc:news_text'] = news_text

        from datetime import datetime
        now = datetime.now()
        posted = date
        difference = now - posted
        weeks, days = divmod(difference.days, 7)
        minutes, seconds = divmod(difference.seconds, 60)
        hours, minutes = divmod(minutes, 60)

        time_posted = []
        time_posted.append({'weeks': weeks,
                            'days': days,
                            'hours': hours,
                            'minutes': minutes})

        namespace['date'] = date
        namespace['posted'] = difference
        # Person who added the job
        namespace['user'] = usertitle
        namespace['user_uri'] = userurl
        # if reviewer or members , show users who apply
        is_branch_manager_or_member = False
        user = context.user
        if user :
            reviewer = self.parent.has_user_role(user.name,'abakuc:branch_manager')
            member = self.parent.has_user_role(user.name,'abakuc:branch_member')
            is_branch_manager_or_member = reviewer or member
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        # Navigation in news
        #Search the catalogue, list all news items in company
        #root = context.root
        #catalog = context.server.catalog
        #query = []
        #query.append(EqQuery('format', 'news'))
        #today = (date.today()).strftime('%Y-%m-%d')
        #query.append(RangeQuery('closing_date', today, None))
        #query = AndQuery(*query)
        #results = catalog.search(query)
        #document_names = results.get_documents()
        #doc_index = document_names.index(self.name)
        #is_first_document = doc_index == 0
        #is_last_document = doc_index == len(document_names) - 1
        #namespace['next_doc'] = None
        #namespace['prev_doc'] = None
        #next_doc_img = self.get_handler('/ui/abakuc/images/next_doc.gif')
        #namespace['next_doc_img'] = self.get_pathto(next_doc_img)
        #prev_doc_img = self.get_handler('/ui/abakuc/images/prev_doc.gif')
        #namespace['prev_doc_img'] = self.get_pathto(prev_doc_img)
        #if document_names:
        #    # Next document
        #    if is_last_document:
        #        namespace['next_doc'] = '../../;view'
        #    else:
        #        namespace['next_doc'] = (
        #            '../%s/;view' % document_names[doc_index + 1])
        #    # Previous document

        handler = self.get_handler('/ui/abakuc/news/news_view.xml')
        return stl(handler, namespace)

    view_rest__access__ = True
    view_rest__sublabel__ = u"As reStructuredText"
    def view_rest(self, context):
        news_text = self.news_text.encode('utf-8')
        return rest.to_html_events(news_text)


    view_xml__access__ = True
    view_xml__sublabel__ = u"As reStructuredText"
    def view_xml(self, context):
        namespace = {}
        news_text = self.news_text.encode('utf-8')
        namespace['abakuc:news_text'] = rest.to_str(news_text, format='xml')


        handler = self.get_handler('/ui/abakuc/news/news_view.xml')
        return stl(handler, namespace)
    ###########################################################
    # Edit details
    ###########################################################

    edit_news_fields = ['dc:title' , 'dc:description',
                        'abakuc:closing_date']


    edit_metadata_form__access__ = 'is_branch_manager_or_member'
    edit_metadata_form__label__ = 'Edit news'
    def edit_metadata_form(self, context):
        namespace = {}
        for key in self.edit_news_fields:
            namespace[key] = self.get_property(key)
        # Build namespace
        news_text = self.get_property('abakuc:news_text')
        namespace['abakuc:news_text'] = news_text
        # Return stl
        handler = self.get_handler('/ui/abakuc/news/news_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager_or_member'
    def edit_metadata(self, context):
        for key in self.edit_news_fields:
            self.set_property(key, context.get_form_value(key))
        news_text = context.get_form_value('abakuc:news_text')
        self.set_property('abakuc:news_text', news_text)
        message = u'Changes Saved.'
        return context.come_back(message, goto=';view')


    #######################################################################
    ## Indexes
    #######################################################################

    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        indexes['closing_date'] = self.get_property('abakuc:closing_date')
        address = self.parent
        company = address.parent
        indexes['company'] = company.name
        indexes['address'] = address.name
        return indexes


    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager_or_member(self, user, object):
        address = self.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_remove(self, user, object):
        address = self.parent
        return address.is_branch_manager_or_member(user, object)

register_object_class(News)
