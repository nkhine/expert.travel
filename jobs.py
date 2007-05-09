# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.registry import register_object_class
from itools.stl import stl

# Import from abakuc
from base import Handler, Folder
from handlers import ApplicationsLog

class Jobs(Folder):
 
    class_id = 'jobs'
    class_title = u'UK Travel Jobs'
    class_icon16 = 'abakuc/images/Automator16.png'
    class_icon48 = 'abakuc/images/Automator48.png'

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
        cache['log_applications.csv.metadata'] = self.build_metadata(handler)


    def get_document_types(self):
        return []

    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        county_id = self.get_property('abakuc:county')
        if county_id:
            csv = self.get_handler('/regions.csv')
            country, region, county = csv.get_row(county_id)
            indexes['region'] = region
            indexes['county'] = str(county_id)
        return indexes

    #######################################################################
    # User Interface
    view__access__ = True
    view__label__ = u'Job'
    def view(self, context):
        root = context.root
        get_property = self.metadata.get_property

        #namespace
        namespace = {}
        namespace['title'] = self.title_or_name
        namespace['description'] = self.get_property('dc:description')

        handler = self.get_handler('/ui/abakuc/job_view.xml')
        return stl(handler, namespace)

    def edit_metadata_form(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')

        # Area where the job is located 
        rows = self.get_handler('/regions.csv').get_rows()
        job_county = self.get_property('abakuc:county')

        countries = {}
        regions = {}
        for index, row in enumerate(rows):
            country, region, county = row
            is_selected = (index == job_county)
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
