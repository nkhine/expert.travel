# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the future
from __future__ import with_statement

# Import from the Standard Library
from random import choice
from string import ascii_letters

# Import from itools
from itools import get_abspath
from itools.datatypes import String
from itools.handlers import get_handler
from itools.stl import stl
from itools.web import get_context
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class
from itools.cms.root import Root as BaseRoot
from itools.cms.html import XHTMLFile

# Import from our package
from adverts import Adverts
#from banners import Banners
#from company import Companies
#from countries import Countries
from base import Handler
from companies import Companies, Company, Address
from handlers import EnquiriesLog
from uktravel import UKTravel
#from videos import Videos 
from users import UserFolder
from destinations import Destinations



def title_to_name(title):
    title = title.encode('ascii', 'replace')
    name = title.lower().replace('/', '_').replace('?', '_')
    return '_'.join(name.split())


class Regions(Handler, CSV):

    class_id = 'regions'
    class_title = u'Regions'

    columns = ['country', 'region', 'county']
    schema = {'country': String(index='keyword'),
              'region': String(index='keyword'),
              'county': String(index='keyword')}


register_object_class(Regions)




class Root(Handler, BaseRoot):

    class_id = 'abakuc'
    class_title = u'Abakuc'
    class_version = '20070218'
    class_domain = 'abakuc'
    class_description = (u'One back-office to bring them all and in the'
                         u' darkness bind them.')

    class_views = [['view']] + BaseRoot.class_views + [['import_data_form']]


    #######################################################################
    # Index & Search
    _catalog_fields = BaseRoot._catalog_fields + [
            ('topic', 'keyword', True, False),
            ('region', 'keyword', True, False),
            ('county', 'keyword', True, False),
            ('town', 'keyword', True, True)]


    #######################################################################
    # New
    def new(self, username=None, password=None):
        BaseRoot.new(self, username=username, password=password)
        cache = self.cache

        # Companies
        companies = Companies()
        cache['companies'] = companies
        cache['companies.metadata'] = self.build_metadata(companies)

        # Regions
        regions = Regions()
        path = get_abspath(globals(), 'data/csv/counties.csv')
        regions.load_state_from(path)
        cache['regions.csv'] = regions
        cache['regions.csv.metadata'] = self.build_metadata(regions)

        # Topics
        topics = CSV()
        path = get_abspath(globals(), 'data/csv/topics.csv')
        topics.load_state_from(path)
        cache['topics.csv'] = topics
        cache['topics.csv.metadata'] = self.build_metadata(topics)

        # UK Travel List
        title = u'UK Travel List'
        uktravel = UKTravel()
        kw = {'dc:title': {'en': title},
              'ikaaro:website_is_open': True}
        cache['uktravel'] = uktravel
        cache['uktravel.metadata'] = self.build_metadata(uktravel, **kw)

        # Destinations Guide 
        title = u'Destinations Guide'
        destinations = Destinations()
        kw = {'dc:title': {'en': title},
              'ikaaro:website_is_open': True}
        cache['destinations'] = destinations
        cache['destinations.metadata'] = self.build_metadata(destinations, **kw)


        help = XHTMLFile()
        cache['help.xhtml'] = help
        cache['help.xhtml.metadata'] = self.build_metadata(help,
                                            **{'dc:title': {'en': u'Help me'}})

        # Adverts 
##        adverts = Adverts()
##        self.cache['adverts'] = adverts
##        self.cache['adverts.metadata'] = self.build_metadata(adverts,
##                                          **{'dc:title': {'en': u'Adverts'}})
        # Banners
##        banners = Banners()
##        self.cache['banners'] = banners
##        self.cache['banners.metadata'] = self.build_metadata(banners,
##                                          **{'dc:title': {'en': u'Banners'}})
        # Countries
##        countries = Countries()
##        self.cache['countries'] = countries
##        self.cache['countries.metadata'] = self.build_metadata(countries,
##                                          **{'dc:title': {'en': u'Countries'}})

        # Videos 
##        videos = Videos()
##        self.cache['videos'] = videos
##        self.cache['videos.metadata'] = self.build_metadata(videos,
##                                          **{'dc:title': {'en': u'Videos'}})


    #######################################################################
    # XXX
    def get_skin(self):
        """Set the default skin"""
        context = get_context()
        hostname = context.uri.authority.host

        # XXX For testing purposes
        if hostname == 'uktravel':
            return self.get_handler('ui/uktravel')

        # XXX For testing purposes
        elif hostname == 'destinations':
            return self.get_handler('ui/destinations')


        # return the default skin
        return self.get_handler('ui/aruni')


    #######################################################################
    # API / Topics
    #######################################################################
    def get_topic_title(self, id):
        topics = self.get_handler('topics.csv')
        for row in topics.get_rows():
            if id == row[0]:
                return row[1]

        raise KeyError


    def get_topics_namespace(self, ids=None):
        topics = self.get_handler('topics.csv')
        namespace = []
        for row in topics.get_rows():
            namespace.append({'id': row[0], 'title': row[1],
                              'is_selected': row[0] in ids})

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
        # Read the input CSV file
        path = get_abspath(globals(), 'data/csv/abakuc_import_companies.csv')
        handler = get_handler(path)
        rows = handler.get_rows()
        rows = list(rows)
        rows = rows[1:1000]

        # Load handlers
        users = self.get_handler('users')
        companies = self.get_handler('companies')
        regions = self.get_handler('regions.csv')
        topics = self.get_handler('topics.csv')

        # Import from the CSV file
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

            # Regions
            results = regions.search(country='gb', region=str(row[2]),
                                     county=str(row[3]))
            n_results = len(results)
            if n_results == 0:
                county = None
                msg = 'No county found for "%s", "%s"'
                print count, msg % (row[2], row[3])
            elif n_results == 1:
                county = results[0]
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
            print company_name
            if companies.has_handler(company_name):
                company = companies.get_handler(company_name)
                # Update the topics
                topics = company.get_property('abakuc:topic')
                if topic_id not in topics:
                    topics += (topic_id,)
                    company.set_property('abakuc:topic', topics)
            else:
                company = companies.set_handler(company_name, Company())
                company.set_property('dc:title', company_title, language='en')
                company.set_property('abakuc:website', str(row[11]))
                company.set_property('abakuc:topic', (topic_id,))

            # Add Address
            address_title = row[6].strip()
            address_name = title_to_name(address_title)
            if not address_name:
                continue
            print address_name
            if company.has_handler(address_name):
                print 'Warning'
            else:
                address = company.set_handler(address_name, Address())
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
                    address.set_user_role(user.name, 'ikaaro:members')

        return 'OK'


register_object_class(Root)
