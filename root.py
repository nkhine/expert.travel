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
from uktravel import UKTravel
#from videos import Videos 
from users import UserFolder
from destinations import Destinations



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
    class_views = [['view']] + BaseRoot.class_views


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

        # Import from the CSV file
        users = cache['users']
        path = get_abspath(globals(), 'data/csv/abakuc_import_companies.csv')
        handler = get_handler(path)
        company_index = 0
        company_map = {}
        topics = {}
        rows = handler.get_rows()
        rows = list(rows)
        rows = rows[1:1000]
        for count, row in enumerate(rows):
            # User
            email = row[10]
            email = str(email).strip()
            if email:
                user = users.set_user(email)
                key = ''.join([ choice(ascii_letters) for x in range(30) ])
                user.set_property('ikaaro:user_must_confirm', key)

            # Topics
            topic_id = str(row[0])
            topics.setdefault(topic_id, row[1])
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
 
            # Company
            company_title = row[5].strip()
            if company_title in company_map:
                company_id, address_index = company_map[company_title]
                company = companies.cache[company_id]
            else:
                company_id = str(company_index)
                address_index = 0
                company_map[company_title] = company_id, address_index
                company_index += 1
                # Add to the database
                company = Company()
                companies.cache[company_id] = company
                kw = {}
                kw['dc:title'] = {'en': company_title}
                kw['abakuc:website'] = str(row[11])
                kw['abakuc:topic'] = topic_id
                metadata = companies.build_metadata(company, **kw)
                companies.cache['%s.metadata' % company_id] = metadata

            # Address
            address_id = str(address_index)
            # Add to the database
            address = Address()
            company.cache[address_id] = address
            kw = {}
            kw['abakuc:address'] = row[6]
            postcode = row[7]
            if postcode:
                kw['abakuc:postcode'] = str(postcode)
            if county:
                kw['abakuc:county'] = county
                kw['abakuc:town'] = row[4]
            kw['abakuc:phone'] = str(row[8])
            kw['abakuc:fax'] = str(row[9])
            ##kw['abakuc:license'] = row[]
            metadata = company.build_metadata(address, **kw)
            company.cache['%s.metadata' % address_id] = metadata

        # Topics
        csv = CSV()
        for id, title in topics.items():
            id = unicode(id)
            csv.add_row([id, title])
        cache['topics.csv'] = csv
        cache['topics.csv.metadata'] = self.build_metadata(csv)

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


    def get_topics_namespace(self, id=None):
        topics = self.get_handler('topics.csv')
        namespace = []
        for row in topics.get_rows():
            namespace.append({'id': row[0], 'title': row[1],
                              'is_selected': row[0] == id})

        return namespace



register_object_class(Root)
