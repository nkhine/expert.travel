# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import String, Unicode
from itools.stl import stl
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class

# Import from abakuc
from base import Handler, Folder


class Companies(Folder):

    class_id = 'companies'
    class_title = u'Companies'

    def get_document_types(self):
        return [Company]



class Company(Folder):

    class_id = 'company'
    class_title = u'Company'

    def get_document_types(self):
        return [Address]



class Address(Folder):

    class_id = 'address'
    class_title = u'Address'

    def get_document_types(self):
        return []


    def get_catalog_indexes(self):
        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        indexes['topic'] = company.get_property('abakuc:topic')
        ##indexes['region'] = self.get_property('abakuc:region')
        ##indexes['county'] = self.get_property('abakuc:county')
        ##indexes['town'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        return indexes


    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    def view(self, context):
        namespace = {}
        namespace['address'] = self.get_property('abakuc:address')
 
        handler = self.get_handler('/ui/abakuc/address_view.xml')
        return stl(handler, namespace)



register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
