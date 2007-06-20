# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
from datetime import datetime
from string import Template
import mimetypes

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.file import File
from itools.stl import stl
from itools.web import get_context
from itools.rest import checkid
from itools.cms.widgets import table
from itools.cms.utils import generate_password
from itools.catalog import EqQuery, AndQuery

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog
from metadata import JobTitle, SalaryRange


class Job(RoleAware, Folder):

    class_id = 'Job'
    class_title = u'Job'
    class_description = u'Add new job board entry'
    class_icon16 = 'abakuc/images/JobBoard16.png'
    class_icon48 = 'abakuc/images/JobBoard48.png'
    class_views = [
        ['view'],
        ['view_candidatures'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]

    
    def get_document_types(self):
        return [Candidature, File]


    new_resource_form__access__ = True
    new_resource__access__ = True


    ###################################################################
    ## Create a new Job

    job_fields = [
        ('dc:title', True),
        ('abakuc:function', True),
        ('abakuc:salary', True),
        ('abakuc:closing_date', True),
        ('dc:description', True),
        ('abakuc:job_text', True)]


    @classmethod
    def new_instance_form(cls, context):
        namespace = context.build_form_namespace(cls.job_fields)
        namespace['class_id'] = Job.class_id
        # Epoz
        job_text = context.get_form_value('abakuc:job_text') or ''
        rte = context.root.get_rte(context, 'abakuc:job_text', job_text)
        namespace['abakuc:job_text'] = rte  
        path = '/ui/abakuc/job_new_resource_form.xml'
        
        handler = context.root.get_handler(path)
        return stl(handler, namespace)


    @classmethod 
    def new_instance(cls, container, context):
        # Check data
        keep = [ x for x, y in cls.job_fields ]
        error = context.check_form_input(cls.job_fields)
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
        for key in ['dc:title' , 'dc:description', 'abakuc:job_text',
                    'abakuc:closing_date', 'abakuc:salary', 'abakuc:function']:
            try:
                value = context.get_form_value(key)
                if not value:
                    message = u'You have to fill all fields.'
                    return context.come_back(message)
                metadata.set_property(key, context.get_form_value(key))
            except:
                message = u'Error of DataTypes.'
                return context.come_back(message)

        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)
        
        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'New Job added.'
        return context.come_back(message, goto=goto) 
    
    #######################################################################
    # View Job details
    ###

    view__access__ = True
    view__label__ = u'Job details'
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
        
        # if reviewer or members , show users who apply
        is_reviewer_or_member = False
        user = context.user
        if user :
            reviewer = self.parent.has_user_role(user.name,'ikaaro:reviewers')
            member = self.parent.has_user_role(user.name,'ikaaro:members')
            is_reviewer_or_member = reviewer or member 
        namespace['is_reviewer_or_member'] = is_reviewer_or_member
        namespace['table'] = None
        if is_reviewer_or_member:
            users = root.get_handler('users')
            nb_candidatures = 0
            candidatures = self.search_handlers(handler_class=Candidature)
            for candidature in candidatures:
                user_id = candidature.get_property('user_id')
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm') is False:
                    nb_candidatures += 1 
            namespace['nb_candidatures'] = nb_candidatures
        handler = self.get_handler('/ui/abakuc/job_view.xml')
        return stl(handler, namespace)

    
    view_candidatures__access__ = 'is_reviewer_or_member'
    view_candidatures__label__ = u'Job Candidatures'
    def view_candidatures(self, context):
        root = context.root
        users = root.get_handler('users')
        namespace = {}
        columns = [('name', u'Id'),
                   ('mtime', u'Date')]
        rows = []
        candidatures = self.search_handlers(handler_class=Candidature)
        for c in candidatures:
            user_id = c.get_property('user_id')
            user = users.get_handler(user_id)
            if not user.has_property('ikaaro:user_must_confirm'): 
                rows.append({'id': c.name,
                             'checkbox': True,
                             'img': '/ui/images/Text16.png',
                             'name': (c.name, c.name),
                             'mtime': c.mtime})

        actions = [('select', u'Select All', 'button_select_all',
                    "return select_checkboxes('browse_list', true);"),
                   ('select', u'Select None', 'button_select_none',
                    "return select_checkboxes('browse_list', false);"),
                   ('remove', 'Supprimer', 'button_delete', None)]
        if rows: 
            namespace['table'] = table(columns, rows, [], [], actions=actions) 
            namespace['msg'] = None
        else:
            namespace['table'] = None
            namespace['msg'] = u'No candidature'
        
        handler = self.get_handler('/ui/abakuc/Job_view_candidatures.xml')
        return stl(handler, namespace)


    ###########################################################
    # Edit details
    ###########################################################
    
    edit_job_fields = ['dc:title' , 'dc:description', 'abakuc:closing_date',
                       'abakuc:salary', 'abakuc:function']
    

    edit_metadata_form__access__ = 'is_reviewer_or_member'
    def edit_metadata_form(self, context):
        namespace = {}
        for key in self.edit_job_fields:
            namespace[key] = self.get_property(key)
        # Build namespace
        salary = self.get_property('abakuc:salary')
        namespace['salary'] = SalaryRange.get_namespace(salary)
        function = self.get_property('abakuc:function')
        namespace['functions'] =  JobTitle.get_namespace(function)
        job_text = self.get_property('abakuc:job_text')
        namespace['abakuc:job_text'] = self.get_rte(context,'abakuc:job_text',
                                                 job_text)
        # Return stl
        handler = self.get_handler('/ui/abakuc/job_edit_metadata.xml')
        return stl(handler, namespace)

    
    edit_metadata__access__ = 'is_reviewer_or_member'
    def edit_metadata(self, context):
        for key in self.edit_job_fields:
            self.set_property(key, context.get_form_value(key))
        job_text = context.get_form_value('abakuc:job_text')
        self.set_property('abakuc:job_text', job_text)
        message = u'Changes Saved.'
        return context.come_back(message, goto=';view')


    def get_epoz_data(self):
        return self.get_property('abakuc:job_text')

    
    ############################################################
    ## Indexes
    #######################################################################
    
    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        indexes['function'] = self.get_property('abakuc:function')
        indexes['salary'] = self.get_property('abakuc:salary')
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


