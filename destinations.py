# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.registry import register_object_class

# Import from abakuc
from website import WebSite


class Destinations(WebSite):
 
      class_id = 'destinations'
      class_title = u'Destinations Guide'
      class_icon16 = 'abakuc/images/Resources16.png'
      class_icon48 = 'abakuc/images/Resources48.png'

register_object_class(Destinations)

