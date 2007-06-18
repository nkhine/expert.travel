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


    ###################################################################
    ## Create a new Job
    
   
    @classmethod
    def new_instance_form(cls, context):
        namespace = {}
        namespace['salary'] = SalaryRange.get_namespace(None) 
        namespace['functions'] =  JobTitle.get_namespace(None)
        namespace['class_id'] = Job.class_id
        path = '/ui/abakuc/job_new_resource_form.xml'
        handler = context.root.get_handler(path)
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
        
        # if reviewer , show users who apply
        reviewers = False
        user = context.user
        if user :
            reviewers = self.parent.has_user_role(user.name,'ikaaro:reviewers')
        namespace['reviewers'] = reviewers
        namespace['table'] = None
        if reviewers:
            namespace['applicants'] = {}
            for applicant in ['1', '2', '3']:
                namespace['applicants'] = {'name': applicant}
            namespace['table'] = ''
        return stl(handler, namespace)


    job_fields = ['dc:title' , 'dc:description', 'abakuc:job_text',         
                  'abakuc:closing_date', 'abakuc:salary', 'abakuc:function']


    def edit_metadata_form(self, context):
        namespace = {}
        for key in self.job_fields:
            namespace[key] = self.get_property(key)
        # Build namespace
        salary = self.get_property('abakuc:salary')
        namespace['salary'] = SalaryRange.get_namespace(salary)
        function = self.get_property('abakuc:function')
        namespace['functions'] =  JobTitle.get_namespace(function)
        # Return stl
        handler = self.get_handler('/ui/abakuc/job_edit_metadata.xml')
        return stl(handler, namespace)

    
    def edit_metadata(self, context):
        for key in self.job_fields:
            self.set_property(key, context.get_form_value(key))
        message = u'Changes Saved.'
        return context.come_back(message)

    ############################################################
    # Apply for a job
    ############################################################
    apply_fields = [
       # ('abakuc:enquiry_subject', True),
       # ('abakuc:enquiry', True),
       # ('abakuc:enquiry_type', True),
        ('ikaaro:firstname', True),
        ('ikaaro:lastname', True),
        ('ikaaro:email', True),
        ('abakuc:phone', False)]

    apply_fields_auth = []

    apply_form__access__ = True
    apply_form__label__ = u'Apply to the Job'
    def apply_form(self, context):
        if context.user is None:
            namespace = context.build_form_namespace(self.apply_fields)
            namespace['is_authenticated'] = False
        else:
            namespace = context.build_form_namespace(self.apply_fields_auth)
            namespace['is_authenticated'] = True

        # Return stl
        handler = self.get_handler('/ui/abakuc/Job_apply_form.xml.en')
        return stl(handler, namespace)


    apply__access__ = True
    apply__label__ = u'Apply to the Job'
    def apply(self, context):
        root = context.root
        user = context.user

        # Check input data
        if user is None:
            apply_fields = self.apply_fields
        else:
            apply_fields = self.apply_fields_auth
        keep = [ x for x, y in apply_fields ]
        error = context.check_form_input(apply_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        message = u'ok'
        return message.encode('utf-8') 

register_object_class(Job)
