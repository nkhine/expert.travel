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
# Rivers
############################################################################

class Rivers(Handler, ikaaroFolder):

    class_id = 'rivers'
    class_title = u'Rivers'
    class_description = u'Folder containing all the world rivers'
    class_icon48 = 'abakuc/images/Destination48.png'
    class_icon16 = 'abakuc/images/Destination16.png'

    def get_document_types(self):
        return [River]


    def get_skeleton(self, **kw):
        skeleton = {}

        path = get_abspath(globals(), 'data/rivers.csv')
        handler = get_handler(path)
        for row in handler.get_rows():
            i, name, main_title, km, miles = row
            name = name.lower()
            if name not in skeleton:
                title = main_title.title()
                river = River()
                metadata = self.build_metadata(river, **{'dc:title': title})
                skeleton[name] = river
                skeleton['.%s.metadata' % name] = metadata
                
        return skeleton


register_object_class(Rivers)

class River(Handler, ikaaroFolder):

    class_id = 'river'
    class_title = u'River'
    class_description = u'Add a new River'

register_object_class(River)
