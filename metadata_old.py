# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import datetime
from copy import deepcopy
import re

# Import from itools
from itools import get_abspath
from itools.datatypes import (DataType, Enumerate, Tokens, Boolean, String,
                              Unicode, DateTime, Decimal, URI, Integer)
from itools.schemas import Schema as BaseSchema, register_schema
from itools import vfs



#############################################################################
# Data to load on start-up
#############################################################################

path = get_abspath(globals(), 'data/txt/regions.txt')
file = vfs.open(path)
lines = file.read().split('\n')
file.close()
regions = []
region_id = None
for line in lines:
    line = line.strip()
    if line:
        id, label = line.split('#')
        if region_id is None:
            region_id = id
            regions.append({'id': id, 'label': label, 'counties': []})
        else:
            id = '%s/%s' % (region_id, id)
            regions[-1]['counties'].append({'id': id, 'label': label})
    else:
        region_id = None

#############################################################################
# Data Types
#############################################################################
class PhoneNumber(String):

    @staticmethod
    def is_valid(value):
        return re.match("^0\d{2,4}[ -]{1}[\d]{3}[\d -]{1}[\d -]{1}[\d]{1,4}$",
                        value.lower()) is not None

class EMail(String):

    @staticmethod
    def is_valid(value):
        email = value.split('@')
        if len(email) != 2:
            return False

        right = email[1]
        if value.count('.') == 0:
            return False

        for x in value.split('.'):
            if not x:
                return False

        return True

        
class Date(DataType):
 
    @staticmethod
    def decode(value):
        if not value:
            return ''
        year, month, day = value.split('-')
        year, month, day = int(year), int(month), int(day)
        return datetime.date(year, month, day)


    @staticmethod
    def encode(value):
        if not value:
            return ''
        return value.strftime('%Y-%m-%d')



class DateLiteral(DataType):

    weekdays_short = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    weekdays_long = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday']
    # begin at index 1
    months_short = ['', 'jan', 'fev', 'mar', 'apr', 'may', 'jun', 'jul',
            'augÂ»', 'sep', 'oct', 'nov', 'dec']
    months_long = ['', 'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december']

    @classmethod
    def encode(cls, value, short=False, hour=True):
        weekday = value.weekday()
        month = value.month
        if hour:
            date = value.strftime("# %d & %Y %H:%M")
        else:
            date = value.strftime("# %d & %Y")
        if short:
            date = date.replace('#', cls.weekdays_short[weekday])
        else:
            date = date.replace('#', cls.weekdays_long[weekday])
        if short:
            date = date.replace('&', cls.months_short[month])
        else:
            date = date.replace('&', cls.months_long[month])

        return date



class UnicodeEnumerate(Unicode, Enumerate):

    @classmethod
    def get_namespace(cls, name):
        options = cls.get_options()
        for option in options:
            option['selected'] = option['value'] == name
        return options


class UserTitle(Enumerate):

    options = [
        {'name': 'Mr', 'label': u"Mr"},
        {'name': 'Mrs', 'label': u"Mrs"},
        {'name': 'Miss', 'label': u"Miss"},
        {'name': 'Ms', 'label': u"Ms"}
    ]


class BusinessProfile(Enumerate):

    options =  [
        {'name': 'Multiple', 'label': u"Multiple"},
        {'name': 'Independent', 'label': u"Independent"},
        {'name': 'Homeworker', 'label': u"Homeworker"},
        {'name': 'Call Centre', 'label': u"Call Centre"},
        {'name': 'Others', 'label': u"Others"}
    ]

