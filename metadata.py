# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, String, Unicode, Email, Tokens
from itools.schemas import Schema as BaseSchema, register_schema



class Schema(BaseSchema):
 
    class_prefix = 'abakuc'
    class_uri = 'http://xml.abakuc.com/namespaces/abakuc'

    datatypes = {
        # Company
        'website': String,
        'topic': Tokens,
        # Address
        'address': Unicode,
        'postcode': String,
        'county': Integer,
        'town': Unicode,
        'phone': String,
        'fax': String,
        'license': Unicode,
        # Email
        'fullname':Unicode,
        'enquiry':Unicode,
        'typeenquiry':String
        }


register_schema(Schema)
