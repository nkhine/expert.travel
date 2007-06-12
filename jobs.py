# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class
from itools.stl import stl
from itools.web import get_context

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog


class Jobs(Folder):
 
    class_id = 'jobs'
    class_title = u'UK Travel Jobs'
    class_icon16 = 'abakuc/images/JobBoard16.png'
    class_icon48 = 'abakuc/images/JobBoard48.png'

    def get_document_types(self):
        return [Job]


    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job Board'
    def view(self, context):
        namespace = {}

        handler = self.get_handler('/ui/abakuc/jobs_view.xml')
        return stl(handler, namespace)


class Job(RoleAware, Folder):

    class_id = 'job'
    class_title = u'Job'
    class_description = u'Add new job board entry'
    class_icon16 = 'abakuc/images/Advert16.png'
    class_icon48 = 'abakuc/images/Advert48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form']]


    __fixed_handlers__ = ['log_applications.csv']


    def new(self, **kw):
        Folder.new(self, **kw)
        handler = ApplicationsLog()
        cache = self.cache
        cache['log_applications.csv'] = handler
        cache['log_applications.csv.metadata'] = handler.build_metadata(handler)


    def get_document_types(self):
        return []

    def get_catalog_indexes(self):
        from root import world

        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        indexes['topic'] = company.get_property('abakuc:topic')
        county_id = self.get_property('abakuc:county')
        if county_id:
            row = world.get_row(county_id)
            indexes['country'] = row[5]
            indexes['region'] = row[7]
            indexes['county'] = str(county_id)
        indexes['town'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        return indexes
    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job'
    def view(self, context):
        root = context.root
        get_property = self.get_property
        from root import world

        county_id = self.get_property('abakuc:county')
        if county_id is None:
            # XXX Every address should have a county
            country = region = county = '-'
        else:
            row = world.get_row(county_id)
            country = row[6]
            region = row[7]
            county = row[8]

        #namespace
        namespace = {}
        namespace['title'] = self.title_or_name
        namespace['description'] = self.get_property('dc:description')
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        handler = self.get_handler('/ui/abakuc/job_view.xml')
        return stl(handler, namespace)

    def edit_metadata_form(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')

    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address_county=None):
        from root import world
        root = get_context().root
        
        namespace = {}
        
        rows = world.get_rows()
        
        countries = {}
        regions = {}
        for index, row in enumerate(rows):
            country = row[6]
            region = row[7]
            county = row[8]
            is_selected = (index == address_county)
            id = str(index)

            # Add the country if not yet added
            if country in countries:
                country_ns = countries[country]
            else:
                country_ns = {'id': index, 'title': country,
                              'is_selected': False, 'display': 'none',
                              'regions': []}
                countries[country] = country_ns

            # Add the region if not yet added
            if region in regions:
                region_ns = regions[region]
            else:
                region_ns = {'id': index, 'title': region,
                              'is_selected': False, 'display': 'none',
                              'counties': []}
                regions[region] = region_ns
                # Add to the country
                country_ns['regions'].append(
                    {'id': id, 'title': region, 'is_selected': False})

            region_ns['counties'].append({'id': id, 'title': county,
                                          'is_selected': is_selected})

            # If this county is selected, activate the right blocks
            if is_selected:
                country_ns['is_selected'] = True
                country_ns['display'] = 'inherit'
                region_ns['is_selected'] = True
                region_ns['display'] = 'inherit'
                for x in country_ns['regions']:
                    if x['title'] == region:
                        x['is_selected'] = True
                        break

        countries = countries.values()
        countries.sort(key=lambda x: x['title'])
        namespace['countries'] = countries

        regions = regions.values()
        regions.sort(key=lambda x: x['title'])
        namespace['regions'] = regions


        handler = root.get_handler('ui/abakuc/regions_select_form.xml.en')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        namespace = {}
        namespace['title'] = self.title_or_name
        namespace['description'] = self.get_property('dc:description')
        address_county = self.get_property('abakuc:county')
        namespace['form'] = self.get_form(address_county)

        handler = self.get_handler('/ui/abakuc/job_edit_metadata.xml')
        return stl(handler, namespace)

    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')
        county = context.get_form_value('abakuc:county')
        self.set_property('dc:title', title)
        self.set_property('dc:description', description)
        self.set_property('abakuc:county', county)


        message = u'Changes Saved.'
        return context.come_back(message)

register_object_class(Jobs)
register_object_class(Job)
