# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.stl import stl
from itools.cms.folder import Folder
from itools.cms.access import RoleAware
from itools.cms.file import File
from itools.cms.utils import reduce_string
from itools.cms.registry import register_object_class, get_object_class
from itools.xhtml import Document as XHTMLDocument

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
               ['permissions_form',
                    'new_user_form'],
                ['edit_metadata_form']]

    browse_content__access__ = 'is_allowed_to_add' 
    new_resource_form__access__ = 'is_allowed_to_add'
    new_resource__access__ = 'is_allowed_to_add'
    edit_metadata_form__access__ = 'is_allowed_to_add'
    permissions_form__access__ = 'is_admin'
    new_user_form__access__ = 'is_admin'

    def get_document_types(self):
        return [File]

    def get_images(self):
        images = list(self.search_handlers(format=File.class_id))
        images.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return images

    #######################################################################
    # ACL 
    #######################################################################
    def is_training_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        office = self.parent
        # Is reviewer or member
        return office.has_user_role(user.name, 'abakuc:training_manager')

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
    
    def is_allowed_to_view(self, user, object):
        # Protect the document
        return self.is_training_manager_or_member(user, object)

    def is_allowed_to_edit(self, user, object):
        # Protect the document
        return self.is_training_manager(user, object)

    def is_allowed_to_add(self, user, object):
        # Protect the document
        return self.is_training_manager(user, object)

    def is_allowed_to_move(self, user, object):
        # Protect the document
        return self.is_training_manager(user, object)

    def is_allowed_to_trans(self, user, object, name):
        return self.is_training_manager(user, object)
    #######################################################################
    # Tabs 
    #######################################################################
    tabs__access__ = True 
    def tabs(self, context):
        """
        Media folder tabs:
        We want to split the content into different tabs so that: 
        [Images] [Videos] [Documents] [Manage]
        """
        context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')

        root = context.root

        namespace = {}
        namespace['images'] = self.images(context)
        namespace['browse_content'] = self.browse_content(context)
        user = context.user
        office = self.get_site_root()

        if user is not None:
            is_training_manager = office.has_user_role(user.name, 'abakuc:training_manager')
            namespace['is_training_manager'] = is_training_manager
        else:
            namespace['is_training_manager'] = None 


        template_path = 'ui/abakuc/media/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    #######################################################################
    # View media folder 
    #######################################################################

    view__access__ = 'is_allowed_to_view' 
    view__label__ = u'Media folder'
    #def view(self, context):
    #    office = self.parent
    #    user = context.user
    #    # Set style
    #    context.styles.append('/ui/abakuc/jquery/css/jqGalScroll.css')
    #    # Add the js scripts
    #    context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
    #    context.scripts.append('/ui/abakuc/jquery/addons/jqgalscroll.js')
    #    # Get all the images and flash objects
    #    handlers = self.search_handlers(handler_class=File)
    #    images = []
    #    flash = []
    #    others = []
    #    for handler in handlers:
    #        handler_state = handler.get_property('state')
    #        if handler_state == 'public':
    #            type = handler.get_content_type()
    #            url = '/media/%s' % handler.name
    #            if type == 'image':
    #                item = {'url': url,
    #                        'title': handler.get_property('dc:title'),
    #                        'icon': handler.get_path_to_icon(size=16),
    #                        'mtime': handler.get_mtime().strftime('%Y-%m-%d %H:%M'),
    #                        'description': handler.get_property('dc:description'),
    #                        'keywords': handler.get_property('dc:subject')}
    #                images.append(item)
    #            elif type == 'application/x-shockwave-flash':
    #                item = {'url': url,
    #                        'title': handler.get_property('dc:title'),
    #                        'icon': handler.get_path_to_icon(size=16),
    #                        'mtime': handler.get_mtime().strftime('%Y-%m-%d %H:%M'),
    #                        'description': handler.get_property('dc:description'),
    #                        'keywords': handler.get_property('dc:subject')}
    #                flash.append(item)
    #            else:
    #                title = handler.get_property('dc:title')
    #                if title == '':
    #                    title = 'View document'
    #                else:
    #                    title = reduce_string(title, 10, 20)
    #                item = {'url': url,
    #                        'title': title,
    #                        'icon': handler.get_path_to_icon(size=16),
    #                        'mtime': handler.get_mtime().strftime('%Y-%m-%d %H:%M'),
    #                        'description': handler.get_property('dc:description'),
    #                        'keywords': handler.get_property('dc:subject')}
    #                others.append(item)
    #            
    #    # Namespace
    #    namespace = {}
    #    namespace['images'] = images
    #    namespace['flash'] = flash
    #    namespace['others'] = others
    #    namespace['title'] = self.get_property('dc:title')
    #    handler = self.get_handler('/ui/abakuc/media/view.xml')
    #    return stl(handler, namespace)

    view__access__ = True 
    view__label__ = u'Media folder'
    def view(self, context):
        # Namespace
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['tabs'] = self.tabs(context)
        handler = self.get_handler('/ui/abakuc/media/view.xml')
        return stl(handler, namespace)

    images__access__ = True 
    images__label__ = u'Images'
    def images(self, context):
        # Set style
        context.styles.append('/ui/abakuc/media/global.css')
        context.styles.append('/ui/abakuc/media/thickbox.css')
        
        ## Add the js scripts
        #context.scripts.append('/ui/abakuc/jquery/jquery.pack.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.easing.1.3.js')
        context.scripts.append('/ui/abakuc/jquery/thickbox-modified.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.scrollto.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.serialScroll.js')

        context.scripts.append('/ui/abakuc/tools.js')
        context.scripts.append('/ui/abakuc/media/tools.js')
        context.scripts.append('/ui/abakuc/media/product.js')
        # Get all the images and flash objects
        handlers = self.search_handlers(handler_class=File)
        images = []
        for handler in handlers:
            handler_state = handler.get_property('state')
            if handler_state == 'public':
                type = handler.get_content_type()
                url_220 = '/media/%s/;icon220' % handler.name
                url_70 = '/media/%s/;icon70' % handler.name
                if type == 'image':
                    item = {'url_220': url_220,
                            'url_70': url_70,
                            'name': handler.name,
                            'title': handler.get_property('dc:title'),
                            'icon': handler.get_path_to_icon(size=16),
                            'mtime': handler.get_mtime().strftime('%Y-%m-%d %H:%M'),
                            'description': handler.get_property('dc:description'),
                            'keywords': handler.get_property('dc:subject')}
                    images.append(item)
        # Namespace
        namespace = {}
        have_image = len(images)
        if have_image > 0:
            if have_image == 1:
                namespace['more_than'] = False
            else:
                namespace['more_than'] = True
                
            namespace['image_1'] = images[0]
            namespace['images'] = images[1:]
            namespace['have_image'] = True 
            namespace['total_images'] = len(images)
        else:
            namespace['have_image'] = None 
            namespace['total_images'] = None

        handler = self.get_handler('/ui/abakuc/media/images.xml')
        return stl(handler, namespace)


register_object_class(Media)
