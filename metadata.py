# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, String, Unicode, Email, Tokens
from itools.schemas import Schema as BaseSchema, register_schema
from itools.datatypes import Enumerate 

class Continent(Enumerate):

    options =  [
        {'name': 'Africa', 'label': u"Africa"},
        {'name': 'Americas', 'label': u"Americas"},
        {'name': 'Asia', 'label': u"Asia"},
        {'name': 'Europe', 'label': u"Europe"},
        {'name': 'Oceania', 'label': u"Oceania"}
    ]


class SubContinent(Enumerate):

    options =  [
        {'name': 'Africa', 'label': u"Africa"},
        {'name': 'Americas', 'label': u"Americas"},
        {'name': 'Asia', 'label': u"Asia"},
        {'name': 'Europe', 'label': u"Europe"},
        {'name': 'Oceania', 'label': u"Oceania"}
    ]


class Schema(BaseSchema):
 
    class_prefix = 'abakuc'
    class_uri = 'http://xml.abakuc.com/namespaces/abakuc'

    datatypes = {
        #Country Schema
        'continent': Continent(default='Oceania',
                              title=u'Continent',
                              is_mandatory=True),

        'sub_continent': Unicode(title=u'Sub continent', is_mandatory=True),
        # Company
        'website': String,
        'topic': Tokens,
        'type': String,
        # Address
        'address': Unicode,
        'postcode': String,
        'county': Integer,
        'town': Unicode,
        'phone': String,
        'fax': String,
        'license': Unicode,
        # Email
        'enquiry_subject': Unicode,
        'enquiry': Unicode,
        'enquiry_type': String
        }


register_schema(Schema)
