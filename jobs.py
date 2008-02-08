# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
import datetime
#from datetime import datetime
from string import Template
import mimetypes

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.file import File
from itools.stl import stl
from itools.web import get_context
from itools.rest import checkid, to_html_events
from itools.cms.widgets import table
from itools.cms.utils import generate_password
from itools.catalog import EqQuery, AndQuery, RangeQuery

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog
from metadata import JobTitle, SalaryRange
from utils import get_sort_name

# Definition of the fields of the forms to add new job application 
application_fields = [
    ('abakuc:applicant_note', True),
    ('ikaaro:firstname', True),
    ('ikaaro:lastname', True),
    ('ikaaro:email', True),
    ('abakuc:phone', False)]

application_fields_auth = [
    ('abakuc:applicant_note', True)]


class Job(Folder, RoleAware):

    class_id = 'Job'
    class_title = u'Job'
    class_description = u'Add new job board entry'
    class_icon16 = 'abakuc/images/JobBoard16.png'
    class_icon48 = 'abakuc/images/JobBoard48.png'
    class_views = [
        ['view'],
        ['application_form'],
        ['edit_metadata_form'],
        ['view_candidatures'],
        ['add_job_form'],
        ['history_form']]

    
    def get_document_types(self):
        return []

    ###################################################################
    ## Permissions for anonymous users to apply for job and add CV file 

    # XXX [SECURITY BUG] See http://bugs.abakuc.com/show_bug.cgi?id=117 
    new_resource_form__access__ = True
    # This tells us who can upload
    new_resource__access__ = True


    ###################################################################
    ## Create a new Job

    job_fields = [
        ('dc:title', True),
        ('dc:description', True),
        ('abakuc:function', True),
        ('abakuc:salary', True),
        ('abakuc:closing_date', True),
        ('abakuc:job_text', True)]


    @classmethod
    def new_instance_form(cls, context, address_country=None,
                          address_region=None, address_county=None):
        # XXX This uses different form then the
        # XXX metadata_edit_form
        # XXX look to merge the two
        # List authorized countries
        countries = [
            {'name': x, 'title': x, 'selected': x == address_country}
            for x, y in context.root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'

        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])
        regions = context.root.get_regions_stl(country=address_country,
                                       selected_region=address_region)
        county = context.root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = context.build_form_namespace(cls.job_fields)
        here = get_context().handler
        document_names = [ x for x in here.get_handler_names()
                           if x.startswith('job') ]
        if document_names:
            i = get_sort_name(document_names[-1])[1] + 1
            name = 'job%d' % i
        else:
            name = 'job1'
        namespace['class_id'] = Job.class_id
        namespace['name'] = name
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county

        path = '/ui/abakuc/jobs/job_new_resource_form.xml'
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
        keep = [ x for x, y in cls.job_fields ]
        error = context.check_form_input(cls.job_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        #
        name = context.get_form_value('name')
        title = context.get_form_value('dc:title')
        
        # Check the name 
        # We use this as fall back, should someone
        # hacks the submit form
        name = name.strip() or title.strip()
        if not name:
            message = u'Please give a title to your job'
            return context.come_back(message)
        
        name = name.lower()
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
                    'abakuc:closing_date', 'abakuc:salary', 
                    'abakuc:function', 'abakuc:county']:
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

        property = {
            (None, 'user'): username,
            ('dc', 'date'): datetime.now(),
        } 
        metadata.set_property('ikaaro:history', property)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)
        
        goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'New Job added.'
        return context.come_back(message, goto=goto) 

    add_job_form__access__ = 'is_reviewer_or_member' 
    add_job_form__label__ = u'Add new job'
    def add_job_form(self, context):
        url = '../;new_resource_form?type=Job'
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new job'
        return context.come_back(message, goto=goto)


    #######################################################################
    # View Job details
    ###

    view__access__ = True
    view__label__ = u'Job details'
    def view(self, context):
        username = self.get_property('owner')
        users = self.get_handler('/users')
        user_exist = users.has_handler(username) 
        usertitle = (user_exist and 
                     users.get_handler(username).get_title() or username)
        user = (user_exist and 
                     users.get_handler(username).name)
        userurl = '/users/%s/;view' % user
        root = context.root
        company = self.parent.parent
        # Country, Region, County
        from root import world

        county_id = self.get_property('abakuc:county')
        if county_id is None:
            # XXX Every job should have a county
            country = region = county = None 
        else:
            row = world.get_row(county_id)
            country = row[6]
            region = row[7]
            county = row[8]
        #namespace
        namespace = {}
        namespace['company'] = company.get_property('dc:title')
        salary = self.get_property('abakuc:salary')
        namespace['abakuc:salary'] = SalaryRange.get_value(salary)
        function = self.get_property('abakuc:function')
        namespace['abakuc:function'] =  JobTitle.get_value(function)
        for key in ['dc:title' , 'dc:description', 'abakuc:closing_date']:
            namespace[key] = self.get_property(key)
        
        job_text = to_html_events(self.get_property('abakuc:job_text'))
        namespace['abakuc:job_text'] = job_text

        # Country, Region, County
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county

        #Find similar jobs
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'Job'))
        today = (datetime.date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query.append(EqQuery('function', function))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        jobs = []
        for job in list(documents):
            job = root.get_handler(job.abspath)
            get = job.get_property
            # Information about the job
            address = job.parent
            company = address.parent
            #logo = company.has_handler('logo')
            namespace['logo'] = company.has_handler('logo')
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 job.name)
            jobs.append({'url': url,
                         'title': job.title})
        # Person who added the job
        namespace['user'] = usertitle
        namespace['user_uri'] = userurl
        #XXX Can we list all other jobs excluding the one we
        #XXX are looking at
        namespace['jobs'] = jobs

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
        handler = self.get_handler('/ui/abakuc/jobs/job_view.xml')
        return stl(handler, namespace)

    view_candidatures__access__ = 'is_reviewer_or_member'
    view_candidatures__label__ = u'Job candidatures'
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
        
        handler = self.get_handler('/ui/abakuc/jobs/view_applications.xml')
        return stl(handler, namespace)


    application_form__access__ = True 
    application_form__label__ = u'Apply now!'
    def application_form(self, context):
        class_id = 'Candidature'
        keep = ['title', 'version', 'type', 'state', 'module', 'priority',
            'assigned_to', 'comment']
        if context.user is None:
            namespace = context.build_form_namespace(application_fields)
            namespace['is_authenticated'] = False
        else:
            namespace = context.build_form_namespace(application_fields_auth)
            namespace['is_authenticated'] = True
        namespace['class_id'] = class_id
        # Check input data
        #error = context.check_form_input(application_fields)
        #if error is not None:
        #    return context.come_back(error, keep=keep)

        # Add
        path = '/ui/abakuc/jobs/new_instance_form.xml'
        handler = context.root.get_handler(path)
        return stl(handler, namespace)    

    #######################################################################
    # XXX User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address_country=None, address_region=None,
                 address_county=None):
        context = get_context()
        root = context.root
        # List authorized countries
        countries = [
            {'name': x, 'title': x, 'selected': x == address_country}
            for x, y in root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'

        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])
        regions = root.get_regions_stl(country=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = {}
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county
        handler = root.get_handler('ui/abakuc/jobs/jobs_form.xml')
        return stl(handler, namespace)


    ###########################################################
    # Edit details
    ###########################################################
    
    edit_job_fields = ['dc:title' , 'dc:description', 'abakuc:closing_date',
                       'abakuc:salary', 'abakuc:function']
    

    edit_metadata_form__access__ = 'is_reviewer_or_member'
    edit_metadata_form__label__ = u'Modify job details'
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
        namespace['abakuc:job_text'] = job_text
        # XXX Form
        # Get the country,  the region and  the county
        from root import world
        address_county = self.get_property('abakuc:county')
        if address_county is None:
            address_country = None
            address_region = None
        else:
            rows = world.get_row(address_county)
            address_country = rows.get_value('country')
            address_region = rows.get_value('region')
        namespace['form'] = self.get_form(address_country, address_region,
                                          address_county)
        # Return stl
        handler = self.get_handler('/ui/abakuc/jobs/job_edit_metadata.xml')
        return stl(handler, namespace)

    
    edit_metadata__access__ = 'is_reviewer_or_member'
    def edit_metadata(self, context):
        for key in self.edit_job_fields:
            self.set_property(key, context.get_form_value(key))
        job_text = context.get_form_value('abakuc:job_text')
        self.set_property('abakuc:job_text', job_text)
        address_county = context.get_form_value('abakuc:county')
        self.set_property('abakuc:county', address_county)
        message = u'Changes Saved.'
        return context.come_back(message, goto=';view')


    #######################################################################
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
    class_icon16 = 'abakuc/images/Applicant16.png'
    class_icon48 = 'abakuc/images/Applicant48.png'
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
        path = '/ui/abakuc/jobs/new_instance_form.xml'
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
            return context.come_back(u'Please upload your CV')
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
        
        for x in container.search_handlers(handler_class=Candidature):
            if user_id == x.get_property('user_id'):
                msg = u"""
                You have already applied for this particular vacancy. Your
                details have NOT been sent again.
                       """
                return context.come_back(msg)

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
            message = (u"Your job application has been succesfully sent. "
                       u"Good luck with your application!")
            return message.encode('utf-8')
        
        # Send confirmation email
        hostname = context.uri.authority.host
        from_addr = 'jobs@expert.travel'
        subject = u"[%s] Job application needs confirmation." % (hostname)
        subject = container.gettext(subject)
        body = container.gettext(
            u"This email has been generated in response to your"
            u" job application at http://%s.\n"
            "\n"
            u"In order to ensure that only genuine application are submitted, "
            u"this can only be achieved if we are able to validate the "
            u"authenticity of the applicant and a valid email address.\n"
            "\n"
            u"To confirm that you want to apply for this position, "
            u"please visit this web page:\n"
            "\n"
            u"  $confirm_url"
            u"\n"
            u"Some email clients may split this onto two lines,  "
            u"if this is the case, please copy and "
            u"paste the full line into your browser URL bar.\n"
            u"\n"
            u"Good Luck!"
            u"\n"
            u"Expert Travel Jobs"
            u"\n"
            u"http://%s") % (hostname, hostname)
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

        url = '/ui/abakuc/jobs/confirm_form.xml'
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

        # Get the Company Name
        company = self.parent.parent.parent
        to_company = company.get_property('dc:title')

        message = (u"Thank you, your CV and application "
                   u"has been submitted to <b>%s.</b><br/>" 
                   u"If you like to login, please go to " 
                   u"""<a href="/;view">Home</a>"""
            % (to_company))
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
        body_template = ('You have a new job application for your announcement : %s\n'
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
        # Notes as rest
        note = self.get_property('abakuc:applicant_note')
        namespace['applicant_note'] = to_html_events(note)
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
        
        handler = self.get_handler('/ui/abakuc/jobs/view_application.xml')
        return stl(handler, namespace)

  
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_reviewer_or_member(self, user, object):
        address = self.parent.parent
        return address.is_reviewer_or_member(user, object)


    def is_allowed_to_remove(self, user, object):
        address = self.parent.parent
        return address.is_reviewer(user, object)


    def is_allowed_to_view(self, user, object):
        # Protect CV 
        return self.is_reviewer_or_member(user, object)        

register_object_class(Job)
register_object_class(Candidature)
