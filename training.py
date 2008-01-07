# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library

# Import from itools
from itools.stl import stl
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.registry import register_object_class
from itools.cms.widgets import batch
from itools.cms.skins import Skin 
from itools.cms.file import File
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware
from itools.datatypes import FileName
from itools.web import get_context
# Import from abakuc
from base import Handler, Folder
from website import WebSite
from document import Document
from utils import get_sort_name
from exam import Exam

class Trainings(Folder):

    class_id = 'trainings'
    class_title = u'Training programmes'
    class_icon16 = 'abakuc/images/Trainings16.png'
    class_icon48 = 'abakuc/images/Trainings48.png'
    class_views = [
                #['view'],
                ['browse_content?mode=list'],
                ['new_resource_form'],
                ['edit_metadata_form']]

    
    def get_document_types(self):
        return [Training]

    #######################################################################
    # User Interface
    #######################################################################
    #view__access__ = 'is_allowed_to_view'
    #view__label__ = u'View'
    #def view(self, context):
    #    here = context.handler
    #    namespace = {}
    #    title = here.get_title()
    #    items = self.search_handlers(handler_class=Training)
    #    namespace['items'] = []
    #    for item in items:
    #        state = item.get_property('state')
    #        if state == 'public':
    #            get = item.get_property
    #            url = '%s/;view' %  item.name
    #            description = reduce_string(get('dc:description'),
    #                                        word_treshold=90,
    #                                        phrase_treshold=240)
    #            namespace['items'].append({'url': url,
    #                      'description': description,
    #                      'title': item.title_or_name})

    #        namespace['title'] = title 
    #        handler = self.get_handler('/ui/abakuc/training/list.xml')
    #        return stl(handler, namespace)

        # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(trainings)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #trainings = trainings[batch_start:batch_fin]
        ## Namespace 
        #if trainings:
        #    msgs = (u'There is one training programme.',
        #            u'There are ${n} training programmes.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'Currently there no published training programmes.'
        #
        #namespace['batch'] = batch
        #namespace['msg'] = msg 

class Training(WebSite):

    class_id = 'training'
    class_title = u'Training programme'
    class_icon16 = 'abakuc/images/Training16.png'
    class_icon48 = 'abakuc/images/Training48.png'
    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form']]

  
    new_resource_form__access__ = 'is_reviewer' 
    new_resource__access__ = 'is_reviewer'

    def get_document_types(self):
        return [Module]

    def get_level1_title(self, level1):
        return None 

    #######################################################################
    # API 
    #######################################################################
    def get_modules(self):
        modules = list(self.search_handlers(format=Module.class_id))
        modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return modules
    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_training_form(name=None, description=None, topics=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['description'] = description 
        namespace['topics'] = root.get_topics_namespace(topics)

        handler = root.get_handler('ui/abakuc/training/training_form.xml')
        return stl(handler, namespace)
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_reviewer_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'ikaaro:reviewers') or
                self.has_user_role(user.name, 'ikaaro:members'))
    

    def is_admin(self, user, object):
        return self.is_reviewer(user, object)


    def is_reviewer(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'ikaaro:reviewers') 

    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_edit'
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Module)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['title'] = title 
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)
        # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(modules)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #modules = modules[batch_start:batch_fin]
        ## Namespace 
        #if modules:
        #    msgs = (u'There is one module.',
        #            u'There are ${n} modules.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'Currently there no published training modules.'
        #
        #namespace['batch'] = batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        root = get_context().root
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description
        topics = self.get_property('abakuc:topic')
        namespace['topics'] = root.get_topics_namespace(topics)
        handler = self.get_handler('/ui/abakuc/training/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')
        topics = context.get_form_values('topic')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')
        self.set_property('abakuc:topic', tuple(topics))
        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


#######################################################################
# Training module 
#######################################################################
class Module(Folder, WorkflowAware, Handler):

    class_id = 'module'
    class_title = u'Trainig module'
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'

    def get_document_types(self):
        return [Topic, Exam]

    new_resource_form__access__ = 'is_admin'

    #######################################################################
    # API 
    #######################################################################
    def get_topics(self):
        topics = list(self.search_handlers(format=Topic.class_id))
        topics.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return topics
    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = True 
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Topic)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['title'] = title 
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)
        # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(items)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #items = items[batch_start:batch_fin]
        ## Namespace 
        #if items:
        #    msgs = (u'There is one topic.',
        #            u'This module has ${n} topics.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'This module has no published topics.'
        #
        #namespace['batch'] = news_batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Generate the module name
        module_names = [ x for x in here.get_handler_names()
                           if x.startswith('module') ]
        if module_names:
            i = get_sort_name(module_names[-1])[1] + 1
            name = 'module%d' % i
        else:
            name = 'module1'
        namespace['name'] = name 
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description

        handler = self.get_handler('/ui/abakuc/training/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        name = context.get_form_value('name')
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


#######################################################################
# Training topic 
#######################################################################
class Topic(Folder):

    class_id = 'topic'
    class_title = u'Module topic'
    class_icon16 = 'abakuc/images/Topic16.png'
    class_icon48 = 'abakuc/images/Topic48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form', 'new_user_form']]

    def get_document_types(self):
        return [Document]

    #######################################################################
    # API 
    #######################################################################
    def get_document_names(self):
        ac = self.get_access_control()
        user = get_context().user

        documents = []
        for handler in self.get_handlers():
            if not isinstance(handler, Document):
                continue
            if handler.real_handler is not None:
                continue
            if ac.is_allowed_to_view(user, handler):
                name = handler.name
                sort_name = get_sort_name(FileName.decode(name)[0])
                documents.append((sort_name, handler.name))
        documents.sort()
        return [ x[1] for x in documents ]
    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Document)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            # XXX Had to hard link the .en in the uri
            # item name seems to strip the language
            language = item.get_property('dc:language')
            url = '%s.%s/;view' %  (item.name, language)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['title'] = title 
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)
      # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(items)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #items = items[batch_start:batch_fin]
        ## Namespace 
        #if items:
        #    msgs = (u'There is one topic.',
        #            u'This module has ${n} topics.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'This module has no published topics.'
        #
        #namespace['batch'] = news_batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description

        handler = self.get_handler('/ui/abakuc/training/topic_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_reviewer_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'ikaaro:reviewers') or
                self.has_user_role(user.name, 'ikaaro:members'))
    

    def is_admin(self, user, object):
        return self.is_reviewer(user, object)


    def is_reviewer(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'ikaaro:reviewers') 


register_object_class(Trainings)
register_object_class(Training)
register_object_class(Module)
register_object_class(Topic)
