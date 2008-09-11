# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>


# Import from the standard library
import mimetypes
from datetime import datetime, date

# Import from itools
from itools import uri
from itools import i18n
from itools import handlers
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
from itools.cms.registry import get_object_class
from itools.cms.access import AccessControl
from itools.cms.binary import Image
from itools.cms.folder import Folder
from itools.cms.base import Handler
from itools.cms.metadata import Password
from itools.cms.registry import register_object_class
from itools.cms.users import UserFolder as iUserFolder, User as iUser
from itools.cms.utils import get_parameters
from itools.rest import checkid
from itools.cms.widgets import batch, table
from itools.xml import Parser
from itools.datatypes import Email
from itools.cms.workflow import WorkflowAware
from itools.xhtml import Document as XHTMLDocument
from itools.cms.utils import reduce_string
from itools.catalog import EqQuery, AndQuery, RangeQuery

# Import from our product
from bookings import Bookings
from companies import Company, Address
from training import Training, Module
from exam import Exam
from news import News
from jobs import Job, Candidature
from utils import title_to_name, get_sort_name
from metadata import JobTitle, SalaryRange

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


    view__access__ = 'is_allowed_to_edit'
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

    #def is_travel_agent(self):
    #    """
    #    Check to see if the user is on a training site.
    #    Return a bool
    #    """
    #    root = self.get_site_root()
    #    is_travel_agent = root.has_user_role(self.name, 'abakuc:branch_member')
    #    return is_travel_agent

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

    #def get_training(self):
    #    root = self.get_root()
    #    results = root.search(format='training', members=self.name)
    #    for training in results.get_documents():
    #        return root.get_handler(training.abspath)
    #    return None

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
    ########################################################################
    # Indexing
    ########################################################################
    def get_catalog_indexes(self):
        from root import world
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
        indexes['function'] = get_property('abakuc:functions')
        companies_handler = root.get_handler('companies')
        if companies_handler:
            companies = \
            list(companies_handler.search_handlers(handler_class=Company))
            for company in companies:
                company_title = company.get_handler(company.abspath)
                addresses = \
                    list(company.search_handlers(handler_class=Address))
                for address in addresses:
                    username = self.name
                    users = address.get_members()
                    if username in users:
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
                to = training.get_property('dc:title')
                username = self.name
                users = training.get_members()
                if username in users:
                    training_programmes.append(to)
        indexes['training_programmes'] = training_programmes
    
        return indexes
        

    #######################################################################
    # Manage bookings
    #######################################################################
    def search_bookings(self, query=None, **kw):

        bookings = self.get_handler('.bookings')
        if query or kw:
            ids = bookings.search(query, **kw)
            return bookings.get_rows(ids)
        return bookings.get_rows()

    #######################################################################
    # jQuery TABS 
    #######################################################################

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
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        root = context.root
        users = root.get_handler('users')
        address = self.get_address()
        company = address.parent

        is_branch_manager = address.has_user_role(self.name, 'abakuc:branch_manager')

        namespace = {}

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
        else:
            namespace['news'] = self.news_table(context)
        namespace['jobs'] = self.jobs_table(context)
        namespace['enquiries'] = self.enquiries_list(context)
        namespace['current_training'] = self.training(context)
        namespace['training'] = self.training_table(context)
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
        #namespace['branches'] = self.list_addresses(context)
        namespace['is_branch_manager'] = is_branch_manager
        # Company
        namespace['company'] = {'name': company.name,
                                'title': company.get_property('dc:title'),
                                'website': company.get_website(),
                                'path': self.get_pathto(company)}
        # Address
        addr = {'name': address.name,
                'address_path': self.get_pathto(address)}

        namespace['address'] = addr
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
            <script type="text/javascript">
                var TABS_COOKIE = 'profile_cookie';
                $(function() {
                    $('#container-user ul').tabs((parseInt($.cookie(TABS_COOKIE))) || 1,{click: function(clicked) {
                        var lastTab = $(clicked).parents("ul").find("li").index(clicked.parentNode) + 1;
                       $.cookie(TABS_COOKIE, lastTab, {path: '/'});
                    },
                    fxFade: true,
                    fxSpeed: 'fast',
                    fxSpeed: "normal"
                    });
                });
            </script>
            <div id="container-user">
                <ul>
                <stl:block if="office">
                    <stl:block if="is_training_manager">
                        <li><a href="#fragment-1"><span>Manage training</span></a></li>
                        <li><a href="#fragment-2"><span>News</span></a></li>
                        <stl:block if="bookings">
                            <li><a href="#fragment-3"><span>Bookings
                                (${howmany_bookings})</span></a></li>
                        </stl:block>
                        <li><a href="#fragment-5"><span>Statistics</span></a></li>
                        <stl:block if="is_branch_manager">
                            <li><a href="#fragment-6"><span>Administrate</span></a></li>
                        </stl:block>
                    </stl:block>
                    <stl:block if="not is_training_manager">
                        <li><a href="#fragment-1"><span>Current training</span></a></li>
                        <li><a href="#fragment-2"><span>News</span></a></li>
                        <stl:block if="bookings">
                            <li><a href="#fragment-3"><span>Bookings</span></a></li>
                        </stl:block>
                        <li><a href="#fragment-4"><span>Other training</span></a></li>
                        <stl:block if="is_branch_manager">
                            <li><a href="#fragment-6"><span>Administrate</span></a></li>
                        </stl:block>
                    </stl:block>
                </stl:block>
                <stl:block if="not office">
                    <li><a href="#fragment-1"><span>News</span></a></li>
                    <li><a href="#fragment-2"><span>Jobs</span></a></li>
                    <li stl:if="howmany"><a href="#fragment-3"><span>Enquiries (${howmany})</span></a></li>
                    <li><a href="#fragment-4"><span>Training</span></a></li>
                    <li><a href="#fragment-5"><span>Branches</span></a></li>
                    <li stl:if="is_branch_manager"><a href="#fragment-6"><span>Administrate</span></a></li>
                </stl:block>
                </ul>
                <stl:block if="office">
                    <stl:block if="is_training_manager">
                        <div id="fragment-1">
                            ${current_training}
                        </div>
                        <div id="fragment-2">
                            ${news}
                        </div>
                        <stl:block if="bookings">
                            <div id="fragment-3">${bookings}</div>
                        </stl:block>
                        <div id="fragment-5">
                          ${statistics}
                        </div>
                    </stl:block>
                    <stl:block if="not is_training_manager">
                        <div id="fragment-1">
                            ${current_training}
                        </div>
                        <div id="fragment-2">
                            ${news}
                        </div>
                        <stl:block if="bookings">
                            <div id="fragment-3">${bookings}</div>
                        </stl:block>
                        <div id="fragment-4">
                          ${training} 
                        </div>
                    </stl:block>
                    <stl:block if="is_branch_manager">
                      <div id="fragment-6">
                         <h2>Administrative actions</h2>
                           <p>
                           <a href="${company/path}/;edit_metadata_form?referrer=1">
                             Modify company details
                           </a>
                           </p>
                           <p>
                           <a href="${address/address_path}/;edit_metadata_form?referrer=1">
                             Modify address details
                           </a>
                           </p>
                           <p>
                            <a href="${address/address_path}/;permissions_form">
                              Users associate to the address
                            </a>
                           </p>
                           <p>
                             <a href="${address/address_path}/;new_user_form">
                               Associate a new user to the address
                             </a>
                           </p>
                      </div>
                    </stl:block>
                </stl:block>
                <stl:block if="not office">
                    <div id="fragment-1">
                      ${news}
                    </div>
                    <div id="fragment-2">
                      ${jobs}
                    </div>
                    <div stl:if="howmany" id="fragment-3">
                      ${enquiries}
                    </div>
                    <div id="fragment-4">
                      ${training}
                    </div>
                    <div id="fragment-5">
                      {branches}
                    </div>
                    <stl:block if="is_branch_manager">
                      <div id="fragment-6">
                        <h2>Administrative actions</h2>
                          <p>
                          <a href="${company/path}/;edit_metadata_form?referrer=1">
                            Modify company details
                          </a>
                          </p>
                          <p>
                          <a href="${address/address_path}/;edit_metadata_form?referrer=1">
                            Modify address details
                          </a>
                          </p>
                          <p>
                           <a href="${address/address_path}/;permissions_form">
                             Users associate to the address
                           </a>
                          </p>
                          <p>
                            <a href="${address/address_path}/;new_user_form">
                              Associate a new user to the address
                            </a>
                          </p>
                      </div>
                    </stl:block>
                </stl:block> <!-- Not office TAB content -->
            </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


    #######################################################################
    # Edit Account
    account_fields = iUser.account_fields + ['abakuc:phone', 'abakuc:job_title']

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
    # Profile
    profile__access__ = 'is_allowed_to_view'
    profile__label__ = u'Profile'
    def profile(self, context):
        from root import world
        from datetime import datetime, date

        namespace = {}
        user = context.user
        root = context.root
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


        #User's state
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
        if address is None:
            handler = self.get_handler('/ui/abakuc/users/profile.xml')
            return stl(handler, namespace)
        company = address.parent

        # XXX Test
        # This returns None
        my_company = self.get_company()
        namespace['my_company'] = my_company

        # Company
        namespace['company'] = {'name': company.name,
                                'title': company.get_property('dc:title'),
                                'website': company.get_website(),
                                'path': self.get_pathto(company)}
        # Address
        addr = {'name': address.name,
                'address': address.get_property('abakuc:address'),
                'town': address.get_property('abakuc:town'),
                'county': address.get_property('abakuc:county'),
                'postcode':address.get_property('abakuc:postcode'),
                'phone': address.get_property('abakuc:phone'),
                'fax': address.get_property('abakuc:fax'),
                'address_path': self.get_pathto(address)}

        namespace['address'] = addr
        # Bookings
        #if office:
        #    items = office_name.search_handlers(handler_class=Bookings)
        #    if items is not None:
        #        bookings = []
        #        for item in list(items):
        #            csv = item.get_handler('.bookings')
        #            if csv:
        #                namespace['csv'] = csv 
        #                results = []
        #                for row in csv.get_rows():
        #                    keys = ["date_booking", "reference_number", "from_date", "to_date",
        #                            "party_name",
        #                            "user", "tour_operator", "holiday_type", "holiday_subtype",
        #                            "number", "duration", "destination1", "destination2",
        #                            "destination3", "destination4", "destination5", "comments",
        #                            "hotel"]                    
        #                    keys = row
        #                    results.append({
        #                           'index': row.number,
        #                           'user': user})
        #                namespace['howmany_bookings'] = len(results)
        #                namespace['results'] = results
        #                get = item.get_property
        #                url = '/%s' % item.name
        #                booking_to_add = { 'url': url,
        #                                    'title': get('dc:title')}
        #                bookings.append(booking_to_add)    
        #        namespace['items'] = bookings
        #    else: 
        #        namespace['items'] = None 
                
        # Enquiries
        csv = address.get_handler('log_enquiry.csv')
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
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name, news.name)
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
            url = '/companies/%s/%s/%s' % (company.name, address.name, job.name)
            jobs.append({'url': url,
                         'title': job.title})
        namespace['jobs'] = jobs

        # Training programmes
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
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

        pp.pprint(is_current_programme)
        pp.pprint(programmes)
        pp.pprint(other_programmes)
        # Tabs
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
        return 'Hello'

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
        company = address.parent
        url = '/companies/%s/%s/;new_resource_form?type=news' % (company.name,
                                                                address.name)
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
        company = address.parent
        url = '/companies/%s/%s/;new_resource_form?type=Job' % (company.name,
                                                                address.name)
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
    # News table used in the 'tabs' method
    def news_table(self, context):
        namespace = {}
        address = self.get_address()
        company = address.parent
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
        # Table with News
        columns = [('c1', u'Title'),
                   ('c2', u'To be archived on'),
                   ('c3', u'Short description')]
        # Get all News
        address_news = address.search_handlers(handler_class=News)
        # Construct the lines of the table
        news_items = []
        for news in list(address_news):
            #job = root.get_handler(job.abspath)
            get = news.get_property
            # Information about the news
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=40)
            news_to_add ={'id': news.name,
                         'checkbox': is_branch_manager,
                         'img': '/ui/abakuc/images/News16.png',
                         'c1': (get('dc:title'),url),
                         'c2': get('abakuc:closing_date'),
                         'c3': description}
            news_items.append(news_to_add)
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
        root = context.root
        namespace = {}
        address = self.get_address()
        company = address.parent
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
            # Table with Jobs
        columns = [('c1', u'Title'),
                   ('c2', u'To be archived on'),
                   ('c3', u'Applications'),
                   ('c4', u'Short description')]
        # Get all Jobs
        address_jobs = address.search_handlers(handler_class=Job)
        # Construct the lines of the table
        jobs = []
        for job in list(address_jobs):
            get = job.get_property
            # Information about the job
            url = '/companies/%s/%s/%s/' % (company.name, address.name,
                                                 job.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=40)
            #Get no of applicants
            users = root.get_handler('users')
            nb_candidatures = 0
            y = root.get_handler(url)
            candidatures = y.search_handlers(handler_class=Candidature)
            for x in candidatures:
                user_id = x.get_property('user_id')
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm') is False:
                        nb_candidatures += 1
            job_to_add ={'id': job.name,
                         'checkbox': is_branch_manager,
                         'img': '/ui/abakuc/images/JobBoard16.png',
                         'c1': (get('dc:title'),url+';view'),
                         'c2': get('abakuc:closing_date'),
                         'c4': description}
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
        sortby = context.get_form_value('sortby', 'c2')
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

        namespace['job_table'] = job_table
        namespace['job_batch'] = job_batch
        namespace['job_msg'] = msg
        handler = self.get_handler('/ui/abakuc/jobs/jobs_table.xml')
        return stl(handler, namespace)


    ########################################################################
    # List Enquiries
    def enquiries_list(self, context):
        root = context.root
        users = root.get_handler('users')

        namespace = {}
        address = self.get_address()
        company = address.parent

        csv = address.get_handler('log_enquiry.csv')
        url = '/companies/%s/%s/' % (company.name, address.name)
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

        handler = self.get_handler('/ui/abakuc/enquiries/enquiries_list.xml')
        return stl(handler, namespace)
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
        #namespace['tp'] = None
        #tp = self.get_training()
        # Table
        columns = [('title', u'Title'),
                   ('function', u'Function'),
                   ('description', u'Short description')]
        # Get all Training programmes
        items = training.search_handlers(handler_class=Training)
        # Construct the lines of the table
        trainings = []
        for item in list(items):
            #job = root.get_handler(job.abspath)
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
        items = trainings[batch_start:batch_fin]
        # Order
        sortby = context.get_form_value('sortby', 'id')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        items.sort(lambda x,y: cmp(x[sortby], y[sortby]))
        if reverse:
            trainings.reverse()
        # Set batch informations
        # Namespace
        if trainings:
            actions = [('select', u'Select All', 'button_select_all',
                        "return select_checkboxes('browse_list', true);"),
                       ('select', u'Select None', 'button_select_none',
                        "return select_checkboxes('browse_list', false);"),
                       ('create_training', u'Add new training', 'button_ok',
                        None),
                       ('remove_training', 'Delete training/s', 'button_delete', None)]
            training_table = table(columns, items, [sortby], sortorder, actions)
            msgs = (u'There is one training.', u'There are ${n} training programmes.')
            training_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            training_table = None
            training_batch = None
            msg = u'No training programmes'

        namespace['training_table'] = training_table
        namespace['batch'] = training_batch
        namespace['items'] = trainings
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
            modules = self.parent.parent.get_modules()
            xx = [
                {'name': x.name, 'title': '%d - %s' % (i+1, x.title)}
                for i, x in enumerate(modules)]
            # Sort the modules
            modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                            get_sort_name(y.name)))
            namespace['modules'] = []

            for module in modules:
                # Get all of the modules' properties
                get = module.get_property
                url = '/%s/;view' %  module.name
                description = reduce_string(get('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                namespace['modules'].append({'url': url,
                          'description': description,
                          'title': module.title_or_name})

                ns = {'title': module.title_or_name, 'url': url}

                # Get module objects, such as Exams and Marketing Forms
                exams = list(module.search_handlers(format=Exam.class_id))
                # If we have NO exams
                ns['exam'] = None 
                if exams !=[]:
                    for item in exams: 
                        title = item.title_or_name
                        url = '/%s/%s/;take_exam_form' % (module.name, item.name)
                        result = item.get_result(self.name)
                        if result != []:
                            allowed_to_take_exam = root.is_allowed_to_take_exam(self.name, item)
                            passed, n_attempts, time, mark, kk = result
                            if allowed_to_take_exam and passed is False:
                                result = {
                                        'title': title,
                                        'passed': passed,
                                        'attempt': n_attempts,
                                        'time': time,
                                        'mark': str(round(mark, 2)),
                                        'url': url
                                        }
                                ns['exam'] = result
                            else:
                                result = {
                                        'title': title,
                                        'passed': passed,
                                        'attempt': n_attempts,
                                        'time': time,
                                        'mark': str(round(mark, 2)),
                                        'url': url
                                        }
                                ns['exam'] = result

                marketing_form = module.get_marketing_form(self.name)
                if marketing_form is not None:
                    feedback = marketing_form.get_result(self.name)
                    print feedback
                else:
                    print 'No mkt form'
                # First module

                # XXX Profile Page Exams / Marketing v 0.1
                # Is this the first module?
                #prev_module = module.get_prev_module()
                #if prev_module is not None:
                #    prev_exam = prev_module.get_exam(self.name)
                #    if prev_exam is not None:
                #        passed = prev_exam.get_result(self.name)[0]
                #        if passed is True:
                #            if exam is not None:
                #                result = exam.get_result(self.name)
                #                passed, n_attempts, time, mark, kk = result
                #                if passed is False:
                #                    title = exam.title_or_name
                #                    url = '/%s/%s/;take_exam_form' % (module.name, exam.name)
                #                    exam = {'title': title,
                #                            'passed': passed,
                #                            'attempts': n_attempts,
                #                            'mark': str(round(mark, 2)),
                #                            'url': url}
                #                    ns['exam'] = exam
                #        else:
                #            #First module if exam is passed
                #            exam = {'title': None,
                #                    'passed': True,
                #                    'attempts': None,
                #                    'mark': None,
                #                    'url': None}
                #            ns['exam'] = exam
                #    else:
                #        exam = {'title': None,
                #                'passed': True,
                #                'attempts': None,
                #                'mark': None,
                #                'url': None}
                #        ns['exam'] = exam 
                #        exams = module.get_exam(self.name)
                #        if exams is not None:
                #            result = exams.get_result(self.name)
                #            passed, n_attempts, time, mark, kk = result
                #            if passed is False:
                #                title = exams.title_or_name
                #                url = '/%s/%s/;take_exam_form' % (module.name, exams.name)
                #                exam = {'title': title,
                #                        'passed': passed,
                #                        'attempts': n_attempts,
                #                        'mark': str(round(mark, 2)),
                #                        'url': url}
                #                ns['exam'] = exam
                #    # Check for previous exam
                #    prev_marketing = prev_module.get_marketing_form(self.name)
                #    if prev_marketing is not None:
                #        marketing = {'title': None,
                #                     'passed': True,
                #                     'url': None}
                #        ns['marketing'] = marketing
                #    else:
                #        # No marketing form in last module or it has been
                #        # filled.
                #        if marketing_form is not None:
                #            # Check for previous exam
                #            prev_exam = prev_module.get_exam(self.name)
                #            if prev_exam is not None:
                #                print 'We have an exam in the previous module'
                #                passed = prev_exam.get_result(self.name)[0]
                #                if passed is False:
                #                    marketing = {'title': None,
                #                                 'passed': True,
                #                                 'url': None}
                #                    ns['marketing'] = marketing
                #            else:
                #                print 'We may not have an exam or we may have\
                #                passed it'
                #                passed = marketing_form.get_result(self.name)[0]
                #                if passed is False:
                #                    title = marketing_form.title_or_name
                #                    url = '/%s/%s/;fill_form' % (module.name, marketing_form.name)
                #                    marketing = {'title': title,
                #                                 'passed': passed,
                #                                 'url': url}
                #                    ns['marketing'] = marketing
                #        else:
                #            marketing = {'title': None,
                #                         'passed': True,
                #                         'url': None}
                #            ns['marketing'] = marketing
                #else:
                #    print 'I am the first module XXX'
                #    if marketing_form is not None:
                #        passed = marketing_form.get_result(self.name)[0]
                #        if passed is False:
                #            title = marketing_form.title_or_name
                #            url = '/%s/%s/;fill_form' % (module.name, marketing_form.name)
                #            marketing = {'title': title,
                #                         'passed': passed,
                #                         'url': url}
                #            ns['marketing'] = marketing

                #    else:
                #        marketing = {'title': None,
                #                     'passed': True,
                #                     'url': None}
                #        ns['marketing'] = marketing
                #        # Exam namespace
                #        if exam is not None:
                #            result = exam.get_result(self.name)
                #            passed, n_attempts, kk, mark, kk = result
                #            if passed is False:
                #                title = exam.title_or_name
                #                url = '/%s/%s/;take_exam_form' % (module.name, exam.name)
                #                exam = {'title': title,
                #                        'passed': passed,
                #                        'attempts': n_attempts,
                #                        'mark': None,
                #                        'url': url}
                #                ns['exam'] = exam
                #        else:
                #            exam = {'title': None,
                #                    'passed': True,
                #                    'attempts': None,
                #                    'mark': None,
                #                    'url': None}
                #            ns['exam'] = exam 

                ## XXX Profile Page Exams / Marketing v 0.1


                #path_to_module = '../../%s' % module.name
                #ns['url'] = '%s' % path_to_module
                #if is_training_manager:
                #    ns['add_topic'] = '/%s/;new_resource_form?type=topic' % path_to_module
                #    ns['add_marketing'] = '/%s/;new_resource_form?type=marketing'  % path_to_module
                #    ns['add_exam'] = '/%s/;new_resource_form?type=Exam'  % path_to_module
                #    if last_exam_passed is True:
                #        # Check for marketing form.
                #        ns['marketing'] = None
                #        if marketing_form is not None:
                #            url = '/%s/%s/;fill_form' % (module.name,
                #                                        marketing_form.name)
                #            marketing = {'url': url}
                #            ns['marketing'] = marketing

                #        else:
                #            ns['exam'] = None
                #            # Check for exam
                #            exam = None
                #            exams = list(module.search_handlers(format=Exam.class_id))
                #            if exams != []:
                #                exam = module.get_exam(self.name)
                #                last_exam_passed = False
                #                if exam is not None:
                #                    title = exam.title_or_name
                #                    result = exam.get_result(self.name)
                #                    passed, n_attempts, kk, mark, kk = result
                #                    url = '/%s/%s/;take_exam_form' % (module.name,
                #                                                    exam.name)
                #                    exam = {'title': title,
                #                            'passed': passed,
                #                            'attempts': n_attempts,
                #                            'mark': str(round(mark, 2)),
                #                            'url': url}
                #                    last_exam_passed = passed
                #                    ns['exam'] = exam
                #        # Exams
                #        exams = list(module.search_handlers(format=Exam.class_id))
                #        if exams != []:
                #            exam = module.get_exam(self.name)
                #            last_exam_passed = False
                #            if exam is not None:
                #                title = exam.title_or_name
                #                result = exam.get_result(self.name)
                #                passed, n_attempts, kk, mark, kk = result
                #                url = '/%s/%s/;take_exam_form' % (module.name,
                #                                                exam.name)
                #                exam = {'title': title,
                #                        'passed': passed,
                #                        'attempts': n_attempts,
                #                        'mark': str(round(mark, 2)),
                #                        'url': url}
                #                last_exam_passed = passed
                #                ns['exam'] = exam

                #else:
                #    # Not training manager
                #    if last_exam_passed is True:
                #        # Check for marketing form.
                #        marketing_form = module.get_marketing_form(self.name)
                #        ns['marketing'] = None
                #        if marketing_form is not None:
                #            url = '/%s/%s/;fill_form' % (module.name,
                #                                        marketing_form.name)
                #            marketing = {'url': url}
                #            ns['marketing'] = marketing

                #        else:
                #            ns['exam'] = None
                #            # Check for exam
                #            exam = None
                #            exams = list(module.search_handlers(format=Exam.class_id))
                #            if exams != []:
                #                exam = module.get_exam(self.name)
                #                last_exam_passed = False
                #                if exam is not None:
                #                    title = exam.title_or_name
                #                    result = exam.get_result(self.name)
                #                    passed, n_attempts, kk, mark, kk = result
                #                    url = '/%s/%s/;take_exam_form' % (module.name,
                #                                                    exam.name)
                #                    exam = {'title': title,
                #                            'passed': passed,
                #                            'attempts': n_attempts,
                #                            'mark': str(round(mark, 2)),
                #                            'url': url}
                #                    last_exam_passed = passed
                #                    ns['exam'] = exam
                #        # Exams
                #        #exams = list(module.search_handlers(format=Exam.class_id))
                #        if exams != []:
                #            exam = module.get_exam(self.name)
                #            last_exam_passed = False
                #            if exam is not None:
                #                title = exam.title_or_name
                #                result = exam.get_result(self.name)
                #                passed, n_attempts, kk, mark, kk = result
                #                url = '/%s/%s/;take_exam_form' % (module.name,
                #                                                exam.name)
                #                exam = {'title': title,
                #                        'passed': passed,
                #                        'attempts': n_attempts,
                #                        'mark': str(round(mark, 2)),
                #                        'url': url}
                #                last_exam_passed = passed
                #                ns['exam'] = exam




                # Add namespace
                module_ns.append(ns)
                namespace['programme'] = {'title': root.title_or_name,
                          'modules': module_ns,
                          'league': '../../;league_table'}

                print namespace['programme']
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


register_object_class(User)
