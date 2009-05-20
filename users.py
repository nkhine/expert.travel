# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
import mimetypes
from datetime import datetime, date
from urllib import urlencode

# Import from itools
from itools import handlers
from itools import uri
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.cms.access import AccessControl
from itools.cms.base import Handler
from itools.cms.binary import Image
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.metadata import Password
from itools.cms.registry import get_object_class
from itools.cms.registry import register_object_class
from itools.cms.users import UserFolder as iUserFolder, User as iUser
from itools.cms.utils import get_parameters
from itools.cms.utils import reduce_string
from itools.cms.widgets import batch, table
from itools.cms.workflow import WorkflowAware
from itools.datatypes import Boolean, Email, Enumerate, Integer, is_datatype
from itools.i18n import format_datetime
from itools.rest import checkid
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
from itools.xhtml import Document as XHTMLDocument
from itools.xml import Parser

# Import from our product
from bookings import Bookings
from companies import Company, Address
from training import Training, Module
from exam import Exam
from marketing import Marketing
from product import Product
from news import News
from jobs import Job, Candidature
from utils import title_to_name, get_sort_name, t1, t2, t3, t4, t5
from metadata import JobTitle, SalaryRange
from forum import Forum

class UserFolder(iUserFolder):
    class_id = 'users'
    class_version = '20040625'
    class_icon16 = 'images/UserFolder16.png'
    class_icon48 = 'images/UserFolder48.png'
    class_views = [['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_user_form'],
                   ['edit_metadata_form'],
                   ['view']]


    view__access__ = 'is_admin'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        columns = [('name', u'Name'),
                   ('title', u'Title'),
                   ('lastname', u'Lastname'),
                   ('firstname', u'Firstname'),
                   ('user_must_confirm', u'Confirm')]
        # Get data
        rows = []
        users = self.search_handlers(handler_class=User)
        for u in users:
            confirm = u.get_property('ikaaro:user_must_confirm')
            if confirm:
                confirm = 'No'
            else:
                confirm = 'Yes'
            rows.append({'id': u.name,
                         'checkbox': True,
                         'img': '/ui/images/User16.png',
                         'name': (u.name,'%s/' % u.name),
                         'title': u.title,
                         'lastname': u.get_property('ikaaro:lastname'),
                         'firstname': u.get_property('ikaaro:firstname'),
                         'user_must_confirm': confirm})

        # Create table
        actions = [('select', u'Select All', 'button_select_all',
                    "return select_checkboxes('browse_list', true);"),
                   ('select', u'Select None', 'button_select_none',
                    "return select_checkboxes('browse_list', false);"),
                   ('remove', 'Remove', 'button_delete', None)]
        if rows:
            sortby = context.get_form_value('sortby', 'id')
            sortorder = context.get_form_value('sortorder', 'up')
            rows.sort(lambda x,y: cmp(x[sortby], y[sortby]))
            if sortorder == 'down':
                rows.reverse()
            namespace['table'] = table(columns, rows, [sortby],
                                       sortorder, actions=actions)
            namespace['msg'] = None
        else:
            namespace['table'] = None
            namespace['msg'] = u'No Users'

        handler = self.get_handler('/ui/abakuc/Users_view.xml')
        return stl(handler, namespace)


    def get_document_types(self):
            return [User]

register_object_class(UserFolder)

