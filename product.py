# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime

# Import from itools
from itools.cms.versioning import VersioningAware
from itools.stl import stl
from itools.cms.file import File
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.registry import register_object_class, get_object_class
from itools.web import get_context
# Import from abakuc
from utils import title_to_name

class Product(Folder):

    class_id = 'product'
    class_title = u'Product'
    class_description = u'Product'
    class_views = [
        ['view'],
        ['edit_form'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['setup_hotel_form']]


    edit_fields = ['dc:title' , 'dc:description', 'dc:subject',
                       'dc:subject', 'abakuc:closing_date',
                       'abakuc:departure_date', 'abakuc:return_date',
                       'abakuc:price']


    def new(self, **kw):
        Folder.new(self, **kw)
        cache = self.cache

    def get_document_types(self):
        return [File]

    #######################################################################
    ## Indexes
    #######################################################################

    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        #indexes['function'] = self.get_property('abakuc:function')
        #indexes['salary'] = self.get_property('abakuc:salary')
        indexes['closing_date'] = self.get_property('abakuc:closing_date')
        address = self.parent
        company = address.parent
        indexes['company'] = company.name
        indexes['address'] = address.name
        return indexes

    @staticmethod
    def get_form(name=None, description=None, website=None, subject=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['description'] = description
        namespace['website'] = website
        namespace['subject'] = subject

        handler = root.get_handler('ui/abakuc/product/form.xml')
        return stl(handler, namespace)

    def get_address(self, addr=None):
        from companies import Company, Address
        root = self.get_root()
        companies = root.get_handler('companies')
        items = companies.search_handlers(handler_class=Company)
        for item in items:
            if item.has_handler(addr):
                return item.get_handler(addr)
        return None

    ########################################################################
    # Setup Hotel/Address
    setup_hotel_form__access__ = 'is_branch_manager'
    setup_hotel_form__label__ = u'Setup hotel'
    def setup_hotel_form(self, context):
        namespace = {}
        hotel = self.get_address(self.get_property('abakuc:address'))
        if hotel is not None:
            namespace['hotel'] = hotel.parent.name
        else:
            namespace['hotel'] = None
        name = context.get_form_value('dc:title')
        name = name.strip()

        namespace['name'] = name

        if name:
            name = name.lower()
            found = []
            companies = self.get_handler('/companies')
            for company in companies.search_handlers():
                title = company.get_property('dc:title')
                topic = company.get_property('abakuc:topic')
                if name not in title.lower():
                    continue
                if 'hotel' not in topic:
                    continue
                found.append({'name': company.name, 'title': title})
            found.sort()
            namespace['n_found'] = len(found)
            namespace['found'] = found
            namespace['form'] = self.get_form()
        else:
            namespace['found'] = None
            namespace['form'] = None

        handler = self.get_handler('/ui/abakuc/product/setup_hotel.xml')
        return stl(handler, namespace)

    setup_hotel__access__ = 'is_branch_manager'
    def setup_hotel(self, context):
        from companies import Company
        # Add Company
        title = context.get_form_value('dc:title')

        if not title:
            message = u'Please give a Name to the hotel'
            return context.come_back(message)

        # Description
        description = context.get_form_value('dc:description')
        subject = context.get_form_value('dc:subject')

        # Add the company
        root = context.root
        companies = root.get_handler('/companies')
        name = title_to_name(title)
        if companies.has_handler(name):
            message = u'The hotel already exist'
            return context.come_back(message)

        company, metadata = self.set_object('/companies/%s' % name, Company())

        # Set Properties
        website = context.get_form_value('abakuc:website')
        topics = ['hotel']
        types = 'other'

        metadata.set_property('dc:title', title, language='en')
        metadata.set_property('dc:description', description)
        metadata.set_property('dc:subject', subject)
        metadata.set_property('abakuc:website', website)
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('abakuc:type', types)
        metadata.set_property('ikaaro:website_is_open', False)

        # Set the Address..
        name = name.encode('utf_8').replace('&', '%26')
        return context.uri.resolve(';setup_address_form?company=%s' % name)

    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_address_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 address_country=None, address_region=None,
                 address_county=None):
        context = get_context()
        root = context.root
        # List authorized countries
        countries = [
            {'name': y, 'title': x, 'selected': y == address_country}
            for x, y in root.get_active_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'
        # Show a list with all authorized countries
        countries.sort(key=lambda y: y['name'])
        regions = root.get_regions_stl(country_code=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town
        namespace['phone'] = phone
        namespace['fax'] = fax
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county
        handler = root.get_handler('ui/abakuc/companies/company/address/form.xml')
        return stl(handler, namespace)

    setup_address_form__access__ = 'is_branch_manager'
    def setup_address_form(self, context):
        from companies import Address
        company_name = context.get_form_value('company')
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)

        namespace = {}
        namespace['company_name'] = company_name
        namespace['company_title'] = company.get_title()
        #XXX If there is a logo, it lists this as well.
        namespace['addresses'] = [
            {'name': x.name, 'title': x.get_title(),
             'postcode': x.get_property('abakuc:postcode')}
            for x in company.search_handlers(handler_class=Address) ]
        namespace['addresses'].sort(key=lambda x: x['postcode'])
        namespace['form'] = self.get_address_form()

        handler = self.get_handler('/ui/abakuc/users/setup_address.xml')
        return stl(handler, namespace)


    setup_address_select__access__ = 'is_branch_manager'
    def setup_address_select(self, context):
        user = context.user
        company_name = context.get_form_value('company_name')
        address_name = context.get_form_value('address_name')

        # Add to new address
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)
        address = company.get_handler(address_name)
        reviewers = address.get_property('abakuc:branch_manager')
        if not reviewers:
            address.set_user_role(self.name, 'abakuc:branch_manager')
        else:
            address.set_user_role(self.name, 'abakuc:guest')
        self.set_property('abakuc:address', address_name)
        message = u'Hotel/Address selected.'
        # Take user back to the product
        home = ';view'
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_branch_manager'
    def setup_address(self, context):
        from companies import Address
        user = context.user
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
        # Link the hotel's address to the product
        self.set_property('abakuc:hotel', name)

        for name in ['address', 'county', 'town', 'postcode',
                     'phone', 'fax']:
            name = 'abakuc:%s' % name
            value = context.get_form_value(name)
            address.set_property(name, value)

        message = u'Company/Address setup done.'
        home = ';view'
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = True
    view__label__ = u'View'
    def view(self, context):
        # Build the namespace
        namespace = {}
        # Get the country, the region and the county
        from root import world
        address = self.get_property('abakuc:hotel')
        hotel_address = self.get_address(address)
        hotel = hotel_address.parent
        if hotel_address is not None: 
            county = hotel_address.get_property('abakuc:county')
        else:
            county = None
        if county is None:
            continent = None
            country = None
            region = None
        else:
            for row_number in world.search(county=county):
                row = world.get_row(row_number)
                continent = row[1]
                country = row[6]
                region = row[7]
                county = row[8]
        namespace['continent'] = continent
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        namespace['hotel'] = hotel.get_property('dc:title')
        for key in ['dc:title' , 'dc:description', 'dc:subject']:
            namespace[key] = self.get_property(key)

        handler = self.get_handler('/ui/abakuc/product/view.xml')
        return stl(handler, namespace)

    edit_form__access__ = 'is_allowed_to_edit'
    edit_form__label__ = u'Edit'
    def edit_form(self, context):
        # Build the namespace
        namespace = {}
        for key in self.edit_fields:
            namespace[key] = self.get_property(key)
            print namespace[key]


        handler = self.get_handler('/ui/abakuc/product/edit.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_allowed_to_edit'
    def edit_metadata(self, context):
        from datetime import datetime
        verify = [('dc:title', True), ('dc:description', True),
                        ('dc:subject', True),
                        ('abakuc:closing_date', True)]

        # Check input data
        error = context.check_form_input(verify)
        if error is not None:
            return context.come_back(error)
        for key in self.edit_fields:
            self.set_property(key, context.get_form_value(key))
        return context.come_back(MSG_CHANGES_SAVED)

###########################################################################
# Register
###########################################################################
register_object_class(Product)
