# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the future
from __future__ import with_statement
import datetime
import pickle
# Import from the Standard Library
from random import choice
from string import ascii_letters
import re

# Import from itools
from itools.catalog import EqQuery, AndQuery, PhraseQuery, RangeQuery
from itools import get_abspath
from itools.datatypes import Integer, String, Unicode
from itools.handlers import get_handler
from itools.cms.csv import CSV as BaseCSV
from itools.stl import stl
from itools.web import get_context
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class
from itools.cms.root import Root as BaseRoot
from itools.cms.html import XHTMLFile
from itools.xhtml import Document as XHTMLDocument
from itools.catalog import (TextField, KeywordField, 
                            IntegerField, BoolField)
# Import from abakuc our modules
from base import Handler
from handlers import EnquiriesLog
from users import UserFolder
from companies import Companies, Company, Address
from countries import Countries, Country
from destinations import Destinations
from expert_travel import ExpertTravel
from training import Trainings, Training
from utils import title_to_name



def get_host_prefix(context):
    hostname = context.uri.authority.host
    tab = hostname.split('.', 1)
    if len(tab)>1:
        return tab[0]
    return None



class World(BaseCSV):

    columns = ['id', 'continent', 'sub_id', 'sub_continent', 'country_id',
                'iana_root_zone', 'country', 'region', 'county']

    schema = {'id': Integer,
              'continent': String,
              'sub_id': Integer,
              'sub_continent': String,
              'country_id': Integer,
              'iana_root_zone': String(index='keyword'),
              'country': String,
              'region': Unicode(index='keyword'),
              'county': Unicode(index='keyword')}


path = get_abspath(globals(), 'data/countries_austria_full.csv')
world = World(path)

