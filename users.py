# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>


# Import from the standard library
import mimetypes

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
from itools.cms.widgets import table, batch
from itools.xml import Parser
from itools.datatypes import Email
from itools.cms.workflow import WorkflowAware
from itools.xhtml import Document as XHTMLDocument
from itools.cms.utils import reduce_string

# Import from our product
from companies import Company, Address 
from training import Training
from news import News
from jobs import Job
from utils import title_to_name
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
                   ['browse_content?mode=thumbnails',
                    'browse_content?mode=list',
                    'browse_content?mode=image'],
                   ['new_resource_form'],
                   ['state_form'],
                   ['edit_form', 'edit_account_form', 
                    'edit_portrait_form', 'edit_password_form'],
                   ['tasks_list']]

    ########################################################################
    # API
    ########################################################################
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

    def get_tabs_stl(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        root = context.root
        users = root.get_handler('users')

        namespace = {}
        namespace['news'] = self.news_table(context)
        namespace['jobs'] = self.jobs_table(context)
        namespace['enquiries'] = self.enquiries_list(context)
        address = self.get_address()
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
        #namespace['branches'] = self.list_addresses(context)
        is_reviewer = address.has_user_role(self.name, 'ikaaro:reviewers')
        namespace['is_reviewer'] = is_reviewer
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
                    $('#container-1 ul').tabs((parseInt($.cookie(TABS_COOKIE))) || 1,{click: function(clicked) {
                        var lastTab = $(clicked).parents("ul").find("li").index(clicked.parentNode) + 1;
                       $.cookie(TABS_COOKIE, lastTab, {path: '/'});
                    },
                    fxFade: true,
                    fxSpeed: 'fast',
                    fxSpeed: "normal" 
                    });
                });
            </script>
        <div id="container-1">
            <ul>
                <li><a href="#fragment-1"><span>News</span></a></li>
                <li><a href="#fragment-2"><span>Jobs</span></a></li>
                <li stl:if="howmany"><a href="#fragment-3"><span>Enquiries (${howmany})</span></a></li>
                <li><a href="#fragment-4"><span>Training</span></a></li>
                <li><a href="#fragment-5"><span>Branches</span></a></li>
                <li><a href="#fragment-6"><span>Administrate</span></a></li>
            </ul>
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
              {Training programmes}
            </div>
            <div id="fragment-5">
              {branches}
            </div>
          <stl:block if="is_reviewer">
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
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


    #######################################################################
    # Edit Account 
    account_fields = iUser.account_fields + ['abakuc:phone']
    
    edit_account_form__access__ = 'is_allowed_to_edit'
    edit_account_form__label__ = u'Edit'
    edit_account_form__sublabel__ = u'Account'
    def edit_account_form(self, context):
        root = get_context().root
        job_functions = self.get_property('abakuc:job_function')
        logo = self.has_handler('logo')

        # Build the namespace
        namespace = {}
        for key in self.account_fields:
            namespace[key] = self.get_property(key)
        namespace['job_functions'] = root.get_functions_namespace(job_functions)
        namespace['logo'] = logo
        # Ask for password to confirm the changes
        if self.name != context.user.name:
            namespace['must_confirm'] = False
        else:
            namespace['must_confirm'] = True

        handler = self.get_handler('/ui/abakuc/user_edit_account.xml')
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
        job_functions = context.get_form_values('job_function')
        logo = context.get_form_value('logo')
        # Save changes
        for key in self.account_fields:
            value = context.get_form_value(key)
            self.set_property(key, value)
        self.set_property('abakuc:job_function', job_functions)
        

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

        namespace = {}
        user = context.user
        root = context.root
        users = root.get_handler('users')
        portrait = self.has_handler('portrait')
        
        # Get Company and Address
        namespace['address'] = None
        address = self.get_address()
        
        # User Role
        is_self = user is not None and user.name == self.name
        is_admin = root.is_admin(user, self)
        namespace['is_self_or_admin'] = is_self or is_admin
        namespace['is_admin'] = is_admin
        if address:
            is_reviewer = address.has_user_role(self.name, 'ikaaro:reviewers')
            is_member = address.has_user_role(self.name, 'ikaaro:members')
            is_guest = address.has_user_role(self.name, 'ikaaro:guests')
            is_reviewer_or_member = is_reviewer or is_member
        else:
            is_reviewer = False
            is_member = False
            is_guest = False
            is_reviewer_or_member = False

        namespace['is_reviewer'] = is_reviewer
        namespace['is_member'] = is_member
        namespace['is_guest'] = is_guest
        namespace['is_reviewer_or_member'] = is_reviewer_or_member

        #User's state
        namespace['statename'] = self.get_statename()
        state = self.get_state()
        namespace['state'] = self.gettext(state['title'])
        # User Identity
        namespace['firstname'] = self.get_property('ikaaro:firstname')
        namespace['lastname'] = self.get_property('ikaaro:lastname')
        namespace['email'] = self.get_property('ikaaro:email')
        namespace['portrait'] = portrait
        if address is None:
            handler = self.get_handler('/ui/abakuc/user_profile.xml')
            return stl(handler, namespace)
        company = address.parent
        
        
        # Company
        namespace['company'] = {'name': company.name,
                                'title': company.get_property('dc:title'),
                                'website': company.get_website(),
                                'path': self.get_pathto(company)}
        # Address
        county = address.get_property('abakuc:county')
        addr = {'name': address.name,
                'address': address.get_property('abakuc:address'),
                'town': address.get_property('abakuc:town'),
                'county': world.get_row(county)[8],
                'postcode':address.get_property('abakuc:postcode'),
                'phone': address.get_property('abakuc:phone'),
                'fax': address.get_property('abakuc:fax'),
                'address_path': self.get_pathto(address)}

        namespace['address'] = addr
        
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
        
        # Tabs
        namespace['tabs'] = self.get_tabs_stl(context)

        namespace['contact'] = None
        if user is None:
            return u'You need to be registered!'     
        if address.has_user_role(user.name, 'ikaaro:guests'):
            contacts = address.get_property('ikaaro:reviewers')
            if contacts:
                contact = users.get_handler(contacts[0])
                namespace['contact'] = contact.get_property('ikaaro:email')
            else:
                contact = '<span style="color:red;">The administrator</span>'
                namespace['contact'] = Parser(contact)
        handler = self.get_handler('/ui/abakuc/user_profile.xml')
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
    view__access__ = True 
    def view(self, context):
        return 'Hello' 

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
            is_reviewer = address.has_user_role(self.name, 'ikaaro:reviewers')
            is_member = address.has_user_role(self.name, 'ikaaro:members')
            is_guest = address.has_user_role(self.name, 'ikaaro:guests')
            is_reviewer_or_member = is_reviewer or is_member
        else:
            is_reviewer = False
            is_member = False
            is_guest = False
            is_reviewer_or_member = False
        # Table with News
        columns = [('title', u'Title'),
                   ('closing_date', u'Closing Date'),
                   ('description', u'Short description')]
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
                         'checkbox': is_reviewer,
                         'img': '/ui/abakuc/images/JobBoard16.png',
                         'title': (get('dc:title'),url),
                         'closing_date': get('abakuc:closing_date'),
                         'description': description}
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
        sortby = context.get_form_value('sortby', 'closing_date')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        news_items.sort(lambda x,y: cmp(x[sortby], y[sortby]))
        if reverse:
            news_items.reverse()
        # Set batch informations
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
            msg = u'No news has been posted.'

        namespace['news_table'] = news_table
        namespace['news_batch'] = news_batch
        namespace['news_msg'] = msg 
        handler = self.get_handler('/ui/abakuc/news/news_table.xml')
        return stl(handler, namespace)
   
    
    ########################################################################
    # Job table used in the 'tabs' method
    def jobs_table(self, context):
        namespace = {}
        address = self.get_address()
        company = address.parent
        if address:
            is_reviewer = address.has_user_role(self.name, 'ikaaro:reviewers')
            is_member = address.has_user_role(self.name, 'ikaaro:members')
            is_guest = address.has_user_role(self.name, 'ikaaro:guests')
            is_reviewer_or_member = is_reviewer or is_member
        else:
            is_reviewer = False
            is_member = False
            is_guest = False
            is_reviewer_or_member = False
            # Table with Jobs
        columns = [('title', u'Title'),
                   ('closing_date', u'Closing Date'),
                   ('function', u'Function'),
                   ('description', u'Short description')]
        # Get all Jobs
        address_jobs = address.search_handlers(handler_class=Job)
        # Construct the lines of the table
        jobs = []
        for job in list(address_jobs):
            #job = root.get_handler(job.abspath)
            get = job.get_property
            # Information about the job
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 job.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=40)
            job_to_add ={'id': job.name, 
                         'checkbox': is_reviewer,
                         'img': '/ui/abakuc/images/JobBoard16.png',
                         'title': (get('dc:title'),url),
                         'closing_date': get('abakuc:closing_date'),
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'description': description}
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
        sortby = context.get_form_value('sortby', 'closing_date')
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
            job_table = None
            job_batch = None
            msg = u'No jobs'

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
        url = '/companies/%s/%s/;view_enquiry' % (company.name, address.name) 
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

        handler = self.get_handler('/ui/abakuc/user_setup_company.xml')
        return stl(handler, namespace)
 

    setup_company__access__ = 'is_self_or_admin'
    def setup_company(self, context):
        # Add Company
        title = context.get_form_value('dc:title')
        
        if not title:
            message = u'Please give a Name to your Company'
            return context.come_back(message)
        
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
        metadata.set_property('abakuc:website', website)
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('abakuc:type', types)
        metadata.set_property('ikaaro:website_is_open', True) 

        # Add the logo
        if logo_form:
            logo, logo_metadata = company.set_object(logo_name, logo)
            logo_metadata.set_property('state', 'public')

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

        handler = self.get_handler('/ui/abakuc/user_setup_address.xml')
        return stl(handler, namespace)


    setup_address_select__access__ = 'is_self_or_admin'
    def setup_address_select(self, context):
        company_name = context.get_form_value('company_name')
        address_name = context.get_form_value('address_name')

        # Add to new address
        companies = self.get_handler('/companies')
        company = companies.get_handler(company_name)
        address = company.get_handler(address_name)
        reviewers = address.get_property('ikaaro:reviewers')
        if not reviewers:
            address.set_user_role(self.name, 'ikaaro:reviewers')
        else:
            address.set_user_role(self.name, 'ikaaro:guests')
        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address selected.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)


    setup_address__access__ = 'is_self_or_admin'
    def setup_address(self, context):
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
        address.set_user_role(self.name, 'ikaaro:reviewers')

        root = context.root
        # Remove from old address
        old_address = self.get_address()
        if old_address is not None:
            old_address.set_user_role(self.name, None)

        message = u'Company/Address setup done.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

    ########################################################################
    # Setup training 
    setup_training_form__access__ = 'is_self_or_admin'
    setup_training_form__sublabel__ = u'Setup a training programme'
    def setup_training_form(self, context):
        name = context.get_form_value('dc:title')
        name = name.strip()

        namespace = {}
        namespace['name'] = name

        if name:
            name = name.lower()
            found = []
            trainings = self.get_handler('/trainings')
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

        handler = self.get_handler('/ui/abakuc/user_setup_training.xml')
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
        trainings = root.get_handler('/trainings')
        name = title_to_name(title)
        if trainings.has_handler(name):
            message = u'The training already exist'
            return context.come_back(message)

        training, metadata = self.set_object('/trainings/%s' % name, Training())
        
        # Set Properties
        topics = context.get_form_values('topic')
        metadata.set_property('dc:title', title, language='en')
        metadata.set_property('abakuc:topic', tuple(topics))
        metadata.set_property('ikaaro:website_is_open', True) 

        message = u'trainings setup done.'
        goto = context.uri.resolve(';profile')
        return context.come_back(message, goto=goto)

register_object_class(User)
