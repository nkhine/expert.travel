# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import os
import re
import datetime
from random import choice 

# import from itools
from itools import get_abspath
from itools.datatypes import URI
from itools import vfs
from itools.handlers.Image import Image as iImage
from itools.stl import stl
from itools.web import get_context
from itools import uri
from itools.cms.registry import register_object_class

# import from ikaaro
from itools.cms.access import AccessControl
from itools.cms.Folder import Folder as BaseFolder
from itools.cms.File import File as BaseFile
from itools.cms.workflow import WorkflowAware as baseWorkflowAware
from itools.cms.Handler import Handler as ikaaroHandler

# import from abakuc
from base import Handler
from countries import City 
from metadata import BannerType, WebsiteTarget, Schema


############################################################################
# Banners
############################################################################


class Banners(BaseFolder):

    class_id = 'banners'
    class_title = u'Banners Tool'
    class_description = u'Manage Banners with statistics.'
    class_version = '20050913'
    class_icon48 = 'abakuc/images/Banners48.png'
    class_icon16 = 'abakuc/images/Banners16.png'
    class_views = [['browse_content?mode=thumbnails',
                    'browse_content?mode=list',
                    'browse_content?mode=image'],
                   ['new_resource_form']]

    def get_document_types(self):
        return [Banner]

register_object_class(Banners)


############################################################################
# Banner
############################################################################

