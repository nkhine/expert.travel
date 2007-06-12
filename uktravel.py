# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.stl import stl
from itools.cms.registry import register_object_class
from itools.cms.html import XHTMLFile

# Import from abakuc
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
        cache['news.xhtml.metadata'] = news.build_metadata(
            **{'dc:title': {'en': u'News Folder List'}})
        events = XHTMLFile()
        cache['events.xhtml'] = events
        cache['events.xhtml.metadata'] = events.build_metadata(
            **{'dc:title': {'en': u'Events'}})
        faq = XHTMLFile()
        cache['faq.xhtml'] = faq
        cache['faq.xhtml.metadata'] = faq.build_metadata(
            **{'dc:title': {'en': u'FAQs'}})
        help = XHTMLFile()
        cache['help.xhtml'] = help
        cache['help.xhtml.metadata'] = help.build_metadata(
            **{'dc:title': {'en': u'Help'}})


    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        elif name == 'jobs':
            return self.get_handler('/jobs')
        return WebSite._get_virtual_handler(self, segment)


    #######################################################################
    # User Interface / Navigation
    #######################################################################
    site_format = 'address'


    def get_level1_title(self, level1):
        topics = self.get_handler('../topics.csv')
        for row in topics.get_rows():
            if level1 == row[0]:
                return row[1]

        raise KeyError




register_object_class(UKTravel)

