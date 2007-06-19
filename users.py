# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import uri
from itools import i18n
from itools import handlers
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
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
                   ('remove', 'Supprimer', 'button_delete', None)]
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
        # Build the namespace
        namespace = {}
        for key in self.account_fields:
            namespace[key] = self.get_property(key)
        # Ask for password to confirm the changes
        if self.name != context.user.name:
            namespace['must_confirm'] = False
        else:
            namespace['must_confirm'] = True

        handler = self.get_handler('/ui/abakuc/user/edit_account.xml')
        return stl(handler, namespace)


    #######################################################################
    # Profile
    profile__access__ = 'is_allowed_to_view'
    profile__label__ = u'Profile'
    def profile(self, context):
        from root import world

        user = context.user
        root = context.root

        namespace = {}
        # Personal
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        # Company
        # XXX note used
        #results = root.search(format='address', members=self.name)
        namespace['address'] = None
        address = self.get_address()
        if address is None:
            handler = self.get_handler('/ui/abakuc/user_profile.xml')
            return stl(handler, namespace)

        company = address.parent
        namespace['company_name'] = company.name
        namespace['address_name'] = address.name
        namespace['company_title'] = company.get_property('dc:title')
        namespace['website'] = company.get_website()
        namespace['address'] = address.get_property('abakuc:address')
        namespace['town'] = address.get_property('abakuc:town')
        county = address.get_property('abakuc:county')
        namespace['county'] = world.get_row(county)[8]
        namespace['postcode'] = address.get_property('abakuc:postcode')
        namespace['phone'] = address.get_property('abakuc:phone')
        namespace['fax'] = address.get_property('abakuc:fax')

        namespace['address_path'] = self.get_pathto(address)
        # Enquiries
        csv = address.get_handler('log_enquiry.csv')
        results = []
        for row in csv.get_rows():
            date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
            if resolved:
                continue
            user = root.get_handler('users/%s' % user_id)
            results.append({
                'index': row.number,
                'email': user.get_property('ikaaro:email'),
                'enquiry_subject': enquiry_subject})
        results.reverse()
        namespace['enquiries'] = results 
        namespace['howmany'] = len(results)
        # Reviewer of the adress ?
        reviewer = address.has_user_role(self.name,'ikaaro:reviewers')
        namespace['reviewer'] = reviewer
        ####
        # Jobs
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
                         'checkbox': reviewer,
                         'img': '/ui/abakuc/images/JobBoard16.png',
                         'title': (get('dc:title'),url),
                         'closing_date': get('abakuc:closing_date'),
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'description': get('dc:description')}
            jobs.append(job_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 20
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
                       ('remove_job', 'Supprimer', 'button_delete', None)]
            job_table = table(columns, jobs, [sortby], sortorder, actions)
            job_batch = batch(context.uri, batch_start, batch_size,
                              batch_total)
            msg = None
        else:
            job_table = None
            job_batch = None
            msg = u'No jobs'
        
        namespace['table'] = job_table
        namespace['batch'] = job_batch
        namespace['msg'] = msg 
        
        handler = self.get_handler('/ui/abakuc/user_profile.xml')
        return stl(handler, namespace)


    ########################################################################
    # Remove job
    remove_job__access__ = 'is_self_or_admin'
    def remove_job(self, context):
        ids = context.get_form_values('ids')
        root = context.root
        if not ids:
            return context.come_back(u'Please select a Job')
        address = self.get_address() 
        company = (address.parent).name
        address = address.name
        for job_id in ids:
            job = root.get_handler('/companies/%s/%s/%s' % (company, address,
                                                            job_id))
            self.del_handler(job.abspath)
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
        name = title_to_name(title)
        company, metadata = self.set_object('/companies/%s' % name, Company())

        # Set Properties
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')

        company.set_property('dc:title', title, language='en')
        company.set_property('abakuc:website', website)
        company.set_property('abakuc:topic', tuple(topics))
        company.set_property('abakuc:type', types)

        # Logo
        logo = context.get_form_value('logo')
        if logo is not None:
            filename, mimetype, data = logo
            logo = Image()
            try:
                logo.load_state_from_string(data)
            except:
                pass
            else:
                self.set_object('logo', logo)
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
        address.set_user_role(self.name, 'ikaaro:guests')

        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)
            # XXX root.reindex_handler(old_address)

        # Reindex
        #root.reindex_handler(address)

        message = u'Company/Address selected.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_self_or_admin'
    def setup_address(self, context):
        name = context.get_form_value('company_name')
        company = self.get_handler('/companies/%s' % name)

        # Add Address
        address = context.get_form_value('abakuc:address')
        name = title_to_name(address)
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
            # XXX root.reindex_handler(old_address)

        # Reindex
        # XXX root.reindex_handler(address)        

        message = u'Company/Address setup done.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

register_object_class(User)
