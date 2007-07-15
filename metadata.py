# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, String, Unicode, Email, Tokens, Date
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


class JobTitle(Enumerate):
    
    options = [
        {'name': 'airlines', 'value': u'Airlines'},
        {'name': 'business_travel', 'value': u'Business Travel'},
        {'name': 'call_centre_telesales', 'value': u'Call Centre/Telesales'},
        {'name': 'car_hire', 'value': u'Car Hire'},
        {'name': 'conference_incentives_events', 'value': u'Conference/Incentives/Events'},
        {'name': 'cruises', 'value': u'Cruises'},
        {'name': 'executive_management', 'value': u'Executive/Management'},
        {'name': 'foreign_exchange', 'value': u'Foreign Exchange'},
        {'name': 'hotel_leisure', 'value': u'Hotel/Leisure'},
        {'name': 'other', 'value': u'Other'},
        {'name': 'rail', 'value': u'Rail'},
        {'name': 'retail', 'value': u'Retail'},
        {'name': 'support_staff', 'value': u'Support Staff'},
        {'name': 'temporary', 'value': u'Temporary'},
        {'name': 'operations', 'value': u'Tour Operations'},
        {'name': 'overseas', 'value': u'Overseas'},
        {'name': 'reservations_ticketing', 'value': u'Reservations/Ticketing'},
        {'name': 'it', 'value': u'IT'},
        {'name': 'sales_marketing', 'value': u'Sales/Marketing'},
        {'name': 'student', 'value': u'Student'}]

class SalaryRange(Enumerate):

    options = [
        {'name': '1', 'value': u'Under £15K'},
        {'name': '2', 'value': u'£15K-£20K'},
        {'name': '3', 'value': u'£20K-£25K'},
        {'name': '4', 'value': u'£25K-£30K'},
        {'name': '5', 'value': u'£30K-£35K'},
        {'name': '6', 'value': u'£35K-£40K'},
        {'name': '7', 'value': u'£40K-£45K'},
        {'name': '8', 'value': u'£45K-£50K'},
        {'name': '9', 'value': u'£50K-£70K'},
        {'name': '10', 'value': u'£70K-£100K'},
        {'name': '11', 'value': u'£100K+'},
        {'name': '12', 'value': u'Unspecified'}]



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
        'enquiry_type': String,
        # Job
        'function': JobTitle,
        'salary': SalaryRange,
        'closing_date': Date, 
        'job_text': Unicode,
        'applicant_note': Unicode
        }


register_schema(Schema)
