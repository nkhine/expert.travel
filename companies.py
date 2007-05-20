# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime

# Import from itools
from itools.datatypes import String, Unicode, Email
from itools.stl import stl
from itools.web import get_context
from itools.cms.access import RoleAware
from itools.cms.binary import Image
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler, Folder
from handlers import EnquiriesLog




class Companies(Folder):

    class_id = 'companies'
    class_title = u'Companies Directory'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    def get_document_types(self):
        return [Company]

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return 'bobo'



class Company(Folder):

    class_id = 'company'
    class_title = u'Company'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'
  
    def get_document_types(self):
        return [Address]


    #######################################################################
    # API
    #######################################################################
    def get_website(self):
        website = self.get_property('abakuc:website')
        if website.startswith('http://'):
            return website
        return 'http://' + website


    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['website'] = self.get_website()

        addresses = []
        for address in self.search_handlers():
            addresses.append({
                'name': address.name,
                'address': address.get_property('abakuc:address')})
        namespace['addresses'] = addresses
 
        handler = self.get_handler('/ui/abakuc/company_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(name=None, website=None, topics=None, logo=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['website'] = website
        namespace['topics'] = root.get_topics_namespace(topics)
        namespace['logo'] = logo

        handler = root.get_handler('ui/abakuc/company_form.xml')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        namespace = {}
        title = self.get_property('dc:title')
        website = self.get_property('abakuc:website')
        topics = self.get_property('abakuc:topic')
        logo = self.has_handler('logo')
        namespace['form'] = self.get_form(title, website, topics, logo)

        handler = self.get_handler('/ui/abakuc/company_edit_metadata.xml')
        return stl(handler, namespace)


    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        logo = context.get_form_value('logo')

        self.set_property('dc:title', title, language='en')
        self.set_property('abakuc:website', website)
        self.set_property('abakuc:topic', tuple(topics))

        # The logo
        if context.has_form_value('remove_logo'):
            if self.has_handler('logo'):
                self.del_handler('logo')
        elif logo is not None:
            filename, mimetype, data = logo
            if self.has_handler('logo'):
                logo = self.get_handler('logo')
                try:
                    logo.load_state_from_string(data)
                except:
                    self.load_state()
            else:
                logo = Image()
                try:
                    logo.load_state_from_string(data)
                except:
                    pass
                else:
                    self.set_handler('logo', logo)

        # Reindex
        root = context.root
        for address in self.search_handlers(format='address'):
            root.reindex_handler(address)

        message = u'Changes Saved.'
        return context.come_back(message)



class Address(RoleAware, Folder):

    class_id = 'address'
    class_title = u'Address'
    class_icon16 = 'abakuc/images/Employees16.png'
    class_icon48 = 'abakuc/images/Employees48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form', 'new_user_form']]

    __fixed_handlers__ = ['log_enquiry.csv']


    def new(self, **kw):
        Folder.new(self, **kw)
        handler = EnquiriesLog()
        cache = self.cache
        cache['log_enquiry.csv'] = handler
        cache['log_enquiry.csv.metadata'] = self.build_metadata(handler)


    def get_document_types(self):
        return []


    def get_catalog_indexes(self):
        from root import world

        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        indexes['topic'] = company.get_property('abakuc:topic')
        county_id = self.get_property('abakuc:county')
        if county_id:
            row = world.get_row(county_id)
            indexes['country'] = row[5]
            indexes['region'] = row[7]
            indexes['county'] = str(county_id)
        indexes['town'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        return indexes


    #######################################################################
    # API
    #######################################################################
    def get_title(self):
        address = self.get_property('abakuc:address')
        return address or self.name


    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'Address'
    view__access__ = True
    def view(self, context):
        from root import world

        county_id = self.get_property('abakuc:county')
        if county_id is None:
            # XXX Every address should have a county
            region = '-'
            county = '-'
            country = '-'
        else:
            row = world.get_row(county_id)
            country = row[6]
            region = row[7]
            county = row[8]

        namespace = {}
        namespace['company'] = self.parent.get_property('dc:title')
        namespace['address'] = self.get_property('abakuc:address')
        namespace['town'] = self.get_property('abakuc:town')
        namespace['postcode'] = self.get_property('abakuc:postcode')
        namespace['phone'] = self.get_property('abakuc:phone')
        namespace['fax'] = self.get_property('abakuc:fax')
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        
        addresses = []
        for address in self.parent.search_handlers():
            addresses.append({
                'name': address.name,
                'address': address.get_property('abakuc:address')})
        namespace['addresses'] = addresses
 

        handler = self.get_handler('/ui/abakuc/address_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 address_county=None):
        from root import world

        root = get_context().root

        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town 
        namespace['phone'] = phone
        namespace['fax'] = fax

        rows = world.get_rows()

        countries = {}
        regions = {}
        for index, row in enumerate(rows):
            country = row[6]
            region = row[7]
            county = row[8]
            is_selected = (index == address_county)
            id = str(index)

            # Add the country if not yet added
            if country in countries:
                country_ns = countries[country]
            else:
                country_ns = {'id': index, 'title': country,
                              'is_selected': False, 'display': 'none',
                              'regions': []}
                countries[country] = country_ns

            # Add the region if not yet added
            if region in regions:
                region_ns = regions[region]
            else:
                region_ns = {'id': index, 'title': region,
                             'is_selected': False, 'display': 'none',
                             'counties': []}
                regions[region] = region_ns
                # Add to the country
                country_ns['regions'].append(
                    {'id': id, 'title': region, 'is_selected': False})

            region_ns['counties'].append({'id': id, 'title': county,
                                          'is_selected': is_selected})

            # If this county is selected, activate the right blocks
            if is_selected:
                country_ns['is_selected'] = True
                country_ns['display'] = 'inherit'
                region_ns['is_selected'] = True
                region_ns['display'] = 'inherit'
                for x in country_ns['regions']:
                    if x['title'] == region:
                        x['is_selected'] = True
                        break

        countries = countries.values()
        countries.sort(key=lambda x: x['title'])
        namespace['countries'] = countries

        regions = regions.values()
        regions.sort(key=lambda x: x['title'])
        namespace['regions'] = regions

        handler = root.get_handler('ui/abakuc/address_form.xml.en')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        address = self.get_property('abakuc:address')
        postcode = self.get_property('abakuc:postcode')
        town = self.get_property('abakuc:town')
        phone = self.get_property('abakuc:phone')
        fax = self.get_property('abakuc:fax')
        address_county = self.get_property('abakuc:county')

        namespace = {}
        namespace['form'] = self.get_form(address, postcode, town, phone, fax,
                                          address_county)

        handler = self.get_handler('/ui/abakuc/address_edit_metadata.xml')
        return stl(handler, namespace)


    def edit_metadata(self, context):
        keys = ['address', 'postcode', 'town', 'phone', 'fax', 'county']

        for key in keys:
            key = 'abakuc:%s' % key
            value = context.get_form_value(key)
            self.set_property(key, value)

        message = u'Changes Saved.'
        return context.come_back(message)


    #######################################################################
    # User Interface / Enquiries
    enquiry_form__access__ = True
    def enquiry_form(self, context):
        namespace = {}

        handler = self.get_handler('/ui/abakuc/enquiry_edit_metadata.xml')
        return stl(handler, namespace)


    enquiry__access__ = True
    def enquiry(self, context):
        tab = {}
        tab['email'] = context.get_form_value('ikaaro:email')
        for key in 'fullname', 'enquiry', 'phone', 'typeenquiry':
            tab[key] = context.get_form_value('abakuc:%s' % key)

        subject = u'[%s]' % tab['typeenquiry']
        body = 'Name: %(fullname)s - Phone: %(phone)s - %(enquiry)s' % tab

        # Check the input data
        if not tab['email'] or not tab['fullname'] or not tab['typeenquiry']:
            return context.come_back(u'Please fill the missing fields.')

        # Check the from address
        if not Email.is_valid(tab['email']):
            message = u'A valid email address must be provided.'
            return context.come_back(message)

        # Sent the mail
        root = self.get_root()
        users = root.get_handler('users')
        for name in self.get_property('ikaaro:members'):
            to_addr = users.get_handler(name).get_property('ikaaro:email')
            root.send_email(tab['email'], to_addr, subject, body)
 
        # Save the mail in csv
        row = [datetime.now(), tab['typeenquiry'], tab['fullname'],
               tab['email'], tab['phone'], tab['enquiry']]

        # check if the handler exist
        handler = self.get_handler('log_enquiry.csv')
        handler.add_row(row)

        message = u'Mail sent.'
        return context.come_back(message)



register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
