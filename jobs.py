# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class
from itools.stl import stl
from itools.web import get_context
from itools.rest import checkid

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog
from metadata import JobTitle, SalaryRange


class Job(Folder): #RoleAware, Folder):

    class_id = 'Job'
    class_title = u'Job'
    class_description = u'Add new job board entry'
    class_icon16 = 'abakuc/images/JobBoard16.png'
    class_icon48 = 'abakuc/images/JobBoard48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]


    __fixed_handlers__ = ['log_applications.csv']


    #def new(self, **kw):
    #    Folder.new(self, **kw)
    #    cache = self.cache
        #cache['log_applications.csv'] = handler
        #cache['log_applications.csv.metadata'] = handler.build_metadata(handler)


    #def get_document_types(self):
    #    return []

    ###################################################################
    ## Create a new Job
    
   
    @classmethod
    def new_instance_form(cls, context):
        namespace = {}
        namespace['salary'] = SalaryRange.get_namespace(None) 
        namespace['functions'] =  JobTitle.get_namespace(None)
        namespace['class_id'] = Job.class_id
        handler = context.root.get_handler('/ui/abakuc/job_new_resource_form.xml')
        return stl(handler, namespace)

    @classmethod 
    def new_instance(cls, container, context):
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
        if container.has_handler(name):
            message = u'There is already another object with this name.'
            return context.come_back(message)
        
        # Set properties
        handler = cls()
        metadata = handler.build_metadata()
        for key in ['dc:title' , 'dc:description', 'abakuc:job_text',
                    'abakuc:closing_date', 'abakuc:salary', 'abakuc:function']:
            metadata.set_property(key, context.get_form_value(key))
        
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)
        
        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'New resource added.'
        return context.come_back(message, goto=goto) 
    
    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job'
    def view(self, context):
        root = context.root
        #namespace
        namespace = {}
        salary = self.get_property('abakuc:salary')
        namespace['abakuc:salary'] = SalaryRange.get_value(salary)
        function = self.get_property('abakuc:function')
        namespace['abakuc:function'] =  JobTitle.get_value(function)
        for key in ['dc:title' , 'dc:description', 'abakuc:job_text',
                    'abakuc:closing_date']:
            namespace[key] = self.get_property(key)
        handler = self.get_handler('/ui/abakuc/job_view.xml')
        return stl(handler, namespace)


   # def edit_metadata_form(self, context):
   #     namespace = {}
   #     namespace['referrer'] = None
   #     if context.get_form_value('referrer'):
   #         namespace['referrer'] = str(context.request.referrer)
   #     # Form
   #     namespace = {}
   #     namespace['title'] = self.title_or_name
   #     namespace['description'] = self.get_property('dc:description')
   #     address_county = self.get_property('abakuc:county')
   #     namespace['form'] = self.get_form(address_county)

   #     handler = self.get_handler('/ui/abakuc/job_edit_metadata.xml')
   #     return stl(handler, namespace)

   # 
   # def edit_metadata(self, context):
   #     title = context.get_form_value('dc:title')
   #     description = context.get_form_value('dc:description')
   #     county = context.get_form_value('abakuc:county')
   #     self.set_property('dc:title', title)
   #     self.set_property('dc:description', description)
   #     self.set_property('abakuc:county', county)


   #     message = u'Changes Saved.'
   #     return context.come_back(message)

register_object_class(Job)
