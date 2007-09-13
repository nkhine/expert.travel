# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>


# Import from the standard library
import mimetypes

# Import from itools
from itools import uri
from itools import i18n
from itools import handlers
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
from itools.cms.registry import get_object_class
from itools.cms.access import AccessControl
from itools.cms.binary import Image
from itools.cms.folder import Folder
from itools.cms.base import Handler
from itools.cms.metadata import Password
from itools.cms.registry import register_object_class
from itools.cms.users import UserFolder as iUserFolder, User as iUser
from itools.cms.utils import get_parameters
from itools.rest import checkid
from itools.cms.widgets import table, batch
from itools.xml import Parser
from itools.datatypes import Email

# Import from our product
from companies import Company, Address 
from jobs import Job
from utils import title_to_name
from metadata import JobTitle, SalaryRange



class UserFolder(iUserFolder):

    class_id = 'users'
    class_version = '20040625'
    class_icon16 = 'images/UserFolder16.png'
    class_icon48 = 'images/UserFolder48.png'
    class_views = [['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_user_form'],
                   ['edit_metadata_form'],
                   ['view']]


    view__access__ = 'is_allowed_to_edit'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        columns = [('name', u'Name'),
                   ('title', u'Title'),
                   ('lastname', u'Lastname'),
                   ('firstname', u'Firstname'),
                   ('user_must_confirm', u'Confirm')]
        # Get data
        rows = []
        users = self.search_handlers(handler_class=User)
        for u in users:
            confirm = u.get_property('ikaaro:user_must_confirm')
            if confirm:
                confirm = 'No'
            else:
                confirm = 'Yes'
            rows.append({'id': u.name,
                         'checkbox': True,
                         'img': '/ui/images/User16.png',
                         'name': (u.name,'%s/' % u.name),
                         'title': u.title,
                         'lastname': u.get_property('ikaaro:lastname'),
                         'firstname': u.get_property('ikaaro:firstname'),
                         'user_must_confirm': confirm})

        # Create table
        actions = [('select', u'Select All', 'button_select_all',
                    "return select_checkboxes('browse_list', true);"),
                   ('select', u'Select None', 'button_select_none',
                    "return select_checkboxes('browse_list', false);"),
                   ('remove', 'Remove', 'button_delete', None)]
        if rows:
            sortby = context.get_form_value('sortby', 'id')
            sortorder = context.get_form_value('sortorder', 'up')
            rows.sort(lambda x,y: cmp(x[sortby], y[sortby]))
            if sortorder == 'down':
                rows.reverse()
            namespace['table'] = table(columns, rows, [sortby],
                                       sortorder, actions=actions)
            namespace['msg'] = None
        else:
            namespace['table'] = None
            namespace['msg'] = u'No Users'

        handler = self.get_handler('/ui/abakuc/Users_view.xml')
        return stl(handler, namespace)


    def get_document_types(self):
            return [User]


register_object_class(UserFolder)



