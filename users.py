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
        namespace = {}
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        # Company
        root = context.root
        regions = root.get_handler('regions.csv')
        results = root.search(format='address', members=self.name)
        for address in results.get_documents():
            address = root.get_handler(address.abspath)
            company = address.parent
            namespace['company_name'] = company.get_property('dc:title')
            namespace['website'] = company.get_website()
            namespace['address'] = address.get_property('abakuc:address')
            namespace['town'] = address.get_property('abakuc:town')
            county = address.get_property('abakuc:county')
            namespace['county'] = regions.get_row(county)[2]
            namespace['postcode'] = address.get_property('abakuc:postcode')
            namespace['phone'] = address.get_property('abakuc:phone')
            namespace['fax'] = address.get_property('abakuc:fax')

            namespace['address_path'] = self.get_pathto(address)
            # Enquiries
            enquiries = address.get_handler('log_enquiry.csv')
            namespace['enquiries'] = enquiries.get_nrows()

##        namespace['title'] = self.get_property('dc:title') or self.name

        handler = self.get_handler('/ui/abakuc/user_profile.xml')
        return stl(handler, namespace)

        
    ########################################################################
    # Edit
    change_company_form__access__ = 'is_self_or_admin'
    change_company_form__sublabel__ = u'Change Company'
    def change_company_form(self, context):
        root = context.root
        namespace = {}
        search_form = {}
        search_form['company_name'] = None
        search_form['too_many_companies'] = None
        search_form['no_result'] = None
        search_form['results'] = None
        create_form = None
        my_company = self.get_property('abakuc:company_name')
        perform_search = True
        query = {'parent_path': '/companies'}
        if context.has_form_value('company_name'):
            company_name = context.get_form_value('company_name')
            search_form['company_name'] = company_name
            query['title'] = company_name
        elif my_company:
            query['name'] = my_company
        else:
            perform_search = False
            
        catalog = root.get_handler('.catalog')
        results = catalog.search(**query)
        nb_results = results.get_n_documents()
        search_form['too_many_companies'] = False
        companies = []
        if perform_search:
            search_form['no_result'] = nb_results == 0
            if nb_results < 5:
                results = results.get_documents()
                companies = []
                for result in results:
                    info = {}
                    info['title'] = result.title
                    info['name'] = result.name
                    info['is_actual'] = result.name == my_company
                    company = root.get_handler(result.abspath)
                    info['website'] = company.get_property('abakuc:website')
                    companies.append(info)
                search_form['results'] = companies
            else:
                search_form['too_many_companies'] = True

        namespace['search_form'] = search_form

        create_form = {}
        profiles = BusinessProfile.get_namespace('Others')
        create_form['business_profiles'] = profiles
        namespace['create_form'] = create_form

        create_business_form = {}
        business_functions = BusinessFunction.get_namespace('Other')
        create_business_form['business_function'] = business_functions
        namespace['create_business_form'] =  create_business_form

        handler = self.get_handler('/ui/abakuc/user_change_company_form.xml')
        return stl(handler, namespace)


    change_company__access__ = 'is_self_or_admin'
    def change_company(self, context):
        if context.has_form_value('company_name'):
            root = context.root
            companies = root.get_handler('companies')
            companies_names = companies.get_handler_names()
            company_name = context.get_form_value('company_name')
            new_name = company_name.lower().strip().replace(' ', '-')

            # XXX Useful only until there is no more company name with ' '
            if new_name not in companies_names:
                if company_name in companies_names:
                    # Rename company, replacing ' ' by '_'
                    new_name = checkid(new_name)
                    handler = companies.get_handler(company_name)
                    handler_metadata = handler.get_metadata()
                    companies.set_handler(new_name, handler, move=True)
                    companies.del_handler('%s.metadata' % new_name)
                    companies.set_handler('%s.metadata' % new_name, 
                                          handler_metadata)
                    companies.del_handler(company_name)

                    # Change company of each user in this company
                    for user in self.parent.search_handlers(format=
                                                            User.class_id):
                        if user.get_property('abakuc:company_name') == \
                          company_name:
                            user.set_property('abakuc:company_name', new_name)
                            root.reindex_handler(user)
                else:
                    message = u'Problem, company not found in registry'
                    return context.come_back(message,goto=';change_branch_form')

            # Set new company
            old_company_name = self.get_property('abakuc:company_name')
            if old_company_name not in (company_name, new_name):
                self.set_property('abakuc:company_name', new_name)
                self.set_property('abakuc:branch_name', '')
                root.reindex_handler(self)
                message = u'Company changed'
            else:
                message = u'Same company: no change'
        else:
            message = u'Missing parameter: company name'

        return context.come_back(message, goto=';change_branch_form')


    create_company__access__ = 'is_self_or_admin'
    def create_company(self, context):
        # Params check (XXX: redisplay them when error)
        for name in ['company_title', 'company_website', 
                     'company_profile', 'company_function']:
            if context.get_form_value(name) in ('', None):
                return context.come_back(u'Missing parameter')

        company_title = context.get_form_value('company_title')
        company_name = company_title.lower().strip().replace(' ', '-')
        companies = self.get_handler('/companies')
        if companies.has_handler(company_name):
            return context.come_back(u'Please search for this company again.')
        company_website = context.get_form_value('company_website')
        company_profile = context.get_form_value('company_profile')
        company_function = context.get_form_value('company_function')

        metadata = {}
        metadata['dc:title'] = company_title
        metadata['abakuc:website'] = company_website
        metadata['abakuc:business_profile'] = company_profile
        metadata['abakuc:business_function'] = company_function
        companies.set_handler(company_name, Company(), **metadata)

        self.set_property('abakuc:company_name', company_name)
        self.set_property('abakuc:branch_name', '')
        context.root.reindex_handler(self)

        message = u'Company created'
        return context.come_back(message, goto=';change_branch_form')


    #######################################################################
    # Change branch 
    change_branch_form__access__ = 'is_self_or_admin'
    change_branch_form__sublabel__ = u'Change Branch'
    def change_branch_form(self, context):
        namespace = {}
        search_form = {}
        search_form['results'] = []
        my_company_name  = self.get_property('abakuc:company_name')
        my_branch_name = self.get_property('abakuc:branch_name')
        my_company = self.get_company()
        if my_company is not None:
            branches = []
            for branch in my_company.search_handlers(format=Branch.class_id):
                get_property = branch.metadata.get_property
                #region = get_property('abakuc:region')
                #region, county = Region.get_labels(region)
                branches.append({
                    'is_actual': branch.name == my_branch_name,
                    'name': branch.name,
                    'address': get_property('abakuc:address'),
                    'street': get_property('abakuc:street'),
                    'post_code': get_property('abakuc:postcode'),
                    'post_town': get_property('abakuc:city'),
                    'phone': get_property('abakuc:phone'),
                    'fax': get_property('abakuc:fax'),
                    'uk_or_nonuk': get_property('abakuc:uk_or_nonuk')})
                    #'region': region,
                    #'county': county})

            if branches:
                namespace['title'] = u'Select your branch'
            else:
                namespace['title'] = u'Create your branch'

            search_form['results'] = branches

            #create_form = {}
            #create_form['regions'] = Region.get_namespace(None)

            create_company_uk_or_nonuk = {}
            company_uk_or_nonuk = UK_or_NonUK.get_namespace('UK')
            create_company_uk_or_nonuk['uk_or_nonuk'] = company_uk_or_nonuk

            namespace['create_company_uk_or_nonuk'] = create_company_uk_or_nonuk
            namespace['search_form'] = search_form
            namespace['create_form'] = create_form
            namespace['no_company_defined'] = False
        else:
            namespace['no_company_defined'] = True
            namespace['title'] = u'No Company defined'


        handler = self.get_handler('/ui/abakuc/user_change_branch_form.xml')
        return stl(handler, namespace)


    #######################################################################
    # Create branch 
    create_branch__access__ = 'is_self_or_admin'
    create_branch_form__sublabel__ = u'Create Branch'
    def create_branch(self, context):
        # Check params
        for name in ['company_address', 'company_city', 'company_postcode',
                     'company_phone', 'company_fax',
                     'company_uk_or_nonuk']:
            if context.get_form_value(name) in ('', None):
                return context.come_back(u"Missing parameter")

        my_company = self.get_company()
        company_address = context.get_form_value('company_address')
        # Check if already exists either with '_' or ' '
        branch_name = company_address
        if my_company.has_handler(branch_name):
            return context.come_back(u"Branch already exists")
        branch_name = company_address.lower().strip().replace(' ', '-')
        if my_company.has_handler(branch_name):
            return context.come_back(u"Branch already exists")

        company_street = context.get_form_value('company_street')
        company_city = context.get_form_value('company_city')
        company_postcode = context.get_form_value('company_postcode')
        company_phone = context.get_form_value('company_phone')
        company_fax = context.get_form_value('company_fax')
        company_uk_or_nonuk = context.get_form_value('company_uk_or_nonuk')
        #company_region = context.get_form_value('company_region')

        metadata = {}
        metadata['abakuc:address'] = company_address
        metadata['abakuc:street'] = company_street
        metadata['abakuc:city'] = company_city
        metadata['abakuc:postcode'] = company_postcode
        metadata['abakuc:phone'] = company_phone
        metadata['abakuc:fax'] = company_fax
        metadata['abakuc:uk_or_nonuk'] = company_uk_or_nonuk
        #metadata['abakuc:region'] = company_region

        my_company.set_handler(branch_name, Branch(), **metadata)

        self.set_property('abakuc:branch_name', branch_name)
        context.root.reindex_handler(self)

        return context.come_back(u"Branch created")


    change_branch__access__ = 'is_self_or_admin'
    def change_branch(self, context):
        if context.has_form_value('branch_name'):
            branch_name = context.get_form_value('branch_name')
            current_branch_name = self.get_property('abakuc:branch_name')
            if branch_name != current_branch_name:
                my_company = self.get_company()
                if my_company.has_handler(branch_name):
                    self.set_property('abakuc:branch_name', branch_name)
                    context.root.reindex_handler(self)
                    message = u'Branch changed'
                else:
                    message = u"Your company doesn't match this branch"
            else:
                message = u'Same branch : no change'
        else:
            message = u'Missing parameter'

        return context.come_back(message)

    ########################################################################
    # Edit
    change_company_form__access__ = 'is_self_or_admin'
    change_company_form__sublabel__ = u'Change Company'
    def change_company_form(self, context):
        root = context.root
        namespace = {}
        search_form = {}
        search_form['company_name'] = None
        search_form['too_many_companies'] = None
        search_form['no_result'] = None
        search_form['results'] = None
        create_form = None
        my_company = self.get_property('abakuc:company_name')
        perform_search = True
        query = {'parent_path': '/companies'}
        if context.has_form_value('company_name'):
            company_name = context.get_form_value('company_name')
            search_form['company_name'] = company_name
            query['title'] = company_name
        elif my_company:
            query['name'] = my_company
        else:
            perform_search = False
            
        catalog = root.get_handler('.catalog')
        results = catalog.search(**query)
        nb_results = results.get_n_documents()
        search_form['too_many_companies'] = False
        companies = []
        if perform_search:
            search_form['no_result'] = nb_results == 0
            if nb_results < 5:
                results = results.get_documents()
                companies = []
                for result in results:
                    info = {}
                    info['title'] = result.title
                    info['name'] = result.name
                    info['is_actual'] = result.name == my_company
                    company = root.get_handler(result.abspath)
                    info['website'] = company.get_property('abakuc:website')
                    companies.append(info)
                search_form['results'] = companies
            else:
                search_form['too_many_companies'] = True

        namespace['search_form'] = search_form

        create_form = {}
        profiles = BusinessProfile.get_namespace('Others')
        create_form['business_profiles'] = profiles
        namespace['create_form'] = create_form

        create_business_form = {}
        business_functions = BusinessFunction.get_namespace('Other')
        create_business_form['business_function'] = business_functions
        namespace['create_business_form'] =  create_business_form

        handler = self.get_handler('/ui/abakuc/user_change_company_form.xml')
        return stl(handler, namespace)


    change_company__access__ = 'is_self_or_admin'
    def change_company(self, context):
        if context.has_form_value('company_name'):
            root = context.root
            companies = root.get_handler('companies')
            companies_names = companies.get_handler_names()
            company_name = context.get_form_value('company_name')
            new_name = company_name.lower().strip().replace(' ', '-')

            # XXX Useful only until there is no more company name with ' '
            if new_name not in companies_names:
                if company_name in companies_names:
                    # Rename company, replacing ' ' by '_'
                    new_name = checkid(new_name)
                    handler = companies.get_handler(company_name)
                    handler_metadata = handler.get_metadata()
                    companies.set_handler(new_name, handler, move=True)
                    companies.del_handler('%s.metadata' % new_name)
                    companies.set_handler('%s.metadata' % new_name, 
                                          handler_metadata)
                    companies.del_handler(company_name)

                    # Change company of each user in this company
                    for user in self.parent.search_handlers(format=
                                                            User.class_id):
                        if user.get_property('abakuc:company_name') == \
                          company_name:
                            user.set_property('abakuc:company_name', new_name)
                            root.reindex_handler(user)
                else:
                    message = u'Problem, company not found in registry'
                    return context.come_back(message,goto=';change_branch_form')

            # Set new company
            old_company_name = self.get_property('abakuc:company_name')
            if old_company_name not in (company_name, new_name):
                self.set_property('abakuc:company_name', new_name)
                self.set_property('abakuc:branch_name', '')
                root.reindex_handler(self)
                message = u'Company changed'
            else:
                message = u'Same company: no change'
        else:
            message = u'Missing parameter: company name'

        return context.come_back(message, goto=';change_branch_form')


    create_company__access__ = 'is_self_or_admin'
    def create_company(self, context):
        # Params check (XXX: redisplay them when error)
        for name in 'company_title', 'company_website', 'company_profile':
            if context.get_form_value(name) in ('', None):
                return context.come_back(u'Missing parameter')

        company_title = context.get_form_value('company_title')
        company_name = company_title.lower().strip().replace(' ', '-')
        companies = self.get_handler('/companies')
        if companies.has_handler(company_name):
            return context.come_back(u'Please search for this company again.')
        company_website = context.get_form_value('company_website')
        company_profile = context.get_form_value('company_profile')
        company_function = context.get_form_value('company_function')

        metadata = {}
        metadata['dc:title'] = company_title
        metadata['abakuc:website'] = company_website
        metadata['abakuc:business_profile'] = company_profile
        metadata['abakuc:business_function'] = company_function
        companies.set_handler(company_name, Company(), **metadata)

        self.set_property('abakuc:company_name', company_name)
        self.set_property('abakuc:branch_name', '')
        context.root.reindex_handler(self)

        message = u'Company created'
        return context.come_back(message, goto=';change_branch_form')


    #######################################################################
    # Change branch 
    change_branch_form__access__ = 'is_self_or_admin'
    change_branch_form__sublabel__ = u'Change Branch'
    def change_branch_form(self, context):
        namespace = {}
        search_form = {}
        search_form['results'] = []
        my_company_name  = self.get_property('abakuc:company_name')
        my_branch_name = self.get_property('abakuc:branch_name')
        my_company = self.get_company()
        if my_company is not None:
            branches = []
            for branch in my_company.search_handlers(format=Branch.class_id):
                get_property = branch.metadata.get_property
                #region = get_property('abakuc:region')
                #region, county = Region.get_labels(region)
                branches.append({
                    'is_actual': branch.name == my_branch_name,
                    'name': branch.name,
                    'street': get_property('abakuc:street'),
                    'address': get_property('abakuc:address'),
                    'post_code': get_property('abakuc:postcode'),
                    'post_town': get_property('abakuc:city'),
                    'phone': get_property('abakuc:phone'),
                    'fax': get_property('abakuc:fax'),
                    'uk_or_nonuk': get_property('abakuc:uk_or_nonuk')})
                    #'region': region,
                    #'county': county})

            if branches:
                namespace['title'] = u'Select your branch'
            else:
                namespace['title'] = u'Create your branch'

            search_form['results'] = branches

            create_form = {}
            #create_form['regions'] = Region.get_namespace(None)

            namespace['search_form'] = search_form
            namespace['create_form'] = create_form
            namespace['no_company_defined'] = False
        else:
            namespace['no_company_defined'] = True
            namespace['title'] = u'Company details not defined!'

        create_company_uk_or_nonuk = {}
        company_uk_or_nonuk = UK_or_NonUK.get_namespace('UK')
        create_company_uk_or_nonuk['uk_or_nonuk'] = company_uk_or_nonuk
        namespace['company_uk_or_nonuk'] = company_uk_or_nonuk

        handler = self.get_handler('/ui/abakuc/user_change_branch_form.xml')
        return stl(handler, namespace)


    #######################################################################
    # Create branch 
    create_branch__access__ = 'is_self_or_admin'
    create_branch_form__sublabel__ = u'Create Branch'
    def create_branch(self, context):
        # Check params
        for name in ['company_address', 'company_city', 'company_postcode',
                     'company_phone', 'company_fax', 'company_uk_or_nonuk']:
                     #'company_region']:
            if context.get_form_value(name) in ('', None):
                return context.come_back(u"Missing parameter")
        
        my_company = self.get_company()
        company_address = context.get_form_value('company_address')
        # Check if already exists either with '_' or ' '
        branch_name = company_address
        if my_company.has_handler(branch_name):
            return context.come_back(u"Branch already exists")
        branch_name = company_address.lower().strip().replace(' ', '_')
        if my_company.has_handler(branch_name):
            return context.come_back(u"Branch already exists")

        company_street = context.get_form_value('company_street')
        company_city = context.get_form_value('company_city')
        company_postcode = context.get_form_value('company_postcode')
        company_phone = context.get_form_value('company_phone')
        # Check the phone and fax number 
        company_phone = company_phone.strip()
        if not PhoneNumber.is_valid(company_phone):
            message = u'A valid phone number must be provided.'
            return context.come_back(message)

        company_fax = context.get_form_value('company_fax')
        company_uk_or_nonuk = context.get_form_value('company_uk_or_nonuk')
        #company_region = context.get_form_value('company_region')

        metadata = {}
        metadata['abakuc:address'] = company_address
        metadata['abakuc:street'] = company_street
        metadata['abakuc:city'] = company_city
        metadata['abakuc:postcode'] = company_postcode
        metadata['abakuc:phone'] = company_phone
        metadata['abakuc:fax'] = company_fax
        metadata['abakuc:uk_or_nonuk'] = company_uk_or_nonuk
        #metadata['abakuc:region'] = company_region
        metadata['abakuc:city'] = company_city

        my_company.set_handler(branch_name, Branch(), **metadata)

        self.set_property('abakuc:branch_name', branch_name)
        context.root.reindex_handler(self)

        return context.come_back(u"Branch created")


    change_branch__access__ = 'is_self_or_admin'
    def change_branch(self, context):
        if context.has_form_value('branch_name'):
            branch_name = context.get_form_value('branch_name')
            current_branch_name = self.get_property('abakuc:branch_name')
            if branch_name != current_branch_name:
                my_company = self.get_company()
                if my_company.has_handler(branch_name):
                    self.set_property('abakuc:branch_name', branch_name)
                    context.root.reindex_handler(self)
                    message = u'Branch changed'
                else:
                    message = u"Your company doesn't match this branch"
            else:
                message = u'Same branch : no change'
        else:
            message = u'Missing parameter'

        return context.come_back(message)

        
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
