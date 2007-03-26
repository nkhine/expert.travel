# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import smtplib

# Import from itools
import itools
from itools import i18n
from itools.i18n import fuzzy
from itools.stl import stl
from itools.web import get_context
from itools.cms.Folder import Folder as iFolder
from itools.cms.Handler import Handler
from itools.cms.registry import register_object_class
from itools.cms.access import AccessControl

# Import from abakuc 
from metadata import BusinessFunction, BusinessProfile, UK_or_NonUK


class Branch(AccessControl, iFolder):

    class_id = 'company branch'
    class_title = u'Company Branch'
    class_icon16 = 'abakuc/images/Branch16.png'
    class_icon48 = 'abakuc/images/Branch48.png'
    class_views = [
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['edit_metadata_form']]
    

    def is_allowed_to_edit(self, user, object):
        if user is None:
            return False

        root = get_context().root
        if root.is_admin(user):
            return True

        get_property = user.metadata.get_property
        return (get_property('abakuc:company_name') == object.parent.name
                and get_property('abakuc:branch_name') == object.name)

    def get_document_types(self):
        return [User]

    ########################################################################
    # Metadata
    def edit_metadata_form(self, context):
        #context = get_context()
        root, user = context.root, context.user
        namespace = {}

        get_property = self.get_metadata().get_property
        # Title
        namespace['street'] = get_property('abakuc:street')
        namespace['address'] = get_property('abakuc:address')
        namespace['post_town'] = get_property('abakuc:city')
        namespace['post_code'] = get_property('abakuc:postcode')
        namespace['phone'] = get_property('abakuc:phone')
        namespace['fax'] = get_property('abakuc:fax')
        # Regions
        #user_region = self.get_property('abakuc:region')
        #namespace['regions'] = Region.get_namespace(user_region)
        # UK or Non-UK
        uk_or_nonuk = get_property('abakuc:uk_or_nonuk')
        uk_or_nonuk = UK_or_NonUK.get_namespace(uk_or_nonuk)
        namespace['uk_or_nonuk'] = uk_or_nonuk
        #namespace['is_travel_agent'] = user.is_travel_agent()
        namespace['user_profile'] = None
        namespace['choose_company'] = None
        namespace['choose_branch'] = None
        namespace['update_company'] = None
       # if namespace['is_travel_agent']:
       #     user_path = str(self.get_pathto(user))
       #     namespace['user_profile'] = user.get_profile_url(self)
       #     namespace['choose_company'] = "%s/;change_company_form" % user_path
       #     namespace['choose_branch'] = "%s/;change_branch_form" % user_path
       #     namespace['update_company'] ="%s/;goto_company_edit_form" % user_path

        handler = self.get_handler('/ui/abakuc/branch_edit_metadata.xml')
        return stl(handler, namespace)


   # edit_metadata__access__ = is_allowed_to_edit
    def edit_metadata(self, context):
        # Set metadata
        set_property = self.metadata.set_property
        for pname in ['abakuc:street', 'abakuc:address', 'abakuc:postcode',
                      'abakuc:city', 'abakuc:phone', 'abakuc:fax',
                      'abakuc:uk_or_nonuk']:
                      #'abakuc:region', 'abakuc:uk_or_nonuk']:
            set_property(pname, context.get_form_value(pname))

            
        # Come back
        return context.come_back(u'Branch modified!')

    ########################################################################
    # Users
    browse_users__access__ = 'is_admin'
    browse_users__label__ = u'Users'
    def browse_users(self, context):
        namespace = {}
        root = context.root
        users = []
        catalog = root.get_handler('.catalog')
        for brain in catalog.search(format=users.User.class_id,
                                    company_name=self.parent.name,
                                    branch_name=self.name):
            user = root.get_handler(brain.abspath)
            users.append({'name': user.name, 'href': self.get_pathto(user)})
        namespace['users'] = users


        handler = self.get_handler('/ui/abakuc/branch_list_users.xml')
        return stl(handler, namespace)


