# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath
from itools import vfs
from itools.handlers import get_handler
from itools.web import get_context
from itools.stl import stl
from itools.csv import CSV, Row
from itools.datatypes import Boolean, Email, Integer, String, Unicode
from itools.cms.root import Root as BaseRoot
from itools.cms.folder import Folder as ikaaroFolder
from itools.cms.website import WebSite
from itools.cms.workflow import WorkflowAware as ikaaroWorkflowAware
from itools.cms.access import RoleAware
from itools.cms.file import File as ikaaroFile
from itools.cms.html import XHTMLFile as ikaaroHTML
from itools.cms.registry import register_object_class


# Import from abakuc
from base import Handler
from metadata import Continent, SubContinent
import users
# XXX from website import WebSite


############################################################################
# Rivers 
############################################################################

class Rivers(Handler, ikaaroFolder):

    class_id = 'Rivers'
    class_title = u'Rivers on the World'
    class_description = u'Folder containing all the Rivers'
    class_icon48 = 'abakuc/images/Destination48.png'
    class_icon16 = 'abakuc/images/Destination16.png'

    def new(self, **kw):
        ikaaroFolder.new(self, **kw)
        cache = self.cache
        path = get_abspath(globals(), 'data/river.csv')
        handler = get_handler(path)
        for row in handler.get_rows():
            id, continent_name, region_id, region, river_id, name = row
            name = name.lower().strip().replace(' ', '-').replace('\'', '').replace(',', '')
            title = name.title().replace('-', ' ')
            River = River()
            metadata = River.build_metadata(**{'dc:title': title,
                                        'abakuc:continent': continent_name,
                                        'abakuc:sub_continent': region,
                                        'ikaaro:website_is_open': True})
            cache[name] = River
            cache['%s.metadata' % name] = metadata


    def get_document_types(self):
        return [River]


############################################################################
# River 
############################################################################
class River(WebSite):

    class_id = 'river'
    class_title = u'River'
    class_description = u'Add a new River'
    class_icon48 = 'abakuc/images/TouristOffice48.png'
    class_icon16 = 'abakuc/images/TouristOffice16.png'
    class_views = [
        ['view'], 
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['new_resource_form'],
        ['permissions_form', 'new_user_form'], 
        ['edit_metadata_form']]

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'Rivers':
            return self.get_handler('/rivers')
        return WebSite._get_virtual_handler(self, segment)


    #######################################################################
    # User Interface / Navigation
    #######################################################################
    site_format = 'River'

    def get_level1_title(self, level1):
        return level1

    def get_document_types(self):
        return [City]


    def get_catalog_indexes(self):
        indexes = WebSite.get_catalog_indexes(self)
        indexes['level1'] = self.get_property('abakuc:continent')
        indexes['level2'] = self.get_property('abakuc:sub_continent')
        return indexes


    view__access__ = 'is_allowed_to_view'
    view__label__ = u'River'
    def view(self, context):
        # XXX 
        txt = 'List town :'
        cities = list(self.search_handlers(handler_class=City))
        for city in cities:
            txt = txt + city.name
        return txt


    ########################################################################
    # Metadata
    # edit_metadata_form__access__ = is_allowed_to_edit
    def edit_metadata_form(self, context):
        context = get_context()
        root, user = context.root, context.user
        namespace = {}

        get_property = self.get_metadata().get_property
        # Title
        title = get_property('dc:title', language='en')
        namespace['title'] = title
        # Description
        description = get_property('dc:description', language='en')
        namespace['description'] = description
        # Continent
        continent = get_property('abakuc:continent')
        continent = Continent.get_namespace(continent)
        namespace['continent'] = continent
        # Sub Continent 
        sub_continent = get_property('abakuc:sub_continent')
        #sub_continent = SubContinent.get_namespace(sub_continent)
        namespace['sub_continent'] = sub_continent
            
        handler = self.get_handler('/ui/abakuc/river_edit_metadata.xml')
        return stl(handler, namespace)


   # edit_metadata__access__ = is_allowed_to_edit
    def edit_metadata(self, context):
        metadata = self.get_metadata()
        # The title
        title = context.get_form_value('dc:title')
        metadata.set_property('dc:title', title)
        # Description
        description = context.get_form_value('dc:description')
        metadata.set_property('dc:description', description)
        # Continent
        continent = context.get_form_value('abakuc:continent')
        metadata.set_property('abakuc:continent', continent)
        # Business function 
        sub_continent = context.get_form_value('abakuc:sub_continent')
        metadata.set_property('abakuc:sub_continent', sub_continent)
        # Come back
        return context.come_back(u'River modified!')


register_object_class(Rivers)
register_object_class(River)
