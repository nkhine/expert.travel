# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.WebSite import WebSite
from itools.cms.html import XHTMLFile
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler


class Destinations(Handler, WebSite):
 
      class_id = 'destinations'
      class_title = u'Destinations Guide'

      def new(self, **kw):
          WebSite.new(self, **kw)
          cache = self.cache
          # Add extra handlers here 
          home = XHTMLFile()
          cache['home.xhtml'] = home 
          cache['home.xhtml.metadata'] = self.build_metadata(home,
                                              **{'dc:title': {'en': u'Welcome to the Destinations Guide'}})


      #######################################################################
      # User Interface
      #######################################################################
      view__access__ = 'is_allowed_to_view'
      view__label__ = u'View'
      def view(self, context):
          handler = self.get_handler('home.xhtml')
          return stl(handler)

register_object_class(Destinations)