########################################################################
# User
########################################################################
class User(iUser, WorkflowAware, Handler):

    class_id = 'user'
    class_version = '20040625'
    class_title = 'User'
    class_icon16 = 'images/User16.png'
    class_icon48 = 'images/User48.png'
    class_views = [['profile'],
                   ['state_form'],
                   ['edit_form', 'edit_account_form',
                    'edit_portrait_form', 'edit_password_form'],
                   ['tasks_list']]


    ########################################################################
    # API
    ########################################################################
    confirm_registration__access__ = True
    def confirm_registration(self, context):
        keep = ['key']
        register_fields = [('newpass', True),
                           ('newpass2', True)]
        # Check register key
        must_confirm = self.get_property('ikaaro:user_must_confirm')
        if context.get_form_value('key') != must_confirm:
            return self.gettext(u"Bad key.").encode('utf-8')

        # Check input data
        error = context.check_form_input(register_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Check passwords
        password = context.get_form_value('newpass')
        password2 = context.get_form_value('newpass2')
        if password != password2:
            return context.come_back(MSG_PASSWORD_MISMATCH, keep=keep)

        # Set user
        self.set_password(password)
        self.del_property('ikaaro:user_must_confirm')

        # Set cookie
        self.set_auth_cookie(context, password)

        message = (u"Operation successful!\n Welcome to Expert.Travel your FREE"
                  u" application for the Travel Trade industry.\n"
                  u"Please setup your company details")
        goto = "./;profile"
        return context.come_back(message, goto=goto)

    # Return the profile url relative to the given handler
    def get_profile_url(self, where_from):
        views = self.get_views()
        if 'to_home' in views:
            home = '/;profile'
        elif 'bmi_home' in views:
            home = '/;profile'
        else:
            home = '/;profile'

        url = str(where_from.get_pathto(self)) + home
        return url


    # FIXME 015 Check usage of this method and clean up
    def is_tourist_office_manager(self, user, object):
        root = self.get_site_root()
        return root.has_user_role(self.name, 'abakuc:training_manager')

    # FIXME 015 Check usage of this method and clean up
    def is_branch_member(self, user, object):
        if user is None:
            return False
        if self.is_admin(user, object):
            return False
        if self.is_tourist_office_manager(user, object):
            return False
        return True

    def is_training(self):
        """
        Check to see if the user is on a training site.
        Return a bool
        """
        training = self.get_site_root()
        if isinstance(training, Training):
            training = True
        else:
            training = False
        return training

    def get_company(self):
        root = self.get_root()
        results = root.search(format='company', members=self.name)
        for company in results.get_documents():
            return root.get_handler(company.abspath)
        return None

    def get_address(self):
        root = self.get_root()
        results = root.search(format='address', members=self.name)
        for address in results.get_documents():
            return root.get_handler(address.abspath)
        return None

    def get_job(self):
        root = self.get_root()
        results = root.search(format='job', members=self.name)
        for job in results.get_documents():
            return root.get_handler(job.abspath)
        return None

    def get_products(self):
        root = self.get_root()
        results = root.search(format='product', members=self.name)
        for product in results.get_documents():
            return root.get_handler(product.abspath)
        return None
    #######################################################################
    # Manage bookings
    def search_bookings(self, query=None, **kw):

        bookings = self.get_handler('.bookings')
        if query or kw:
            ids = bookings.search(query, **kw)
            return bookings.get_rows(ids)
        return bookings.get_rows()

    ########################################################################
    # Indexing
    ########################################################################
    def get_catalog_indexes(self):
        from root import world
        import pprint
        pp = pprint.PrettyPrinter(indent=4)

        indexes = iUser.get_catalog_indexes(self)
        get_property = self.get_metadata().get_property
        # The registration date
        registration_date = get_property('abakuc:registration_date')
        if registration_date is not None:
            indexes['registration_date'] = registration_date
            indexes['registration_year'] = registration_date.year
            indexes['registration_month'] = registration_date.month
            # Other user fields
            root = get_context().root
            #root = context.root
            indexes['function'] = get_property('abakuc:functions')
            address = self.get_address()
            #companies_handler = root.get_handler('companies')
            #if companies_handler:
            #    companies = \
            #    list(companies_handler.search_handlers(handler_class=Company))
            #    for company in companies:
            #        company_title = company.get_handler(company.abspath)
            #        addresses = \
            #            list(company.search_handlers(handler_class=Address))
            #        for address in addresses:
            #            username = self.name
            #            users = address.get_members()
            #            if username in users:
            #                indexes['address'] = address.get_property('abakuc:address')
            #                county = address.get_property('abakuc:county')
            #                indexes['abakuc:county'] = county
            #                if county is not None:
            #                    for row_number in world.search(county=county):
            #                        row = world.get_row(row_number)
            #                        country = row[5]
            #                        region = row[7]
            #                        indexes['country'] = country
            #                        indexes['region'] = region
            #                indexes['company'] = company.get_property('dc:title')
            #                indexes['type'] = company.get_property('abakuc:type')
            #                topics = company.get_property('abakuc:topic')
            #                indexes['topic'] = tuple(topics)
            # Optimise the company/address indexing
            if address:
                company = address.parent
                indexes['address'] = address.get_property('abakuc:address')
                county = address.get_property('abakuc:county')
                indexes['abakuc:county'] = county
                if county is not None:
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        country = row[5]
                        region = row[7]
                        indexes['country'] = country
                        indexes['region'] = region
                indexes['company'] = company.get_property('dc:title')
                indexes['type'] = company.get_property('abakuc:type')
                topics = company.get_property('abakuc:topic')
                indexes['topic'] = tuple(topics)

            # Index the user's training programmes
            training_programmes = []
            training_handler = root.get_handler('training')
            if training_handler:
                trainings = \
                list(training_handler.search_handlers(handler_class=Training))
                for training in trainings:
                    username = self.name
                    users = training.get_members()
                    if username in users:
                        training_programmes.append(training.name)
            indexes['training_programmes'] = training_programmes
    
        pp.pprint(indexes)
        return indexes

    #######################################################################
    # jQuery TABS 
    #######################################################################

    def tabs(self, context):
        """
        User profile tabs:
        We want to split the User details and Company details on two
        different tabs, so that:
        [Profile] [Company]
        """
        # Set Style
        # Add a script
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        #context.scripts.append('/ui/abakuc/ui.tabs.js')
        #context.scripts.append('/ui/abakuc/js/jquery-ui-1.7.1.custom.min.js')
        root = context.root

        namespace = {}
        namespace['user'] = self.user(context)
        #company = self.company(context)
        namespace['company'] = self.company(context)
        address = self.get_address()
        namespace['has_address'] = address
        # Manager tabs
        namespace['is_branch_manager'] = None
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            namespace['is_branch_manager'] = is_branch_manager
            affiliations = self.affiliations(context)
            namespace['affiliations'] = affiliations
            namespace['addresses'] = self.addresses(context)
            namespace['manage'] = self.manage(context)

        template_path = 'ui/abakuc/users/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    def get_tabs_stl(self, context):
        """
        These are dependant on the site type and user.
        
        If site is Training, then the TABS change, so that:
        
        If user has role Training Manager, the TABS are:
        - Manage training
        - News (add)
        - Manage bookings / Add booking module
        - Statistics
        - Other *

        If user has role Branch Manager, Branch Member, the TABS are
        - Current training (list Modules, Exams, Marketing)
        - News - (list News items posted by Users who are in the Contact)
        If the TP has a Booking Module, then
        - Bookings - user can add, view and manage their own bookings)
        
        If site is NOT Training, but any other type, then the TABS are:

        If User is Branch Manager:
        - News (add)
        - Jobs (add)
        - Enquiries - manage enquiries
        - Training (list all training programmes)
        - Administrate

        If User is Branch Member:
        - News (list)
        - Jobs (list)
        - Training (list all training programmes)
        - Administrate
        """
        # Build stl
        root = context.root
        users = root.get_handler('users')
        address = self.get_address()
        #company = address.parent
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False
        namespace = {}
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member
        #  Training Office TABS
        office = self.is_training()
        namespace['office'] = office
        if office is True:
            root = self.get_site_root()
            bookings_module = list(root.search_handlers(handler_class=Bookings))
            is_training_manager = root.has_user_role(self.name, 'abakuc:training_manager')
            namespace['is_training_manager'] = is_training_manager
            if is_training_manager:
                namespace['current_training'] = self.training(context)
                if is_branch_manager:
                    namespace['news'] = self.news_table(context)
                    if bookings_module:
                        for bookings in bookings_module:
                            booking = bookings.get_handler('.bookings')
                            bookings = []
                            for row in booking.get_rows():
                                bookings.append({'index': row.number})
                            namespace['howmany_bookings'] = len(bookings)
                        namespace['bookings'] = self.bookings(context)
                    else:
                        namespace['bookings'] = None 
                else:
                    namespace['news'] = self.news(context)
                    if bookings_module:
                        for bookings in bookings_module:
                            booking = bookings.get_handler('.bookings')
                            bookings = []
                            for row in booking.get_rows():
                                bookings.append({'index': row.number})
                            namespace['howmany_bookings'] = len(bookings)
                        namespace['bookings'] = self.bookings(context)
                    else:
                        namespace['bookings'] = None 
                namespace['statistics'] = self.statistics(context)
            else:
                namespace['news'] = self.news(context)
                if bookings_module:
                    namespace['bookings'] = self.bookings(context)
                else:
                    namespace['bookings'] = None 
        # Other sites
        else:
            namespace['news'] = self.news_table(context)
            namespace['jobs'] = self.jobs_table(context)
            namespace['products'] = self.products_table(context)
            namespace['enquiries'] = self.enquiries_list(context)
        namespace['current_training'] = self.training(context)
        namespace['training'] = self.training_table(context)
        namespace['forum'] = self.forum(context)
        if address:
            company = address.parent
            csv = address.get_handler('log_enquiry.csv')
            results = []
            for row in csv.get_rows():
                date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
                if resolved:
                    continue
                user = users.get_handler(user_id)
                if user.get_property('ikaaro:user_must_confirm') is None:
                   results.append({'index': row.number})
            namespace['howmany'] = len(results)

        template_path = 'ui/abakuc/users/tabs_stl.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    #######################################################################
    # Edit Account
    account_fields = iUser.account_fields + ['abakuc:phone', 'abakuc:job_title',
                    'abakuc:user_disabled']

    edit_account_form__access__ = 'is_allowed_to_edit'
    edit_account_form__label__ = u'Edit'
    edit_account_form__sublabel__ = u'Account'
    def edit_account_form(self, context):
        root = get_context().root
        functions = self.get_property('abakuc:functions')
        logo = self.has_handler('logo')

        # Build the namespace
        namespace = {}
        for key in self.account_fields:
            namespace[key] = self.get_property(key)
        namespace['functions'] = root.get_functions_namespace(functions)
        namespace['logo'] = logo
        # Ask for password to confirm the changes
        if self.name != context.user.name:
            namespace['must_confirm'] = False
        else:
            namespace['must_confirm'] = True

        # Disable account check box
        user = context.user
        is_admin = root.is_admin(user, self) 
        namespace['is_admin'] = is_admin

        handler = self.get_handler('/ui/abakuc/users/edit_account_form.xml')
        return stl(handler, namespace)

    edit_account__access__ = 'is_allowed_to_edit'
    def edit_account(self, context):
        # Check password to confirm changes
        password = context.get_form_value('password')
        user = context.user
        if self.name == user.name:
            if not self.authenticate(password):
                return context.come_back(
                    u"You mistyped your actual password, your account is"
                    u" not changed.")

        # Check the email is good
        email = context.get_form_value('ikaaro:email')
        if not Email.is_valid(email):
            return context.come_back(MSG_INVALID_EMAIL)

        # Check email address has an MX record
        email_uri = 'mailto:'+email
        r1 = get_reference(email_uri)
        host = r1.host
        import dns.resolver
        from dns.exception import DNSException
        # Here we check to see if email host has an MX record
        try:
            # This may take long
            answers = dns.resolver.query(host, 'MX')
        except DNSException, e:
            answers = None
        if not answers:
            message = u'The email supplied is invalid!'
            return context.come_back(MSG_INVALID_EMAIL)


        root = context.root
        results = root.search(email=email)
        if results.get_n_documents():
            message = (u'There is another user with the email "%s", '
                       u'please try again')
        job_title = context.get_form_values('job_title')
        functions = context.get_form_values('functions')
        logo = context.get_form_value('logo')
        # Save changes
        for key in self.account_fields:
            value = context.get_form_value(key)
            self.set_property(key, value)
        self.set_property('abakuc:functions', functions)

        url = ';profile'
        goto = context.uri.resolve(url)
        message = u'Account changed.'
        return context.come_back(message, goto=goto)

    #######################################################################
    # Profile page
    #######################################################################
    profile__access__ = 'is_allowed_to_view'
    profile__label__ = u'Profile'
    def profile(self, context):
        '''
        The user's profile page, is the first point where the user can access
        the rest of the system. Here we want to verify that they belong to a
        company and address, so that the page checks:
        1) Does the user belong to an address
            if not, show the news, jobs and training tabs, but for the profile,
            ask the user to complete profile.
        We have (3) ACL:
            a) Guest
            b) Branch member
            c) Branch manager
        '''
        from root import world
        from datetime import datetime, date

        namespace = {}
        root = context.root
        user = context.user
        users = root.get_handler('users')
        trainings = root.get_handler('training')
        portrait = self.has_handler('portrait')

        # Get Company and Address
        namespace['address'] = None
        address = self.get_address()

        namespace['contact'] = None
        if user is None:
            return u'You need to be registered!'
        if address is not None:
            if address.has_user_role(user.name, 'abakuc:guest'):
                contacts = address.get_property('abakuc:branch_manager')
                if contacts:
                    contact = users.get_handler(contacts[0])
                    namespace['contact'] = contact.get_property('ikaaro:email')
                else:
                    contact = '<span style="color:red;">The administrator</span>'
                    namespace['contact'] = Parser(contact)

        # Is the user on a Training Portal?
        office_name = self.get_site_root()
        office = self.is_training()
        if office:
            is_training_manager = office_name.has_user_role(self.name, 'abakuc:training_manager')
            is_branch_manager = office_name.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = office_name.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = office_name.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
            is_member = is_branch_manager_or_member or is_guest or is_training_manager
        else:
            is_training_manager = False
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False
            is_member = False
        # Whether the user is in TP or not
        # Bool 0/1
        namespace['office'] = office

        # User Role
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['is_admin'] = is_admin
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False

        namespace['is_training_manager'] = is_training_manager
        namespace['is_branch_manager'] = is_branch_manager
        namespace['is_branch_member'] = is_branch_member
        namespace['is_guest'] = is_guest
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        #XXX This does not work if there is no news/jobs
        #Search the catalogue, list 3 news items.
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'news'))
        today = date.today().strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        namespace['nb_news'] = len(documents)
        documents = documents[0:3]
        news_items = []
        for news in documents:
            news = root.get_handler(news.abspath)
            #get = news.get_property
            address = news.parent
            company = address.parent
            url = '/%s/%s/%s/;view' % (company.name, address.name, news.name)
            news_items.append({'url': url,
                               'title': news.title})

        namespace['news_items'] = news_items
        #Search the catalogue, list last 4 jobs.
        query = []
        query.append(EqQuery('format', 'Job'))
        today = date.today().strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        namespace['nb_jobs'] = len(documents)
        documents = documents[0:4]
        jobs = []
        for job in documents:
            job = root.get_handler(job.abspath)
            address = job.parent
            company = address.parent
            url = '/%s/%s/%s' % (company.name, address.name, job.name)
            jobs.append({'url': url,
                         'title': job.title})
        namespace['jobs'] = jobs

        # Training programmes
        items = trainings.search_handlers(handler_class=Training)
        
        # List all training programmes the user belongs to
        is_current_programme = []
        programmes = []
        # List all other training programmes
        other_programmes = []

        for item in items:
            url = 'http://%s' % (item.get_vhosts())
            ns = {'title': item.title_or_name,
                  'url': url}
            if item.has_user_role(self.name, 'abakuc:branch_member'):
                if item.name is office_name.name:
                    is_current_programme.append(ns)
                else:
                    programmes.append(ns)
            else:
                other_programmes.append(ns)
        # Tabs
        namespace['user_tabs'] = self.tabs(context)
        namespace['tabs'] = self.get_tabs_stl(context)

        handler = self.get_handler('/ui/abakuc/users/profile.xml')
        return stl(handler, namespace)

    #######################################################################
    # User upload portrait
    #######################################################################
    @staticmethod
    def get_form(portrait=None):
        root = get_context().root

        namespace = {}
        namespace['portrait'] = portrait

        handler = root.get_handler('ui/abakuc/portrait_form.xml')
        return stl(handler, namespace)


    ########################################################################
    # View user's public profile page
    portrait_form__access__ = 'is_self_or_admin'
    portrait_form__sublabel__ = u'Upload or modify your portrait'
    def portrait_form(self, context, portrait=None):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        portrait = self.has_handler('portrait')
        namespace['form'] = self.get_form(portrait)

        handler = self.get_handler('/ui/abakuc/portrait_metadata.xml')
        return stl(handler, namespace)


    portrait__access__ = 'is_self_or_admin'
    def portrait(self, context):
        portrait = context.get_form_value('portrait')

        ## The portrait
        if context.has_form_value('remove_portrait'):
            if self.has_handler('portrait'):
                self.del_object('portrait')
        elif portrait is not None:
            name, mimetype, data = portrait
            guessed = mimetypes.guess_type(name)[0]
            if guessed is not None:
                mimetype = guessed
            portrait_cls = get_object_class(mimetype)
            portrait = portrait_cls(string=data)
            portrait_name = 'portrait'
            # Check format of portrait
            if not isinstance(portrait, Image):
                msg = u'You can upload a JPG, GIF or PNG file (File size limit is 100K).'
                return context.come_back(msg)
            # Check size
            size = portrait.get_size()
            if size is not None:
                width, height = size
                if width > 150 or height > 150:
                    msg = u'Your portrait is too big (max 150x150 px)'
                    return context.come_back(msg)

            # Add or edit the portrait
            if self.has_handler('portrait'):
                # Edit the portrait
                portrait = self.get_handler('portrait')
                try:
                    portrait.load_state_from_string(data)
                except:
                    self.load_state()
                portrait = portrait.load_state_from_string(string=data)
            else:
                # Add the new portrait
                portrait = portrait_cls(string=data)
                portrait, metadata = self.set_object(portrait_name, portrait)
                metadata.set_property('state', 'public')

        message = u'Portrait uploaded.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)
    ########################################################################
    # View user's public profile page
    view__access__ = 'is_allowed_to_view'
    def view(self, context):
        namespace = {}
        handler_state = self.get_property('state')
        if handler_state == 'public':
            namespace['dc:title'] = None
            return 'Hello'
        else:
            namespace['dc:title'] = 'None'
            handler = self.get_handler('/ui/abakuc/users/view.xml')
            return stl(handler, namespace)

    ########################################################################
    # User's pages 
    user__access__ = 'is_self_or_admin'
    def user(self, context):
        user = context.user
        root = context.root
        address = self.get_address()
        portrait = self.has_handler('portrait')
        namespace = {}
        # User Role
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['is_admin'] = is_admin
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False

        namespace['is_branch_manager'] = is_branch_manager
        namespace['is_branch_member'] = is_branch_member
        namespace['is_guest'] = is_guest
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        #User's state
        url = '/users/%s/' % user.name
        namespace['url'] = url
        namespace['statename'] = self.get_statename()
        state = self.get_state()
        namespace['state'] = self.gettext(state['title'])
        # User Identity
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        namespace['job_title'] = self.get_property('abakuc:job_title')
        namespace['points'] = self.get_property('abakuc:points')
        namespace['portrait'] = portrait

        handler = self.get_handler('/ui/abakuc/users/user.xml')
        return stl(handler, namespace)

    ########################################################################
    # User's company pages 
    ########################################################################
    company__access__ = 'is_self_or_admin'
    def company(self, context):
        root = context.site_root
        here = context.handler or root
        users = self.get_handler('/users')
        user = context.user
        address = self.get_address()
        # Get Company and Address
        namespace = {}
        namespace['user'] = self.user(context)
        namespace['address'] = None
        namespace['contact'] = None
        if user is None:
            return u'You need to be registered!'
        if address is not None:
            is_guest = address.has_user_role(user.name, 'abakuc:guest')
            namespace['is_guest'] = is_guest
            if address.has_user_role(user.name, 'abakuc:guest'):
                contacts = address.get_property('abakuc:branch_manager')
                if contacts:
                    contact = users.get_handler(contacts[0])
                    namespace['contact'] = contact.get_property('ikaaro:email')
                #else:
                #    contact = '<span style="color:red;">the administrator</span>'
                #    namespace['contact'] = Parser(contact)
            # Company
            company = address.parent
            namespace['company'] = {'name': company.name,
                                    'title': company.get_property('dc:title'),
                                    'website': company.get_website(),
                                    'path': here.get_pathto(company)}
            # Address
            addr = {'name': address.name,
                    'address': address.get_property('abakuc:address'),
                    'town': address.get_property('abakuc:town'),
                    'county': address.get_property('abakuc:county'),
                    'postcode':address.get_property('abakuc:postcode'),
                    'phone': address.get_property('abakuc:phone'),
                    'fax': address.get_property('abakuc:fax'),
                    'address_path': here.get_pathto(address)}

            namespace['address'] = addr

        namespace['setup_company_form'] = '/users/%s/;setup_company_form' % (user.name)
        handler = self.get_handler('/ui/abakuc/users/company.xml')
        return stl(handler, namespace)


    ########################################################################
    # List all addresses for user's company 
    ########################################################################
    addresses__access__ = 'is_self_or_admin'
    def addresses(self, context):
        namespace = {}
        address = self.get_address()
        company = address.parent
        response = Company.list_addresses(company, context)
        namespace['response'] = response
        # Return the page
        handler = self.get_handler('/ui/abakuc/response.xml')
        return stl(handler, namespace)

    affiliations__access__ = 'is_self_or_admin'
    def affiliations(self, context, is_branch_manager=None, title=None):
        root = get_context().root
        namespace = {}
        address = self.get_address()
        if address:
            items = address.get_affiliations(context)
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            namespace['is_branch_manager'] = is_branch_manager
            # batch
            batch_start = int(context.get_form_value('batchstart', default=0))
            batch_size = 4
            batch_total = len(items)
            batch_fin = batch_start + batch_size
            if batch_fin > batch_total:
                batch_fin = batch_total
            items = items[batch_start:batch_fin]
            # Namespace
            if items:
                items_batch = batch(context.uri, batch_start, batch_size,
                                  batch_total,
                                  msgs=(u"Your company has one affiliation.",
                                        u"Your company has ${n} affiliations."))
                msg = None
            else:
                items_batch = None
                msg = u"Your company does not have any affiliations."
            namespace['batch'] = items_batch
            namespace['msg'] = msg
            namespace['items'] = items
            
            #items_to_add = []
            #items2keys = set(item['affiliation'] for item in items)
            #for item in affiliations:
            #    if item['id'] not in items2keys:
            #        items_to_add.append(item)
            #items_to_add.sort(key=lambda x: x['id'])
            namespace['items_to_add'] = address.get_affiliations_to_add(context)
            print namespace['items_to_add']

        handler = self.get_handler('/ui/abakuc/users/affiliations.xml')
        return stl(handler, namespace)

    add_affiliation__access__ = 'is_self_or_admin'
    def add_affiliation(self, context):
        check_fields = [('affiliation', True), ('affiliation_no', True)]
        keep = [ x for x, y in check_fields ]
        error = context.check_form_input(check_fields)
        if error is not None:
            message = u'Please select and add an affiliation number.'
            return context.come_back(message, keep=keep)
        affiliation = context.get_form_value('affiliation')
        affiliation_no = context.get_form_value('affiliation_no')
        address = self.get_address()
        if address:
            row = [affiliation, affiliation_no]
            csv = address.get_handler('affiliation.csv')
            csv.add_row(row)
            message = (u"Your affiliation has been added")
            return context.come_back(message.encode('utf-8'))


    edit_affiliation__access__ = 'is_self_or_admin'
    def edit_affiliation(self, context):
        check_fields = [('affiliation_no', True)]
        keep = [ x for x, y in check_fields ]
        error = context.check_form_input(check_fields)
        if error is not None:
            message = u'Please add an affiliation number.'
            return context.come_back(message, keep=keep)
        new_affiliation_no = context.get_form_value('affiliation_no')
        address = self.get_address()
        if address:
            url = ';profile'
            index = context.get_form_value('index', type=Integer)
            csv = address.get_handler('affiliation.csv')
            row = csv.get_row(index)
            if row[1] == new_affiliation_no:
                goto = context.uri.resolve(url)
                message = (u"Affilation number is the same, no changes made!")
                return context.come_back(message.encode('utf-8'), goto=goto)
            row.set_value('affiliation_no', new_affiliation_no)
            goto = context.uri.resolve(url)
            message = (u"The affiliation number has been updated!")
            return context.come_back(message.encode('utf-8'), goto=goto)

    delete_affiliation__access__ = 'is_self_or_admin'
    def delete_affiliation(self, context):
        check_fields = [('index', True)]
        keep = [ x for x, y in check_fields ]
        error = context.check_form_input(check_fields)
        if error is not None:
            message = u'Invalid or no record selected for removal!'
            return context.come_back(message, keep=keep)
        # Get the row
        address = self.get_address()
        if address:
            index = context.get_form_value('index', type=Integer)
            csv = address.get_handler('affiliation.csv')
            if csv:
                csv.del_row(index)
            url = ';profile'
            goto = context.uri.resolve(url)
            message = (u"The affilation has been deleted!")
            return context.come_back(message.encode('utf-8'), goto=goto)

    ########################################################################
    # Manage tab 
    ########################################################################
    manage__access__ = 'is_self_or_admin'
    def manage(self, context):
        address = self.get_address()
        # Get Company and Address
        namespace = {}
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            namespace['is_branch_manager'] = is_branch_manager
            # Manage branch members
            addr = {'name': address.name,
                    'address_path': self.get_pathto(address)}
            namespace['address'] = addr
            # Company
            company = address.parent
            namespace['company'] = {'name':company.name,
                                    'title': company.get_property('dc:title'),
                                    'website': company.get_website(),
                                    'path': self.get_pathto(company)}


        handler = self.get_handler('/ui/abakuc/users/manage.xml')
        return stl(handler, namespace)

    ########################################################################
    # Statistics UI 
    statistics__access__ = 'is_allowed_to_view'
    statistics__label__ = u'Statistics Module'
    def statistics(self, context):
        root = self.get_site_root()
        is_office = self.is_training()
        namespace = {}
        namespace['title'] = root.title_or_name
        namespace['office'] = is_office
        # Statistics
        if is_office:
            response = Training.statistics(root, context)
            namespace['response'] = response
            # Return the page
            handler = self.get_handler('/ui/abakuc/statistics/statistics.xml')
            return stl(handler, namespace)
        else:
            return None 

    #business_type__access__ = 'is_allowed_to_view'
    #business_type__label__ = u'Business type stats'
    #def business_type(self, context):
    #    # Set Style
    #    context.styles.append('/ui/abakuc/yui/fonts/fonts-min.css')
    #    context.styles.append('/ui/abakuc/yui/datatable/assets/skins/sam/datatable.css')
    #    # Add a script
    #    office_name = self.get_site_root()
    #    office = self.is_training()
    #    namespace = {}
    #    namespace['office'] = office
    #    # Statistics
    #    if office:
    #        namespace['title'] = office_name.title_or_name

    #        # Return the page
    #        handler = self.get_handler('/ui/abakuc/statistics/business_type.xml')
    #        return stl(handler, namespace)


    #business_function__access__ = 'is_allowed_to_view'
    #business_function__label__ = u'Business function stats'
    #def business_function(self, context):
    #    # Set Style
    #    context.styles.append('/ui/abakuc/yui/fonts/fonts-min.css')
    #    context.styles.append('/ui/abakuc/yui/datatable/assets/skins/sam/datatable.css')
    #    #context.styles.append('/ui/abakuc/yui/container/assets/skins/sam/container.css')
    #    #context.styles.append('/ui/abakuc/yui/menu/assets/skins/sam/menu.css')
    #    #context.styles.append('/ui/abakuc/yui/button/assets/skins/sam/button.css')
    #    #context.styles.append('/ui/abakuc/yui/calendar/assets/skins/sam/calendar.css')
    #    #context.styles.append('/ui/abakuc/yui/editor/assets/skins/sam/editor.css')
    #    #context.styles.append('/ui/abakuc/yui/resize/assets/skins/sam/resize.css')
    #    #context.styles.append('/ui/abakuc/yui/layout/assets/skins/sam/layout.css')
    #    # Add a script
    #    office_name = self.get_site_root()
    #    office = self.is_training()
    #    namespace = {}
    #    namespace['office'] = office
    #    # Statistics
    #    if office:
    #        namespace['title'] = office_name.title_or_name

    #        # Return the page
    #        #handler = self.get_handler('/ui/abakuc/statistics/chart.xml')
    #        handler = self.get_handler('/ui/abakuc/statistics/business_function.xml')
    #        return stl(handler, namespace)

    #functions__access__ = 'is_allowed_to_view'
    #functions__label__ = u'Job function stats'
    #def functions(self, context):
    #    # Set Style
    #    context.styles.append('/ui/abakuc/yui/fonts/fonts-min.css')
    #    context.styles.append('/ui/abakuc/yui/datatable/assets/skins/sam/datatable.css')
    #    # Add a script
    #    office_name = self.get_site_root()
    #    office = self.is_training()
    #    namespace = {}
    #    namespace['office'] = office
    #    # Statistics
    #    if office:
    #        namespace['title'] = office_name.title_or_name

    #        # Return the page
    #        handler = self.get_handler('/ui/abakuc/statistics/functions.xml')
    #        return stl(handler, namespace)


    ########################################################################
    # Bookings UI
    bookings__access__ = 'is_allowed_to_view'
    bookings__label__ = u'Booking Module'
    def bookings(self, context):
        '''
        Returns the data to populate the TABS method depending on the
        user that is logged in.

        If the user is Trainin Manager, then the Bookings statistics is
        displayed, else we show the users's own bookings.
        '''
        user = context.user
        root = self.get_site_root()
        office = self.is_training()
        # Namespaces
        namespace = {}
        namespace['office'] = office

        # Bookings
        if office:
            items = root.search_handlers(handler_class=Bookings)
            if items is not None:
                for item in list(items):
                    if root.is_training_manager(user, self):
                        response = Bookings.statistics(item, context)
                        namespace['response'] = response
                    else:
                        response = Bookings.manage_bookings(item, context)
                        namespace['response'] = response

            # Return the page
            handler = self.get_handler('/ui/abakuc/bookings/bookings.xml')
            return stl(handler, namespace)


    #######################################################################
    # News - Search Interface
    #######################################################################
    news__access__ = True
    news__label__ = u'Current news'
    def news(self, context):
        '''
        Return all the news of the training manager's company
        including the addresses.

        Ensures that it only works if the user is within a 
        Training prgramme.
        '''
        is_office = self.is_training()
        if is_office is True:
            root = context.root
            office = self.get_site_root()
            users = self.get_handler('/users')
            namespace = {}
            namespace['office'] = office
            namespace['contacts'] = []
            all_news = []
            for name in office.get_property('ikaaro:contacts'):
                #XXX Bug, we always have to have one contact.
                to_user = users.get_handler(name)
                address = to_user.get_address()
                address_news = list(address.search_handlers(handler_class=News))
                all_news = all_news + address_news
                news_ns = []
                for news in all_news:
                    ns = {}
                    news = root.get_handler(news.abspath)
                    get = news.get_property
                    # Information about the news item
                    address = news.parent
                    company = address.parent
                    username = news.get_property('owner')
                    user_exist = users.has_handler(username)
                    usertitle = (user_exist and
                                 users.get_handler(username).get_title() or username)
                    url = '/companies/%s/%s/%s' % (company.name, address.name,
                                                   news.name)
                    description = reduce_string(get('dc:description'),
                                                word_treshold=90,
                                                phrase_treshold=240)
                    news_item = {
                        'url': url,
                        'title': news.title,
                        'closing_date': get('abakuc:closing_date'),
                        'date_posted': get('dc:date'),
                        'owner': usertitle,
                        'description': description}
                    ns['news_item'] = news_item

                    news_ns.append(ns)

            #namespace['all_news'] = {'news': news_ns}
            batch_start = int(context.get_form_value('batchstart', default=0))
            batch_size = 5
            batch_total = len(news_ns)
            batch_fin = batch_start + batch_size
            if batch_fin > batch_total:
                batch_fin = batch_total
            news_ns = news_ns[batch_start:batch_fin]
            # Namespace
            if news_ns:
                news_batch = batch(context.uri, batch_start, batch_size,
                                  batch_total,
                                  msgs=(u"There is 1 news item.",
                                        u"There are ${n} news items."))
                msg = None
            else:
                news_batch = None
                msg = u"Appologies, currently we don't have any news announcements"
            namespace['batch'] = news_batch
            namespace['msg'] = msg
            namespace['news_items'] = news_ns

            # Return the page
            handler = self.get_handler('/ui/abakuc/training/list_news.xml')
            return stl(handler, namespace)
        else:
            return 'Not allowed'
    ########################################################################
    # Create a new news item
    create_news__access__ = 'is_self_or_admin'
    def create_news(self, context):
        address = self.get_address()
        url = '/%s/;new_resource_form?type=news' % (self.get_pathto(address))
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new news item'
        return context.come_back(message, goto=goto)


    ########################################################################
    # Remove news item/s
    remove_news__access__ = 'is_self_or_admin'
    def remove_news(self, context):
        ids = context.get_form_values('ids')
        root = context.root
        if not ids:
            return context.come_back(u'Please select a news item to remove')
        address = self.get_address()
        for news_id in ids:
            address.del_object(news_id)
        return context.come_back(u'News(s) delete')
    ########################################################################
    # Create a new job
    create_job__access__ = 'is_self_or_admin'
    def create_job(self, context):
        address = self.get_address()
        url = '/%s/;new_resource_form?type=Job' % (self.get_pathto(address))
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new job'
        return context.come_back(message, goto=goto)


    ########################################################################
    # Remove job
    remove_job__access__ = 'is_self_or_admin'
    def remove_job(self, context):
        ids = context.get_form_values('ids')
        root = context.root
        if not ids:
            return context.come_back(u'Please select a Job')
        address = self.get_address()
        for job_id in ids:
            address.del_object(job_id)
        return context.come_back(u'Job(s) delete')

    ########################################################################
    # Create a new product
    create_product__access__ = 'is_self_or_admin'
    def create_product(self, context):
        address = self.get_address()
        url = '/%s/;new_resource_form?type=product' % (self.get_pathto(address))
        goto = context.uri.resolve(url)
        message = u'Please use this form to add a new product'
        return context.come_back(message, goto=goto)


    ########################################################################
    # Remove job
    remove_product__access__ = 'is_self_or_admin'
    def remove_product(self, context):
        ids = context.get_form_values('ids')
        root = context.root
        if not ids:
            return context.come_back(u'Please select a Product')
        address = self.get_address()
        for product_id in ids:
            address.del_object(product_id)
        return context.come_back(u'Product(s) delete')
    ########################################################################
    # News table used in the 'tabs' method
    def news_table(self, context):
        root = context.site_root
        here = context.handler or root
        namespace = {}
        address = self.get_address()
        if address:
            company = address.parent
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
            # Table with News
            columns = [('c1', u'Title'),
                       ('c2', u'To be archived on'),
                       ('c3', u'Short description')]
            # Get all News
            address_news = address.search_handlers(handler_class=News)
            # Construct the lines of the table
            news_items = []
            for news in list(address_news):
                handler = root.get_handler(news.abspath)
                get = news.get_property
                # Information about the news
                url = '%s/;view' % here.get_pathto(handler)
                description = reduce_string(get('dc:description'),
                                            word_treshold=10,
                                            phrase_treshold=40)
                news_to_add ={'id': news.name,
                             'checkbox': is_branch_manager_or_member,
                             'img': '/ui/abakuc/images/News16.png',
                             'c1': (get('dc:title'),url),
                             'c2': get('abakuc:closing_date'),
                             'c3': description}
                news_items.append(news_to_add)
        else:
            news_items = []
            columns = []
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        news_items = news_items[batch_start:batch_fin]
        # Order
        sortby = context.get_form_value('sortby', 'c2')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        news_items.sort(lambda x,y: cmp(x[sortby], y[sortby]))
        if reverse:
            news_items.reverse()
        # Namespace
        if news_items:
            actions = [('select', u'Select All', 'button_select_all',
                        "return select_checkboxes('browse_list', true);"),
                       ('select', u'Select None', 'button_select_none',
                        "return select_checkboxes('browse_list', false);"),
                       ('create_news', u'Add news ', 'button_ok',
                        None),
                       ('remove_news', 'Delete News/s', 'button_delete', None)]
            news_table = table(columns, news_items, [sortby], sortorder, actions)
            msgs = (u'There is one news item.', u'There are ${n} news items.')
            news_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            actions = [('create_news', u'Add news ', 'button_ok',
                        None)]
            news_table = table(columns, news_items, [sortby], sortorder, actions)
            news_batch = None
            msg = None

        namespace['news_table'] = news_table
        namespace['news_batch'] = news_batch
        namespace['news_msg'] = msg
        handler = self.get_handler('/ui/abakuc/news/news_table.xml')
        return stl(handler, namespace)


    ########################################################################
    # Job table used in the 'tabs' method
    def jobs_table(self, context):
        root = context.site_root
        here = context.handler or root
        namespace = {}
        address = self.get_address()
        if address:
            company = address.parent
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
            columns = [('c1-2', u'Title'),
                       ('c2-2', u'To be archived on'),
                       ('c3-2', u'Applications'),
                       ('c4-2', u'Short description')]
            # Get all Jobs
            address_jobs = address.search_handlers(handler_class=Job)
            # Construct the lines of the table
            jobs = []
            for item in list(address_jobs):
                get = item.get_property
                handler = root.get_handler(item.abspath)
                # Information about the news
                url = '%s/;view' % here.get_pathto(handler)
                # Information about the job
                description = reduce_string(get('dc:description'),
                                            word_treshold=10,
                                            phrase_treshold=40)
                #Get no of applicants
                users = root.get_handler('users')
                nb_candidatures = 0
                y = root.get_handler(item.abspath)
                candidatures = y.search_handlers(handler_class=Candidature)
                for x in candidatures:
                    user_id = x.get_property('user_id')
                    user = users.get_handler(user_id)
                    if user.has_property('ikaaro:user_must_confirm') is False:
                            nb_candidatures += 1
                job_to_add ={'id': item.name,
                             'checkbox': is_branch_manager_or_member,
                             'img': '/ui/abakuc/images/JobBoard16.png',
                             'c1-2': (get('dc:title'),url),
                             'c2-2': get('abakuc:closing_date'),
                             'c4-2': description}
                if nb_candidatures > 0:
                    job_to_add['c3'] = nb_candidatures,url+';view_candidatures'
                else:
                    job_to_add['c3'] = None
                jobs.append(job_to_add)
            # Set batch informations
            batch_start = int(context.get_form_value('batchstart', default=0))
            batch_size = 5
            batch_total = len(jobs)
            batch_fin = batch_start + batch_size
            if batch_fin > batch_total:
                batch_fin = batch_total
            jobs = jobs[batch_start:batch_fin]
            # Order
            sortby = context.get_form_value('sortby', 'c2-2')
            sortorder = context.get_form_value('sortorder', 'up')
            reverse = (sortorder == 'down')
            jobs.sort(lambda x,y: cmp(x[sortby], y[sortby]))
            if reverse:
                jobs.reverse()
            # Set batch informations
            # Namespace
            if jobs:
                actions = [('select', u'Select All', 'button_select_all',
                            "return select_checkboxes('browse_list', true);"),
                           ('select', u'Select None', 'button_select_none',
                            "return select_checkboxes('browse_list', false);"),
                           ('create_job', u'Add new job', 'button_ok',
                            None),
                           ('remove_job', 'Delete Job/s', 'button_delete', None)]
                job_table = table(columns, jobs, [sortby], sortorder, actions)
                msgs = (u'There is one job.', u'There are ${n} jobs.')
                job_batch = batch(context.uri, batch_start, batch_size,
                                  batch_total, msgs=msgs)
                msg = None
            else:
                jobs_actions = [('create_job', u'Add new job', 'button_ok',
                            None)]
                job_table = table(columns, jobs, [sortby], sortorder, jobs_actions)
                job_batch = None
                msg = None
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False
            job_table = None
            job_batch = None
            msg = None

        namespace['job_table'] = job_table
        namespace['job_batch'] = job_batch
        namespace['job_msg'] = msg
        handler = self.get_handler('/ui/abakuc/jobs/jobs_table.xml')
        return stl(handler, namespace)

    ########################################################################
    # Product table used in the 'tabs' method
    def products_table(self, context):
        root = context.site_root
        here = context.handler or root
        namespace = {}
        address = self.get_address()
        if address:
            company = address.parent
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
            columns = [('c1-3', u'Title'),
                       ('c2-3', u'To be archived on'),
                       ('c3-3', u'Applications'),
                       ('c4-3', u'Short description')]
            # Get all Jobs
            address_products = address.search_handlers(handler_class=Product)
            # Construct the lines of the table
            products = []
            for product in list(address_products):
                get = product.get_property
                # Information about the job
                handler = root.get_handler(product.abspath)
                # Information about the news
                url = '%s/;view' % here.get_pathto(handler)
                description = reduce_string(get('dc:description'),
                                            word_treshold=10,
                                            phrase_treshold=40)
                closing_date = get('abakuc:closing_date')
                # All products should have a closing date
                if closing_date is None:
                    closing_date = date.today()
                #Get no of applicants
                product_to_add ={'id': product.name,
                             'checkbox': is_branch_manager_or_member,
                             'img': '/ui/abakuc/images/JobBoard16.png',
                             'c1-3': (get('dc:title'),url+';view'),
                             'c2-3': closing_date,
                             'c4-3': description}
                products.append(product_to_add)
            # Set batch informations
            batch_start = int(context.get_form_value('batchstart', default=0))
            batch_size = 5
            batch_total = len(products)
            batch_fin = batch_start + batch_size
            if batch_fin > batch_total:
                batch_fin = batch_total
            products = products[batch_start:batch_fin]
            # Order
            sortby = context.get_form_value('sortby', 'c1-3')
            sortorder = context.get_form_value('sortorder', 'up')
            reverse = (sortorder == 'down')
            products.sort(lambda x,y: cmp(x[sortby], y[sortby]))
            if reverse:
                products.reverse()
            # Set batch informations
            # Namespace
            if products:
                actions = [('select', u'Select All', 'button_select_all',
                            "return select_checkboxes('browse_list', true);"),
                           ('select', u'Select None', 'button_select_none',
                            "return select_checkboxes('browse_list', false);"),
                           ('create_product', u'Add new Product', 'button_ok',
                            None),
                           ('remove_product', 'Delete Product/s', 'button_delete', None)]
                product_table = table(columns, products, [sortby], sortorder, actions)
                msgs = (u'There is one product.', u'There are ${n} products.')
                product_batch = batch(context.uri, batch_start, batch_size,
                                  batch_total, msgs=msgs)
                msg = None
            else:
                products_actions = [('create_product', u'Add new product', 'button_ok',
                            None)]
                product_table = table(columns, products, [sortby], sortorder, products_actions)
                product_batch = None
                msg = None
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False
            product_table = None
            product_batch = None
            msg = None

        namespace['product_table'] = product_table
        namespace['product_batch'] = product_batch
        namespace['product_msg'] = msg
        handler = self.get_handler('/ui/abakuc/product/products_table.xml')
        return stl(handler, namespace)
    ########################################################################
    # List Enquiries
    def enquiries_list(self, context):
        root = context.root
        users = root.get_handler('users')

        namespace = {}
        address = self.get_address()
        if address:
            company = address.parent

            csv = address.get_handler('log_enquiry.csv')
            url = '/companies/%s/%s/' % (company.name, address.name)
            print url
            results = []
            for row in csv.get_rows():
                date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
                if resolved:
                    continue
                user = users.get_handler(user_id)
                if user.get_property('ikaaro:user_must_confirm') is None:
                   results.append({
                       'index': row.number,
                       'email': user.get_property('ikaaro:email'),
                       'enquiry_subject': enquiry_subject})
                results.reverse()
            namespace['enquiries'] = results
            namespace['howmany'] = len(results)
            namespace['url'] = url
        else:
            namespace['enquiries'] = None 
            namespace['howmany'] = None
            namespace['url'] = None

        handler = self.get_handler('/ui/abakuc/enquiries/enquiries_list.xml')
        return stl(handler, namespace)

    # List all enquiries the user has made
    my_enquiries__access__ = 'is_self_or_admin'
    def my_enquiries(self, context):
        root = context.root
        companies = root.get_handler('companies')
        items = companies.search_handlers(handler_class=Company)
        for item in items:
            addresses = item.search_handlers(handler_class=Address)
            for address in addresses:
                csv = address.get_handler('log_enquiry.csv')
                results = []
                for row in csv.get_rows():
                    date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
                    if resolved:
                        continue
                    # Return my enquiries
                    if user_id == self.name:
                        print enquiry_subject

    ########################################################################
    # Training table used in the 'tabs' method
    def training_table(self, context):
        namespace = {}
        #Programme
        office = self.get_site_root()
        to_url = str(self.get_pathto(office))
        programme = {}
        programme['title'] = office.title_or_name
        programme['url'] = to_url
        namespace['programme'] = programme
        user = context.user
        root = context.root
        is_admin = root.is_admin(user, self)
        namespace['is_admin'] = is_admin
        training = root.get_handler('training')
        # Table
        columns = [('title', u'Title'),
                   ('function', u'Function'),
                   ('description', u'Short description')]
        # Get all Training programmes
        items = training.search_handlers(handler_class=Training)
        trainings = []
        for item in items:
            url = 'http://%s' % (item.get_vhosts())
            ns = {'title': item.title_or_name,
                  'url': url}
            is_open = item.get_property('ikaaro:website_is_open')
            if is_open is True:
                get = item.get_property
                # Information about the training
                url = 'http://%s' % (item.get_vhosts())
                # XXX fix so that we can extract the first uri
                if item:
                    is_training_manager = item.has_user_role(self.name, 'abakuc:training_manager')
                    is_branch_manager = item.has_user_role(self.name, 'abakuc:branch_manager')
                    is_branch_member =item.has_user_role(self.name, 'abakuc:branch_member')
                    is_guest = item.has_user_role(self.name, 'abakuc:guest')
                    is_branch_manager_or_member = is_branch_manager or is_branch_member
                    is_member = is_branch_manager_or_member or is_guest or is_training_manager
                else:
                    is_training_manager = False
                    is_branch_manager = False
                    is_branch_member = False
                    is_guest = False
                    is_branch_manager_or_member = False
                    is_member = False
                # from the tuple
                if item.name is not office.name:
                    description = reduce_string(get('dc:description'),
                                                word_treshold=50,
                                                phrase_treshold=200)
                    training_to_add ={'id': item.name,
                                     'checkbox': is_branch_manager, # XXX fix this.
                                     'url': url,
                                     'login': url+'/;login_form',
                                     'is_training_manager': is_training_manager,
                                     'is_branch_manager_or_member': is_branch_manager_or_member,
                                     'is_guest': is_guest,
                                     'is_member': is_member,
                                     'img': '/ui/abakuc/images/Training16.png',
                                     'title': get('dc:title'),
                                     'description': description}
                    trainings.append(training_to_add)

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(trainings)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        training_items = trainings[batch_start:batch_fin]
        # Order
        sortby = context.get_form_value('sortby', 'id')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        training_items.sort(lambda x,y: cmp(x[sortby], y[sortby]))
        if reverse:
            trainings.reverse()
        # Set batch informations
        # Namespace
        if training_items:
            #actions = [('select', u'Select All', 'button_select_all',
            #            "return select_checkboxes('browse_list', true);"),
            #           ('select', u'Select None', 'button_select_none',
            #            "return select_checkboxes('browse_list', false);"),
            #           ('create_training', u'Add new training', 'button_ok',
            #            None),
            #           ('remove_training', 'Delete training/s', 'button_delete', None)]
            #training_table = table(columns, training_items, [sortby], sortorder, actions)
            msgs = (u'There is one training.', u'There are ${n} training programmes.')
            training_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            #training_table = None
            training_batch = None
            msg = u'No training programmes!'

        #namespace['training_table'] = training_table
        namespace['batch'] = training_batch
        namespace['items'] = training_items
        namespace['msg'] = msg
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)

    ########################################################################
    # Current training
    training__access__ = 'is_allowed_to_view'
    training__sublabel__ = u'Current training programme'
    def training(self, context):
        namespace = {}
        user = context.user
        root = context.root
        users = root.get_handler('users')

        # Get Company and Address
        namespace['address'] = None
        address = self.get_address()

        # Is the user on a Training Portal?
        office = self.is_training()
        namespace['office'] = office
        if office is True:
            root = self.get_site_root()
            is_training_manager = root.has_user_role(self.name, 'abakuc:training_manager')
            namespace['is_training_manager'] = is_training_manager
        # Get TP modules
        module_ns = []
        if office:
            modules = root.get_modules()
            xx = [
                {'name': x.name, 'title': '%d - %s' % (i+1, x.title)}
                for i, x in enumerate(modules)]
            # Sort the modules
            modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                            get_sort_name(y.name)))

            namespace['modules'] = []

            # Index the modules by name
            for index, module in enumerate(modules):
                module_index = modules.index(module)
                is_first_module = module_index == 0
                is_last_module = module_index == len(modules) - 1
                # Get all of the modules' properties
                last_exam_passed = True 
                get = module.get_property
                url = '/%s/;view' %  module.name
                description = reduce_string(get('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                ns = {'title': module.title_or_name, 'url': None,
                        'description': description, 'index': index}
                
                if is_training_manager:
                    ns['url'] = url
                    ns['manage_marketing'] = None
                    ns['add_marketing'] = None
                    ns['manage_exam'] = None
                    ns['add_exam'] = None
                    ### Marketing
                    marketing_forms = list(module.search_handlers(format=Marketing.class_id))
                    for marketing_form in marketing_forms:
                        if marketing_form is not None:
                            title = marketing_form.title_or_name
                            url = '/%s/%s/;analyse' % (module.name, marketing_form.name)
                            marketing = {'title': title,
                                         'url': url}
                            ns['manage_marketing'] = marketing
                        else:
                            url = '/%s/;new_resource_form?type=marketing' % module.name
                            marketing = {'title': None, 'url': url}
                            ns['add_marketing'] = marketing
                    ### Exam 
                    exams = list(module.search_handlers(format=Exam.class_id))
                    for exam in exams:
                        if exam is not None:
                            title = exam.title_or_name
                            url = '/%s/%s/;analyse' % (module.name, exam.name)
                            exam = {'title': title,
                                         'url': url}
                            ns['manage_exam'] = exam
                        else:
                            url = '/%s/;new_resource_form?type=marketing' % module.name
                            ns['add_exam'] = {'title': None, 'url': url}
                else:
                    if is_first_module:
                        last_exam_passed = True
                        ns['url'] = url 
                        ns['exam'] = None
                        ### Marketing
                        marketing_form = module.get_marketing_form(self.name)
                        ns['marketing'] = None
                        if marketing_form is not None:
                            passed = marketing_form.get_result(self.name)[0]
                            if passed is False:
                                title = marketing_form.title_or_name
                                url = '/%s/%s/;fill_form' % (module.name, marketing_form.name)
                                marketing = {'title': title,
                                             'passed': passed,
                                             'url': url}
                                ns['marketing'] = marketing
                                exam = None
                        else:
                            # Exams
                            exam = None
                            exs = list(module.search_handlers(format=Exam.class_id))
                            if exs != []:
                                exam = module.get_exam(self.name)
                                last_exam_passed = False
                                if exam is not None:
                                    result = exam.get_result(self.name)
                                    passed, n_attempts, kk, mark, kk = result
                                    url = '/%s/%s/;take_exam_form' % (module.name,
                                                                     exam.name)
                                    exam = {'passed': passed, 
                                            'attempts': n_attempts,
                                            'mark': str(round(mark, 1)), 
                                            'url': url}
                                    last_exam_passed = passed
                                    ns['exam'] = exam

                    else:
                    #elif is_last_module:
                        # We need to find out if the exam has been
                        # passed in the previous modules
                        ns['url'] = None
                        ns['exam'] = None
                        prev_module = module.get_prev_module()
                        exs = list(prev_module.search_handlers(format=Exam.class_id))
                        if exs != []:
                            exam = prev_module.get_exam(self.name)
                            if exam is not None:
                                passed = exam.get_result(self.name)[0]
                                #passed, n_attempts, kk, mark, kk = result
                                if passed:
                                    ns['url'] = url
                                    # we need to get the current marketing form
                                    ### Marketing
                                    marketing_form = module.get_marketing_form(self.name)
                                    ns['marketing'] = None
                                    if marketing_form is not None:
                                        passed = marketing_form.get_result(self.name)[0]
                                        if passed is False:
                                            title = marketing_form.title_or_name
                                            url = '/%s/%s/;fill_form' % (module.name, marketing_form.name)
                                            marketing = {'title': title,
                                                         'passed': passed,
                                                         'url': url}
                                            ns['marketing'] = marketing
                                            ns['exam'] = None
                                    else:
                                        exs = list(module.search_handlers(format=Exam.class_id))
                                        if exs != []:
                                            exam = module.get_exam(self.name)
                                            if exam is not None:
                                                passed = exam.get_result(self.name)[0]
                                                if passed:
                                                    result = exam.get_result(self.name)
                                                    passed, n_attempts, kk, mark, kk = result
                                                    exam = {'passed': passed, 
                                                            'attempts': n_attempts,
                                                            'mark': str(round(mark, 1)), 
                                                            'url': None}
                                                    last_exam_passed = passed
                                                else:
                                                    url = '/%s/%s/;take_exam_form' % (module.name,
                                                                                     exam.name)
                                                    exam = {'passed': False, 
                                                            'attempts': None,
                                                            'mark': None, 
                                                            'url': url}
                                                ns['exam'] = exam

                # Add namespace
                #allowed_to_take_exam = root.is_allowed_to_take_exam(self.name, item)
                module_ns.append(ns)
                namespace['programme'] = {'title': root.title_or_name,
                          'modules': module_ns,
                          'league': '../../;league_table'}

        # User Role
        # XXX Fix so that we have the permissions for TP
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['is_admin'] = is_admin
        if address:
            is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')
            is_branch_member = address.has_user_role(self.name, 'abakuc:branch_member')
            is_guest = address.has_user_role(self.name, 'abakuc:guest')
            is_branch_manager_or_member = is_branch_manager or is_branch_member
        else:
            is_branch_manager = False
            is_branch_member = False
            is_guest = False
            is_branch_manager_or_member = False

        namespace['is_branch_manager'] = is_branch_manager
        namespace['is_branch_member'] = is_branch_member
        namespace['is_guest'] = is_guest
        namespace['is_branch_manager_or_member'] = is_branch_manager_or_member

        namespace['contact'] = None
        if user is None:
            return u'You need to be registered!'
        if address:
            if address.has_user_role(user.name, 'abakuc:guest'):
                contacts = address.get_property('abakuc:branch_manager')
                if contacts:
                    contact = users.get_handler(contacts[0])
                    namespace['contact'] = contact.get_property('ikaaro:email')
                else:
                    contact = '<span style="color:red;">The administrator</span>'
                    namespace['contact'] = Parser(contact)

        handler = self.get_handler('/ui/abakuc/training/profile.xml')
        return stl(handler, namespace)
    ########################################################################
    # Setup Company/Address
    setup_company_form__access__ = 'is_self_or_admin'
    setup_company_form__sublabel__ = u'Switch to another company'
    def setup_company_form(self, context):
        name = context.get_form_value('dc:title')
        name = name.strip()

        namespace = {}
        namespace['name'] = name

        if name:
            name = name.lower()
            found = []
            companies = self.get_handler('/companies')
            for company in companies.search_handlers():
                title = company.get_property('dc:title')
                if name not in title.lower():
                    continue
                found.append({'name': company.name, 'title': title})
            found.sort()
            namespace['n_found'] = len(found)
            namespace['found'] = found
            namespace['form'] = Company.get_form()
        else:
            namespace['found'] = None
            namespace['form'] = None

        handler = self.get_handler('/ui/abakuc/users/setup_company.xml')
        return stl(handler, namespace)


    setup_company__access__ = 'is_self_or_admin'
    def setup_company(self, context):
        # Add Company
        title = context.get_form_value('dc:title')

        if not title:
            message = u'Please give a Name to your Company'
            return context.come_back(message)

        # Description
        description = context.get_form_value('dc:description')
        subject = context.get_form_value('dc:subject')
        # Check the Logo
        logo_form = context.get_form_value('logo')
        if logo_form:
            name, mimetype, body = logo_form
            guessed = mimetypes.guess_type(name)[0]
            if guessed is not None:
                mimetype = guessed
            logo_cls = get_object_class(mimetype)
            logo = logo_cls(string=body)
            logo_name = 'logo'
            # Check format
            if not isinstance(logo, Image):
                msg = u'Your logo must be an Image PNG or JPEG'
                return context.come_back(msg)
            # Check size
            size = logo.get_size()
            if size is not None:
                width, height = size
                if width > 200 or height > 200:
                    msg = u'Your logo is too big (max 200x200 px)'
                    return context.come_back(msg)

        # Add the company
        root = context.root
        companies = root.get_handler('/companies')
        name = title_to_name(title)
        if companies.has_handler(name):
            message = u'The Company already exist'
            return context.come_back(message)

        company, metadata = self.set_object('/companies/%s' % name, Company())

        # Set Properties
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')

        metadata.set_property('dc:title', title, language='en')
        metadata.set_property('dc:description', description)
        metadata.set_property('dc:subject', subject)
        metadata.set_property('abakuc:website', website)
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('abakuc:type', types)
        metadata.set_property('ikaaro:website_is_open', True)

        # Add the logo
        if logo_form:
            logo, logo_metadata = company.set_object(logo_name, logo)
            logo_metadata.set_property('state', 'public')

        # Link the User to the Company
        company.set_user_role(self.name, 'abakuc:branch_manager')

        root = context.root
        # Remove from old company
        old_company = self.get_company()
        if old_company is not None:
            old_company.set_user_role(self.name, None)
        # Set the Address..
        name = name.encode('utf_8').replace('&', '%26')
        return context.uri.resolve(';setup_address_form?company=%s' % name)



    setup_address_form__access__ = 'is_self_or_admin'
    def setup_address_form(self, context):
        company_name = context.get_form_value('company')
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)

        namespace = {}
        namespace['company_name'] = company_name
        namespace['company_title'] = company.get_title()
        #XXX If there is a logo, it lists this as well.
        namespace['addresses'] = [
            {'name': x.name, 'title': x.get_title(),
             'postcode': x.get_property('abakuc:postcode')}
            for x in company.search_handlers(handler_class=Address) ]
        namespace['addresses'].sort(key=lambda x: x['postcode'])
        namespace['form'] = Address.get_form()

        handler = self.get_handler('/ui/abakuc/users/setup_address.xml')
        return stl(handler, namespace)


    setup_address_select__access__ = 'is_self_or_admin'
    def setup_address_select(self, context):
        user = context.user
        company_name = context.get_form_value('company_name')
        address_name = context.get_form_value('address_name')

        # Add to new address
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)
        address = company.get_handler(address_name)
        reviewers = address.get_property('abakuc:branch_manager')
        if not reviewers:
            address.set_user_role(self.name, 'abakuc:branch_manager')
        else:
            address.set_user_role(self.name, 'abakuc:guest')
        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address selected.'
        home = '/users/%s/;edit_account_form' % (user.name)
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_self_or_admin'
    def setup_address(self, context):
        user = context.user
        name = context.get_form_value('company_name')
        company = self.get_handler('/companies/%s' % name)

        # Add Address
        address = context.get_form_value('abakuc:address')
        if not address:
            message = u'Please give an Address'
            return context.come_back(message)

        name = title_to_name(address)
        if company.has_handler(name):
            message = u'The address already exist'
            return context.come_back(message)


        if not context.get_form_value('abakuc:county'):
            message = u'Please choose a county'
            return context.come_back(message)

        address, metadata = company.set_object(name, Address())

        # Set Properties
        for name in ['address', 'county', 'town', 'postcode',
                     'phone', 'fax']:
            name = 'abakuc:%s' % name
            value = context.get_form_value(name)
            address.set_property(name, value)

        # Link the User to the Address
        address.set_user_role(self.name, 'abakuc:branch_manager')

        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address setup done.'
        home = '/users/%s/;edit_account_form' % (user.name)
        goto = context.uri.resolve(home)
        return context.come_back(message, goto=goto)

    ########################################################################
    # Setup training
    setup_training_form__access__ = 'is_admin'
    setup_training_form__sublabel__ = u'Setup a training programme'
    def setup_training_form(self, context):
        name = context.get_form_value('dc:title')
        name = name.strip()

        namespace = {}
        namespace['name'] = name

        if name:
            name = name.lower()
            found = []
            trainings = self.get_handler('/training')
            for training in trainings.search_handlers():
                title = training.get_property('dc:title')
                if name not in title.lower():
                    continue
                found.append({'name': training.name, 'title': title})
            found.sort()
            namespace['n_found'] = len(found)
            namespace['found'] = found
            namespace['form'] = Training.get_training_form()
        else:
            namespace['found'] = None
            namespace['form'] = None

        handler = self.get_handler('/ui/abakuc/training/user_setup_training.xml')
        return stl(handler, namespace)


    setup_training__access__ = 'is_self_or_admin'
    def setup_training(self, context):
        # Add Company
        title = context.get_form_value('dc:title')

        if not title:
            message = u'Please give a Name to your training'
            return context.come_back(message)

        # Add the company
        root = context.root
        trainings = root.get_handler('/training')
        name = title_to_name(title)
        if trainings.has_handler(name):
            message = u'The training already exist'
            return context.come_back(message)

        training, metadata = self.set_object('/training/%s' % name, Training())

        # Set Properties
        topics = context.get_form_values('topic')
        vhosts = context.get_form_values('ikaaro:vhosts')
        metadata.set_property('dc:title', title, language='en')
        metadata.set_property('ikaaro:vhosts', vhosts)
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('ikaaro:website_is_open', True)

        message = u'trainings setup done.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

    forum__access__ = True
    def forum(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        site_root = self.get_site_root()
        namespace = {}
        forums = []
        if isinstance(site_root, Training):
            namespace['office'] = True
            forum = list(site_root.search_handlers(format=Forum.class_id))
            for item in forum:
                forums.append(item)
        else:
            namespace['office'] = False 
            # Get the expert.travel forum
            forum = list(site_root.search_handlers(format=Forum.class_id))
            for item in forum:
                forums.append(item)
            # Get all Training programmes forums
            root = context.root
            training = root.get_handler('training')
            items = training.search_handlers(handler_class=Training)
            for item in items:
                tp_forum = list(item.search_handlers(format=Forum.class_id))
                is_open = item.get_property('ikaaro:website_is_open')
                if is_open is True:
                    for item in tp_forum:
                        item != []
                        forums.append(item)
        # Build the select list of forums and their URLs
        current_forums = []
        forum_links = []
        for item in forums:
            ns = {}
            root = item.get_site_root()
            title = item.title_or_name
            language = item.get_property('dc:language')
            description = reduce_string(item.get_property('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            if isinstance(root, Training):
                url = 'http://%s/%s' % ((str(root.get_vhosts()[0])), item.name)
            else:
                url = '/%s' % (item.name)
            # List the last 5 threads for each forum
            threads = item.get_thread_namespace(context)[:5]
            forum_to_add = {'title': title,
                            'description': description,
                            'language': language,
                            'url': url,
                            'threads': threads}

            ns['forum'] = forum_to_add
            current_forums.append(ns)
            forum_links.append({'title': title,
                            'url': url,
                            'is_selected': None})

        # Set batch informations
        batch_start = int(context.get_form_value('t5', default=0))
        batch_size = 2
        batch_total = len(current_forums)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        current_forums = current_forums[batch_start:batch_fin]
         # Namespace
        if current_forums:
            forums_batch = t5(context.uri, batch_start, batch_size,
                              batch_total, msgs=(u"There is 1 forum.",
                                    u"There are ${n} forums."))
            msg = None
        else:
            forums_batch = None
            msg = u"Appologies, currently we don't have any forums"
        namespace['batch'] = forums_batch
        namespace['msg'] = msg
       
        namespace['forum_links'] = forum_links
        namespace['forum'] = current_forums
        namespace['my_threads'] = '/users/%s/;my_threads' % self.name 
        handler = self.get_handler('/ui/abakuc/forum/list.xml')
        return stl(handler, namespace)  

    my_threads__access__ = 'is_self_or_admin'
    def my_threads(self, context):
        root = context.root
        users = root.get_handler('users')
        # Set Style
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        username = self.name
        results = root.search(format='ForumThread', owner=username)
        namespace = {}
        my_threads = []
        for item in results.get_documents():
            hostname = get_context().uri.authority.host
            thread = self.get_handler(item.abspath)
            forum = thread.parent
            site_root = forum.parent
            if isinstance(site_root, Training):
                url = 'http://%s/%s' % ((str(site_root.get_vhosts()[0])), forum.name)
            else:
                language = forum.get_property('dc:language')
                # XXX update in production
                url = 'http://%s.expert_travel/%s' % (language, forum.name)
            accept_language = context.get_accept_language()
            title = thread.title
            thread_url = '%s/%s' % (url, thread.name)
            last = thread.get_last_post()
            last_author_id = last.get_property('owner')
            last_metadata = users.get_handler('%s.metadata' % last_author_id)
            add_my_posts = {'name': thread.name,
                            'forum_title': forum.title,
                            'forum_url': url,
                            'title': title,
                            'author': (self.get_title() or
                                self.get_property('dc:title') or
                                self.get_property('ikaaro:email')),
                            'replies': len(thread.get_replies()),
                            'last_date': format_datetime(last.get_mtime(), accept_language),
                            'last_author': (users.get_handler(last_author_id).get_title() or
                                last_metadata.get_property('dc:title') or
                                last_metadata.get_property('ikaaro:email')),
                            'last_post': last.name,
                            'url': thread_url}
            my_threads.append(add_my_posts)
        #forums = []
        #if isinstance(site_root, Training):
        #    namespace['office'] = True
        #    forum = list(site_root.search_handlers(format=Forum.class_id))
        #    for item in forum:
        #        forums.append(item)
        #else:
        #    namespace['office'] = False 
        #    # Get the expert.travel forum
        #    forum = list(site_root.search_handlers(format=Forum.class_id))
        #    for item in forum:
        #        forums.append(item)
        #    # Get all Training programmes forums
        #    training = root.get_handler('training')
        #    items = training.search_handlers(handler_class=Training)
        #    for item in items:
        #        tp_forum = list(item.search_handlers(format=Forum.class_id))
        #        for item in tp_forum:
        #            is_open = item.get_property('ikaaro:website_is_open')
        #            if is_open is True:
        #                item != []
        #                forums.append(item)
        ## Build the select list of forums and their URLs
        #my_threads = []
        #for item in forums:
        #    ns = {}
        #    root = item.get_site_root()
        #    title = item.title_or_name
        #    description = reduce_string(item.get_property('dc:description'),
        #                                word_treshold=90,
        #                                phrase_treshold=240)
        #    if isinstance(root, Training):
        #        url = 'http://%s/%s' % ((str(root.get_vhosts()[0])), item.name)
        #    else:
        #        url = '/%s' % (item.name)
        #    # Locate all my threads
        #    threads = list(item.search_handlers(handler_class=item.thread_class))
        #    for thread in threads:
        #        my_posts = self.name == thread.get_property('owner')
        #        accept_language = context.get_accept_language()
        #        if my_posts:
        #            title = thread.title
        #            thread_url = '%s/%s' % (url, thread.name)
        #            last = thread.get_last_post()
        #            last_author_id = last.get_property('owner')
        #            last_metadata = users.get_handler('%s.metadata' % last_author_id)
        #            add_my_posts = {'name': thread.name,
        #                            'forum_title': item.title,
        #                            'forum_url': url,
        #                            'title': title,
        #                            'author': (self.get_title() or
        #                                self.get_property('dc:title') or
        #                                self.get_property('ikaaro:email')),
        #                            'replies': len(thread.get_replies()),
        #                            'last_date': format_datetime(last.get_mtime(), accept_language),
        #                            'last_author': (users.get_handler(last_author_id).get_title() or
        #                                last_metadata.get_property('dc:title') or
        #                                last_metadata.get_property('ikaaro:email')),
        #                            'last_post': last.name,
        #                            'url': thread_url}
        #            my_threads.append(add_my_posts)

        # Set batch informations
        batch_start = int(context.get_form_value('t5', default=0))
        batch_size = 16
        batch_total = len(my_threads)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        my_threads = my_threads[batch_start:batch_fin]
         # Namespace
        if my_threads:
            my_threads_batch = t5(context.uri, batch_start, batch_size,
                              batch_total, msgs=(u"There is 1 thread.",
                                    u"There are ${n} threads, that you have \
                                    posted."))
            msg = None
        else:
            my_threads_batch = None
            msg = u"You currently don't have any threads posted."
        namespace['batch'] = my_threads_batch
        namespace['msg'] = msg
       
        namespace['my_threads'] = my_threads
        handler = self.get_handler('/ui/abakuc/forum/user.xml')
        return stl(handler, namespace)  

register_object_class(User)
