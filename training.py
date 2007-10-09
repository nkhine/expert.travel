# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library

# Import from itools
from itools.stl import stl
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.widgets import batch
from itools.cms.file import File
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware
from itools.xhtml import Document

# Import from abakuc
from base import Handler, Folder
from website import WebSite

class Trainings(Folder):

    class_id = 'trainings'
    class_title = u'Training programmes'
    class_icon16 = 'abakuc/images/Trainings16.png'
    class_icon48 = 'abakuc/images/Trainings48.png'

    
    def get_document_types(self):
        return [Training]

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return 'bobo'


class Training(WebSite):

    class_id = 'training'
    class_title = u'Training programme'
    class_icon16 = 'abakuc/images/Training16.png'
    class_icon48 = 'abakuc/images/Training48.png'

    site_format = 'module'

    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form']]
    
    new_resource_form__access__ = 'is_allowed_to_edit'
    new_resource__access__ = 'is_allowed_to_edit'

    def get_document_types(self):
        return [Module, Folder]

    def get_level1_title(self, level1):
        return None

    #######################################################################
    # ACL
    #######################################################################

    #######################################################################
    # Security / Access Control
    #######################################################################
    #def is_allowed_to_edit(self, user, object):
    #    for address in self.search_handlers(handler_class=Address):
    #        if address.is_allowed_to_edit(user, address):
    #            return True
    #    return False

    def is_reviewer(self, user, object):
        for module in self.search_handlers(handler_class=Module):
            if module.is_reviewer(user, module):
                return True
        return False
    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return 'bobo'
    #def view(self, context):
    #    namespace = {}
    #    namespace['title'] = self.get_property('dc:title')
    #    namespace['description'] = self.get_property('dc:description')
    #    namespace['modules'] = self.view_modules(context)

    #    handler = self.get_handler('/ui/abakuc/training_view.xml')
    #    return stl(handler, namespace)


    ####################################################################
    # View training modules 
    view_modules__label__ = u'Training modules'
    view_modules__access__ = True
    def view_modules(self, context):
        namespace = {}
        modules = self.search_handlers(handler_class=Module)
        namespace['modules'] = []
        for module in modules:
            get = module.get_property
            url = '%s/;view' %  module.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['modules'].append({'url': url,
                      'description': description,
                      'title': module.title_or_name})

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
        namespace['modules'] = modules

        handler = self.get_handler('/ui/abakuc/modules_view.xml')
        return stl(handler, namespace)

    #######################################################################
    # User Interface / Edit
    #######################################################################
    #edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        # Description
        description = self.get_property('dc:description')

        handler = self.get_handler('/ui/abakuc/training_edit_metadata.xml')
        return stl(handler, namespace)


    #edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


#######################################################################
# Training module 
#######################################################################
class Module(Folder):

    class_id = 'module'
    class_title = u'Trainig module'
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'

    def get_document_types(self):
        return [Topic]

    #######################################################################
    # User Interface / View
    #######################################################################
    #view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        namespace['topics'] = self.view_topics(context)

        handler = self.get_handler('/ui/abakuc/module_view.xml')
        return stl(handler, namespace)


    ####################################################################
    # View training modules 
    view_modules__label__ = u'Training modules'
    view_modules__access__ = True
    def view_topics(self, context):
        namespace = {}
        modules = self.search_handlers(handler_class=Topic)
        namespace['topics'] = []
        for topic in topics:
            url = '%s/;view' %  topic.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['topics'].append({'url': url,
                      'description': description,
                      'title': topic.title_or_name})

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
        #            u'There are ${n} topics.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'Currently there no published topics.'
        #
        #namespace['batch'] = news_batch
        #namespace['msg'] = msg 
        namespace['topics'] = topics

        handler = self.get_handler('/ui/abakuc/topics_view.xml')
        return stl(handler, namespace)

    #######################################################################
    # User Interface / Edit
    #######################################################################
    #edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        # Description
        description = self.get_property('dc:description')

        handler = self.get_handler('/ui/abakuc/module_edit_metadata.xml')
        return stl(handler, namespace)


    #edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
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

    #def get_document_types(self):
    #    return [Document, File]

    #######################################################################
    # User Interface / View
    #######################################################################
    view__label__ = u'Topic'
    view__access__ = True
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        
        documents = []
        for document in self.parent.search_handlers(handler_class=Document):
            module = document.parent
            current_document = self.get_property('dc:title')
            url = '/training/%s/%s/;view' % (module.name, document.name)
            documents.append({
                'name': document.name,
                'is_current': document.name == current_document,
                'url': url,
                'description': document.get_property('dc:description')})
        namespace['documents'] = documents

        handler = self.get_handler('/ui/abakuc/topic_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    #edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        # Description
        description = self.get_property('dc:description')

        handler = self.get_handler('/ui/abakuc/topic_edit_metadata.xml')
        return stl(handler, namespace)


    #edit_metadata__access__ = 'is_reviewer'
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
