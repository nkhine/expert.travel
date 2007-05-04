# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class
from itools.stl import stl

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog

class Jobs(Folder):
 
    class_id = 'jobs'
    class_title = u'UK Travel Jobs'
    class_icon16 = 'abakuc/images/Automator16.png'
    class_icon48 = 'abakuc/images/Automator48.png'

    def get_document_types(self):
        return [Job]


    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job Board'
    def view(self, context):
        namespace = {}

        handler = self.get_handler('/ui/abakuc/jobs_view.xml')
        return stl(handler, namespace)
class Job(RoleAware, Folder):

    class_id = 'job'
    class_title = u'Job'
    class_description = u'Add new job board entry'
    class_icon16 = 'abakuc/images/Advert16.png'
    class_icon48 = 'abakuc/images/Advert48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]


    __fixed_handlers__ = ['log_applications.csv']


    def new(self, **kw):
        Folder.new(self, **kw)
        handler = ApplicationsLog()
        cache = self.cache
        cache['log_applications.csv'] = handler
        cache['log_applications.csv.metadata'] = self.build_metadata(handler)


    def get_document_types(self):
        return []


    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job'
    def view(self, context):
        return 'Job Entry'

register_object_class(Jobs)
register_object_class(Job)
