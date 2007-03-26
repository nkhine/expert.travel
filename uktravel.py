# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath
from itools.datatypes import Integer
from itools.handlers import get_handler
from itools.stl import stl
from itools.cms.csv import CSV
from itools.cms.WebSite import WebSite
from itools.cms import widgets
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler
from companies import Companies



class UKTravel(Handler, WebSite):
 
    class_id = 'uktravel'
    class_title = u'UK Travel List'


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
        text = context.get_form_value('search_text')

        # The namespace
        namespace = {}
        namespace['title'] = None
        namespace['regions'] = []

        # Topic
        if topic is not None:
            namespace['title'] = root.get_topic_title(topic)
            # Regions
            regions = []
            csv = root.get_handler('regions.csv')
            uri = context.uri
            for region_id, region_title in csv.get_rows():
                regions.append({'href': uri.replace(region=region_id),
                                'title': region_title})
            namespace['regions'] = regions

        # Build the query
        query = {'format': 'address'}
        if topic is not None:
            query['topic'] = topic
        if region is not None:
            query['region'] = region
        if text:
            query['title'] = text

        # Search
        results = root.search(**query)

        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 5
        total = results.get_n_documents()
        namespace['batch'] = widgets.batch(context.uri, start, size, total)

        # Search
        regions = root.get_handler('regions.csv')
        companies = root.get_handler('companies')
        addresses = []
        documents = results.get_documents(sort_by='title')
        for address in documents[start:start+size]:
            address = root.get_handler(address.abspath)
            get_property = address.metadata.get_property
            company = address.parent
            region_id = get_property('abakuc:region')
            region_id = int(region_id)
            region = regions.get_row(region_id)[1]
            addresses.append(
                {'href': '%s/;view' % self.get_pathto(address),
                 'title': company.title,
                 'town': get_property('abakuc:town'),
                 'address': get_property('abakuc:address'),
                 'postcode': get_property('abakuc:postcode'),
                 'county': get_property('abakuc:county'),
                 'region': region,
                 'phone': get_property('abakuc:phone'),
                 'fax': get_property('abakuc:fax'),
                 })
        namespace['companies'] = addresses

        handler = self.get_handler('ui/abakuc/search.xml')
        return stl(handler, namespace)



register_object_class(UKTravel)

