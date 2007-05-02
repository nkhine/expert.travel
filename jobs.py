# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Folder


class Jobs(Folder):
 
    class_id = 'jobs'
    class_title = u'UK Travel Jobs'
    class_icon16 = 'abakuc/images/Automator16.png'
    class_icon48 = 'abakuc/images/Automator48.png'


    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job Board XXX'
    def view(self, context):
        return 'Job Board View'


register_object_class(Jobs)

