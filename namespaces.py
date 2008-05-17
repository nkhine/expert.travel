
# Import from the Standard Library
from copy import deepcopy

# Import from itools
from itools import get_abspath
from itools import vfs
from itools.datatypes import Boolean, Date, Integer, String, Unicode, URI
from itools.xml import xml
from itools.schemas import Schema, register_schema



#############################################################################
# Data to load on start-up
#############################################################################

path = get_abspath(globals(), 'regions.txt')
file = vfs.open(path)
lines = file.read().split('\n')
file.close()
regions = []
region_id = None
for line in lines:
    line = line.strip()
    if line:
        id, title = line.split('#')
        if region_id is None:
            region_id = id
            regions.append({'id': id, 'title': title, 'counties': []})
        else:
            id = '%s/%s' % (region_id, id)
            regions[-1]['counties'].append({'id': id, 'title': title})
    else:
        region_id = None


#############################################################################
# Data Types
#############################################################################

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


class Enumerate(String):

    # XXX Shouldn't it be None?
    default = ''

    @classmethod
    def get_namespace(cls, value):
        options = cls.get_options()
        for option in options:
            option['is_selected'] = option['id'] == value
        return options


class UserTitle(Enumerate):

    @classmethod
    def get_options(cls):
        return [{'id': 'Mr', 'label': 'Mr'},
                {'id': 'Mrs', 'label': 'Mrs'},
                {'id': 'Miss', 'label': 'Miss'},
                {'id': 'Dr', 'label': 'Dr'}]


class BusinessProfile(Enumerate):

    @classmethod
    def get_options(cls):
        return [{'id': 'multiple', 'label': 'Multiple'},
                {'id': 'independent', 'label': 'Independent'},
                {'id': 'homeworker', 'label': 'Homeworker'},
                {'id': 'call_centre', 'label': 'Call Centre'},
                {'id': 'other', 'label': 'Other'}]


class BusinessFunction(Enumerate):

    @classmethod
    def get_options(cls):
        return [{'id': 'travel_agent', 'label': 'Travel Agent'},
                {'id': 'tour_Operator', 'label': 'Tour Operator'},
                {'id': 'national_tourist_board',
                 'label': 'National Tourist Board'},
                {'id': 'airline', 'label': 'Airline'},
                {'id': 'representation_company',
                 'label': 'Representation Company'},
                {'id': 'public_relations', 'label': 'Public Relations'},
                {'id': 'association', 'label': 'Association'},
                {'id': 'car_hire', 'label': 'Car Hire'},
                {'id': 'insurance', 'label': 'Insurance'},
                {'id': 'technology', 'label': 'Technology'},
                {'id': 'academia', 'label': 'Academia'},
                {'id': 'other', 'label': 'Other'}]


class JobFunction(Enumerate):

    @classmethod
    def get_options(cls):
        return [{'id': 'owner_director', 'label': 'Owner/Director'},
                {'id': 'manager', 'label': 'Manager'},
                {'id': 'assistant_manager', 'label': 'Assistant Manager'},
                {'id': 'travel_consultant', 'label': 'Travel Consultant'},
                {'id': 'student', 'label': 'Student'},
                {'id': 'managing_director', 'label': 'Managing Director'},
                {'id': 'sales_director', 'label': 'Sales Director'},
                {'id': 'marketing_director', 'label': 'Marketing Director'},
                {'id': 'marketing_manager', 'label': 'Marketing Manager'},
                {'id': 'marketing_assistant', 'label': 'Marketing Assistant'},
                {'id': 'product_manager', 'label': 'Product Manager'},
                {'id': 'reservation_staff', 'label': 'Reservation Staff'},
                {'id': 'other', 'label': 'Other'}]


class Norman(Enumerate):

    @staticmethod
    def get_counties(id):
        """
        From a region id (e.g 'south_east') returns the list of the region's
        counties.
        """
        for region in regions:
            if region['id'] == id:
                return region['counties'][:]
        return None



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
                            return region['title'], county['title']
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


    @staticmethod
    def get_counties(id):
        """
        From a region id (e.g 'south_east') returns the list of the region's
        counties.
        """
        for region in regions:
            if region['id'] == id:
                return region['counties'][:]
        return None



#############################################################################
# Schemas
#############################################################################

class BaseSchema(Schema):

    @classmethod
    def get_datatype(cls, name):
        try:
            return cls.schema[name]
        except KeyError:
            raise xml.XMLError, 'unknown property "%s"' % name



class UserSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/user'
    class_prefix = 'user'

    schema = {
        'terms_and_cond': Boolean(default=False,
                                  title=u'Terms and Conditions',
                                  is_mandatory= True),
        # User
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
        'company_name': Unicode(default=None, title=u'', is_mandatory=False),
        'branch_name': String(title=u'', is_mandatory=False),
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
        'non_member': Boolean(default=False), # XXX
    }

register_schema(UserSchema)



class CompanySchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/company'
    class_prefix = 'company'

    schema = {
        'website': Unicode(title=u'Website Address', is_mandatory=False),
        'business_profile': BusinessProfile(default='Others',
                                            title=u'Business Profile',
                                            is_mandatory=True),
        }

register_schema(CompanySchema)



class BranchSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/branch'
    class_prefix = 'branch'

    schema = {
        'address': Unicode(title=u'Address', is_mandatory=True),
        'city': Unicode(title=u'Post Town', is_mandatory=True),
        'postcode': Unicode(title=u'Post Code', is_mandatory=True),
        'region': Region(title=u'Region', is_mandatory=True),
        'phone': Unicode(title=u'Phone Number', is_mandatory=True),
        'fax': Unicode(title=u'Fax Number', is_mandatory=True),
        }

register_schema(BranchSchema)



class DocumentSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/document'
    class_prefix = 'document'

    schema = {'credits': Unicode,
              'image1': String(default=''),
              'image2': String(default=''),
              'map_image': String(default=''),
              'dyk_title': Unicode,
              'dyk_description': Unicode,
              'top1': Unicode,
              'top2': Unicode,
              'top3': Unicode,
              'top4': Unicode,
              'business_functions': String(default=[])}

register_schema(DocumentSchema)



class PrizeSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/prize'
    class_prefix = 'prize'

    schema = {'start_date': Date,
              'end_date': Date,
              'class_name': String,
              'category': String,
              'percentage': Integer(default=85),
              'fulfillment_company': Unicode,
              'fulfillment_company_email': String(default='')}

register_schema(PrizeSchema)



class ExamSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/exam'
    class_prefix = 'exam'

    schema = {'exam_time': Integer(default=20),
              'questions_nums': Integer(default=20),
              'pass_marks_percentage': Integer(default=70)}

register_schema(ExamSchema)



class GameSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/game'
    class_prefix = 'game'

    schema = {'game_rule': Unicode,
              'game_time': Integer(default=45),
              'attempts_num': Integer(default=3)}

register_schema(GameSchema)



class BannerSchema(BaseSchema):

    class_uri = 'http://xml.traveluni.com/namespaces/banner'
    class_prefix = 'banner'

    schema = {'url': URI,
              'target' : String(default=''),
              'slot0' : String(default=''),
              'slot1' : String(default=''),
              'slot2' : String(default=''),
              'slot3' : String(default=''),
              }

register_schema(BannerSchema)

class BannerTarget(Enumerate):

    @classmethod
    def get_options(cls):
        return [{'id': '_blank', 'label': u"Popup in a new windows"},
                {'id': '_self', 'label': u"Stay in the windows"}, ]



