# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the future
from __future__ import with_statement

# Import from the Standard Library
from random import choice
from string import ascii_letters

# Import from itools
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
from itools.catalog import  KeywordField, IntegerField

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


path = get_abspath(globals(), 'data/countries_full.csv')
world = World(path)

class Root(Handler, BaseRoot):

    class_id = 'abakuc'
    class_title = u'Abakuc'
    class_version = '20070218'
    class_domain = 'abakuc'
    class_description = (u'One back-office to bring them all and in the'
                         u' darkness bind them.')

    class_views = [['view']] + BaseRoot.class_views + [['import_data_form']]
    site_format =''
    #######################################################################
    # Administrator Email
    contact_email = 'norman@khine.net'
    
    #######################################################################
    # Index & Search
    _catalog_fields = BaseRoot._catalog_fields + [
            KeywordField('level0', is_stored=True),
            KeywordField('level1', is_stored=True),
            KeywordField('level2', is_stored=True),
            KeywordField('level3', is_stored=True),
            KeywordField('level4', is_stored=True),
            KeywordField('user_id', is_stored=False),
            KeywordField('closing_date', is_stored=False),
            KeywordField('company', is_stored=False),
            KeywordField('address', is_stored=False),
            KeywordField('function', is_stored=False),
            KeywordField('salary', is_stored=False),
            KeywordField('description', is_stored=False)]


    #######################################################################
    # New
    def new(self, username=None, password=None):
        BaseRoot.new(self, username=username, password=password)
        cache = self.cache
        
        # Companies
        title = u'Companies Directory'
        kw = {'dc:title': {'en': title}}
        companies = Companies()
        cache['companies'] = companies
        cache['companies.metadata'] = companies.build_metadata(**kw)

        # Countries
        title = u'Countries'
        kw = {'dc:title': {'en': title}}
        countries = Countries()
        cache['countries'] = countries
        cache['countries.metadata'] = countries.build_metadata(**kw)

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
        if ui.has_handler(hostname):
            return ui.get_handler(hostname)
        for name in ui.get_handler_names():
            if hostname.endswith(name):
                return ui.get_handler(name)

        # Default
        return ui.get_handler('aruni')
        #return ui.get_handler('uk.expert.travel')


    def send_email(self, from_addr, to_addr, subject, body, **kw):
        # XXX While testing, uncomment the right line
        to_addr = 'norman@khine.net'
        BaseRoot.send_email(self, from_addr, to_addr, subject, body, **kw)


    #######################################################################
    # API
    #######################################################################
    def get_training(self):
        root = get_context().root
        handler = root.get_handler('training')
        training = list(handler.search_handlers(format=Training.class_id))
        training.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return training

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
        job_functions = self.get_handler('functions.csv')
        namespace = []
        for row in job_functions.get_rows():
            namespace.append({
                'id': row[0], 'title': row[1],
                'is_selected': (ids is not None) and (row[0] in ids)})

        return namespace
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

        # Read the input CSV file
        path = get_abspath(globals(), 'data/abakuc_import_companies.csv')
        handler = get_handler(path)
        rows = handler.get_rows()
        rows = list(rows)
        rows = rows[1:100]

        # Load handlers
        users = self.get_handler('users')
        companies = self.get_handler('companies')
        topics = self.get_handler('topics.csv')

        # Import from the CSV file
        good = 0
        for count, row in enumerate(rows):
            # User
            email = row[10]
            email = str(email).strip()
            if email:
                user = users.set_user(email)
                key = ''.join([ choice(ascii_letters) for x in range(30) ])
                user.set_property('ikaaro:user_must_confirm', key)
            else:
                user = None

            # Filter the UK Regions and Counties
            results = world.search(iana_root_zone='uk', region=str(row[2]),
                               county=str(row[3]))

            n_results = len(results)
            if n_results == 0:
                county = None
                msg = 'No county found for "%s", "%s"'
                print count, msg % (row[2], row[3])
            elif n_results == 1:
                county = results[0]
                good += 1
            else:
                county = None
                msg = 'Several counties found for "%s", "%s" '
                print count, msg % (row[2], row[3])
 
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
                metadata.set_property('ikaaro:website_is_open', True)
            # Add Address
            address_title = row[6].strip()
            address_name = title_to_name(address_title)
            if not address_name:
                continue
            if company.has_handler(address_name):
                print 'Warning'
            else:
                address, metadata = company.set_object(address_name, Address())
                address.set_property('abakuc:address', address_title)
                postcode = row[7]
                if postcode:
                    address.set_property('abakuc:postcode', str(postcode))
                if county:
                    address.set_property('abakuc:county', county)
                    address.set_property('abakuc:town', row[4])
                address.set_property('abakuc:phone', str(row[8]))
                address.set_property('abakuc:fax', str(row[9]))
                ##address.set_property('abakuc:license', row[])
                if user is not None:
                    address.set_user_role(user.name, 'ikaaro:reviewers')

        print '%s/%s' % (good, count)
        message = ('Remember to reindex the database now:'
                   ' <a href=";catalog_form">reindex</a>.')
        return message


    #######################################################################
    # API for Website identification
    #######################################################################
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
        return list_countries


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
        if not isinstance(root, Company):
            country_code = get_host_prefix(context)
            if country_code is not None:
                # Rule for address as: http://fr.expert.travel/
                country_name = self.get_country_name(country_code)
                return [(country_name, country_code)]

        return self.get_active_countries(context)


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
        country = context.get_form_value('country', type=Unicode)
        selected_region = context.get_form_value('selected_region', type=Unicode)
        data = self.get_regions_stl(country, selected_region)
        return data


    def get_regions_stl(self, country=None, selected_region=None): 
        # Get data
        rows = world.get_rows()
        regions = []
        for row in rows:
            if country == row[6]:
                region = row[7]
                if region not in regions:
                    regions.append(region)

        regions = [{'name': x,
                    'title': x,
                    'selected': x==selected_region} for x in regions]
        regions.sort(key=lambda x: x['title'])
        # Build stl
        namespace = {}
        namespace['regions'] = regions
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
        <div id="div_regions">
          <select id="regions" name="regions"
              onchange="javascript: get_regions('/;get_counties_str?region='+ this.value, 'div_county')">
              <option value=""></option>
              <option stl:repeat="region regions" value="${region/name}"
                      selected="${region/selected}">
              ${region/title}
              </option>
          </select>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace) 


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
                counties.append({'name': index,
                                 'title': county,
                                 'selected': selected_county==index})
        counties.sort(key=lambda x: x['title'])
        # Build stl
        namespace = {}
        namespace['counties'] = counties
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
        <div id="div_county">
          <select id="abakuc:county" name="abakuc:county">
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
