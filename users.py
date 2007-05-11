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
from itools.cms.Folder import Folder
from itools.cms.Handler import Handler
from itools.cms.metadata import Password
from itools.cms.registry import register_object_class
from itools.cms.users import UserFolder as iUserFolder, User as iUser
from itools.cms.utils import get_parameters, checkid

# Import from our product
from companies import Company, Address 
#from metadata import (BusinessProfile, BusinessFunction, PhoneNumber,
#                      UK_or_NonUK)



class UserFolder(iUserFolder):

    class_id = 'users'
    class_version = '20040625'
    class_icon16 = 'images/UserFolder16.png'
    class_icon48 = 'images/UserFolder48.png'
    class_views = [['browse_thumbnails', 'browse_list'],
                   ['new_user_form'],
                   ['edit_metadata_form']]


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
                   ['edit_form', 'edit_account_form', 'edit_password_form',
                    'edit_company_form', 'edit_branch_form',
                    'change_company_form', 'change_branch_form'],
                   ['tasks_list']]

    ########################################################################
    # API
    ########################################################################
    def get_company(self):
        company_name = self.get_property('abakuc:company_name')

        if company_name in (None, ''):
            return None
        return get_context().root.get_handler('companies/%s' % company_name)
        

    def get_branch(self):
        company = self.get_company()
        if company is None:
            return None

        branch_name = self.get_property('abakuc:branch_name')
        if branch_name in (None, ''):
            return None

        try:
            return company.get_handler(branch_name)
        except LookupError:
            return None


    #######################################################################
    # Profile
    profile__access__ = 'is_allowed_to_view'
    profile__label__ = u'Profile'
    def profile(self, context):
        from root import world

        namespace = {}
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        # Company
        root = context.root
        results = root.search(format='address', members=self.name)
        namespace['address'] = None
        for address in results.get_documents():
            address = root.get_handler(address.abspath)
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
            enquiries = address.get_handler('log_enquiry.csv')
            namespace['enquiries'] = enquiries.get_nrows()

        handler = self.get_handler('/ui/abakuc/user_profile.xml')
        return stl(handler, namespace)

        
    ########################################################################
    # Setup Company/Address
    setup_company_form__access__ = 'is_self_or_admin'
    def setup_company_form(self, context):
        name = context.get_form_value('dc:title')

        namespace = {}
        namespace['name'] = name

        name = name.strip().lower()
        if name:
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

        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)
        address = company.get_handler(address_name)
        address.set_user_role(self.name, 'ikaaro:guests')

        root = context.root
        root.reindex_handler(address)

        message = u'Company/Address selected.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

        
    #######################################################################
    # Edit branch 
    edit_branch_form__access__ = 'is_allowed_to_edit'
    edit_branch_form__label__ = u'Preferences'
    edit_branch_form__sublabel__ = u'Edit Branch Details'
    def edit_branch_form(self, context):
        branch = self.get_branch()
        if branch is None:
            return get_reference("./;no_company?no_branch=1")

        my_branch = self.get_pathto(branch)
        return get_reference('%s/;edit_metadata_form' % my_branch)
        
    
    #######################################################################
    # Edit company 
    edit_company_form__access__ = 'is_allowed_to_edit'
    edit_company_form__label__ = u'Preferences'
    edit_company_form__sublabel__ = u'Edit Company Details'
    def edit_company_form(self, context):
        company = self.get_company()
        if company is None:
            return get_reference("./;no_company")

        my_company = self.get_pathto(company)
        return get_reference('%s/;edit_metadata_form' % my_company)


    #######################################################################
    # No Comapny Information 
    no_company__access__ = 'is_self_or_admin'
    def no_company(self, context):
        namespace = {}
        namespace['no_branch'] = context.get_form_value('no_branch')
        handler = self.get_handler('/ui/abakuc/user_no_company.xml')
        return stl(handler, namespace)


register_object_class(User)
