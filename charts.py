# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath
from itools.handlers import get_handler
import itools.csv
from itools.cms.Folder import Folder as ikaaroFolder
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler


############################################################################
# Chart 
############################################################################

class Chart(Handler, ikaaroFolder):

    class_id = 'chart'
    class_title = u'Chart'
    class_description = u'Chart class to display pretty charts in a flash file'
    class_icon48 = 'abakuc/images/Chart48.png'
    class_icon16 = 'abakuc/images/Chart16.png'


register_object_class(Chart)
