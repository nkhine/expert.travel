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
from itools.cms.Folder import Folder as ikaaroFolder
from itools.cms.WebSite import WebSite
from itools.cms.workflow import WorkflowAware as ikaaroWorkflowAware
from itools.cms.access import RoleAware
from itools.cms.File import File as ikaaroFile
from itools.cms.html import XHTMLFile as ikaaroHTML
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler
from metadata import Continent, SubContinent
import users
from website import WebSite


############################################################################
# City
############################################################################
class City(ikaaroFolder, ikaaroWorkflowAware, Handler):

    class_id = 'city'
    class_title = u'City'
    class_description = u'Publish a new City'
    class_icon48 = 'abakuc/images/TouristOffice48.png'
    class_icon16 = 'abakuc/images/TouristOffice16.png'
    class_views = [
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['permissions_form', 'new_user_form'], 
        ['edit_metadata_form']]

############################################################################
# Country 
############################################################################
class Country(WebSite):

    class_id = 'country'
    class_title = u'Country'
    class_description = u'Add a new Country'
    class_icon48 = 'abakuc/images/TouristOffice48.png'
    class_icon16 = 'abakuc/images/TouristOffice16.png'
    class_views = [
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['new_resource_form'],
        ['permissions_form', 'new_user_form'], 
        ['edit_metadata_form']]

    def get_document_types(self):
        return [City]


    #__roles__ = BaseRoot.__roles__ + [
    #    {'name': 'abakuc:travel_agent_member',
    #     'title': u'Travel Agent',
    #     'unit': u'Travel Agent'},
    #    {'name': 'abakuc:travel_agent_manager',
    #     'title': u'Travel Agent(Manager)',
    #     'unit': u'Travel Agent(Manager)'},
    #    {'name': 'abakuc:tourist_office_member',
    #     'title': u'Tourist Office',
    #     'unit': u'Tourist Office'},
    #    {'name': 'abakuc:tourist_office_manager',
    #     'title': u'Tourist Office(Manager)',
    #     'unit': u'Tourist Office(Manager)'}
    #   ]

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
            
        handler = self.get_handler('/ui/abakuc/country_edit_metadata.xml')
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
        return context.come_back(u'Country modified!')

############################################################################
# Countries 
############################################################################

class Countries(Handler, ikaaroFolder):

    class_id = 'countries'
    class_title = u'Countries in the World'
    class_description = u'Folder containing all the Countries'
    class_icon48 = 'abakuc/images/Destination48.png'
    class_icon16 = 'abakuc/images/Destination16.png'

    def new(self, **kw):
        ikaaroFolder.new(self, **kw)
        cache = self.cache
        path = get_abspath(globals(), 'data/csv/country.csv')
        handler = get_handler(path)
        for row in handler.get_rows():
            id, continent_name, region_id, region, country_id, name = row
            name = name.lower().strip().replace(' ', '-')
            title = name.title().replace('-', ' ')
            country = Country()
            metadata = self.build_metadata(country,
                                        **{'dc:title': title,
                                        'abakuc:continent': continent_name,
                                        'abakuc:sub_continent': region})
            cache[name] = country
            cache['%s.metadata' % name] = metadata



    def get_document_types(self):
        return [Country]


register_object_class(Countries)
register_object_class(Country)
register_object_class(City)

