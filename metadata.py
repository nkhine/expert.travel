# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Boolean, Integer, String, Unicode,\
                            Email, Tokens, Date, Decimal, Enumerate
from itools.schemas import Schema as BaseSchema, register_schema

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


class RoomType(Enumerate):

    options =  [
        {'name': 'standard', 'label': u"Standard"},
        {'name': 'executive', 'label': u"Executive"},
        {'name': 'deluxe', 'label': u"Deluxe"},
        {'name': 'family', 'label': u"Family"},
        {'name': 'presidential', 'label': u"Presidential"}
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
        {'name': '11', 'value': u'£100K+'}]

class Schema(BaseSchema):

    class_prefix = 'abakuc'
    class_uri = 'http://xml.abakuc.com/namespaces/abakuc'

    datatypes = {
        #Country Schema
        'continent': Continent(default='Oceania',
                              title=u'Continent',
                              is_mandatory=True),

        'sub_continent': Unicode(title=u'Sub continent', is_mandatory=True),
        # User
        'user_disabled': Boolean(default=False), 
        'company_manager': Tokens(default=()),
        'branch_manager': Tokens(default=()),
        'branch_member': Tokens(default=()),
        'training_manager': Tokens(default=()),
        'partner': Tokens(default=()),
        'guest': Tokens(default=()),
        'job_title': String,
        'functions': String,
        'registration_date': Date,
        'last_login_date': Date,
        'previous_login_dates': Date,
        'points': Integer(default=0),
        'terms': Boolean(default=True,
                                  title=u'Terms & Conditions'),
        # Company
        'website': String,
        'topic': Tokens,
        'type': String,
        # Affiliations
        'abta': Unicode(title=u'ABTA', is_mandatory=False),
        'iata': Unicode(title=u'IATA', is_mandatory=False),
        'world_choice': Unicode(title=u'World Choice', is_mandatory=False),
        'travel_trust': Unicode(title=u'Travel Trust Association',
                                is_mandatory=False),
        'atol': Unicode(title=u'ATOL', is_mandatory=False),
        'advantage': Unicode(title=u'Advantage', is_mandatory=False),
        'midconsort': Unicode(title=u'Midconsort', is_mandatory=False),
        'global_travel': Unicode(title=u'Global Travel Group',
                                 is_mandatory=False),
        # Address
        'address': Unicode,
        'postcode': String,
        'county': Unicode,
        'town': Unicode,
        'phone': String,
        'freephone': Boolean(default=False,
                                title=u'Freephone'),
        'fax': String,
        #'licence': String,
        'licence': Unicode,
        # Email
        'enquiry_subject': Unicode,
        'enquiry': Unicode,
        'enquiry_type': String,
        # Document
        'image1': String(default=''),
        'image1_credit': Unicode,
        'image2': String(default=''),
        'image2_credit': Unicode,
        # Exam
        'exam_time': Integer(default=20),
        'questions_nums': Integer(default=20),
        'pass_marks_percentage': Integer(default=70),
        # Product 
        'airline': Tokens,
        'airport': Tokens,
        'board': String,
        'currency': Unicode,
        'departure_date': Date,
        'holiday_activity': Tokens,
        'holiday_type': String,
        'price': Decimal(default=0.00),
        'return_date': Date,
        'text': Unicode,
        # Hotel
        'hotel': Unicode,
        'rating': String,
        # News
        'unique_id': String,
        'news_text': Unicode,
        # Job
        'function': JobTitle,
        'salary': SalaryRange,
        'posted_on': Date,
        'closing_date': Date,
        'job_text': Unicode,
        'applicant_note': Unicode,
        'credits': Unicode,
        'image1': String(default=''),
        'image2': String(default=''),
        'map_image': String(default=''),
        'dyk_title': Unicode,
        'dyk_description': Unicode,
        'top1': Unicode,
        'top2': Unicode,
        'top3': Unicode,
        'top4': Unicode }

register_schema(Schema)
