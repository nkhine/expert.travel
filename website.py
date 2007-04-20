# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.stl import stl
from itools.cms.WebSite import WebSite as BaseWebSite

# Import from abakuc
from base import Handler



class WebSite(Handler, BaseWebSite):
 
    def GET(self, context):
        return context.uri.resolve2(';view')


    view__access__ = True
    def view(self, context):
        handler = self.get_handler('/ui/%s/home.xhtml' % self.name)
        return stl(handler)