class BusinessFunction(Enumerate):

    options = [
        {'name': 'Travel Agent', 'label': u"Travel Agent"},
        {'name': 'Tour Operator', 'label': u"Tour Operator"},
        {'name': 'National Tourist Board',
         'label': u"National Tourist Board"},
        {'name': 'Airline', 'label': u"Airline"},
        {'name': 'Representation Company',
         'label': u"Representation Company"},
        {'name': 'Public Relations', 'label': u"Public Relations"},
        {'name': 'Association', 'label': u"Association"},
        {'name': 'Car Hire', 'label': u"Car Hire"},
        {'name': 'Insurance', 'label': u"Insurance"},
        {'name': 'Technology', 'label': u"Technology"},
        {'name': 'Academia', 'label': u"Academia"},
        {'name': 'Other', 'label': u"Other"}
    ]


class JobFunction(Enumerate):

    options = [
        {'name': 'Owner/Director', 'label': u"Owner/Director"},
        {'name': 'Manager', 'label': u"Manager"},
        {'name': 'Assistant Manager', 'label': u"Assistant Manager"},
        {'name': 'Travel Consultant', 'label': u"Travel Consultant"},
        {'name': 'Student', 'label': u"Student"},
        {'name': 'Managing Director', 'label': u"Managing Director"},
        {'name': 'Sales Director', 'label': u"Sales Director"},
        {'name': 'Marketing Director', 'label': u"Marketing Director"},
        {'name': 'Marketing Manager', 'label': u"Marketing Manager"},
        {'name': 'Marketing Assistant', 'label': u"Marketing Assistant"},
        {'name': 'Product Manager', 'label': u"Product Manager"},
        {'name': 'Reservation Staff', 'label': u"Reservation Staff"},
        {'name': 'Other', 'label': u"Other"}
    ]


class WebsiteTarget(Enumerate):

    options = [
        {'name': '_blank', 'label': 'Open in a new window'},
        {'name': '_self', 'label': 'Stay in the the same window'}
    ]


class BannerType(Enumerate):

    options = [
        {'name': 'boxed', 'label': 'Boxed Rectangle (160x80)'},
        {'name': 'sky_scraper', 'label': 'Sky scraper (160x600)'},
        {'name': 'top_banner', 'label': 'Top banner (468x60)'},
        {'name': 'in_line', 'label': 'Inline Rectangle (300x250)'}
    ]

class UK_or_NonUK(Enumerate):

    options =  [
        {'name': 'UK', 'label': u"UK"},
        {'name': 'Non-UK', 'label': u"Non-UK"}
    ]

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

class Region(Enumerate):

    @staticmethod
    def get_labels(id):
        """
        From a given region id (e.g. 'south_east/oxfordshire'), returns a
        tuple with the labels for the region and the county (e.g. 'South East'
        and 'Oxfordshire').
        """
        if id:
            region_id, county_id = id.split('/')
            for region in regions:
                if region['id'] == region_id:
                    for county in region['counties']:
                        if county['id'] == id:
                            return region['label'], county['label']
        return None, None


    @staticmethod
    def get_namespace(value):
        """
        Returns the namespace for all the regions and counties, ready to
        use to draw a selection box in STL. The namespace structure is:

          [{'id': <region id>, 'label': <region label>,
            'counties': [{'id': <county id>, 'label': <county label>,
                          'is_selected': <True | False>}
                         ...]
           }
           ...
          ]
        """
        aux = deepcopy(regions)

        if value is not None:
            region_id = value.split('/')[0]
        else:
            region_id = None

        for region in aux:
            region['is_selected'] = (region['id'] == region_id)
            for county in region['counties']:
                county['is_selected'] = (county['id'] == value)
        return aux


#############################################################################
# Schema
#############################################################################


