# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import datetime

# Import from itools
from itools.stl import stl
from itools.cms.folder import Folder
from itools.cms.access import RoleAware
from itools.cms.file import File
from itools.cms.registry import register_object_class, get_object_class

class Media(Folder, RoleAware):
    class_id = 'Media'
    class_title = u'Media'
    class_description = u'Media content folder'
    class_icon16 = 'abakuc/images/JobBoard16.png'
    class_icon48 = 'abakuc/images/JobBoard48.png'
    class_views = [
                ['view'],
                ['browse_content?mode=list',
                'browse_content?mode=thumbnails'],
                ['new_resource_form'],
                ['edit_metadata_form']]

    def get_document_types(self):
        return [File, Folder]

    #######################################################################
    # View media folder 
    #######################################################################

    view__access__ = True
    view__label__ = u'Media folder'
    def view(self, context):
        namespace = {}
        handler = self.get_handler('/ui/abakuc/media/view.xml')
        return stl(handler, namespace)

register_object_class(Media)
