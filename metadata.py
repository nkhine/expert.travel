# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, String, Unicode
from itools.schemas import Schema as BaseSchema, register_schema



class Schema(BaseSchema):
 
    class_prefix = 'abakuc'
    class_uri = 'http://xml.abakuc.com/namespaces/abakuc'

    datatypes = {
        # Company
        'website': String,
        'topic': String,
        # Address
        'address': Unicode,
        'postcode': String,
        'town': Integer,
        'phone': String,
        'fax': String,
        'license': Unicode,
        }


register_schema(Schema)