class Candidature(RoleAware, Folder):

    class_id = 'Candidature'
    class_title = u'Job Candidature'
    class_description = u'A Candidature'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]


    ############################################################
    # Apply for a job
    ############################################################
    apply_fields = [
        ('abakuc:applicant_note', True),
        ('ikaaro:firstname', True),
        ('ikaaro:lastname', True),
        ('ikaaro:email', True),
        ('abakuc:phone', False)]

    apply_fields_auth = [
        ('abakuc:applicant_note', True)]


    @classmethod
    def new_instance_form(cls, context):
        if context.user is None:
            namespace = context.build_form_namespace(cls.apply_fields)
            namespace['is_authenticated'] = False
        else:
            namespace = context.build_form_namespace(cls.apply_fields_auth)
            namespace['is_authenticated'] = True
        namespace['class_id'] = cls.class_id
        # Return stl
        path = '/ui/abakuc/Candidature_new_instance_form.xml'
        handler = context.root.get_handler(path)
        return stl(handler, namespace)


    @classmethod
    def new_instance(cls, container, context):
        root = context.root
        user = context.user

        # Check input data
        if user is None:
            apply_fields = cls.apply_fields
        else:
            apply_fields = cls.apply_fields_auth
        keep = [ x for x, y in apply_fields ]
        error = context.check_form_input(apply_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        
        # Check the cv
        file = context.get_form_value('file')
        if file is None:
            return context.come_back(u'Please put your CV')
        name, mimetype, body = file
        guessed = mimetypes.guess_type(name)[0]
        if guessed is not None:
            mimetype = guessed
        if mimetype not in ['application/vnd.oasis.opendocument.text',
                            'application/pdf',
                            'application/msword']:
            return context.come_back(u'Your CV must be an DOC, ODT or PDF')

        # Name already used?
        candidatures = container.search_handlers(handler_class=cls)
        nb_candidatures =  str(len(list(candidatures))+1)
        name = 'Candidature_%s' % nb_candidatures
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
        
        # Create the User
        confirm = None
        if user is None:
            users = root.get_handler('users')
            email = context.get_form_value('ikaaro:email')
            # Check the user is not already there
            catalog = context.server.catalog
            results = catalog.search(username=email)
            print email, results.get_n_documents()
            if results.get_n_documents() == 0:
                firstname = context.get_form_value('ikaaro:firstname')
                lastname = context.get_form_value('ikaaro:lastname')
                user = users.set_user(email)
                user.set_property('ikaaro:firstname', firstname)
                user.set_property('ikaaro:lastname', lastname)
                confirm = generate_password(30)
                user.set_property('ikaaro:user_must_confirm', confirm)
            else:
                user_id = results.get_documents()[0].name
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm'):
                    confirm = user.get_property('ikaaro:user_must_confirm')
        user_id = str(user.name)
        
        # Create the candidature
        handler, metadata = container.set_object(name, cls())
        for key in ['abakuc:applicant_note']:
            metadata.set_property(key, context.get_form_value(key))
        metadata.set_property('user_id', user_id)
        
        # Add the CV
        cv_cls = get_object_class(mimetype)
        cv = cv_cls(string=body)
        cv, cv_metadata = handler.set_object('cv.%s'%cv_cls.class_extension, cv)
        # Authenticated user, we are done
        if confirm is None:
            handler.send_email_to_members(context, all=False)
            message = u'Your candidature has been sent'
            return message.encode('utf-8')
        
        # Send confirmation email
        hostname = context.uri.authority.host
        from_addr = 'jobs@uktravellist.info'
        subject = u"[%s] Register confirmation required" % hostname
        subject = container.gettext(subject)
        body = container.gettext(
            u"This email has been generated in response to your"
            u" job candidature  on the UK Travel List.\n"
            u"To submit your enquiry, click the link:\n"
            u"\n"
            u"  $confirm_url"
            u"\n"
            u"If the text is on two lines, please copy and "
            u"paste the full line into your browser URL bar."
            u"\n"
            u"Thank you for visiting the UK Travel List website."
            u"\n"
            u"UK Travel List Team")
        url = '%s/;confirm_candidature_form?user=%s&key=%s' % (name, user_id,
                                                               confirm)
        url = context.uri.resolve(url)
        body = Template(body).substitute({'confirm_url': str(url)})
        root.send_email(from_addr, email, subject, body)
        # Back
        company = container.parent.get_property('dc:title')
        message = (
            u"Your candidature to <strong>%s</strong> needs to be validated."
            u"<p>An email has been sent to <strong><em>%s</em></strong>,"
            u" to finish the enquiry process, please follow the instructions"
            u" detailed within it.</p>"
            u"<p>If you don not receive the email, please check your SPAM"
            u' folder settings or <a href="/;contact_form">contact us.</a></p>'
            % (company, email))
        return message.encode('utf-8')

    
    #######################################################################
    ## Indexes
    #######################################################################
    
    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        indexes['user_id'] = self.get_property('user_id')
        return indexes
    
    #######################################################################
    ##  Confirm candidature & send Mail
    #######################################################################

    confirm_candidature_form__access__ = True
    def confirm_candidature_form(self, context):
        root = context.root

        user_id = context.get_form_value('user')
        users = root.get_handler('users')
        user = users.get_handler(user_id)

        # Check register key
        must_confirm = user.get_property('ikaaro:user_must_confirm')
        if (must_confirm is None
            or context.get_form_value('key') != must_confirm):
            return self.gettext(u"Bad key.").encode('utf-8')

        namespace = {}
        namespace['user_id'] = user_id
        namespace['key'] = must_confirm

        url = '/ui/abakuc/Candidature_confirm_candidature_form.xml'
        handler = self.get_handler(url)
        return stl(handler, namespace)



    confirm_candidature__access__ = True
    def confirm_candidature(self, context):
        keep = ['key']
        register_fields = [('newpass', True),
                           ('newpass2', True)]

        # Check register key
        user_id = context.get_form_value('user')
        root = context.root
        users = root.get_handler('users')
        user = users.get_handler(user_id)
        must_confirm = user.get_property('ikaaro:user_must_confirm')
        if context.get_form_value('key') != must_confirm:
            return self.gettext(u"Bad key.").encode('utf-8')

        # Check input data
        error = context.check_form_input(register_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Check passwords
        password = context.get_form_value('newpass')
        password2 = context.get_form_value('newpass2')
        if password != password2:
            message = u'The passwords do not match.'
            return context.come_back(message, keep=keep)

        # Set user
        user.set_password(password)
        user.del_property('ikaaro:user_must_confirm')

        # Set cookie
        user.set_auth_cookie(context, password)

        # Send email
        self.send_email_to_members(context, all=True)

        message = (u"Thank you, your CV  has been submitted.<br/>" 
                   u"If you like to login, please choose your password")
        return message.encode('utf-8')

    
    def send_email_to_members(self, context, all=False):
        root = context.root
        # User information
        users = root.get_handler('users')
        user_id = self.get_property('user_id')
        user = users.get_handler(user_id)
        firstname = user.get_property('ikaaro:firstname')
        lastname = user.get_property('ikaaro:lastname')
        email = user.get_property('ikaaro:email')
        # Get the names of jobs which has a response from current user
        candidatures = []
        if all is True:
            catalog = context.server.catalog
            query = []
            query.append(EqQuery('format', 'Candidature'))
            query.append(EqQuery('user_id', user_id ))
            query = AndQuery(*query)
            results = catalog.search(query)
            documents = results.get_documents()
            for candidature in documents:
                candidature = root.get_handler(candidature.abspath)
                candidatures.append(candidature)
        else:
            candidatures.append(self)
           
        # Sent an email for each candidature
        subject_template = u'[UK Travel] New Candidature (%s)' 
        body_template = ('A new person post his Candidature to the job : %s\n'
                         'From : %s %s\n')
        for candidature in candidatures:
            job = candidature.parent
            address = job.parent    
            subject = subject_template % job.title
            body = body_template % (job.title, firstname, lastname)
            to_addrs = address.get_property('ikaaro:reviewers')
            for to_addr in to_addrs:
                root.send_email(email, to_addr, subject, body)   


    #######################################################################
    # View
    #######################################################################
    
    view__access__ = 'is_reviewer_or_member'
    view__label__ = u'View Candidature'
    def view(self, context):
        """
        View details about a Candidature
        """
        namespace = {}
        namespace['name'] = self.name
        namespace['applicant_note'] = self.get_property('abakuc:applicant_note')
        # User
        user_id = self.get_property('user_id')
        users = context.root.get_handler('users')
        user = users.get_handler(user_id)
        namespace['user'] = {'firstname': user.get_property('ikaaro:firstname'),
                             'lastname': user.get_property('ikaaro:lastname'),
                             'phone': user.get_property('abakuc:phone'),
                             'email': user.get_property('ikaaro:email')}
        # CV
        cv = list(self.search_handlers(handler_class=File))[0]
        cv_path = cv.name
        cv_icon = cv.get_path_to_icon(48, from_handler=self)
        namespace['cv'] = {'icon': cv_icon,
                           'path': cv_path}
        
        handler = self.get_handler('/ui/abakuc/Candidature_view.xml')
        return stl(handler, namespace)

  
    #######################################################################
    # Security / Access Control
    #######################################################################

    def is_reviewer_or_member(self, user, object):
        job = self.parent
        address = job.parent
        return address.is_reviewer_or_member(user, object)


    def is_allowed_to_remove(self, user, object):
        job = self.parent
        address = job.parent
        return address.is_reviewer(user, object)


    def is_allowed_to_view(self, user, object):
        # Protect CV 
        return self.is_reviewer_or_member(user, object)        

register_object_class(Job)
register_object_class(Candidature)