register_object_class(Branch)

class Company(iFolder):

    class_id = 'company'
    class_title = u'Company'
    class_icon16 = 'abakuc/images/Company16.png'
    class_icon48 = 'abakuc/images/Company48.png'
    class_views = [['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['edit_metadata_form'],
                   ['list_users']]

    def get_document_types(self):
        return [Branch]

    ########################################################################
    # User interface
    ########################################################################

    ########################################################################
    # Metadata
   # edit_metadata_form__access__ = is_allowed_to_edit
    def edit_metadata_form(self, context):
        context = get_context()
        root, user = context.root, context.user
        namespace = {}

        get_property = self.get_metadata().get_property
        # Title
        title = get_property('dc:title', language='en')
        namespace['title'] = title
        # Business profile
        business_profile = get_property('abakuc:business_profile')
        business_profile = BusinessProfile.get_namespace(business_profile)
        namespace['business_profile'] = business_profile
        # Business function 
        business_function = get_property('abakuc:business_function')
        business_function = BusinessFunction.get_namespace(business_function)
        namespace['business_function'] = business_function
        # Website
        namespace['website'] = get_property('abakuc:website')
        #namespace['is_travel_agent'] = user.is_travel_agent()
        namespace['user_profile'] = None
        namespace['choose_company'] = None
        namespace['choose_branch'] = None
        namespace['update_branch'] = None
       # if namespace['is_travel_agent']:
       #     user_path = str(self.get_pathto(user))
       #     namespace['user_profile'] = user.get_profile_url(self)
       #     namespace['choose_company'] = "%s/;change_company_form" % user_path
       #     namespace['choose_branch'] = "%s/;change_branch_form" % user_path
       #     namespace['update_branch'] ="%s/;goto_branch_edit_form" % user_path
            
        handler = self.get_handler('/ui/abakuc/company_edit_metadata.xml')
        return stl(handler, namespace)


   # edit_metadata__access__ = is_allowed_to_edit
    def edit_metadata(self, context):
        metadata = self.get_metadata()
        # The title
        title = context.get_form_value('dc:title')
        metadata.set_property('dc:title', title)
        # Websites
        company_website = context.get_form_value('abakuc:website')
        metadata.set_property('abakuc:website', company_website)
        # Business profile
        business_profile = context.get_form_value('abakuc:business_profile')
        metadata.set_property('abakuc:business_profile', business_profile)
        # Business function 
        business_function = context.get_form_value('abakuc:business_function')
        metadata.set_property('abakuc:business_function', business_function)
        # Come back
        return context.come_back(u'Company modified!')

    ########################################################################
    # Users
    # browse_users__access__ = 'is_allowed_to_edit'
    list_users__label__ = u'List Users'
    def list_users(self):
        context = get_context()
        root = context.root

        namespace = {}

        users = []
        catalog = root.get_handler('.catalog')
        for brain in catalog.search(format=Users.User.class_id,
                                    company_name=self.name):
            user = root.get_handler(brain.abspath)
            users.append({'name': user.name, 'href': self.get_pathto(user)})
        namespace['users'] = users

        handler = self.get_handler('/ui/abakuc/branch_list_users.xml')
        return stl(handler, namespace)


register_object_class(Company)



class Companies(iFolder):

    class_id = 'companies'
    class_title = u'Companies'
    class_icon16 = 'abakuc/images/Companies16.png'
    class_icon48 = 'abakuc/images/Companies48.png'
    class_views = [['browse_content?mode=list'],
                   ['new_resource_form'],
                   ['edit_metadata_form'],
                   ['overview']]


    def get_document_types(self):
        return [Company]


    browse_list__label__ = 'Companies'
    browse_thumbnails__label__ = 'Companies'
    browse_content__access__ = 'is_admin'

register_object_class(Companies)
