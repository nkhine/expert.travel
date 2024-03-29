# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>
# Import from the Standard Library
import locale
import datetime
from urllib import urlencode

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.file import File
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.utils import generate_password
from itools.cms.versioning import VersioningAware
from itools.cms.workflow import WorkflowAware
from itools.datatypes import Decimal
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
from itools.cms.utils import reduce_string

# Import from abakuc
from utils import title_to_name
from itinerary import Itinerary
from utils import abspath_to_relpath, get_sort_name

class Product(Folder, WorkflowAware):

    class_id = 'product'
    class_title = u'Product'
    class_description = u'Product'
    class_icon16 = 'abakuc/images/Briefcase16.png'
    class_icon48 = 'abakuc/images/Briefcase48.png'
    class_views = [
        ['view'],
        ['manage'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['state_form'],
        ['setup_hotel_form']]


    edit_fields = ['dc:title' , 'dc:description', 'dc:subject',
                       'abakuc:text',
                       'abakuc:closing_date', 'abakuc:departure_date',
                       'abakuc:return_date', 'abakuc:price', 'abakuc:currency']

    def new(self, **kw):
        Folder.new(self, **kw)
        cache = self.cache

    def get_document_types(self):
        return [File, Itinerary]

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager_or_member(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_remove(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_edit(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    def is_allowed_to_view(self, user, object):
        product = self.parent
        address = product.parent
        return address.is_branch_manager_or_member(user, object)

    #######################################################################
    ## Indexes
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

    ########################################################################
    # Tabs 
    def tabs(self, context):
        # Add a script
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        # Build stl
        root = context.root
        namespace = {}
        namespace['edit'] = self.edit_form(context)
        namespace['view'] = self.overview(context)
        namespace['hotel'] = self.setup_hotel_form(context)
        namespace['airline'] = self.setup_airline_form(context)
        namespace['itinerary'] = self.edit_itinerary_form(context)
        namespace['browse_content'] = self.browse_content(context)
        namespace['state'] = self.state_form(context)

        template_path = 'ui/abakuc/product/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    view_tabs__access__ = True
    def view_tabs(self, context):
        # Add a script
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        # Build stl
        root = context.root
        namespace = {}
        namespace['overview'] = self.overview(context)
        namespace['hotel'] = self.hotel(context)
        namespace['itinerary'] = self.itinerary(context)
        namespace['documents'] = self.documents(context)
        namespace['contact'] = self.contact(context)

        # Affilations
        address = self.parent
        company = address.parent
        affiliations = company.get_affiliations(context)
        namespace['affiliations'] = affiliations
        # List airlines
        root = context.root
        airline_list = []
        airlines = self.get_property('abakuc:airline')
        if airlines:
            companies = root.get_handler('companies')
            for airline in airlines:
                for item in companies.search_handlers(airline):
                    company = item.parent
                    url = '%s' % self.get_pathto(company)
                airline_list.append({
                    'id': company.name,
                    'title': company.get_title(),
                    'url': url})

        airline_list.sort(key=lambda x: x['id'])
        namespace['airlines'] = airline_list
        template_path = 'ui/abakuc/product/view_tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    ########################################################################
    # API 
    def get_hotels(self, name=None):
        name = name.lower()
        hotels = []
        companies = self.get_handler('/companies')
        for company in companies.search_handlers():
            title = company.get_property('dc:title')
            topic = company.get_property('abakuc:topic')
            if name not in title.lower():
                continue
            if 'hotel' not in topic:
                continue
            hotels.append(company)
            #hotels.append({'name': company.name, 'title': title})
        hotels.sort()
        return hotels

    def get_children(self):
        children = [ self ]
        children.extend(self.get_itinerary())
        children.extend(self.get_days())

    #class Folder(object):
    # def get_images(self):
    #   images = []
    #   for child in self.get_children():
    #     images.extend(child.search_handlers(handler_class=File))
    #   return images



    def get_itinerary(self):
        """
          Returns a namespace (list) of all itineraries
          Each product should only have one itinerary.
        """
        path = '.'
        container = self.get_handler(path)
        items = list(container.search_handlers(format=Itinerary.class_id))
        return items

    def get_itinerary_days(self):
        """
          Returns a namespace (list) to be used for getting the
          images and files that are displayed on the product
          page.
          Each product should only have one itinerary.
        """
        items = self.get_itinerary()
        for item in items:
            container = Itinerary.get_itinerary_day(item)
            return container
        return [] 

    def get_all_images(self):
        items = []
        # Get all the documents for the Product
        handlers = self.search_handlers(handler_class=File)
        for item in handlers:
            image_path = Path(item.abspath)
            handler = self.get_handler(image_path)
            path = self.get_pathto(item)
            type = item.get_content_type()
            if type == 'image':
                url_220 = '%s/;icon220' % path
                url_70 = '%s/;icon70' % path
                items.append({
                    'name': item.name,
                    'title': handler.get_title(),
                    'description': handler.get_property('dc:description'),
                    'url_220': url_220,
                    'url_70': url_70,
                    'icon': item.get_path_to_icon(size=16),
                    'mtime': item.get_mtime().strftime('%Y-%m-%d %H:%M'),
                    'description': handler.get_property('dc:description'),
                    'keywords': handler.get_property('dc:subject')
                })
        # Get all the documents for Itinerary
        itinerary = self.get_itinerary()
        for item in itinerary:
            path = Path(item.abspath)
            url = abspath_to_relpath(path)
            handler = self.get_handler(path)
            handlers = handler.search_handlers(handler_class=File)
            for item in handlers:
                image_path = Path(item.abspath)
                handler = self.get_handler(image_path)
                path = self.get_pathto(item)
                type = item.get_content_type()
                if type == 'image':
                    url_220 = '%s/%s/;icon220' % (url, item.name)
                    url_70 = '%s/%s/;icon70' % (url, item.name)
                    items.append({
                        'name': item.name,
                        'title': handler.get_title(),
                        'description': handler.get_property('dc:description'),
                        'url_220': url_220,
                        'url_70': url_70,
                        'icon': item.get_path_to_icon(size=16),
                        'mtime': item.get_mtime().strftime('%Y-%m-%d %H:%M'),
                        'description': handler.get_property('dc:description'),
                        'keywords': handler.get_property('dc:subject')
                    })
        # Get all the documents for Itinerary Days
        itinerary_days = self.get_itinerary_days()
        for item in itinerary_days:
            path = Path(item.abspath)
            handler = self.get_handler(path)
            handlers = handler.search_handlers(handler_class=File)
            for item in handlers:
                image_path = Path(item.abspath)
                url = abspath_to_relpath(path)
                handler = self.get_handler(image_path)
                path = self.get_pathto(item)
                type = item.get_content_type()
                if type == 'image':
                    url_220 = '%s/%s/;icon220' % (url, item.name)
                    url_70 = '%s/%s/;icon70' % (url, item.name)
                    items.append({
                        'name': item.name,
                        'title': handler.get_title(),
                        'description': handler.get_property('dc:description'),
                        'url_220': url_220,
                        'url_70': url_70,
                        'icon': item.get_path_to_icon(size=16),
                        'mtime': item.get_mtime().strftime('%Y-%m-%d %H:%M'),
                        'description': handler.get_property('dc:description'),
                        'keywords': handler.get_property('dc:subject')
                    })
        return items 

    ########################################################################
    # View 
    overview__access__ = True
    overview__label__ = u'Overview'
    def overview(self, context):
        #context.del_cookie('product_cookie')
        root = context.root
        namespace = {}
        for key in self.edit_fields:
            namespace[key] = self.get_property(key)

        price = self.get_property('abakuc:price')
        currency = self.get_property('abakuc:currency')
        currencies = root.get_currency(currency)
        #for x in [d for d in currencies if d['is_selected']]:
        if currency:
            currency = (d for d in currencies if d['is_selected']).next()
            if currency['id'] == 'EUR':
                locale.setlocale(locale.LC_ALL,('fr', 'ascii'))
                price = locale.format('%.2f', price, True)
                format = '%s %s' % (price, currency['sign'])
            else:
                locale.setlocale(locale.LC_ALL,('en', 'ascii'))
                price = locale.format('%.2f', price, True)
                format = '%s %s' % (currency['sign'], price)
        
        else:
            format = None
        namespace['price'] = format
        companies = root.get_handler('companies')
        # List airlines
        airline_list = []
        airlines = self.get_property('abakuc:airline')
        if airlines:
            for airline in airlines:
                company = companies.get_handler(airline)
                url = '%s' % self.get_pathto(company)
                airline_list.append({
                    'id': company.name,
                    'title': company.get_title(),
                    'url': url})

        airline_list.sort(key=lambda x: x['id'])
        # We only want to list max of 5 airlines
        if len(airline_list) >= 5:
            namespace['airlines'] = airline_list[:5]
        else:
            namespace['airlines'] = airline_list
        # List airports
        airport_list = []
        airports = self.get_property('abakuc:airport')
        if airports:
            for airport in airports:
                company = companies.get_handler(airport)
                url = '%s' % self.get_pathto(company)
                airport_list.append({
                    'id': company.name,
                    'title': company.get_title(),
                    'url': url})

        airport_list.sort(key=lambda x: x['id'])
        # We only want to list max of 5 airports
        if len(airport_list) >= 5:
            namespace['airports'] = airport_list[:5]
        else:
            namespace['airports'] = airport_list

        # Get phone number
        address = self.parent
        namespace['abakuc:phone'] = address.get_property('abakuc:phone')
        template_path = 'ui/abakuc/product/overview.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    edit_form__access__ = 'is_allowed_to_edit'
    edit_form__label__ = u'Edit'
    def edit_form(self, context):
        root = get_context().root
        types = self.get_property('abakuc:holiday_type')
        activities = self.get_property('abakuc:holiday_activity')
        board = self.get_property('abakuc:board')
        currency = self.get_property('abakuc:currency')
        # Build the namespace
        namespace = {}
        namespace['types'] = root.get_holiday_types(types)
        namespace['activities'] = root.get_holiday_activities(activities)
        namespace['board'] =  root.get_board_types(board)
        namespace['currency'] =  root.get_currency(currency)
        for key in self.edit_fields:
            namespace[key] = self.get_property(key)
        handler = self.get_handler('/ui/abakuc/product/edit.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_allowed_to_edit'
    def edit_metadata(self, context):
        verify = [('dc:title', True), ('dc:description', True),
                        ('abakuc:closing_date', True),
                        ('abakuc:departure_date', True),
                        ('abakuc:return_date', True),
                        ('abakuc:price', True),
                        ('abakuc:board', True),
                        ('abakuc:text', True),
                        ('holiday_type', True),
                        ('holiday_activity', True)]

        # Check input data
        error = context.check_form_input(verify)
        if error is not None:
            return context.come_back(error)
        
        # Check dates are correct
        closing_date = context.get_form_value('abakuc:closing_date')
        departure_date = context.get_form_value('abakuc:departure_date')
        return_date = context.get_form_value('abakuc:return_date')
        difference = return_date - departure_date
        if return_date <= departure_date:
            params = {}
            message = (u": Return date is before the departure date."
                         u"Please correct!")
            goto = './;edit_form?%s' % urlencode(params)
            return context.come_back(message, goto=goto)

        # Set metadata
        self.set_property('abakuc:departure_date', departure_date)
        self.set_property('abakuc:return_date', return_date)
        
        # Currency
        currency = context.get_form_value('abakuc:currency')
        self.set_property('abakuc:currency',currency)

        # Board type
        board = context.get_form_value('abakuc:board')
        self.set_property('abakuc:board',board)

        # Holiday type
        holiday_type = context.get_form_value('holiday_type')
        self.set_property('abakuc:holiday_type', holiday_type)
        
        # Holiday activity
        holiday_activity = context.get_form_values('holiday_activity')
        self.set_property('abakuc:holiday_activity', tuple(holiday_activity))


        date = self.get_property('dc:date')
        if date is None:
            self.set_property('dc:date', datetime.date.today())
            self.set_property('abakuc:unique_id', generate_password(30))

        for key in self.edit_fields:
            self.set_property(key, context.get_form_value(key))
        return context.come_back(MSG_CHANGES_SAVED)


    ########################################################################
    # Hotel
    hotel__access__ = True
    hotel__label__ = u'Hotel'
    def hotel(self, context):
        root = context.root
        # Build the namespace
        namespace = {}
        # Get the country, the region and the county
        from root import world
        address = self.get_property('abakuc:hotel')
        namespace['address'] = address
        if address is not None:
            hotel_address = self.get_address(address)
            hotel = hotel_address.parent
            namespace['is_hotel'] = True
            namespace['hotel'] = hotel_address.get_property('abakuc:hotel')
            rating = hotel.get_property('abakuc:rating')
            hotel_rating = root.get_rating_types(rating)
            namespace['rating'] = hotel.get_property('abakuc:rating')
            namespace['website'] = hotel.get_property('abakuc:website')
            if hotel_address is not None: 
                namespace['hotel_url'] = self.get_pathto(hotel_address)
                namespace['hotel_address'] = hotel_address.get_property('abakuc:address')
                namespace['town'] = hotel_address.get_property('abakuc:town')
                namespace['postcode'] = hotel_address.get_property('abakuc:postcode')
                namespace['phone'] = hotel_address.get_property('abakuc:phone')
                namespace['fax'] = hotel_address.get_property('abakuc:fax')
                namespace['rating'] = hotel_address.get_property('abakuc:rating')
                county = hotel_address.get_property('abakuc:county')
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

        template_path = 'ui/abakuc/product/hotel.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    itinerary__access__ = True
    itinerary__label__ = u'itinerary'
    def itinerary(self, context):
        namespace = {}
        handlers = self.search_handlers(handler_class=Itinerary)
        response = None
        if handlers != []:
          for handler in handlers:
              response = Itinerary.view(handler, context)
        namespace['response'] = response
        handler = self.get_handler('/ui/abakuc/response.xml')
        return stl(handler, namespace)


    edit_itinerary_form__access__ = 'is_branch_manager'
    edit_itinerary_form__label__ = u'Edit itinerary'
    def edit_itinerary_form(self, context):
        namespace = {}
        handlers = self.search_handlers(handler_class=Itinerary)
        for handler in handlers:
            response = Itinerary.manage(handler, context)
            namespace['response'] = response
        handler = self.get_handler('/ui/abakuc/response.xml')
        return stl(handler, namespace)
    
    documents__access__ = 'is_branch_manager_or_member'
    documents__label__ = u'Documents'
    def documents(self, context):
        namespace = {}
        #flash = self.get_files(context)[1]
        #others = self.get_files(context)[2]
        # Namespace
        namespace['flash'] = None 
        namespace['others'] = None

        handler = self.get_handler('/ui/abakuc/product/documents.xml')
        return stl(handler, namespace)

    contact__access__ = True
    contact__label__ = u'Overview'
    def contact(self, context):
        from companies import Address
        namespace = {}
        address = self.parent
        response = Address.enquiry_form(address, context)
        namespace['response'] = response
        handler = self.get_handler('/ui/abakuc/response.xml')
        return stl(handler, namespace)


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

    # We get the Hotel Address, linked to the product.
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
        address = self.get_property('abakuc:hotel')
        namespace['address'] = address
        if address is not None:
            hotel = self.get_address(address)
            namespace['hotel'] = hotel.parent.get_property('dc:title')
        else:
            namespace['hotel'] = None
        name = context.get_form_value('dc:title')
        name = name.strip()
        namespace['name'] = name
        if name:
            if len(name) <= 1:
                namespace['name'] = None 
                message = u'Please increase your search word!.'
                return context.come_back(message)
            else:
                found = []
                hotels = self.get_hotels(name)
                for company in hotels:
                    title = company.get_property('dc:title')
                    topic = company.get_property('abakuc:topic')
                    found.append({'name': company.name, 'title': title})
                    #addresses = company.get_addresses(context)[1]
                    #for address in addresses:
                    #    title = address.get_property('abakuc:hotel')
                    #    if name not in title.lower():
                    #        continue
                    #    found.append({'name': address.name, 'title': title})
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
                 rating=None, address_country=None, address_region=None,
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

        # Hotel rating
        rating = root.get_rating_types()
        namespace['rating'] = rating
        namespace['hotel'] = None

        # Add hotel contact
        register_fields = [('ikaaro:firstname', True),
                           ('ikaaro:lastname', True),
                           ('ikaaro:email', True)]

        
        
        namespace['ikaaro:firstname'] = None
        namespace['ikaaro:lastname'] = None
        namespace['ikaaro:email'] = None
        handler = root.get_handler('ui/abakuc/product/address_form.xml')
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
        # Link the hotel's address to the product
        self.set_property('abakuc:hotel', address_name)
        message = u'Hotel/Address selected.'
        # Take user back to the product
        home = ';view'
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_branch_manager'
    def setup_address(self, context):
        keep = ['ikaaro:firstname', 'ikaaro:lastname', \
                'ikaaro:email', 'abakuc:address', 'abakuc:county' \
                'abakuc:town', 'abakuc:postcode', 'abakuc:phone' \
                'abakuc:fax']

        from companies import Address
        user = context.user
        name = context.get_form_value('company_name')
        company = self.get_handler('/companies/%s' % name)

        # Add Address
        address = context.get_form_value('abakuc:address')
        if not address:
            message = u'Please give an Address'
            return context.come_back(message, keep=keep)

        name = title_to_name(address)
        if company.has_handler(name):
            message = u'The address already exist'
            return context.come_back(message, keep=keep)


        if not context.get_form_value('abakuc:county'):
            message = u'Please choose a county'
            return context.come_back(message, keep=keep)

        # Create the manager for the address
        firstname = context.get_form_value('ikaaro:firstname').strip()
        lastname = context.get_form_value('ikaaro:lastname').strip()
        email = context.get_form_value('ikaaro:email').strip()
        # Check email address has an MX record
        email_uri = 'mailto:'+email
        r1 = get_reference(email_uri)
        host = r1.host
        import dns.resolver
        from dns.exception import DNSException
        # Here we check to see if email host has an MX record
        try:
            # This may take long
            answers = dns.resolver.query(host, 'MX')
        except DNSException, e:
            answers = None
        if not answers:
            message = u'The email supplied is invalid!'
            return context.come_back(message, keep=keep)
        # Do we already have a user with that email?
        root = context.root
        results = root.search(email=email)
        users = root.get_handler('users')
        if results.get_n_documents():
            user = results.get_documents()[0]
            user = users.get_handler(user.name)
            if not user.has_property('ikaaro:user_must_confirm'):
                message = u'There is already an active user with that email.'
                return context.come_back(message, keep=keep)
        else:
            # Add the user
            user = users.set_user(email, None)
            user.set_property('ikaaro:firstname', firstname, language='en')
            user.set_property('ikaaro:lastname', lastname, language='en')
            user.set_property('owner', user.name)
            # Set the role
            from training import Training
            office = self.get_site_root()
            if isinstance(office, Training):
                # Sets the role of the user, from training.py
                default_role = self.__roles__[2]['name']
                self.set_user_role(user.name, default_role)
            else:
                address, metadata = company.set_object(name, Address())
                default_role = address.__roles__[0]['name']
                address.set_user_role(user.name, default_role)

                # Set Properties
                # Link the hotel's address to the product
                self.set_property('abakuc:hotel', name)

                for name in ['address', 'county', 'town', 'postcode',
                             'phone', 'fax', 'rating', 'hotel']:
                    name = 'abakuc:%s' % name
                    value = context.get_form_value(name)
                    address.set_property(name, value)

        # Set product specific data
        functions = 'marketing-director'
        user.set_property('abakuc:functions', functions)
        # Set the registration date
        user.set_property('abakuc:registration_date', datetime.date.today())
        # Set the terms & conditions
        terms = True 
        user.set_property('abakuc:terms', True)
        # Send confirmation email
        key = generate_password(30)
        user.set_property('ikaaro:user_must_confirm', key)
        user.send_confirmation(context, email)

        # Bring the user to the login form
        message = self.gettext(
            u"Hotel/Address setup done. "
            u"An email has been sent to %s, to validate the hotel "
            u"process follow the instructions detailed in it.") % email

        home = ';view'
        goto = context.uri.resolve(home)
        return context.come_back(message.encode('utf-8'), goto=goto)

    ########################################################################
    # Setup airline 
    setup_airline_form__access__ = 'is_branch_manager'
    setup_airline_form__label__ = u'Setup hotel'
    def setup_airline_form(self, context):
        root = get_context().root
        namespace = {}
        # List all airline companies
        airline = self.get_property('abakuc:airline')
        airport = self.get_property('abakuc:airport')
        namespace['airlines'] = root.get_airlines(airline)
        namespace['airports'] = root.get_airports(airport)
        handler = root.get_handler('ui/abakuc/product/setup_airline.xml')
        return stl(handler, namespace)

    setup_airline__access__ = 'is_branch_manager'
    setup_airline__label__ = u'Setup hotel'
    def setup_airline(self, context):
        root = get_context().root
        airline = context.get_form_values('airline')
        airport = context.get_form_values('airport')
        # Link the hotel's address to the product
        self.set_property('abakuc:airline', tuple(airline))
        self.set_property('abakuc:airport', tuple(airport))
        message = u'Airlines/Airports linked to product.'
        home = ';view'
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = True
    view__label__ = u'View'
    def view(self, context):
        # Set style
        context.styles.append('/ui/abakuc/media/global.css')
        context.styles.append('/ui/abakuc/media/thickbox.css')
        
        ## Add the js scripts
        context.scripts.append('/ui/abakuc/jquery/jquery.easing.1.3.js')
        context.scripts.append('/ui/abakuc/jquery/thickbox-modified.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.scrollto.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.serialScroll.js')

        context.scripts.append('/ui/abakuc/tools.js')
        context.scripts.append('/ui/abakuc/media/tools.js')
        context.scripts.append('/ui/abakuc/media/product.js')
        root = get_context().root
        # Build the namespace
        namespace = {}
        # Namespace
        items = self.get_all_images()
        have_image = len(items)
        if have_image > 0:
            if have_image == 1:
                namespace['more_than'] = False
            else:
                namespace['more_than'] = True
                
            # We return the first image to display
            namespace['image_1'] = items[0]
            # We show the rest here
            namespace['images'] = items[1:]
            namespace['have_image'] = True 
            namespace['total_images'] = len(items)
        else:
            namespace['have_image'] = None 
            namespace['total_images'] = None
        #namespace['images'] = images
        namespace['title'] = self.get_property('dc:title') 
        namespace['description'] = self.get_property('dc:description') 
        # XXX Fix me...
        namespace['flash'] = None 
        namespace['others'] = None 
        namespace['view_tabs'] = self.view_tabs(context)

        for key in self.edit_fields:
            namespace[key] = self.get_property(key)

        handler = self.get_handler('/ui/abakuc/product/view.xml')
        return stl(handler, namespace)

    manage__access__ = 'is_allowed_to_edit'
    manage__label__ = u'Manage'
    def manage(self, context):
        namespace = {}
        namespace['tabs'] = self.tabs(context)
        handler = self.get_handler('/ui/abakuc/product/manage.xml')
        return stl(handler, namespace)



    images__access__ = True 
    images__label__ = u'Images'
    def images(self, context):
        '''
        Used in tabs to display the images in jQuery carousel
        We have a list of the image files only those in state
        public.
        We also change the template depending on how many images we have
        '''
        # Set style
        context.styles.append('/ui/abakuc/media/global.css')
        context.styles.append('/ui/abakuc/media/thickbox.css')
        
        ## Add the js scripts
        context.scripts.append('/ui/abakuc/jquery/jquery.easing.1.3.js')
        context.scripts.append('/ui/abakuc/jquery/thickbox-modified.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.scrollto.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.serialScroll.js')

        context.scripts.append('/ui/abakuc/tools.js')
        context.scripts.append('/ui/abakuc/media/tools.js')
        context.scripts.append('/ui/abakuc/media/product.js')
        # Get all the images and flash objects
        handlers = self.search_handlers(handler_class=File)
        images = []
        for handler in handlers:
            handler_state = handler.get_property('state')
            if handler_state == 'public':
                type = handler.get_content_type()
                url_220 = '%s/;icon220' % handler.name
                url_70 = '%s/;icon70' % handler.name
                if type == 'image':
                    item = {'url_220': url_220,
                            'url_70': url_70,
                            'name': handler.name,
                            'title': handler.get_property('dc:title'),
                            'icon': handler.get_path_to_icon(size=16),
                            'mtime': handler.get_mtime().strftime('%Y-%m-%d %H:%M'),
                            'description': handler.get_property('dc:description'),
                            'keywords': handler.get_property('dc:subject')}
                    images.append(item)
        # Namespace
        namespace = {}
        have_image = len(images)
        if have_image > 0:
            if have_image == 1:
                namespace['more_than'] = False
            else:
                namespace['more_than'] = True
                
            namespace['image_1'] = images[0]
            namespace['images'] = images[1:]
            namespace['have_image'] = True 
            namespace['total_images'] = len(images)
        else:
            namespace['have_image'] = None 
            namespace['total_images'] = None

        handler = self.get_handler('/ui/abakuc/media/images.xml')
        return stl(handler, namespace)

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_allowed_to_view(self, user, object):
        address = self.parent
        return address.is_branch_manager_or_member(user, object)

###########################################################################
# Register
###########################################################################
register_object_class(Product)
