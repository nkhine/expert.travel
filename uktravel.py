# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath
from itools.datatypes import Integer
from itools.handlers import get_handler
from itools.stl import stl
from itools.cms.csv import CSV
from itools.cms import widgets
from itools.cms.registry import register_object_class
from itools.cms.html import XHTMLFile

# Import from abakuc
from companies import Companies
from website import WebSite



class UKTravel(WebSite):
 
    class_id = 'uktravel'
    class_title = u'UK Travel List'
    class_icon48 = 'abakuc/images/Import48.png'
    class_icon16 = 'abakuc/images/Import16.png'

    def new(self, **kw):
        WebSite.new(self, **kw)
        cache = self.cache
        # Add extra handlers here 
        news = XHTMLFile()
        cache['news.xhtml'] = news 
        cache['news.xhtml.metadata'] = self.build_metadata(news,
            **{'dc:title': {'en': u'News Folder List'}})
        jobs = XHTMLFile()
        cache['jobs.xhtml'] = jobs 
        cache['jobs.xhtml.metadata'] = self.build_metadata(jobs,
            **{'dc:title': {'en': u'Job Board'}})
        events = XHTMLFile()
        cache['events.xhtml'] = events
        cache['events.xhtml.metadata'] = self.build_metadata(events,
            **{'dc:title': {'en': u'Events'}})
        faq = XHTMLFile()
        cache['faq.xhtml'] = faq 
        cache['faq.xhtml.metadata'] = self.build_metadata(faq,
            **{'dc:title': {'en': u'FAQs'}})
        help = XHTMLFile()
        cache['help.xhtml'] = help
        cache['help.xhtml.metadata'] = self.build_metadata(help,
            **{'dc:title': {'en': u'Help'}})


    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        return WebSite._get_virtual_handler(self, segment)


    #######################################################################
    # User Interface
    #######################################################################
    search__access__ = True
    def search(self, context):
        root = context.root

        topic = context.get_form_value('topic')
        region = context.get_form_value('region')
        county = context.get_form_value('county')
        town = context.get_form_value('town')
        text = context.get_form_value('search_text')

        # Build the query
        query = {'format': 'address'}
        if topic is not None:
            query['topic'] = topic
        if region is not None:
            query['region'] = region
        if county is not None:
            query['county'] = county
        if town is not None:
            query['town'] = town
        if text:
            query['title'] = text

        # The namespace
        namespace = {}
        namespace['title'] = None
        namespace['regions'] = []

        # Topic
        csv = root.get_handler('regions.csv')
        if topic is not None:
            base = context.uri
            namespace['title'] = root.get_topic_title(topic)
            regions = []
            if region is None:
                # Regions
                for region in csv.get_unique_values('region'):
                    q = query.copy()
                    q['region'] = region
                    if root.search(**q).get_n_documents():
                        uri = base.replace(region=region, batchstart=None)
                        regions.append({'href': uri, 'title': region})
            elif county is None:
                # Counties
                for n in csv.search(region=region):
                    county_id = str(n)
                    q = query.copy()
                    q['county'] = county_id
                    if root.search(**q).get_n_documents():
                        row = csv.get_row(n)
                        county = row[2]
                        uri = base.replace(county=county_id, batchstart=None)
                        regions.append({'href': uri, 'title': county})
            else:
                # Towns
                results = root.search(region=region, county=county)
                towns = [ x.town for x in results.get_documents() ]
                towns = list(set(towns))
                towns.sort()
                for town in towns:
                    q = query.copy()
                    q['town'] = town
                    if root.search(**q).get_n_documents():
                        uri = base.replace(town=town, batchstart=None)
                        regions.append({'href': uri, 'title': town})
            regions.sort(key=lambda x: x['title'])
            namespace['regions'] = regions

        # Search
        results = root.search(**query)

        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 5
        total = results.get_n_documents()
        namespace['batch'] = widgets.batch(context.uri, start, size, total)

        # Search
        companies = root.get_handler('companies')
        addresses = []
        documents = results.get_documents(sort_by='title')
        for address in documents[start:start+size]:
            address = root.get_handler(address.abspath)
            get_property = address.metadata.get_property
            company = address.parent
            county_id = get_property('abakuc:county')
            if county_id is None:
                # XXX Every address should have a county
                region = ''
                county = ''
            else:
                row = csv.get_row(county_id)
                country, region, county = row
            addresses.append(
                {'href': '%s/;view' % self.get_pathto(address),
                 'title': company.title,
                 'town': get_property('abakuc:town'),
                 'address': get_property('abakuc:address'),
                 'postcode': get_property('abakuc:postcode'),
                 'county': county,
                 'region': region,
                 'phone': get_property('abakuc:phone'),
                 'fax': get_property('abakuc:fax'),
                 })
        namespace['companies'] = addresses

        handler = self.get_handler('ui/abakuc/search.xml')
        return stl(handler, namespace)



register_object_class(UKTravel)

