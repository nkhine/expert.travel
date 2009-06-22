# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
import time
import datetime
import random
from string import Template
import mimetypes
from StringIO import StringIO

# Import from PIL
from PIL import Image as PILImage

# Import from itools
#from itools.cms.access import RoleAware
from itools import get_abspath
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.cms.file import File
from itools.cms.html import XHTMLFile
from itools.cms.messages import *
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.utils import generate_password, reduce_string
from itools.cms.widgets import batch
from itools.datatypes import Integer
from itools.i18n import get_language_name
from itools.rest import checkid
from itools.rest import rest, to_html_events
from itools.stl import stl
from itools.uri import Path
from itools.uri import Path, get_reference
from itools.vfs import vfs
from itools.web import get_context

from itools.cms.workflow import WorkflowAware
# Import from abakuc
from base import Handler, Folder
from utils import abspath_to_relpath, get_sort_name

class Itinerary(Folder, WorkflowAware):
    '''
        Folder with view and images from days containing
        day objects which are similar to the training
        documents in that we can traverse them.
    '''
    class_id = 'itinerary'
    class_title = u'Itinerary'
    class_description = u'Add new holiday itinerary'
    class_icon16 = 'abakuc/images/News16.png'
    class_icon48 = 'abakuc/images/News48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['edit_form'],
        ['state_form'],
        ['new_resource_form']]

    browse_content__access__ = 'is_admin'
    new_resource_form__access__ = 'is_branch_manager_or_member'
    new_resource__access__ = 'is_branch_manager_or_member'

    def get_document_types(self):
        return [ItineraryDay, File]

    ###################################################################
    # API 
    ###################################################################
    def get_itinerary_day(self):
        root = self.get_root()
        handlers = self.search_handlers(handler_class=ItineraryDay)
        items = []
        for item in handlers:
            items.append(root.get_handler(item.abspath))
        return items

    def get_itinerary_days(self):
        """
          Returns a namespace (list) of all itineraries
          Each product should only have one itinerary.
        """
        path = '.'
        container = self.get_handler(path)
        items = list(container.search_handlers(format=ItineraryDay.class_id))
        return items


    def get_itinerary_images(self, context):
        """
        Return a list with all the itinerary days that have been
        published.
        """
        items = []
        # Get all the images for the Itinerary 
        handlers = self.search_handlers(handler_class=File)
        here = context.handler
        for item in handlers:
            path = Path(item.abspath)
            url = abspath_to_relpath(path)
            type = item.get_content_type()
            if type == 'image':
                url_220 = '%s/;icon220' % (url)
                url_70 = '%s/;icon70' % (url)
                items.append({
                    'name': item.name,
                    'title': item.get_title(),
                    'description': item.get_property('dc:description'),
                    'url_220': url_220,
                    'url_70': url_70,
                    'icon': item.get_path_to_icon(size=16),
                    'mtime': item.get_mtime().strftime('%Y-%m-%d %H:%M'),
                    'description': item.get_property('dc:description'),
                    'keywords': item.get_property('dc:subject')
                })
        # Get all the documents for Itinerary Days
        itinerary_days = self.get_itinerary_days()
        for item in itinerary_days:
            path = Path(item.abspath)
            url = abspath_to_relpath(path)
            handler = self.get_handler(path)
            handlers = handler.search_handlers(handler_class=File)
            for item in handlers:
                image_path = Path(item.abspath)
                type = item.get_content_type()
                if type == 'image':
                    url_220 = '%s/%s/;icon220' % (url, item.name)
                    url_70 = '%s/%s/;icon70' % (url, item.name)
                    items.append({
                        'name': item.name,
                        'title': item.get_title(),
                        'description': item.get_property('dc:description'),
                        'url_220': url_220,
                        'url_70': url_70,
                        'icon': item.get_path_to_icon(size=16),
                        'mtime': item.get_mtime().strftime('%Y-%m-%d %H:%M'),
                        'description': handler.get_property('dc:description'),
                        'keywords': handler.get_property('dc:subject')
                    })
        return items


    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        # We need to index the news, jobs and products
        indexes['itinerary_day'] = self.get_itinerary_day()
        return indexes

    ###################################################################
    # Create a new news item
    ###################################################################

    itinerary_fields = [
        ('dc:title', True),
        ('dc:description', True),
        ('abakuc:text', True)]

    @classmethod
    def new_instance_form(cls, context):
        namespace = context.build_form_namespace(cls.itinerary_fields)
        namespace['class_id'] = Itinerary.class_id
        path = '/ui/abakuc/product/itinerary/new_instance_form.xml'
        handler = context.root.get_handler(path)
        return stl(handler, namespace)

    @classmethod
    def new_instance(cls, container, context):
        # Generate the name(id)
        x = container.search_handlers(handler_class=cls)
        # A product can only have one itinerary
        items = list(x)
        if items != 0:
            for item in items:
                root = context.root
                item = root.get_handler(item.abspath)
                goto = '%s/;view' % item.name
                message = u'Please modify the original itinerary!'
                return context.come_back(message, goto=goto)            
        from datetime import datetime
        username = ''
        if context is not None:
            user = context.user
            if user is not None:
                username = user.name

        # Check data
        keep = [ x for x, y in cls.itinerary_fields ]
        error = context.check_form_input(cls.itinerary_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        name = 'itinerary'
        # Job title
        title = context.get_form_value('dc:title')
        # Set properties
        handler = cls()
        metadata = handler.build_metadata()
        for key in ['dc:title' , 'dc:description', 'abakuc:text']:
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

        # Set the date the itinerary was posted
        date = datetime.now()
        metadata.set_property('dc:date', date)
        metadata.set_property('abakuc:unique_id', generate_password(30))
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)
        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'Itinerary item has been added. Add some itinerary days now!'
        return context.come_back(message, goto=goto)


    #add_itinerary_day_form__access__ = 'is_branch_manager_or_member'
    #add_itinerary_day_form__label__ = u'Add an itinerary day'
    #def add_itinerary_day_form(self, context):
    #    url = '../;new_resource_form?type=itinerary_day'
    #    goto = context.uri.resolve(url)
    #    message = u'Please use this form to add a new itinerary day'
    #    return context.come_back(message, goto=goto)


    #######################################################################
    # Tabs used in the management screen
    #######################################################################
    manage__access__ = 'is_branch_manager_or_member'
    manage__label__ = 'Edit itinerary'
    def manage(self, context):
        # Add a script
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        # Build stl
        root = context.root
        namespace = {}
        namespace['edit'] = self.edit_metadata_form(context)
        namespace['itinerary'] = self.edit_itinerary_days_form(context)
        namespace['browse_content'] = self.browse_content(context)
        namespace['state'] = self.state_form(context)
        namespace['view'] = self.view(context)

        template_path = 'ui/abakuc/product/itinerary/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    #######################################################################
    # View news details
    ###
	
    view__access__ = True
    view__label__ = u'View itinerary'
    def view(self, context):
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        username = self.get_property('owner')
        users = self.get_handler('/users')
        user_exist = users.has_handler(username)
        usertitle = (user_exist and
                     users.get_handler(username).get_title() or username)
        user = (user_exist and
                     users.get_handler(username).name)
        userurl = '/users/%s/;view' % user
        product = self.parent
        address = product.parent
        company = address.parent
        # date the item was posted
        date = self.get_property('dc:date')
        # namespace
        namespace = {}
        namespace['company'] = company.get_property('dc:title')
        namespace['unique_id'] = self.get_property('abakuc:unique_id')
        for key in ['dc:title' , 'dc:description', 'abakuc:closing_date']:
            namespace[key] = self.get_property(key)

        news_text = rest.to_html_events(self.get_property('abakuc:text'))
        namespace['abakuc:news_text'] = news_text
        # Image
        namespace['image1'] = image1 = self.get_property('abakuc:image1')
        namespace['image1_url'] = '%s/;icon220' % image1
        namespace['image1_title'] = ''
        namespace['image1_credit'] = ''
        namespace['image1_keywords'] = ''
        if image1:
            try:
                image1 = self.get_handler(image1)
            except:
                pass
            else:
                namespace['image1_title'] = image1.get_property('dc:title')
                namespace['image1_credit'] = image1.get_property('dc:description')
                namespace['image1_keywords'] = image1.get_property('dc:subject')

        from datetime import datetime
        now = datetime.now()
        posted = date
        difference = now - posted
        weeks, days = divmod(difference.days, 7)
        minutes, seconds = divmod(difference.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if weeks != 0:
            time_posted = {'weeks': weeks,
                                'days': days,
                                'hours': None,
                                'minutes': None }
        elif days <=7:
            time_posted = {'weeks': None,
                                'days': days,
                                'hours': hours,
                                'minutes': minutes }

        elif days ==0:
            time_posted = {'weeks': None,
                                'days': None,
                                'hours': hours,
                                'minutes': minutes }
        else:
            time_posted = {'weeks': None,
                                'days': days,
                                'hours': hours,
                                'minutes': minutes }
        namespace['date'] = date
        namespace['posted'] = time_posted

        # Person who added the itinerary 
        namespace['user'] = usertitle
        namespace['user_uri'] = userurl
        # if reviewer or members , show users who apply
        is_branch_manager_or_member = False
        user = context.user
        if user :
            reviewer = address.has_user_role(user.name,'abakuc:branch_manager')
            member = address.has_user_role(user.name,'abakuc:branch_member')
            is_branch_manager_or_member = reviewer or member
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        unique_id = self.get_property('abakuc:unique_id')
        namespace['unique_id'] = unique_id
        messages = []
        namespace['messages'] = messages
        namespace['thread'] = messages
        site_root = self.get_site_root()
        url = '/forum'
        if unique_id is not None:
            # link back to news item
            root = context.root
            results = root.search(format='ForumThread', unique_id=unique_id)
            for item in results.get_documents():
                thread = self.get_handler(item.abspath)
                thread_root = thread.get_site_root()
                forum = thread.parent
                forum_root = forum.parent
                from training import Training
                if isinstance(forum_root, Training):
                    url = 'http://%s/%s' % ((str(thread_root.get_vhosts()[0])), \
                                                forum.name)
                else:
                    url = 'http://uk.expert_travel/%s' % (forum.name)
                namespace['forum'] = forum.title
                namespace['thread'] = item.name
                messages = thread.get_message_namespace(context)
                namespace['messages'] = messages
        namespace['url'] = url
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
                              batch_total, msgs=(u"There is 1 discussion.",
                                    u"There are ${n} discussions."))
            msg = None
        else:
            messages_batch = None
            msg = u"Currently we don't have any discussions for this itinerary item."
        namespace['batch'] = messages_batch
        namespace['msg'] = msg

        # List all itinerary day used in the tabs.
        here = context.handler
        handlers = self.get_itinerary_days()
        items = []
        for i, itinerary_day in enumerate(handlers):
            # reduce the title so it fits the verticle tabs width max 15 charecters
            title = reduce_string(itinerary_day.get_title(),
                                        word_treshold=9,
                                        phrase_treshold=240)
            day = {
                'tab_id': i,
                'name': itinerary_day.name,
                'title': title,
                'description': itinerary_day.get_property('dc:description'),
                'body': itinerary_day.get_property('abakuc:news_text')
            }
            handlers = itinerary_day.search_handlers(handler_class=File)
            images = []
            for item in handlers:
                path = Path(item.abspath)
                url = abspath_to_relpath(path)
                url_220 = '%s/;icon220' % (url)
                images.append({
                    'image_name': item.name,
                    'image_title': item.get_title(),
                    'url': url_220,
                    'credit': item.get_property('abakuc:credits'),
                    'subject': item.get_property('dc:subject')
                })
            day['images'] = images
            items.append(day)
        items.sort(key=lambda x: x['name'])
        namespace['itinerary_days'] = items
        # Get all images and randomly display.
        itinerary_images = self.get_itinerary_images(context)
        if itinerary_images == []:
          itinerary_image = None
        else:  
          itinerary_image = random.choice(itinerary_images)
        namespace['itinerary_image'] = itinerary_image

        handler = self.get_handler('/ui/abakuc/product/itinerary/view.xml')
        return stl(handler, namespace)

    ###########################################################
    # Edit details
    ###########################################################

    edit_news_fields = ['dc:title' , 'dc:description',
                        'abakuc:closing_date']


    edit_metadata_form__access__ = 'is_branch_manager_or_member'
    edit_metadata_form__label__ = 'Edit itinerary'
    def edit_metadata_form(self, context):
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        namespace = {}
        for key in self.edit_news_fields:
            namespace[key] = self.get_property(key)
        # Build namespace
        namespace['name'] = self.name
        news_text = self.get_property('abakuc:news_text')
        namespace['abakuc:news_text'] = news_text

        # Image
        get_property = self.get_metadata().get_property
        namespace['image1'] = image1 = get_property('abakuc:image1')
        #namespace['image1_url'] = '%s/;icon220' % image1
        namespace['image1_title'] = ''
        namespace['image1_credit'] = ''
        namespace['image1_keywords'] = ''
        if image1:
            try:
                image1 = self.get_handler(image1)
            except:
                pass
            else:
                image_path = str(abspath_to_relpath(image1.abspath))
                namespace['image1_url'] = '%s/;icon220' % image_path
                namespace['image1_title'] = image1.get_property('dc:title')
                namespace['image1_credit'] = image1.get_property('dc:description')
                namespace['image1_keywords'] = image1.get_property('dc:subject')


        namespace['url'] = str(abspath_to_relpath(self.abspath))
        # Return stl
        handler = self.get_handler('/ui/abakuc/product/itinerary/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager_or_member'
    def edit_metadata(self, context):
        for key in self.edit_news_fields:
            self.set_property(key, context.get_form_value(key))
        news_text = context.get_form_value('abakuc:news_text')
        #Image 1
        image1_title = context.get_form_value('image1_title')
        image1_credit = context.get_form_value('image1_credit')
        image1_keywords = context.get_form_value('image1_keywords')
        image1 = context.get_form_value('abakuc:image1')
        self.set_property('abakuc:image1', image1)
        if image1:
            image1 = self.get_handler(image1)
            image1_title = unicode(image1_title, 'utf8')
            image1.set_property('dc:title', image1_title, language='en')
            image1_keywords = unicode(image1_keywords, 'utf8')
            image1.set_property('dc:subject', image1_keywords)
            image1_credit = unicode(image1_credit, 'utf8')
            image1.set_property('dc:description', image1_credit,
                                language='en')

        self.set_property('abakuc:news_text', news_text)
        # News keywords
        description = context.get_form_value('dc:description')
        items = set(description.split())
        keywords = []
        for item in items:
            if len(item) >= 5:
                keywords.append(item)
        subject = str(keywords[:20]).replace('[', '').replace(']', '').replace('u\'', '').replace('\'', '')
        self.set_property('dc:subject', subject)
        message = u'Changes saved.'
        return context.come_back(message)

    # Edit / Inline / toolbox: add images
    document_image_form__access__ = 'is_allowed_to_edit'
    def document_image_form(self, context):
        from itools.cms.file import File
        from itools.cms.binary import Image
        from itools.cms.widgets import Breadcrumb
        # Build the bc
        if isinstance(self, File):
            start = self.parent
        else:
            start = self
        # Construct namespace
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=Image, start=start)
        namespace['message'] = context.get_form_value('message')

        prefix = Path(self.abspath).get_pathto('/ui/abakuc/training/document/epozimage.xml')
        handler = self.get_handler('/ui/abakuc/training/document/epozimage.xml')
        return stl(handler, namespace, prefix=prefix)


    document_image__access__ = 'is_allowed_to_edit'
    def document_image(self, context):
        """
        Allow to upload and add an image to epoz
        """
        from itools.cms.binary import Image
        root = context.root
        # Get the container
        container = root.get_handler(context.get_form_value('target_path'))
        # Add the image to the handler
        uri = Image.new_instance(container, context)
        if ';document_image_form' not in uri.path:
            handler = container.get_handler(uri.path[0])
            return """
            <script type="text/javascript">
                window.opener.CreateImage('%s');
                window.close();
            </script>
                    """ % handler.abspath

        return context.come_back(message=uri.query['message'])

    #######################################################################
    ## Itinerary days
    #######################################################################
    edit_itinerary_days_form__access__ = 'is_branch_manager_or_member'
    edit_itinerary_days_form__label__ = 'Edit itinerary'
    def edit_itinerary_days_form(self, context):
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        namespace = {}
        # Itiniraries
        handlers = self.get_itinerary_days()
        items = []
        for i, itinerary_day in enumerate(handlers):
            index = context.get_form_value('day', type=Integer)
            if i == index:
                selected = True
                template = ItineraryDay.edit_metadata_form(itinerary_day, context)
            else:
                selected = False
                template = None
            day = {
                'tab_id': i,
                'name': itinerary_day.name,
                'title': itinerary_day.get_title(),
                'description': itinerary_day.get_property('dc:description'),
                'selected': selected,
                'template': template,
                'body': itinerary_day.get_property('abakuc:news_text')
            }
            items.append(day)
        items.sort(key=lambda x: x['name'])
        namespace['days'] = items
        namespace['url'] = str(abspath_to_relpath(self.abspath))
        # Add new itinerary form - pull this from new_resource
        namespace['class_id'] = ItineraryDay.class_id
        # Return stl
        handler = self.get_handler('/ui/abakuc/product/itinerary/edit_itinerary_days.xml')
        return stl(handler, namespace)

    #######################################################################
    ## Indexes
    #######################################################################

    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        indexes['closing_date'] = self.get_property('abakuc:closing_date')
        indexes['unique_id'] = self.get_property('abakuc:unique_id')
        product = self.parent
        address = product.parent
        company = address.parent
        indexes['company'] = company.name
        indexes['address'] = address.name
        return indexes


    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager_or_member(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_remove(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_edit(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_view(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

class ItineraryDay(Folder):

    class_id = 'itinerary_day'
    class_aliases = []
    class_title = u'Itinerary Day'
    class_views = [['view'],
                   ['browse_content?mode=list'],
                   ['edit_metadata_form'],
                   ['state_form']]

    def get_document_types(self):
        return [ File]
    #@classmethod
    #def new_instance_form(cls, context, name=''):
    #    root = context.root
    #    here = context.handler
    #    site_root = here.get_site_root()
    #    namespace = {}
    #    # The class id
    #    namespace['class_id'] = cls.class_id
    #    website_languages = site_root.get_property('ikaaro:website_languages')
    #    default_language = website_languages[0]
    #    languages = []
    #    for code in website_languages:
    #        language_name = get_language_name(code)
    #        languages.append({'code': code,
    #                          'name': cls.gettext(language_name),
    #                          'isdefault': code == default_language})
    #    namespace['languages'] = languages

    #    handler = root.get_handler('/ui/abakuc/training/document/new_instance.xml')
    #    return stl(handler, namespace)


    #@classmethod
    #def new_instance(cls, container, context):
    #    title = context.get_form_value('dc:title')
    #    language = context.get_form_value('dc:language')

    #    # Generate the new_instance name
    #    # based on the class_id
    #    document_names = [ x for x in container.get_handler_names()
    #                       if x.startswith(cls.class_id) ]
    #    if document_names:
    #        i = get_sort_name(max(document_names))[1]+ 1
    #        name = '%s%d.%s' % (cls.class_id, i, cls.class_extension)
    #    else:
    #        name = '%s1.%s' % (cls.class_id, cls.class_extension)

    #    # Check the name
    #    name = name.strip()
    #    if not name:
    #        return context.come_back(MSG_NAME_MISSING)

    #    name = checkid(name)
    #    if name is None:
    #        return context.come_back(MSG_BAD_NAME)

    #    # Add the language extension to the name
    #    #name = FileName.encode((name, cls.class_extension, language))

    #    # Check the name is free
    #    if container.has_handler(name):
    #        return context.come_back(MSG_NAME_CLASH)

    #    # Build the object
    #    handler = cls()
    #    metadata = handler.build_metadata()
    #    metadata.set_property('dc:title', title, language=language)
    #    metadata.set_property('dc:language', language)
    #    # Add the object
    #    handler, metadata = container.set_object(name, handler, metadata)

    #    goto = './%s/;edit_form' % name
    #    return context.come_back(MSG_NEW_RESOURCE, goto=goto)


    def get_files(self):
        """
          Return a list with all the itinerary day's files
          that have been published.
        """
        items = self.search_handlers(handler_class=File)
        return items 


    def get_itinerary_day_files(self, context):
        """
          Reterns a namespace (dictionary) of the files, used in the
          itinerary day ;view template.
        """
        here = context.handler
        handlers = self.get_files()
        items = []
        for i, item in enumerate(handlers):
            path = Path(item.abspath)
            handler = self.get_handler(path)
            if isinstance(here, ItineraryDay):
                url_220 = '%s/;icon220' % item.name
            else:
                if isinstance(here, Itinerary):
                    url_220 = '%s/%s/;icon220' % (self.name, item.name)
                else:
                    url_220 = '%s/%s/%s/;icon220' % (here.name, self.name, item.name)
            items.append({
                'tab_id': i,
                'id': item.name,
                'title': item.get_title(),
                'url': url_220,
                #'credit': handler.get_property('abakuc:credit'),
                'description': handler.get_property('dc:description'),
                'body': handler.get_property('abakuc:news_text')
            })
            # Collect all images for itinerary
        items.sort(key=lambda x: x['id'])
        return items


    ###################################################################
    # Create a new news item
    ###################################################################

    news_fields = [
        ('dc:title', True),
        ('dc:description', False),
        ('abakuc:news_text', False)]

    @classmethod
    def new_instance_form(cls, context):
        namespace = context.build_form_namespace(cls.news_fields)
        namespace['class_id'] = ItineraryDay.class_id
        path = '/ui/abakuc/product/itinerary/days/new_instance_form.xml'
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
        name = 'itinerary_day%s' % y
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
        for key in ['dc:title' ,]:
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
        message = u'Itinerary item has been added.'
        return context.come_back(message, goto=goto)

    #######################################################################
    # View
    #######################################################################
    view__access__ = True
    view__label__ = u'View itinerary day'
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
        # date the item was posted
        date = self.get_property('dc:date')
        # namespace
        namespace = {}
        namespace['company'] = company.get_property('dc:title')
        namespace['unique_id'] = self.get_property('abakuc:unique_id')
        for key in ['dc:title' , 'dc:description']:
            namespace[key] = self.get_property(key)

        news_text = rest.to_html_events(self.get_property('abakuc:news_text'))
        namespace['abakuc:news_text'] = news_text
        # Get one random image 
        images = self.get_itinerary_day_files(context)
        if images == []:
          image = None
        else:  
          image = random.choice(images)
        namespace['image'] = image
        #namespace['image1_url'] = '%s/;icon220' % image1
        #namespace['image1_title'] = ''
        #namespace['image1_credit'] = ''
        #namespace['image1_keywords'] = ''
        #if image1:
        #    try:
        #        image1 = self.get_handler(image1)
        #    except:
        #        pass
        #    else:
        #        namespace['image1_title'] = image1.get_property('dc:title')
        #        namespace['image1_credit'] = image1.get_property('dc:description')
        #        namespace['image1_keywords'] = image1.get_property('dc:subject')

        from datetime import datetime
        now = datetime.now()
        posted = date
        difference = now - posted
        weeks, days = divmod(difference.days, 7)
        minutes, seconds = divmod(difference.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if weeks != 0:
            time_posted = {'weeks': weeks,
                                'days': days,
                                'hours': None,
                                'minutes': None }
        elif days <=7:
            time_posted = {'weeks': None,
                                'days': days,
                                'hours': hours,
                                'minutes': minutes }

        elif days ==0:
            time_posted = {'weeks': None,
                                'days': None,
                                'hours': hours,
                                'minutes': minutes }
        else:
            time_posted = {'weeks': None,
                                'days': days,
                                'hours': hours,
                                'minutes': minutes }
        namespace['date'] = date
        namespace['posted'] = time_posted

        # Person who added the job
        namespace['user'] = usertitle
        namespace['user_uri'] = userurl
        # if reviewer or members , show users who apply
        is_branch_manager_or_member = False
        #user = context.user
        #address = self.parent.parent.parent
        #if user :
        #    reviewer = address.has_user_role(user.name,'abakuc:branch_manager')
        #    member = address.has_user_role(user.name,'abakuc:branch_member')
        #    is_branch_manager_or_member = reviewer or member
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        handler = self.get_handler('/ui/abakuc/product/itinerary/days/view.xml')
        return stl(handler, namespace)

    ###########################################################
    # Edit details
    ###########################################################

    edit_news_fields = ['dc:title' , 'dc:description',
                        'abakuc:closing_date']


    edit_metadata_form__access__ = 'is_branch_manager_or_member'
    edit_metadata_form__label__ = 'Edit news'
    def edit_metadata_form(self, context):
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        namespace = {}
        namespace['url'] = str(abspath_to_relpath(self.abspath))
        for key in self.edit_news_fields:
            namespace[key] = self.get_property(key)
        # Build namespace
        news_text = self.get_property('abakuc:news_text')
        namespace['abakuc:news_text'] = news_text

        # Image
        get_property = self.get_metadata().get_property
        namespace['image1'] = image1 = get_property('abakuc:image1')
        print namespace['image1']
        namespace['image1_title'] = ''
        namespace['image1_credit'] = ''
        namespace['image1_keywords'] = ''
        if image1:
            try:
                image1 = self.get_handler(image1)
            except:
                pass
            else:
                image_path = str(abspath_to_relpath(image1.abspath))
                namespace['image1_url'] = '%s/;icon220' % image_path
                namespace['image1_title'] = image1.get_property('dc:title')
                namespace['image1_credit'] = image1.get_property('dc:description')
                namespace['image1_keywords'] = image1.get_property('dc:subject')


        # Return stl
        handler = self.get_handler('/ui/abakuc/product/itinerary/days/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager_or_member'
    def edit_metadata(self, context):
        for key in self.edit_news_fields:
            self.set_property(key, context.get_form_value(key))
        news_text = context.get_form_value('abakuc:news_text')
        #Image 1
        image1_title = context.get_form_value('image1_title')
        image1_credit = context.get_form_value('image1_credit')
        image1_keywords = context.get_form_value('image1_keywords')
        image1 = context.get_form_value('abakuc:image1')
        self.set_property('abakuc:image1', image1)
        if image1:
            image1 = self.get_handler(image1)
            image1_title = unicode(image1_title, 'utf8')
            image1.set_property('dc:title', image1_title, language='en')
            image1_keywords = unicode(image1_keywords, 'utf8')
            image1.set_property('dc:subject', image1_keywords)
            image1_credit = unicode(image1_credit, 'utf8')
            image1.set_property('dc:description', image1_credit,
                                language='en')

        self.set_property('abakuc:news_text', news_text)
        # News keywords
        description = context.get_form_value('dc:description')
        items = set(description.split())
        keywords = []
        for item in items:
            if len(item) >= 5:
                keywords.append(item)
        subject = str(keywords[:20]).replace('[', '').replace(']', '').replace('u\'', '').replace('\'', '')
        self.set_property('dc:subject', subject)
        message = u'Changes Saved.'
        return context.come_back(message, goto=';view')

    # Edit / Inline / toolbox: add images
    document_image_form__access__ = 'is_allowed_to_edit'
    def document_image_form(self, context):
        from itools.cms.file import File
        from itools.cms.binary import Image
        from itools.cms.widgets import Breadcrumb
        # Build the bc
        if isinstance(self, File):
            start = self.parent
        else:
            start = self
        # Construct namespace
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=Image, start=start)
        namespace['message'] = context.get_form_value('message')

        prefix = Path(self.abspath).get_pathto('/ui/abakuc/training/document/epozimage.xml')
        handler = self.get_handler('/ui/abakuc/training/document/epozimage.xml')
        return stl(handler, namespace, prefix=prefix)


    document_image__access__ = 'is_allowed_to_edit'
    def document_image(self, context):
        """
        Allow to upload and add an image to epoz
        """
        from itools.cms.binary import Image
        root = context.root
        # Get the container
        container = root.get_handler(context.get_form_value('target_path'))
        # Add the image to the handler
        uri = Image.new_instance(container, context)
        if ';document_image_form' not in uri.path:
            handler = container.get_handler(uri.path[0])
            return """
            <script type="text/javascript">
                window.opener.CreateImage('%s');
                window.close();
            </script>
                    """ % handler.abspath

        return context.come_back(message=uri.query['message'])

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager_or_member(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_remove(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_edit(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_view(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

register_object_class(Itinerary)
register_object_class(ItineraryDay)
