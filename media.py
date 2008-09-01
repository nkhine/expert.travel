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

    def get_images(self):
        images = list(self.search_handlers(format=File.class_id))
        images.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return images
    #######################################################################
    # ACL 
    #######################################################################
    def is_training_manager_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        office = self.parent
        # Is reviewer or member
        return (office.has_user_role(user.name, 'abakuc:training_manager') or
                office.has_user_role(user.name, 'abakuc:branch_member'))
    
    def is_allowed_to_edit_map(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is training manager
        return self.has_user_role(user.name, 'abakuc:training_manager')

    def is_allowed_to_view(self, user, object):
        # Protect the document
        return self.is_training_manager_or_member(user, object)

    #######################################################################
    # View media folder 
    #######################################################################

    view__access__ = 'is_allowed_to_view' 
    #view__access__ =  True 
    view__label__ = u'Media folder'
    def view(self, context):
        # Add the js scripts
        context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        # Get all the images and flash objects
        handlers = self.search_handlers(handler_class=File)
        images = []
        flash = []
        for handler in handlers:
            if handler.to_str()[:3] in ('FWS', 'CWS'):
                url = '/media/%s' % handler.name
                item = {'url': url,
                         'title': handler.get_property('dc:title'),
                         'description': handler.get_property('dc:description'),
                         'keywords': handler.get_property('dc:subject')}
                flash.append(item)
            else:
                url = '/media/%s' % handler.name
                item = {'url': url,
                         'title': handler.get_property('dc:title'),
                         'description': handler.get_property('dc:description'),
                         'keywords': handler.get_property('dc:subject')}
                images.append(item)
        namespace = {}
        handler = self.get_handler('/ui/abakuc/media/view.xml')
        return stl(handler, namespace)

register_object_class(Media)
