# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.registry import register_object_class
from itools.stl import stl

# Import from abakuc
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
    # User Interface / Navigation
    #######################################################################
    site_format = 'country'

    def get_level1_title(self, level1):
        return level1



register_object_class(Destinations)
