# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime

# Import from itools
from itools.datatypes import String, Unicode, Email
from itools.stl import stl
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
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'

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
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'
  
    def get_document_types(self):
        return [Address]


    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['website'] = self.get_property('abakuc:website')
 
        handler = self.get_handler('/ui/abakuc/company_view.xml')
        return stl(handler, namespace)

    def edit_metadata_form(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['website'] = self.get_property('abakuc:website')
        topics = self.get_property('abakuc:topic')
        root = context.root
        namespace['topics'] = root.get_topics_namespace(topics)

        namespace['logo'] = self.has_handler('logo')

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


    __roles__ = [
        {'name': 'ikaaro:members', 'title': u"Members", 'unit': u"Member"}]


    def new(self, **kw):
        Folder.new(self, **kw)
        handler = EnquiriesLog()
        cache = self.cache
        cache['log_enquiry.csv'] = handler
        cache['log_enquiry.csv.metadata'] = self.build_metadata(handler)


    def get_document_types(self):
        return []


    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        indexes['topic'] = company.get_property('abakuc:topic')
        county_id = self.get_property('abakuc:county')
        if county_id:
            csv = self.get_handler('/regions.csv')
            country, region, county = csv.get_row(county_id)
            indexes['region'] = region
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
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'Address'
    view__access__ = True
    def view(self, context):
        
        county_id = self.get_property('abakuc:county')
        csv = self.get_handler('/regions.csv')
        if county_id is None:
            # XXX Every address should have a county
            region = '-'
            county = '-'
        else:
            row = csv.get_row(county_id)
            country, region, county = row

        namespace = {}
        #namespace['company'] = company.get_property('dc:title')
        namespace['address'] = self.get_property('abakuc:address')
        namespace['town'] = self.get_property('abakuc:town')
        namespace['postcode'] = self.get_property('abakuc:postcode')
        namespace['phone'] = self.get_property('abakuc:phone')
        namespace['fax'] = self.get_property('abakuc:fax')
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        

        handler = self.get_handler('/ui/abakuc/address_view.xml')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        keys = ['address', 'postcode', 'town', 'phone', 'fax']

        namespace = {}
        for key in keys:
            namespace[key] = self.get_property('abakuc:%s' % key)

        # Towns
        rows = self.get_handler('/regions.csv').get_rows()
        address_county = self.get_property('abakuc:county')

        regions = {}
        for index, row in enumerate(rows):
            country, region, county = row
            is_selected = (index == address_county)

            region = regions.setdefault(region, {'title': region})
            region.setdefault('is_selected', False)
            region.setdefault('display', 'none')
            if is_selected:
                region['is_selected'] = True
                region['display'] = 'inherit'
            region.setdefault('rel', index)
            counties = region.setdefault('counties', [])
            counties.append({'id': str(index),
                          'title': county,
                          'is_selected': is_selected})

        regions = regions.values()
        regions.sort(key=lambda x: x['title'])
        namespace['regions'] = regions

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
        # who is the recipient ?
        contact='sylvain@itaapy.com'
        keys = ['email','fullname','enquiry','phone','typeenquiry']
        
        tab = {}

        for key in keys:
            if key == 'email':
                myKey = 'ikaaro:%s' % key
            else:
                myKey = 'abakuc:%s' % key

            value = context.get_form_value(myKey)
            tab[key]=value

        subject = u'[%s]' % tab['typeenquiry']
        body = 'Name: %(fullname)s - Phone: %(phone)s - %(enquiry)s' % tab

        #Check the input data
        if not tab['email'] or not tab['fullname'] or not tab['typeenquiry']:
          return context.come_back(u'Please fill the missing fields.')

        # Check the from address
        if not Email.is_valid(tab['email']):
          return context.come_back(u'A valid email address must be provided.')
        
        # Sent the mail
        root = self.get_root()
        root.send_email(tab['email'], contact, subject, body)
  
        
        # Save the mail in csv
        row = [datetime.now(),tab['typeenquiry'],tab['fullname'],tab['email']
        ,tab['phone'],tab['enquiry']]


        # check if the handler exist
        #if not self.has_handler('log_enquiry.csv'):
        #    handler = EnquiriesLog()
        #    self.set_handler('log_enquiry.csv', handler)
        handler = self.get_handler('log_enquiry.csv')
        handler.add_row(row)

        message = u'Mail sent.'
        return context.come_back(message)



register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