class Banner(BaseFolder):

    class_id = 'banner'
    class_title = u'Banner'
    class_description = u'Banner object'
    class_version = '20060628'
    class_icon48 = 'abakuc/images/Banner48.png'
    class_icon16 = 'abakuc/images/Banner16.png'
    class_views = [['browse_content?mode=thumbnails',
                    'browse_content?mode=list',
                    'browse_content?mode=image'],
                    ['edit_metadata_form']]


    #def get_namespace(self):
    #    namespace = ikaaroFolder.get_namespace(self)

    #    title = self.get_property('dc:title')
    #    namespace['title'] = title
    #    namespace['banner_target'] = self.get_property('abakuc:banner_target') 

    #    #img = self.get_handler('.logo')
    #    #namespace['img_url'] = here.get_pathto(img)

    #    return namespace 

    #########################################################################
    ## Indexing
    #########################################################################
    #def get_catalog_indexes(self):
    #    indexes = ikaaroFolder.get_catalog_indexes(self)

    #    get_property = self.metadata.get_property
    #    #indexes['destinations'] = list(get_property('abakuc:destinations'))
    #    #indexes['topics'] = list(get_property('abakuc:topics'))
    #    #indexes['banner_pos'] = get_property('abakuc:banner_pos')
    #    count = get_property('abakuc:banner_count')
    #    max = get_property('abakuc:banner_max_click')
    #    indexes['banner_remain_click'] = count <= max
    #    #indexes['banner_home_page'] = get_property('abakuc:banner_home_page')
    #    #indexes['banner_is_local'] = get_property('abakuc:banner_is_local')
    #    indexes['banner_weight'] = str(get_property('abakuc:banner_weight'))
    #    indexes['banner_target'] = get_property('abakuc:banner_target')
    #    indexes['banner_website'] = str(get_property('abakuc:banner_website'))
    #    #indexes['is_flash'] = str(int(self.is_flash()))

    #    return indexes

    #########################################################################
    ## User Interface
    #########################################################################
    #def new(self):
    #    
    ##    path = get_abspath(globals(), 'ui/abakuc/images/px.png')
    ##    pix = vfs.open(path)
    ##    return {'.logo': Image(pix)}


    ##def _get_handler(self, segment, resource):
    ##    name = segment.name
    ##    if name == '.logo':
    ##        return Image(resource)
    ##    return ikaaroFolder._get_handler(self, segment, resource)

    ##
    ##def is_flash(self):
    ##    return self.get_handler('.logo').to_str()[:3] in ('FWS', 'CWS')
    #
    #def get_views(self):
    #    return ['view', 'edit_form', 'state_form'] 

    #def get_subviews(self, name):
    #    return []

    #########################################################################
    ## View Banner
    #########################################################################

    #view__access__ = True  
    #view__label__  = u'View Banner'

    #def view(self):
    #    namespace =  {}
    #    
    #    m = self.metadata 
    #    namespace['title'] = self.get_title_or_name()
    #    namespace['description'] = self.get_description()
    #    namespace['state'] = self.get_property('state')
    #    namespace['href'] = self.get_pathto(self)

    #    namespace['banner_website'] = self.get_property('abakuc:banner_website')
    #    namespace['banner_target'] = self.get_property('abakuc:banner_target')
    #    
    #    #display URL and fix the http:// if ommited from the edit form
    #    website = URI.encode(m.get_property('abakuc:banner_website'))
    #    namespace['website'] = website
    #    namespace['website_url'] = 'http://' + website.split('http://')[-1]

    #    #Other banner properties
    #    namespace['max_click'] = m.get_property('abakuc:banner_max_click')
    #    namespace['count'] = m.get_property('abakuc:banner_count')
    #    namespace['weight'] = m.get_property('abakuc:banner_weight')
    #    
    #    #Image or Flash object
    #    #namespace['is_flash'] = self.is_flash()

    #    
    #    handler = self.get_handler('/ui/abakuc/banner_view.xml')
    #    return stl(handler, namespace)
 
 
 
    #########################################################################
    ## Edit Banner
    #########################################################################

    ## Upload for logo and pictures
    #def upload_image(self, type, resource):
    #    handler_names = self.get_handler_names()

    #    # Check wether the handler is able to deal with the uploaded file
    #    input = self.get_handler('.%s' % type)
    #    try:
    #        input.load_state(resource)
    #    except:
    #        message = (u'Upload failed: either the file does not match this '  
    #                   u'document type (%s) or it contains errors.')
    #        raise UserError, message % self.get_mimetype() 

    def edit_metadata_form(self, context):
        context = get_context()
        root = context.root
        get_property = self.metadata.get_property

        namespace = {}

        # Metadata
        namespace['title'] = self.get_title_or_name()
        namespace['description'] = self.get_description()
        namespace['banner_website'] = get_property('abakuc:banner_website')

        # Banner Type
        banner_type = get_property('abakuc:banner_type')
        banner_type = BannerType.get_namespace(banner_type)
        namespace['banner_type'] = banner_type

        # Banner Target
        banner_target = get_property('abakuc:banner_target')
        banner_target = WebsiteTarget.get_namespace(banner_target)
        namespace['banner_target'] = banner_target

        # Max_click
        namespace['banner_max_click'] = get_property('abakuc:banner_max_click')
        
        # Count number of clicks 
        namespace['banner_count'] = get_property('abakuc:banner_count')

        # Weight of display 
        weight = get_property('abakuc:banner_weight')
        all_weight = []
        for w in range(1, 11):
            all_weight.append({'name': w, 'is_selected': w == weight})
        namespace['all_weight'] = all_weight 
        namespace['banner_weight'] = get_property('abakuc:banner_weight') 

    #    # Flash or image
    #    #namespace['is_flash'] = self.is_flash()
    #
        handler = self.get_handler('/ui/abakuc/banner_metadata.xml')
        return stl(handler, namespace)
 
 
    def edit_metadata(self, context):
        metadata = self.get_metadata()
        # Metadata
        title = context.get_form_value('dc:title')
        metadata.set_property('dc:title', title)
        # Description
        description = context.get_form_value('dc:description')
        metadata.set_property('dc:description', description)
        # Abakuc metadata
        banner_website = context.get_form_value('abakuc:banner_website')
        metadata.set_property('abakuc:banner_website', banner_website)
        
        banner_type = context.get_form_value('abakuc:banner_type')
        metadata.set_property('abakuc:banner_type', banner_type)

        banner_target = context.get_form_value('abakuc:banner_target')
        metadata.set_property('abakuc:banner_target', banner_target)
        
        banner_weight = context.get_form_value('abakuc:banner_weight')
        metadata.set_property('abakuc:banner_weight', banner_weight)
        
        banner_max_click = context.get_form_value('abakuc:banner_max_click')
        metadata.set_property('abakuc:banner_max_click', banner_max_click) 
        banner_count = context.get_form_value('abakuc:banner_count')
        metadata.set_property('abakuc:banner_count', banner_count)
    #    
        return context.come_back(u'Banner modified!') 
 
 
    #########################################################################
    ## Click banner method 
    #########################################################################
 
    #
    #click_banner__access__ = True
    #def click_banner(self, stay_in_tu=False, **kw):
    #    context = get_context()
    #    root, request = context.root, context.request
    #    website_url = kw['website_url']
    #    banner_count = self.get_property('abakuc:banner_count')
    #    new_count = banner_count + 1
    #    self.set_property('abakuc:banner_count', new_count)
    #    res = banner_count = self.get_property('abakuc:banner_count')
    #    if bool(int(stay_in_tu)):
    #        context.response.redirect(request.referer)
    #    else:
    #        context.response.redirect(website_url)
 
register_object_class(Banner)