class Schema(BaseSchema):

    class_uri = 'http://xml.abakuc.com/namespaces/abakuc'
    class_prefix = 'abakuc'

    datatypes = {
        # Roles
        'travel_agent_member': Tokens(default=()),
        'travel_agent_manager': Tokens(default=()),
        'tourist_office_member': Tokens(default=()),
        'tourist_office_manager': Tokens(default=()),
        
        'terms_and_cond': Boolean(default=False,
                                  title=u'Terms &amp Conditions',
                                  is_mandatory= True),
        # User Schema
        'registration_date': Date,
        'user_title': UserTitle(title=u'Title', is_mandatory=True),
        'firstname': Unicode(title=u'First Name', is_mandatory=True),
        'initials': Unicode(title=u'Initials', is_mandatory=False),
        'lastname': Unicode(title=u'Last Name', is_mandatory=True),
        'business_function': BusinessFunction(title=u'Business Function',
                                              is_mandatory=True),
        'job_function': JobFunction(title=u'Job Function', is_mandatory=True),
        'job_title': Unicode(title=u'Job Title', is_mandatory=True),
        'email': EMail(default='', title=u'', is_mandatory=True),
        'contact_me': Boolean(default=True, title=u'', is_mandatory=False),
        'company_name': Unicode(default=None, 
                                title=u'Comapny Name',
                                is_mandatory=False),
        'branch_name': String(title=u'Branch Name', is_mandatory=False),
        
        # Affiliations' Schema
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
        'non_member': Boolean(default=False), 
        
        #Comapny Schema
        'website': URI(title=u'Website Address', is_mandatory=False),
        'business_profile': BusinessProfile(default='Others',
                                            title=u'Business Profile',
                                            is_mandatory=True),
        'business_function': BusinessFunction(default='Other',
                                            title=u'Business Function',
                                            is_mandatory=True),
        #Branch Schema
        'street': Unicode(title=u'Street Name', is_mandatory=True),
        'address': Unicode(title=u'Address', is_mandatory=True),
        'city': Unicode(title=u'Post Town', is_mandatory=True),
        'postcode': Unicode(title=u'Post Code', is_mandatory=True),
        'county': Unicode(title=u'County', is_mandatory=False),
        'region': Region(title=u'Region', is_mandatory=False),
        'country': Unicode(title=u'Country', is_mandatory=False),
        'phone': Unicode(title=u'Phone Number', is_mandatory=True),
        'fax': Unicode(title=u'Fax Number', is_mandatory=True),
        'uk_or_nonuk': UK_or_NonUK(default='UK',
                                   title=u'UK or Non UK',
                                   is_mandatory=False),
        #Country Schema
        'continent': Continent(default='Oceania',
                              title=u'Continent',
                              is_mandatory=True),

        'sub_continent': Unicode(title=u'Sub continent', is_mandatory=True),
        #'sub_continent': SubContinent(default='Oceania',
        #                      title=u'Sub continent',
        #                      is_mandatory=True),
        
        #Advert Schema
        'advert_max_click': Integer(default=100),
        'advert_weight': Integer(default=5),
        'advert_count': Integer(default=0),
        'advert_image:': String(default=''),
        'advert_slot:': String(default=''),
        'advert_pos': String(default=''),
        'advert_target': WebsiteTarget(title=u'Banner Target',
                                        default='_blank'),
        'advert_website': String(default='http://abakuc.com'), 

        #Banner Schema
        'banner_max_click': Integer(default=100),
        'banner_weight': Integer(default=5),
        'banner_count': Integer(default=0),
        'banner_image:': String(default=''),
        'banner_slot:': String(default=''),
        'banner_pos': String(default=''),
        'banner_target': WebsiteTarget(title=u'Banner Target',
                                       default='_blank'),
        'banner_type': BannerType(title=u'Banner Type',
                                       default='boxed'),
        'banner_website': String(default='http://abakuc.com'), 

        #Video Schema
        'video_max_click': Integer(default=100),
        'video_weight': Integer(default=5),
        'video_count': Integer(default=0),
        'video_youtube_code:': String(default=''),
        'video_image:': String(default=''),
        'video_slot:': String(default=''),
        'video_pos': String(default=''),
        'video_target': WebsiteTarget(title=u'Banner Target',
                                      default='_blank'),
        'video_website': String(default='http://abakuc.com'), 
    }

register_schema(Schema)

