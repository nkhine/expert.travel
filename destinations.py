# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.registry import register_object_class
from itools.datatypes import Integer
from itools.cms import widgets
from itools.stl import stl

# Import from abakuc
from countries import Countries
from website import WebSite


class Destinations(WebSite):
 
      class_id = 'destinations'
      class_title = u'Destinations Guide'
      class_icon16 = 'abakuc/images/Resources16.png'
      class_icon48 = 'abakuc/images/Resources48.png'

      def _get_virtual_handler(self, segment):
          name = segment.name
          if name == 'countries':
              return self.get_handler('/countries')
          return WebSite._get_virtual_handler(self, segment)


      #######################################################################
      # User Interface
      #######################################################################
      search__access__ = True
      def search(self, context):
          root = context.root

          continent = context.get_form_value('continent')
          sub_continent = context.get_form_value('sub_continent')
          text = context.get_form_value('search_text')

          # Build the query
          query = {'format': 'country'}
          if continent is not None:
              query['continent'] = continent
          if sub_continent is not None:
              query['sub_continent'] = sub_continent
          if text:
              query['title'] = text


          # The namespace
          namespace = {}
          namespace['title'] = None
          namespace['continent'] = [] 
          namespace['sub_continent'] = []
          namespace['country'] = [] 

          # Search
          # Continent
          results = root.search(**query)

          # Batch
          start = context.get_form_value('batchstart', type=Integer, default=0)
          size = 5
          total = results.get_n_documents()
          namespace['batch'] = widgets.batch(context.uri, start, size, total)

          # Search
          countries = root.get_handler('countries')
          documents = results.get_documents(sort_by='title')
          for country in documents[start:start+size]:
              country = root.get_handler(country.abspath)
              get_property = country.metadata.get_property
              continent = get_property('abakuc:continent')

          namespace['country'] = countries

          handler = self.get_handler('ui/abakuc/countries.xml')
          return stl(handler, namespace)

register_object_class(Destinations)