class User(iUser, Handler):

    class_id = 'user'
    class_version = '20040625'
    class_title = 'User'
    class_icon16 = 'images/User16.png'
    class_icon48 = 'images/User48.png'
    class_views = [['profile'],
                   ['browse_content?mode=thumbnails',
                    'browse_content?mode=list',
                    'browse_content?mode=image'],
                   ['new_resource_form'],
                   ['edit_form', 'edit_account_form', 'edit_password_form'],
                   ['tasks_list']]

    ########################################################################
    # API
    ########################################################################
    def get_address(self):
        root = self.get_root()
        results = root.search(format='address', members=self.name)
        for address in results.get_documents():
            return root.get_handler(address.abspath)
        return None

    def get_job(self):
        root = self.get_root()
        results = root.search(format='job', members=self.name)
        for job in results.get_documents():
            return root.get_handler(job.abspath)
        return None
    #######################################################################
    # Edit Account 
    account_fields = iUser.account_fields + ['abakuc:phone']
    
    edit_account_form__access__ = 'is_allowed_to_edit'
    edit_account_form__label__ = u'Edit'
    edit_account_form__sublabel__ = u'Account'
    def edit_account_form(self, context):
        root = get_context().root
        job_functions = self.get_property('abakuc:job_function')
        logo = self.has_handler('logo')

        # Build the namespace
        namespace = {}
        for key in self.account_fields:
            namespace[key] = self.get_property(key)
        namespace['job_functions'] = root.get_functions_namespace(job_functions)
        namespace['logo'] = logo
        # Ask for password to confirm the changes
        if self.name != context.user.name:
            namespace['must_confirm'] = False
        else:
            namespace['must_confirm'] = True

        handler = self.get_handler('/ui/abakuc/user_edit_account.xml')
        return stl(handler, namespace)

    edit_account__access__ = 'is_allowed_to_edit'
    def edit_account(self, context):
        # Check password to confirm changes
        password = context.get_form_value('password')
        user = context.user
        if self.name == user.name:
            if not self.authenticate(password):
                return context.come_back(
                    u"You mistyped your actual password, your account is"
                    u" not changed.")

        # Check the email is good
        email = context.get_form_value('ikaaro:email')
        if not Email.is_valid(email):
            return context.come_back(MSG_INVALID_EMAIL)

        root = context.root
        results = root.search(email=email)
        if results.get_n_documents():
            message = (u'There is another user with the email "%s", '
                       u'please try again')
        job_functions = context.get_form_values('job_function')
        logo = context.get_form_value('logo')
        # Save changes
        for key in self.account_fields:
            value = context.get_form_value(key)
            self.set_property(key, value)
        self.set_property('abakuc:job_function', job_functions)
        
        # The logo
        if context.has_form_value('remove_logo'):
            if self.has_handler('logo'):
                self.del_object('logo')
        elif logo is not None:
            name, mimetype, data = logo
            guessed = mimetypes.guess_type(name)[0]
            if guessed is not None:
                mimetype = guessed
            logo_cls = get_object_class(mimetype)
            logo = logo_cls(string=data)
            logo_name = 'logo'
            # Check format of Logo
            if not isinstance(logo, Image):
                msg = u'Your logo must be an Image PNG or JPEG'
                return context.come_back(msg)
            # Check size
            size = logo.get_size()
            if size is not None:
                width, height = size
                if width > 200 or height > 200:
                    msg = u'Your logo is too big (max 200x200 px)'
                    return context.come_back(msg)
            
            # Add or edit the logo
            if self.has_handler('logo'):
                # Edit the logo
                logo = self.get_handler('logo')
                try:
                    logo.load_state_from_string(data)
                except:
                    self.load_state()
                logo = logo.load_state_from_string(string=data)
            else:
                # Add the new logo
                logo = logo_cls(string=data)
                logo, metadata = self.set_object(logo_name, logo)
                metadata.set_property('state', 'public')

        url = ';profile'
        goto = context.uri.resolve(url)
        message = u'Account changed.'
        return context.come_back(message, goto=goto)

    #######################################################################
    # Profile
    profile__access__ = 'is_allowed_to_view'
    profile__label__ = u'Profile'
    def profile(self, context):
        from root import world

        namespace = {}
        user = context.user
        root = context.root
        users = root.get_handler('users')
        
        # Get Company and Address
        namespace['address'] = None
        address = self.get_address()
        
        # User Role
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['is_admin'] = is_admin
        if address:
            is_reviewer = address.has_user_role(self.name, 'ikaaro:reviewers')
            is_member = address.has_user_role(self.name, 'ikaaro:members')
            is_guest = address.has_user_role(self.name, 'ikaaro:guests')
            is_reviewer_or_member = is_reviewer or is_member
        else:
            is_reviewer = False
            is_member = False
            is_guest = False
            is_reviewer_or_member = False

        namespace['is_reviewer'] = is_reviewer
        namespace['is_member'] = is_member
        namespace['is_guest'] = is_guest
        namespace['is_reviewer_or_member'] = is_reviewer_or_member

        # User Identity
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        
        if address is None:
            handler = self.get_handler('/ui/abakuc/user_profile.xml')
            return stl(handler, namespace)
        company = address.parent
        
        
        # Company
        namespace['company'] = {'name': company.name,
                                'title': company.get_property('dc:title'),
                                'website': company.get_website(),
                                'path': self.get_pathto(company)}
        # Address
        county = address.get_property('abakuc:county')
        addr = {'name': address.name,
                'address': address.get_property('abakuc:address'),
                'town': address.get_property('abakuc:town'),
                'county': world.get_row(county)[8],
                'postcode':address.get_property('abakuc:postcode'),
                'phone': address.get_property('abakuc:phone'),
                'fax': address.get_property('abakuc:fax'),
                'address_path': self.get_pathto(address)}

        namespace['address'] = addr
        
        # Enquiries
        csv = address.get_handler('log_enquiry.csv')
        results = []
        for row in csv.get_rows():
            date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
            if resolved:
                continue
            user = users.get_handler(user_id)
            results.append({
                'index': row.number,
                'email': user.get_property('ikaaro:email'),
                'enquiry_subject': enquiry_subject})
        results.reverse()
        namespace['enquiries'] = results 
        namespace['howmany'] = len(results)
        
        # Table with Jobs
        namespace['batch'] = ''
        columns = [('title', u'Title'),
                   ('closing_date', u'Closing Date'),
                   ('function', u'Function'),
                   ('description', u'Short description')]
        # Get all Jobs
        address_jobs = address.search_handlers(handler_class=Job)
        # Construct the lines of the table
        jobs = []
        for job in list(address_jobs):
            #job = root.get_handler(job.abspath)
            get = job.get_property
            # Information about the job
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 job.name)
            job_to_add ={'id': job.name, 
                         'checkbox': is_reviewer,
                         'img': '/ui/abakuc/images/JobBoard16.png',
                         'title': (get('dc:title'),url),
                         'closing_date': get('abakuc:closing_date'),
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'description': get('dc:description')}
            jobs.append(job_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(jobs)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        jobs = jobs[batch_start:batch_fin]
        # Order 
        sortby = context.get_form_value('sortby', 'closing_date')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        jobs.sort(lambda x,y: cmp(x[sortby], y[sortby]))
        if reverse:
            jobs.reverse()
        # Set batch informations
        # Namespace 
        if jobs:
            actions = [('select', u'Select All', 'button_select_all',
                        "return select_checkboxes('browse_list', true);"),
                       ('select', u'Select None', 'button_select_none',
                        "return select_checkboxes('browse_list', false);"),
                       ('create_new_job', u'Add new job', 'button_ok',
                        None),
                       ('remove_job', 'Delete Job/s', 'button_delete', None)]
            job_table = table(columns, jobs, [sortby], sortorder, actions)
            msgs = (u'There is one job.', u'There are ${n} jobs.')
            job_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            job_table = None
            job_batch = None
            msg = u'No jobs'

        namespace['table'] = job_table
        namespace['batch'] = job_batch
        namespace['msg'] = msg 

        namespace['contact'] = None
        if user is None:
            return u'You need to be registered!'     
        if address.has_user_role(user.name, 'ikaaro:guests'):
            contacts = address.get_property('ikaaro:reviewers')
            if contacts:
                contact = users.get_handler(contacts[0])
                namespace['contact'] = contact.get_property('ikaaro:email')
            else:
                contact = '<span style="color:red;">The administrator</span>'
                namespace['contact'] = Parser(contact)
        handler = self.get_handler('/ui/abakuc/user_profile.xml')
        return stl(handler, namespace)


    ########################################################################
    # View 
    view__access__ = True 
    def view(self, context):
        return 'Hello' 

    ########################################################################
    # Create a new job 
    create_new_job__access__ = 'is_self_or_admin'
    def create_new_job(self, context):
        address = self.get_address()
        company = address.parent
        url = '/companies/%s/%s/;new_resource_form?type=Job' % (company.name,
                                                                address.name)
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new job'
        return context.come_back(message, goto=goto)
        
    
    ########################################################################
    # Remove job
    remove_job__access__ = 'is_self_or_admin'
    def remove_job(self, context):
        ids = context.get_form_values('ids')
        root = context.root
        if not ids:
            return context.come_back(u'Please select a Job')
        address = self.get_address() 
        for job_id in ids:
            address.del_object(job_id)
        return context.come_back(u'Job(s) delete')

    
    ########################################################################
    # Setup Company/Address
    setup_company_form__access__ = 'is_self_or_admin'
    setup_company_form__sublabel__ = u'Switch to another company'
    def setup_company_form(self, context):
        name = context.get_form_value('dc:title')
        name = name.strip()

        namespace = {}
        namespace['name'] = name

        if name:
            name = name.lower()
            found = []
            companies = self.get_handler('/companies')
            for company in companies.search_handlers():
                title = company.get_property('dc:title')
                if name not in title.lower():
                    continue
                found.append({'name': company.name, 'title': title})
            found.sort()
            namespace['n_found'] = len(found)
            namespace['found'] = found
            namespace['form'] = Company.get_form()
        else:
            namespace['found'] = None
            namespace['form'] = None

        handler = self.get_handler('/ui/abakuc/user_setup_company.xml')
        return stl(handler, namespace)
 

    setup_company__access__ = 'is_self_or_admin'
    def setup_company(self, context):
        # Add Company
        title = context.get_form_value('dc:title')
        
        if not title:
            message = u'Please give an Name to your Company'
            return context.come_back(message)
        
        # Check the Logo
        logo_form = context.get_form_value('logo')
        if logo_form:
            name, mimetype, body = logo_form
            guessed = mimetypes.guess_type(name)[0]
            if guessed is not None:
                mimetype = guessed
            logo_cls = get_object_class(mimetype)
            logo = logo_cls(string=body)
            logo_name = 'logo'
            # Check format
            if not isinstance(logo, Image):
                msg = u'Your logo must be an Image PNG or JPEG'
                return context.come_back(msg)
            # Check size
            size = logo.get_size()
            if size is not None:
                width, height = size
                if width > 200 or height > 200:
                    msg = u'Your logo is too big (max 200x200 px)'
                    return context.come_back(msg)

        # Add the company  
        root = context.root
        companies = root.get_handler('/companies')
        name = title_to_name(title)
        if companies.has_handler(name):
            message = u'The Company already exist'
            return context.come_back(message)

        company, metadata = self.set_object('/companies/%s' % name, Company())
        
        # Set Properties
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')

        metadata.set_property('dc:title', title, language='en')
        metadata.set_property('abakuc:website', website)
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('abakuc:type', types)
        metadata.set_property('ikaaro:website_is_open', True) 

        # Add the logo
        if logo_form:
            logo, logo_metadata = company.set_object(logo_name, logo)
            logo_metadata.set_property('state', 'public')

        # Set the Address..
        name = name.encode('utf_8').replace('&', '%26')
        return context.uri.resolve(';setup_address_form?company=%s' % name)



    setup_address_form__access__ = 'is_self_or_admin'
    def setup_address_form(self, context):
        company_name = context.get_form_value('company')
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)

        namespace = {}
        namespace['company_name'] = company_name
        namespace['company_title'] = company.get_title()
        namespace['addresses'] = [
            {'name': x.name, 'title': x.get_title(),
             'postcode': x.get_property('abakuc:postcode')}
            for x in company.search_handlers() ]
        namespace['addresses'].sort(key=lambda x: x['postcode'])
        namespace['form'] = Address.get_form()

        handler = self.get_handler('/ui/abakuc/user_setup_address.xml')
        return stl(handler, namespace)


    setup_address_select__access__ = 'is_self_or_admin'
    def setup_address_select(self, context):
        company_name = context.get_form_value('company_name')
        address_name = context.get_form_value('address_name')

        # Add to new address
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)
        address = company.get_handler(address_name)
        reviewers = address.get_property('ikaaro:reviewers')
        if not reviewers:
            address.set_user_role(self.name, 'ikaaro:reviewers')
        else:
            address.set_user_role(self.name, 'ikaaro:guests')
        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address selected.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_self_or_admin'
    def setup_address(self, context):
        name = context.get_form_value('company_name')
        company = self.get_handler('/companies/%s' % name)

        # Add Address
        address = context.get_form_value('abakuc:address')
        if not address:
            message = u'Please give an Address'
            return context.come_back(message)

        name = title_to_name(address)
        if company.has_handler(name):
            message = u'The address already exist'
            return context.come_back(message)


        if not context.get_form_value('abakuc:county'):
            message = u'Please choose a county'
            return context.come_back(message)

        address, metadata = company.set_object(name, Address())

        # Set Properties
        for name in ['address', 'county', 'town', 'postcode',
                     'phone', 'fax']:
            name = 'abakuc:%s' % name
            value = context.get_form_value(name)
            address.set_property(name, value)

        # Link the User to the Address
        address.set_user_role(self.name, 'ikaaro:reviewers')

        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address setup done.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

register_object_class(User)
