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
import users


############################################################################
# City
############################################################################
#class Body(ikaaroHTML):
#
#    edit_metadata_form__access__ = 'is_admin'
#    edit_metadata_form__label__ = 'Administrate'
#
#    history_form__access__ = False
#
#
#
#class City(ikaaroFolder, ikaaroWorkflowAware, Handler):
#
#    class_id = 'city'
#    class_title = u'City'
#    class_description = u'Publish a new City'
#    class_icon48 = 'abakuc/images/TouristOffice48.png'
#    class_icon16 = 'abakuc/images/TouristOffice16.png'
#
#    GET__access__ = True
#    def GET(self):
#        context = get_context()
#        uri = context.uri.resolve2(';preview')
#        context.redirect(uri)
#
#
#    #def _get_virtual_handler(self, segment):
#    #    if self.parent is not None:
#    #        adverts = self.get_handler('/adverts')
#    #        name = segment.name
#    #        if adverts.has_handler(name):
#    #            return adverts.get_handler(name)
#    #    return ikaaroFolder._get_virtual_handler(self, segment)
#
#
#    def new(self, **kw):
#        ikaaroFolder.new(self, **kw)
#        cache = self.cache
#        # The first segment of text
#        body = Body()
#        metadata = {'state': 'public', 'dc:language': 'en'}
#        metadata = self.build_metadata(body, **metadata)
#        cache['page00.xhtml.en'] = body
#
#    ########################################################################
#    # API
#    ########################################################################
#
#    def get_document_types(self):
#            return [ikaaroFile, Body]
#
#
#    def get_businesses(self):
#        return str(self.metadata.get_property('abakuc:business_type'))
#
#    business_type = property(get_businesses, None, None, '')
#
#    ########################################################################
#    # User Interface
#    ########################################################################
#    def get_views(self):
#        views = ikaaroFolder.get_views(self)
#        views.append('state_form')
#        views.append('preview')
#        views.append('view_adverts')
#        views.append('view_banners')
#        return views
#
#    ########################################################################
#    # Metadata
#    ########################################################################
#    edit_metadata_form__access__ = 'is_admin'
#    edit_metadata_form__label__ = u'Administrate'
#    def edit_metadata_form(self):
#        context = get_context()
#        root = context.root
#        catalog = root.get_handler('.catalog')
#        
#        # Build the namespace
#        namespace = {}
#
#        get_property = self.metadata.get_property
#        namespace['title'] = get_property('dc:title')
#        namespace['description'] = get_property('dc:description')
#
#        # Topics
#        business = self.get_property('abakuc:business_type') or ()
#
#        ns = []
#        for h in catalog.search(format='business_type'):
#            title = h.title_or_name
#            ns.append((title, {'name': h.name, 'title': title,
#                               'checked': h.name in business}))
#        ns.sort()
#        ns = [t[-1] for t in ns]
#
#        namespace['business_type'] = ns
#
#        handler = self.get_handler('/ui/abakuc/city_metadata.xml')
#        return stl(handler, namespace)
#
#
#    edit_metadata__access__ = 'is_admin'
#    def edit_metadata(self, **kw):
#        context = get_context()
#        root = context.root
#        catalog = root.get_handler('.catalog')
#
#        language = 'en'
#        self.set_property('dc:title', kw['dc:title'], language=language)
#        self.set_property('dc:description', kw['dc:description'],
#                          language=language)
#
#        # Update Business Type
#        self.set_property('abakuc:business_type', tuple(kw.get('names', [])))
#
#        # Reindex
#        root.reindex_handler(self)
#
#        return context.come_back(u'City has been modified!')
#
#
#    ########################################################################
#    # Adverts
#    view_adverts__access__ = 'is_admin'
#    view_adverts__label__ = u'Adverts'
#    def view_adverts(self):
#        context = get_context()
#
#        root = context.root
#        catalog = root.get_handler('.catalog')
#        adverts = root.get_handler('Adverts')
#
#        namespace = {}
#        namespace['adverts'] = []
#        for brain in catalog.search(format='advert', destinations=self.name):
#            advert = adverts.get_handler(brain.name)
#            namespace['adverts'].append({'href': self.get_pathto(advert),
#                                         'title': advert.title_or_name})
#
#        handler = self.get_handler('/ui/abakuc/adverts_view.xml')
#        return stl(handler, namespace)
#
#    ########################################################################
#    # Banners
#    ########################################################################
#    view_adverts__access__ = 'is_admin'
#    view_adverts__label__ = u'Banners'
#    def view_banners(self):
#        context = get_context()
#
#        root = context.root
#        catalog = root.get_handler('.catalog')
#        adverts = root.get_handler('Banners')
#
#        namespace = {}
#        namespace['adverts'] = []
#        for brain in catalog.search(format='advert', destinations=self.name):
#            advert = adverts.get_handler(brain.name)
#            namespace['adverts'].append({'href': self.get_pathto(advert),
#                                         'title': advert.title_or_name})
#
#        handler = self.get_handler('/ui/abakuc/banner_view.xml')
#        return stl(handler, namespace)
#
#register_object_class(City)


############################################################################
# Country 
############################################################################
class Regions(CSV):

    columns = ['region', 'county']

    schema = {'region': Unicode(index='keyword'),
              'county': Unicode(index='keyword')}



class Country(Handler, RoleAware, ikaaroFolder):

    class_id = 'country'
    class_title = u'Country'
    class_description = u'Add a new Country'
    class_icon48 = 'abakuc/images/TouristOffice48.png'
    class_icon16 = 'abakuc/images/TouristOffice16.png'
    class_views = [
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['permissions_form', 'new_user_form'], 
        ['edit_metadata_form']]

    __roles__ = BaseRoot.__roles__ + [
        {'name': 'abakuc:travel_agent_member',
         'title': u'Travel Agent',
         'unit': u'Travel Agent'},
        {'name': 'abakuc:travel_agent_manager',
         'title': u'Travel Agent(Manager)',
         'unit': u'Travel Agent(Manager)'},
        {'name': 'abakuc:tourist_office_member',
         'title': u'Tourist Office',
         'unit': u'Tourist Office'},
        {'name': 'abakuc:tourist_office_manager',
         'title': u'Tourist Office(Manager)',
         'unit': u'Tourist Office(Manager)'}
       ]

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


register_object_class(Country)



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




