# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
import datetime
from string import Template
import mimetypes

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.file import File
from itools.stl import stl
from itools.web import get_context
from itools.rest import checkid, to_html_events

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
        ['view_candidatures'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]

    
    def get_document_types(self):
        return [File]


    new_resource_form__access__ = True
    new_resource__access__ = True


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
        # Check data
        keep = [ x for x, y in cls.news_fields ]
        error = context.check_form_input(cls.news_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        #
        name = context.get_form_value('name')
        title = context.get_form_value('dc:title')
        
        # Check the name 
        name = name.strip() or title.strip()
        if not name:
            message = u'Please give a title to your job'
            return context.come_back(message)
        
        name = checkid(name)
        if name is None:
            message = (u'The title contains illegal characters,'
                       u' choose another one.')
            return context.come_back(message)
        # Name already used?
        while container.has_handler(name):
              try:
                  names = name.split('_')
                  if len(names) > 1:
                      name = '_'.join(names[:-1])
                      number = str(int(names[-1]) + 1) 
                      name = [name, number]
                      name = '_'.join(name)
                  else:
                      name = '_'.join(names) + '_1'
              except:
                  name = '_'.join(names) + '_1'
        
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

        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)
        
        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'News has been added.'
        return context.come_back(message, goto=goto) 
    
    #######################################################################
    # View news details
    ###

    view__access__ = True
    view__label__ = u'News'
    def view(self, context):
        company = self.parent.parent
        #namespace
        namespace = {}
        namespace['company'] = company.get_property('dc:title')
        for key in ['dc:title' , 'dc:description', 'abakuc:closing_date']:
            namespace[key] = self.get_property(key)
        
        news_text = to_html_events(self.get_property('abakuc:news_text'))
        namespace['abakuc:news_text'] = news_text

        # if reviewer or members , show users who apply
        is_reviewer_or_member = False
        user = context.user
        if user :
            reviewer = self.parent.has_user_role(user.name,'ikaaro:reviewers')
            member = self.parent.has_user_role(user.name,'ikaaro:members')
            is_reviewer_or_member = reviewer or member 
        namespace['is_reviewer_or_member'] = is_reviewer_or_member


        handler = self.get_handler('/ui/abakuc/news/news_view.xml')
        return stl(handler, namespace)


    ###########################################################
    # Edit details
    ###########################################################
    
    edit_news_fields = ['dc:title' , 'dc:description',
                        'abakuc:closing_date']
    

    edit_metadata_form__access__ = 'is_reviewer_or_member'
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

    
    edit_metadata__access__ = 'is_reviewer_or_member'
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
    def is_reviewer_or_member(self, user, object):
        address = self.parent
        return address.is_reviewer_or_member(user, object)

    def is_allowed_to_remove(self, user, object):
        address = self.parent.parent
        return address.is_reviewer(user, object)

register_object_class(News)