class Root(Handler, BaseRoot):

    class_id = 'abakuc'
    class_title = u'Abakuc'
    class_version = '20070218'
    class_domain = 'abakuc'
    class_description = (u'One back-office to bring them all and in the'
                         u' darkness bind them, in an' 
                         u' anarchically scalable information system.')

    class_views = [['view']] + BaseRoot.class_views + [['import_data_form']]
    site_format =''
    #######################################################################
    # Administrator Email
    contact_email = 'norman@expert.travel'

    #######################################################################
    # Index & Search
    _catalog_fields = BaseRoot._catalog_fields + [
            KeywordField('level0', is_stored=True),
            KeywordField('level1', is_stored=True),
            KeywordField('level2', is_stored=True),
            KeywordField('level3', is_stored=True),
            KeywordField('level4', is_stored=True),
            KeywordField('user_id', is_stored=False),
            KeywordField('unique_id', is_stored=True),
            KeywordField('closing_date', is_stored=False),
            TextField('company', is_stored=True),
            TextField('address', is_stored=True),
            KeywordField('country', is_stored=True),
            KeywordField('region', is_stored=True),
            KeywordField('abakuc:county', is_stored=True),
            TextField('itinerary', is_stored=True),
            TextField('itinerary_day', is_stored=True),
            # XXX Fix this as is repeated in TP
            #KeywordField('function', is_stored=False),
            KeywordField('salary', is_stored=False),
            TextField('description', is_stored=False),
            # For users KeywordField(training programme statistics)
            KeywordField('registration_date'),
            KeywordField('registration_year'),
            KeywordField('registration_month'),
            # Old TU search keys
            #KeywordField('business_profile', is_indexed=False, is_stored=True),
            #KeywordField('functions', is_indexed=True, is_stored=True),
            #KeywordField('business_function', is_stored=True),
            KeywordField('type'),
            KeywordField('topic'),
            KeywordField('function'),
            KeywordField('training_programmes')]


    #######################################################################
    # New
    def new(self, username=None, password=None):
        BaseRoot.new(self, username=username, password=password)
        cache = self.cache

        # Companies
        title = u'Companies'
        kw = {'dc:title': {'en': title},
              'ikaaro:website_is_open': True}
        #kw = {'dc:title': {'en': title}}
        companies = Companies()
        cache['companies'] = companies
        cache['companies.metadata'] = companies.build_metadata(**kw)

        # Countries
        title = u'Countries'
        kw = {'dc:title': {'en': title}}
        countries = Countries()
        cache['countries'] = countries
        cache['countries.metadata'] = countries.build_metadata(**kw)

        # Affiliations 
        affiliations = CSV()
        path = get_abspath(globals(), 'data/affiliations.csv')
        affiliations.load_state_from(path)
        cache['affiliations.csv'] = affiliations
        cache['affiliations.csv.metadata'] = affiliations.build_metadata()

        # Business Topics
        topics = CSV()
        path = get_abspath(globals(), 'data/topics.csv')
        topics.load_state_from(path)
        cache['topics.csv'] = topics
        cache['topics.csv.metadata'] = topics.build_metadata()

        # Business Types
        types = CSV()
        path = get_abspath(globals(), 'data/types.csv')
        types.load_state_from(path)
        cache['types.csv'] = types
        cache['types.csv.metadata'] = types.build_metadata()

        # User Job Functions
        functions = CSV()
        path = get_abspath(globals(), 'data/functions.csv')
        functions.load_state_from(path)
        cache['functions.csv'] = functions
        cache['functions.csv.metadata'] = functions.build_metadata()

        # Holiday Types
        holiday_types = CSV()
        path = get_abspath(globals(), 'data/holiday_types.csv')
        holiday_types.load_state_from(path)
        cache['holiday_types.csv'] = holiday_types
        cache['holiday_types.csv.metadata'] = holiday_types.build_metadata()

        # Holiday Activities
        holiday_activities = CSV()
        path = get_abspath(globals(), 'data/holiday_activities.csv')
        holiday_activities.load_state_from(path)
        cache['holiday_activities.csv'] = holiday_activities
        cache['holiday_activities.csv.metadata'] = holiday_activities.build_metadata()

        # Board Types
        board_types = CSV()
        path = get_abspath(globals(), 'data/board_types.csv')
        board_types.load_state_from(path)
        cache['board_types.csv'] = board_types
        cache['board_types.csv.metadata'] = board_types.build_metadata()

        # Rating Types
        rating_types = CSV()
        path = get_abspath(globals(), 'data/rating_types.csv')
        rating_types.load_state_from(path)
        cache['rating_types.csv'] = rating_types
        cache['rating_types.csv.metadata'] = rating_types.build_metadata()
        
        # Rating Types
        currency = CSV()
        path = get_abspath(globals(), 'data/currency.csv')
        currency.load_state_from(path)
        cache['currency.csv'] = currency
        cache['currency.csv.metadata'] = currency.build_metadata()

        # Expert Travel
        title = u'Expert Travel Website'
        expert_travel = ExpertTravel()
        kw = {'dc:title': {'en': title},
              'ikaaro:website_is_open': True}
        cache['expert'] = expert_travel
        cache['expert.metadata'] = expert_travel.build_metadata(**kw)

        # Destinations Guide
        title = u'Destinations Guide'
        destinations = Destinations()
        kw = {'dc:title': {'en': title},
              'ikaaro:website_is_open': True}
        cache['destinations'] = destinations
        cache['destinations.metadata'] = destinations.build_metadata(**kw)

        # Training
        title = u'Training Programmes'
        kw = {'dc:title': {'en': title}}
        training = Trainings()
        cache['training'] = training
        cache['training.metadata'] = training.build_metadata(**kw)

        # Help
        help = XHTMLFile()
        cache['help.xhtml'] = help
        cache['help.xhtml.metadata'] = help.build_metadata(
                        **{'dc:title': {'en': u'Help me'}})

    ########################################################################
    # Login
    login_form__access__ = True
    login_form__label__ = u'Login'
    def login_form(self, context):
        namespace = {}
        here = context.handler
        site_root = here.get_site_root()
        namespace['action'] = '%s/;login' % here.get_pathto(site_root)
        namespace['username'] = context.get_form_value('username')

        handler = self.get_handler('/ui/abakuc/login.xml')
        return stl(handler, namespace)

    #######################################################################
    # Select the skin
    #######################################################################
    def get_skin(self):
        hostname = get_context().uri.authority.host
        ui = self.get_handler('ui')

        # Production / Exact match
        if ui.has_handler(hostname):
            return ui.get_handler(hostname)

        # Production / Approx. match
        for name in ui.get_handler_names():
            if hostname.endswith(name):
                return ui.get_handler(name)

        # Development
        hostname = hostname.replace('_', '.')
        # root hostname points to uk.expert.travel
        if hostname == 'expert.travel':
            hostname = 'uk.expert.travel'
        if ui.has_handler(hostname):
            return ui.get_handler(hostname)
        for name in ui.get_handler_names():
            if hostname.endswith(name):
                return ui.get_handler(name)

        # XXX
        # I need to have 3 types of skins:
        # 1) company.expert.travel
        # 2) training.expert.travel
        # 3) destinations.info

        # Default
        return ui.get_handler('aruni')
        #return ui.get_handler('abakuc')


    def send_email(self, from_addr, to_addr, subject, body, **kw):
        # XXX While testing, uncomment the right line
        #to_addr = 'norman@khine.net'
        BaseRoot.send_email(self, from_addr, to_addr, subject, body, **kw)


    #######################################################################
    # API
    #######################################################################
    #def get_training(self):
    #    root = get_context().root
    #    handler = root.get_handler('training')
    #    training = list(handler.search_handlers(format=Training.class_id))
    #    training.sort(lambda x, y: cmp(get_sort_name(x.name),
    #                                 get_sort_name(y.name)))
    #    return training

    def get_affiliations_namespace(self, ids=None):
        affiliations = self.get_handler('affiliations.csv')
        namespace = []
        for row in affiliations.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_topics_namespace(self, ids=None):
        topics = self.get_handler('topics.csv')
        namespace = []
        for row in topics.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_types_namespace(self, ids=None):
        types = self.get_handler('types.csv')
        namespace = []
        for row in types.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_functions_namespace(self, ids=None):
        functions = self.get_handler('functions.csv')
        namespace = []
        for row in functions.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_airlines(self, airline=None):
        companies_handler = self.get_handler('companies')
        companies = companies_handler.search_handlers(handler_class=Company)
        airlines = []
        for item in companies:
            if item.has_property('abakuc:topic', 'airlines-scheduled'):
                airlines.append({
                    'id': item.name,
                    'title': item.get_title(),
                    'is_selected': (airline is not None) and (item.name in airline) })
        
        airlines.sort(key=lambda x: x['id'])
        return airlines

    def get_airports(self, airport=None):
        companies_handler = self.get_handler('companies')
        companies = companies_handler.search_handlers(handler_class=Company)
        airports = []
        for item in companies:
            if item.has_property('abakuc:topic', 'airports'):
                airports.append({
                    'id': item.name,
                    'title': item.get_title(),
                    'is_selected': (airport is not None) and (item.name in airport) })
        
        airports.sort(key=lambda x: x['id'])
        return airports

    def get_holiday_activities(self, ids=None):
        handler = self.get_handler('holiday_activities.csv')
        namespace = []
        for row in handler.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_holiday_types(self, ids=None):
        handler = self.get_handler('holiday_types.csv')
        namespace = []
        for row in handler.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_board_types(self, ids=None):
        handler = self.get_handler('board_types.csv')
        namespace = []
        for row in handler.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_rating_types(self, ids=None):
        handler = self.get_handler('rating_types.csv')
        namespace = []
        for row in handler.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace

    def get_currency(self, ids=None):
        handler = self.get_handler('currency.csv')
        namespace = []
        for row in handler.get_rows():
            namespace.append({
                'id': row[1], 'title': row[0], 'sign': row[2],
                'is_selected': (ids is not None) and (row[1] in ids)})

        return namespace
    def get_licences(self):
        path = get_abspath(globals(), 'data/abakuc_import_companies.csv')
        handler = get_handler(path)
        rows = handler.get_rows()
        rows = list(rows)
        namespace = []
        for count, row in enumerate(rows):
            affiliations = row[12]
            licences = re.split("\n+", affiliations)
            licence_list = [re.split("\((\w+)\)", licence) for licence in licences]
            for x in licence_list:
                for y in x:
                    if y.isupper():
                        namespace.append(y)

        return set(namespace)
        



    #######################################################################
    # User Interface / Import
    #######################################################################
    import_data_form__access__ = 'is_admin'
    import_data_form__label__ = u'Import'
    def import_data_form(self, context):
        handler = self.get_handler('ui/abakuc/import_data.xml')
        return stl(handler)


    import_data__access__ = 'is_admin'
    def import_data(self, context):
        ###################################################################
        # Import Companies
        multiple = ['uk-holiday-operators', 'flight-only-and-airline-consolidators',\
                    'on-line-bookable-tour-operators', 'tour-operators']
        independent = ['travel-agents', 'irish-travel-agents-and-organisers', \
                        'incoming-tour-operators', 'uk-holiday-operators', \
                        'on-line-bookable-travel-agents']
        call_center = ['reservation-offices', 'flight-only-and-airline-consolidators']

        # Read the input CSV file
        path = get_abspath(globals(), 'data/abakuc_import_companies.csv')
        handler = get_handler(path)
        rows = handler.get_rows()
        rows = list(rows)
        print len(rows)
        # We don't want the header
        #rows = rows[1:]
        #rows = rows[1:49]
        rows = rows[1:1550]
        #rows = rows[5500:5605]
        #rows = rows[1:13346]
        # Load handlers
        users = self.get_handler('users')
        companies = self.get_handler('companies')
        topics = self.get_handler('topics.csv')

        # Import from the CSV file
        good = 0
        for count, row in enumerate(rows):
            print count
            # User
            email = row[10]
            email = str(email).strip()
            if email:
                user = users.set_user(email)
                key = ''.join([ choice(ascii_letters) for x in range(30) ])
                user.set_property('ikaaro:user_must_confirm', key)
                user.set_property('abakuc:registration_date', datetime.date.today())
            else:
                user = None

            # Filter the UK Regions and Counties
            results = world.search(iana_root_zone='uk', region=str(row[2]),
                               county=str(row[3]))

            n_results = len(results)
            if n_results == 0:
                county = None
                msg = 'No county found for "%s", "%s"'
            elif n_results == 1:
                county = results[0]
                good += 1
            else:
                county = None
                msg = 'Several counties found for "%s", "%s" '

            # Add Company
            topic_id = str(row[0])
            company_title = row[5].strip()
            company_name = title_to_name(company_title)
            if not company_name:
                continue
            if companies.has_handler(company_name):
                company = companies.get_handler(company_name)
                # Update the topics
                topics = company.get_property('abakuc:topic')
                if topic_id not in topics:
                    topics += (topic_id,)
                    company.set_property('abakuc:topic', topics)
            else:
                company = Company()
                company, metadata = companies.set_object(company_name, company)
                metadata.set_property('dc:title', company_title, language='en')
                metadata.set_property('abakuc:website', str(row[11]))
                metadata.set_property('abakuc:topic', (topic_id,))
                if topic_id in independent:
                    type = 'independent'
                elif topic_id in multiple:
                    type = 'multiple' 
                elif topic_id in call_center:
                    type = 'call-center'
                else:
                    type = 'other'
                metadata.set_property('abakuc:type', 'other')
                metadata.set_property('ikaaro:website_is_open', True)
                # Need to split the licences into individual atoms
                #metadata.set_property('abakuc:licence', row[12])
                #licences = re.split("\n+", row[12])
                #licenceRe = re.compile(r'\(([A-Z]+)\)( No. (\d+))?')
                #my_list = []
                #affiliations = {}
                #for licence in licences:
                #    m = licenceRe.search(licence)
                #    if m:
                #        my_list.append(str(m.group(1)))
                #        if m.group(3) is None:
                #        #    affiliations[m.group(1)] = 'not available'
                #            aff_row = [m.group(1), m.group(3)]
                #        else:
                #            aff_row = [m.group(1), 'none']
                #        #    affiliations[m.group(1)] = m.group(3)
                #        # Storing the affilation data inside a CSV file in the company
                #        # folder
                #        handler = company.get_handler('affiliation.csv')
                #        print handler
                #        handler.add_row(aff_row)
                #        #affiliation = metadata.get_property('abakuc:licence')
                #        #if affiliation:
                #        #    if str(m.group(1) not in affiliation:
                #        #        affiliation += (str(m.group(1)),)
                #        #        metadata.set_property('abakuc:licence', (str(m.group(1)),))
                #    #metadata.set_property('abakuc:licence', (str(my_list),))
                #    #else:
                #    #    metadata.set_property('abakuc:licence', row[12])
                #print affiliations
                # convert to string
                #affiliation = str(my_list).lower().strip().replace('[', '').replace(']', '').replace('\'', '')
                # use pickle function and store the dictionary
                #affiliation = pickle.dumps(affiliations)
                #metadata.set_property('abakuc:licence', affiliation)
                metadata.set_property('abakuc:licence', row[12])
                metadata.set_property('abakuc:type', type)
            # Add Address
            address_title = row[6].strip()
            address_name = title_to_name(address_title)
            if not address_name:
                continue
            if company.has_handler(address_name):
                print address_name
            else:
                address, metadata = company.set_object(address_name, Address())
                address.set_property('abakuc:address', address_title)
                postcode = row[7]
                if postcode:
                    address.set_property('abakuc:postcode', str(postcode.upper()))
                if county:
                    address.set_property('abakuc:county', row[3])
                    address.set_property('abakuc:town', row[4])
                address.set_property('abakuc:phone', str(row[8]))
                address.set_property('abakuc:fax', str(row[9]))
                licences = re.split("\n+", row[12])
                licenceRe = re.compile(r'\(([A-Z]+)\)( No. (\w+))?')
                for licence in licences:
                    m = licenceRe.search(licence)
                    if m:
                        print m.group(3)
                        if m.group(3) is not None:
                            aff_row = [m.group(1), m.group(3)]
                        else:
                            aff_row = [m.group(1), 'none']
                        # Storing the affilation data inside a CSV file in the company
                        # folder
                        handler = address.get_handler('affiliation.csv')
                        handler.add_row(aff_row)
                if user is not None:
                    address.set_user_role(user.name, 'abakuc:branch_manager')

        message = ('Remember to reindex the database now:'
                   ' <a href=";catalog_form">reindex</a>.')
        return message


    import_affiliation__access__ = 'is_admin'
    def import_affiliation(self, context):
        ###################################################################
        # Import affiliations 
        
        companies = self.get_handler('companies')
        # Read the input CSV file
        path = get_abspath(globals(), 'data/abakuc_import_companies.csv')
        handler = get_handler(path)
        rows = handler.get_rows()
        rows = list(rows)

        namespace = []
        affiliation = []
        dic = {}
        for count, row in enumerate(rows):
            affiliations = row[12]
            licences = re.split("\n+", affiliations)
            #licence_list = [re.split("\((\w+)\)", licence) for licence in licences]
            # get the affiliation.csv file
            licenceRe = re.compile(r'([^(]+)\(([A-Z]+)\)( No. (\w+))?')
            for licence in licences:
                m = licenceRe.search(licence)
                if m:
                    print m.group(1), m.group(2), m.group(3)
                    aff_row = [m.group(2), m.group(1)]
                    handler = self.get_handler('affiliations.csv')
                    handler.add_row(aff_row)

        message = ('Remember to reindex the database now:'
                   ' <a href=";catalog_form">reindex</a>.')
        return message


    #######################################################################
    # API for Website identification
    #######################################################################
    def is_training(self):
        '''Return a bool'''
        training = self.get_site_root()
        if isinstance(training, Training):
            training = True
        else:
            training = False
        return training

    def get_authorized_countries(self, context):
        """
        An expert.travel has 3 configuration :
        1/ Company view in a Country website
            http://fr.expert.travel/companies/abakuc
        2/ Company website
            http://abakuc.expert.travel/
        3/ Country website
            http://fr.expert.travel/
        """
        root = context.handler.get_site_root()
        country_code = get_host_prefix(context)
        country_codes = self.list_country_codes()
        if country_code in country_codes:
            # Rule for address as: http://fr.expert.travel/
            country_name = self.get_country_name(country_code)
            return [(country_name, country_code)]
        return self.get_active_countries(context)

    def get_authorized_country(self, context):
        """
        Used in skins.py to search for companies
        only for the specific country.
        We need to extend this so that it does not rely on the URI
        to get the origin of the user.
        Perhaps we should look at where they have logged in from.
        For now all TP's must have the country code in their URI
        i.e. http://uk.tp1.expert.travel etc...
        """
        root = context.handler.get_site_root()
        country_code = get_host_prefix(context)
        if country_code is not None:
            if not isinstance(root, Company):
                # Rule for address as: http://fr.expert.travel/
                country_name = self.get_country_name(country_code)
                return [(country_name, country_code)]
            return self.get_active_countries(context)
        return [(country_name, country_code)]

    def get_active_countries(self, context):
        """
        Return a list with actives countries and it's code as:
        [('United Kingdom', 'uk'), ('France', 'fr')]
        """
        rows = world.get_rows()
        list_countries = set()
        # List countries and its regions
        for row in rows:
            country = row.get_value('country')
            iana_root_zone = row.get_value('iana_root_zone')
            region = row.get_value('region')
            if region and (region!=u'none'):
                list_countries.add((country, iana_root_zone))
        # Return the list of iana_root_zone
        sorted_countries = sorted(list_countries)
        return sorted_countries

    def get_regions(self, country=None, selected_region=None):
        """
        Return a list of regions:
        [('United Kingdom', 'uk'), ('France', 'fr')]
        """
        from root import world
        regions = []
        #rows = world.get_rows()
        row = world.get_row(results[2])
        for row in rows:
            region = row[7]
            if region not in regions:
                regions.append(region)
        regions = [{'id': x,
                    'title': x,
                    'selected': x==selected_region} for x in regions]
        regions.sort(key=lambda x: x['title'])
        return regions

    def list_country_codes(self):
        return world.get_unique_values('iana_root_zone')


    def get_country_name(self, country_code):
        results = world.search(iana_root_zone=country_code)
        if results:
            row = world.get_row(results[0])
            return row.get_value('country')
        return None


    def get_website_country(self, context):
        host_prefix = get_host_prefix(context)
        for active_country in self.get_active_countries(context):
            country_name, country_code = active_country
            if host_prefix==country_code:
                return host_prefix
        return None

    def get_site_types(self, context):
        """
        Each portal has its own list of Business Types
        1/ Expert.Travel deals with Travel Agencies
        2/ Destinations Guide are Hotels etc...
        """
        root = context.handler.get_site_root()

        return self.get_site_types(context)
    ##########################################################################
    # Javascript
    ##########################################################################
    get_regions_str__access__ = True
    def get_regions_str(self, context):
        response = context.response
        response.set_header('Content-Type', 'text/plain')
        #country_code = get_host_prefix(context)
        country_code = context.get_form_value('country_code', type=Unicode)
        selected_region = context.get_form_value('selected_region', type=Unicode)
        data = self.get_regions_stl(country_code, selected_region)
        return data

    def get_regions_stl(self, country_code=None, selected_region=None):
        # Get data
        rows = world.get_rows()
        regions = []
        for row in rows:
            if country_code == row[5]:
                region = row[7]
                if region not in regions:
                    regions.append(region)
        regions = [{'name': x,
                    'title': x,
                    'selected': x==selected_region} for x in regions]
        regions.sort(key=lambda x: x['title'])
        # Build stl
        namespace = {}
        namespace['region'] = regions
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
        <div id="div_regions">
          <select id="region" name="region"
              onchange="javascript: get_regions('/;get_counties_str?region='+ this.value, 'div_county')">
              <option value=""></option>
              <option stl:repeat="region region" value="${region/name}"
                      selected="${region/selected}">
              ${region/title}
              </option>
          </select>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)

    #def get_regions(self, country=None, selected_region=None):
    #    # Get data
    #    rows = world.get_rows()
    #    regions = []
    #    for row in rows:
    #        if country == row[6]:
    #            region = row[7]
    #            if region not in regions:
    #                regions.append(region)

    #    regions = [{'name': x,
    #                'title': x,
    #                'selected': x==selected_region} for x in regions]
    #    regions.sort(key=lambda x: x['title'])

    #    return regions

    get_counties_str__access__ = True
    def get_counties_str(self, context):
        response = context.response
        response.set_header('Content-Type', 'text/plain')
        region = context.get_form_value('region', type=Unicode)
        selected_county = context.get_form_value('selected_county', type=Unicode)
        return self.get_counties_stl(region, selected_county)


    def get_counties_stl(self, region=None, selected_county=None):
        # Get data
        rows = world.get_rows()
        counties = []
        for index, row in enumerate(rows):
            if (region == row[7]):
                county = row[8]
                counties.append({'name': county,
                                 'title': county,
                                 'selected': selected_county==county})
        counties.sort(key=lambda x: x['title'])
        # Build stl
        namespace = {}
        namespace['counties'] = counties
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
        <div id="div_county">
          <select id="county" name="abakuc:county">
              <option stl:repeat="county counties" value="${county/name}"
                      selected="${county/selected}">
              ${county/title}
              </option>
          </select>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


register_object_class(Root)
