# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime, date
from string import Template
import mimetypes

# Import from itools
from itools.datatypes import Email, Integer, String, Unicode, FileName
from itools.i18n.locale_ import format_datetime
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.stl import stl
from itools.web import get_context
from itools.xml import get_element
from itools.xhtml import Document as XHTMLDocument
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.utils import generate_password
from itools.cms.widgets import table, batch
from itools.cms.catalog import schedule_to_reindex
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware
from itools.uri import encode_query, Reference, Path

# Import from abakuc
from base import Handler, Folder
from handlers import EnquiriesLog, EnquiryType
from website import WebSite
from news import News
from jobs import Job
from metadata import JobTitle, SalaryRange 
from product import Products
from utils import get_sort_name


class Companies(Folder):

    class_id = 'companies'
    class_title = u'Companies Directory'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form']]

    
    def get_document_types(self):
        return [Company]

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        companies = self.search_handlers(handler_class=Company)
        items = []
        for item in companies:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            company = {'url': url,
                      'id': item.name,
                      'description': description,
                      'title': item.title_or_name}
            items.append(company)
            items.sort(key=lambda x: x['id'])
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace 
        if items:
            msgs = (u'There is one company.',
                    u'There are ${n} companies.')
            items_batch = batch(context.uri, batch_start, batch_size, 
                          batch_total, msgs=msgs)
            msg = None
        else:
            items_batch = None
            msg = u'Currently there no published companies.'
        
        namespace['batch'] = items_batch
        namespace['msg'] = msg 
        namespace['title'] = title 
        namespace['items'] = items

        handler = self.get_handler('/ui/abakuc/companies/list.xml')
        return stl(handler, namespace)

class Company(WebSite):

    class_id = 'company'
    class_title = u'Company'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    site_format = 'address'
    
    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form']]


    new_resource_form__access__ = 'is_allowed_to_edit'
    new_resource__access__ = 'is_allowed_to_edit'

    def get_document_types(self):
        return [Address, Folder]


    def get_level1_title(self, level1):
        return None

    #######################################################################
    # API
    #######################################################################
    def get_website(self):
        website = self.get_property('abakuc:website')
        if website.startswith('http://'):
            return website
        return 'http://' + website

    def get_tabs_stl(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        namespace = {}
        namespace['news'] = self.list_news(context)
        namespace['jobs'] = self.list_jobs(context)
        namespace['branches'] = self.list_addresses(context)
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
            <script type="text/javascript">
                var TABS_COOKIE = 'company_cookie'; 
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
                <li><a href="#fragment-3"><span>Branches</span></a></li>
            </ul>
            <div id="fragment-1">
              ${news} 
            </div>
            <div id="fragment-2">
              ${jobs}
            </div>
            <div id="fragment-3">
              ${branches}
            </div>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_allowed_to_edit(self, user, object):
        for address in self.search_handlers(handler_class=Address):
            if address.is_allowed_to_edit(user, address):
                return True
        return False

    def is_reviewer(self, user, object):
        for address in self.search_handlers(handler_class=Address):
            if address.is_reviewer(user, address):
                return True
        return False


    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        description = reduce_string(self.get_property('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
        namespace['description'] = description
        #namespace['description'] = self.get_property('dc:description')
        namespace['website'] = self.get_website()
        namespace['logo'] = self.has_handler('logo')

        namespace['tabs'] = self.get_tabs_stl(context)

        handler = self.get_handler('/ui/abakuc/companies/company_view.xml')
        return stl(handler, namespace)


    ####################################################################
    # Users
    get_members_namespace__access__ = 'is_allowed_to_edit'
    get_members_namespace__label__ = u'Users'
    def get_members_namespace(self, context):
        """
        Returns a namespace (list of dictionaries) to be used 
        in the branch view list.
        """
        # This works, but returns only the user's id
        # and also don't know how to break it down
        # into individual branches.
        addresses = self.search_handlers(handler_class=Address)
        members = []
        for address in addresses:
            branch_members = address.get_members()
            for username in branch_members:
                users = self.get_handler('/users')
                user_exist = users.has_handler(username) 
                usertitle = (user_exist and 
                             users.get_handler(username).get_title() or username)
                url = '/users/%s/;profile' % username 
                members.append({'id': username,
                                'title': usertitle, 
                                'url': url})
        # List users 

        return members


    ####################################################################
    # List addresses 
    list_addresses__label__ = u'List addresses'
    list_addresses__access__ = True
    def list_addresses(self, context):
        namespace = {}
        addresses = self.search_handlers(handler_class=Address)
        namespace['addresses'] = []
        for address in addresses:
            company = address.parent
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            enquire = '/companies/%s/%s/;enquiry_form' % (company.name, address.name)
            namespace['addresses'].append({'url': url,
                                           'enquire': enquire,
                                           'address': address.get_property('abakuc:address'),
                                           'postcode': address.get_property('abakuc:postcode'),
                                           'phone': address.get_property('abakuc:phone'),
                                           'title': address.title_or_name})

            members = []
            branch_members = address.get_members()
            for username in branch_members:
                users = self.get_handler('/users')
                user_exist = users.has_handler(username) 
                usertitle = (user_exist and 
                             users.get_handler(username).get_title() or username)
                url = '/users/%s/;profile' % username 
                members.append({'id': username,
                                'title': usertitle, 
                                'url': url})

                namespace['members'] = members 
            namespace['users'] = self.get_members_namespace(address)
            #namespace['users'] = self.get_members_namespace(address)

        handler = self.get_handler('/ui/abakuc/companies/list_addresses.xml')

        return stl(handler, namespace)


    ####################################################################
    # List jobs 
    list_jobs__label__ = u'List jobs'
    list_jobs__access__ = True
    def list_jobs(self, context):
        namespace = {}
        namespace['batch'] = ''
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'Job'))
        query.append(EqQuery('company', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        jobs = []
        for job in list(documents):
            job = root.get_handler(job.abspath)
            get = job.get_property
            # Information about the job
            address = job.parent
            company = address.parent
            url = '%s/%s/;view' % (address.name, job.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'title': get('dc:title'),
                         'closing_date': get('abakuc:closing_date'),
                         'address': address.get_title_or_name(), 
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'salary': SalaryRange.get_value(get('abakuc:salary')),               
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
        # Namespace 
        if jobs:
            msgs = (u'There is one job.',
                    u'There are ${n} jobs.')
            job_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            job_table = None
            job_batch = None
            msg = u'Sorry but there are no jobs'

        namespace['jobs'] = jobs        
        namespace['batch'] = job_batch
        namespace['msg'] = msg 
        handler = self.get_handler('/ui/abakuc/companies/list_jobs.xml')
        return stl(handler, namespace)


    ####################################################################
    # View news 
    list_news__label__ = u'List news'
    list_news__access__ = True
    def list_news(self, context):
        namespace = {}
        namespace['batch'] = ''
        #Search the catalogue, list all news items in company 
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'news'))
        query.append(EqQuery('company', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        news_items = []
        for news in list(documents):
            users = self.get_handler('/users')
            news = root.get_handler(news.abspath)
            get = news.get_property
            # Information about the news item 
            username = news.get_property('owner')
            user_exist = users.has_handler(username) 
            usertitle = (user_exist and 
                         users.get_handler(username).get_title() or username)
            address = news.parent
            company = address.parent
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name, news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            news_items.append({'url': url,
                               'title': news.title,
                               'closing_date': get('abakuc:closing_date'),
                               'date_posted': get('dc:date'),
                               'owner': usertitle,
                               'description': description})
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        news_items = news_items[batch_start:batch_fin]
        # Namespace 
        if news_items:
            msgs = (u'There is one news item.',
                    u'There are ${n} news items.')
            news_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            news_batch = None
            msg = u'Currently there is no news.'
        
        namespace['news_batch'] = news_batch
        namespace['msg'] = msg 
        namespace['news_items'] = news_items
        handler = self.get_handler('/ui/abakuc/companies/list_news.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(name=None, description=None, website=None, topics=None, types=None, logo=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['description'] = description 
        namespace['website'] = website
        namespace['topics'] = root.get_topics_namespace(topics)
        #XXX Make this list only types specific for the sub-site
        #site_specific_types = root.get_site_types(types)
        #if site is localhost list all
        #if site is expert.travel select types with id = 1
        #if site is destinations guide select types with id = 2
        # etc....
        namespace['types'] = root.get_types_namespace(types)
        namespace['logo'] = logo

        handler = root.get_handler('ui/abakuc/companies/company_form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        title = self.get_property('dc:title')
        # Description
        description = self.get_property('dc:description')
        website = self.get_property('abakuc:website')
        topics = self.get_property('abakuc:topic')
        types = self.get_property('abakuc:type')
        logo = self.has_handler('logo')
        namespace['form'] = self.get_form(title, description, website, topics, types, logo)

        handler = self.get_handler('/ui/abakuc/companies/company_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')
        logo = context.get_form_value('logo')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')
        self.set_property('abakuc:website', website)
        self.set_property('abakuc:topic', tuple(topics))
        self.set_property('abakuc:type', types)

        # The logo
        if context.has_form_value('remove_logo'):
            if self.has_handler('logo'):
                self.del_object('logo')
        elif logo is not None:
            name, mimetype, data = logo
            guessed = mimetypes.guess_type(name)[0]
            if guessed is not None:
                mimetype = guessed
            logo_cls = get_object_class(mimetype)
            logo = logo_cls(string=data)
            logo_name = 'logo'
            # Check format of Logo
            if not isinstance(logo, Image):
                msg = u'Your logo must be an Image PNG or JPEG'
                return context.come_back(msg)
            # Check size
            size = logo.get_size()
            if size is not None:
                width, height = size
                if width > 150 or height > 150:
                    msg = u'Your logo is too big (max 150x150 px)'
                    return context.come_back(msg)
            
            # Add or edit the logo
            if self.has_handler('logo'):
                # Edit the logo
                logo = self.get_handler('logo')
                try:
                    logo.load_state_from_string(data)
                except:
                    self.load_state()
                logo = logo.load_state_from_string(string=data)
            else:
                # Add the new logo
                logo = logo_cls(string=data)
                logo, metadata = self.set_object(logo_name, logo)
                metadata.set_property('state', 'public')

        # Re-index addresses
        for address in self.search_handlers(handler_class=Address):
            schedule_to_reindex(address)

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


class Address(RoleAware, WorkflowAware, Folder):

    class_id = 'address'
    class_title = u'Address'
    class_icon16 = 'abakuc/images/Employees16.png'
    class_icon48 = 'abakuc/images/Employees48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['state_form'],
        ['permissions_form', 'new_user_form']]

    __fixed_handlers__ = ['log_enquiry.csv']

    permissions_form__access__ = 'is_reviewer'
    permissions__access__ = 'is_reviewer'
    edit_membership_form__access__ = 'is_reviewer'
    edit_membership__access__ = 'is_reviewer'
    new_user_form__access__ = 'is_reviewer'
    new_user__access__ = 'is_reviewer'
    new_resource_form__access__ = 'is_allowed_to_view'
    new_resource__access__ = 'is_allowed_to_view'
    
    
    def new(self, **kw):
        # Enquiry
        Folder.new(self, **kw)
        handler = EnquiriesLog()
        cache = self.cache
        cache['log_enquiry.csv'] = handler
        cache['log_enquiry.csv.metadata'] = handler.build_metadata()

        # Jobs folder 
        title = u'Products folder'
        kw = {'dc:title': {'en': title}}
        products = Products()
        cache['products'] = products
        cache['products.metadata'] = products.build_metadata(**kw)

    def get_document_types(self):
        return [News, Job]


    get_epoz_data__access__ = 'is_reviewer_or_member'
    def get_epoz_data(self):
        # XXX don't works
        context = get_context()
        job_text = context.get_form_value('abakuc:job_text') 
        return job_text


    def get_catalog_indexes(self):
        from root import world

        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        topics = company.get_property('abakuc:topic')
        if topics is not None:
            indexes['level1'] = list(topics)
        county_id = self.get_property('abakuc:county')
        if county_id:
            row = world.get_row(county_id)
            indexes['level0'] = row.get_value('iana_root_zone')
            indexes['level2'] = row[7]
            indexes['level3'] = row[8] 
        indexes['level4'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        return indexes


    #######################################################################
    # API
    #######################################################################
    def get_title(self):
        address = self.get_property('abakuc:address')
        return address or self.name

    def get_document_names(self):
    #def get_document_names(self, prefix=None):
        ac = self.get_access_control()
        user = get_context().user

        documents = []
        for handler in self.get_handlers():
            if not isinstance(handler, News):
                continue
            if handler.real_handler is not None:
                continue
            if ac.is_allowed_to_view(user, handler):
                name = handler.name
                sort_name = get_sort_name(FileName.decode(name)[0])
                documents.append((sort_name, handler.name))
        documents.sort()
        return [ x[1] for x in documents ]


    def get_members_namespace(self, context):
        """
        Returns a namespace (list of dictionaries) to be used 
        in the branch view list.
        """
        # This works if the user is added to the Company
        root = get_context().root
        users = self.get_handler('/users')
        members = []
        for username in self.get_members():
           user = users.get_handler(username)
           url = '/users/%s/;profile' % username 
           job_function = user.get_property('abakuc:job_function')
           state = user.get_property('state')
           if state == 'public':
                 members.append({'id': user.get_title,
                                 'url': url,
                                 'job_function': job_function,
                                 'phone': user.get_property('abakuc:phone'),
                                 'title': user.get_title()})
        # List users 

        return members


    def get_tabs_stl(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        namespace = {}
        namespace['news'] = self.list_news(context)
        namespace['jobs'] = self.list_jobs(context)
        namespace['branches'] = self.list_addresses(context)
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
            <script type="text/javascript">
                var TABS_COOKIE = 'address_cookie'; 
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
                <li><a href="#fragment-3"><span>Branches</span></a></li>
            </ul>
            <div id="fragment-1">
              ${news} 
            </div>
            <div id="fragment-2">
              ${jobs}
            </div>
            <div id="fragment-3">
              ${branches}
            </div>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


    #######################################################################
    # User Interface / View
    #######################################################################
    view__label__ = u'Address'
    view__access__ = True
    def view(self, context):
        from root import world

        county_id = self.get_property('abakuc:county')
        if county_id is None:
            # XXX Every address should have a county
            country = region = county = '-'
        else:
            row = world.get_row(county_id)
            country = row[6]
            region = row[7]
            county = row[8]

        namespace = {}
        namespace['company'] = self.parent.get_property('dc:title')
        namespace['logo'] = self.parent.has_handler('logo')
        namespace['address'] = self.get_property('abakuc:address')
        namespace['town'] = self.get_property('abakuc:town')
        namespace['postcode'] = self.get_property('abakuc:postcode')
        namespace['phone'] = self.get_property('abakuc:phone')
        namespace['fax'] = self.get_property('abakuc:fax')
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        
        addresses = []
        for address in self.parent.search_handlers(handler_class=Address):
            company = address.parent
            current_address = self.get_property('abakuc:address')
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            addresses.append({
                'name': address.name,
                'is_current': address.name == current_address,
                'url': url,
                'address': address.get_property('abakuc:address'),
                'phone': address.get_property('abakuc:phone'),
                'fax': address.get_property('abakuc:fax')})
        namespace['addresses'] = addresses

        namespace['tabs'] = self.get_tabs_stl(context)
        ################ 
        # Branch Members
        namespace['users'] = self.get_members_namespace(address)

        handler = self.get_handler('/ui/abakuc/companies/address_view.xml')
        return stl(handler, namespace)

    ####################################################################
    # View news 
    list_news__label__ = u'News'
    list_news__access__ = True
    def list_news(self, context):
        namespace = {}
        namespace['batch'] = ''
        #Search the catalogue, list all news items in address 
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'news'))
        query.append(EqQuery('address', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        news_items = []
        for news in list(documents):
            users = self.get_handler('/users')
            news = root.get_handler(news.abspath)
            get = news.get_property
            # Information about the news item 
            username = news.get_property('owner')
            user_exist = users.has_handler(username) 
            usertitle = (user_exist and 
                         users.get_handler(username).get_title() or username)
            address = news.parent
            company = address.parent
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name, news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            news_items.append({'url': url,
                               'title': news.title,
                               'closing_date': get('abakuc:closing_date'),
                               'date_posted': get('dc:date'),
                               'owner': usertitle,
                               'description': description})
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        news_items = news_items[batch_start:batch_fin]
        # Namespace 
        if news_items:
            msgs = (u'There is one news item.',
                    u'There are ${n} news items.')
            news_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            news_batch = None
            msg = u'Currently there is no news.'
        
        namespace['news_batch'] = news_batch
        namespace['msg'] = msg 
        namespace['news_items'] = news_items
        handler = self.get_handler('/ui/abakuc/companies/list_news.xml')
        return stl(handler, namespace)



    ####################################################################
    # View jobs 
    list_jobs__label__ = u'Our jobs'
    list_jobs__access__ = True
    def list_jobs(self, context):
        namespace = {}
        namespace['batch'] = ''
        all_jobs = self.search_handlers(handler_class=Job)
        # Construct the lines of the table
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'Job'))
        query.append(EqQuery('address', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        jobs = []
        for job in list(documents):
            job = root.get_handler(job.abspath)
            address = job.parent
            get = job.get_property
            # Information about the job
            url = '%s/;view' % job.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'title': get('dc:title'),
                         'closing_date': get('abakuc:closing_date'),
                         'address': address.get_title_or_name(), 
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'salary': SalaryRange.get_value(get('abakuc:salary')),               
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
        # Namespace 
        if jobs:
            msgs = (u'There is one job.',
                    u'There are ${n} jobs.')
            job_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            job_table = None
            job_batch = None
            msg = u'Sorry but there are no jobs'

        namespace['jobs'] = jobs        
        namespace['batch'] = job_batch
        namespace['msg'] = msg 
        handler = self.get_handler('/ui/abakuc/companies/list_jobs.xml')
        return stl(handler, namespace)


    ####################################################################
    # View branches 
    list_addresses__label__ = u'Our branches'
    list_addresses__access__ = True
    def list_addresses(self, context):
        namespace = {}
        addresses = self.parent.search_handlers(handler_class=Address)
        namespace['addresses'] = []
        for address in addresses:
            company = address.parent
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            enquire = '/companies/%s/%s/;enquiry_form' % (company.name, address.name)
            namespace['addresses'].append({'url': url,
                                           'enquire': enquire,
                                           'address': address.get_property('abakuc:address'),
                                           'postcode': address.get_property('abakuc:postcode'),
                                           'phone': address.get_property('abakuc:phone'),
                                           'title': address.title_or_name})

        namespace['users'] = self.get_members_namespace(address)
        handler = self.get_handler('/ui/abakuc/companies/list_addresses.xml')

        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 address_country=None, address_region=None,
                 address_county=None):
        context = get_context()
        root = context.root
        # List authorized countries
        countries = [
            {'name': x, 'title': x, 'selected': x == address_country}
            for x, y in root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'

        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])
        regions = root.get_regions_stl(country=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town 
        namespace['phone'] = phone
        namespace['fax'] = fax
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county
        handler = root.get_handler('ui/abakuc/companies/address_form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        address = self.get_property('abakuc:address')
        postcode = self.get_property('abakuc:postcode')
        town = self.get_property('abakuc:town')
        phone = self.get_property('abakuc:phone')
        fax = self.get_property('abakuc:fax')
        # Get the country,  the region and  the county
        from root import world
        address_county = self.get_property('abakuc:county')
        if address_county is None:
            address_country = None
            address_region = None
        else:
            rows = world.get_row(address_county)
            address_country = rows.get_value('country')
            address_region = rows.get_value('region')
        namespace['form'] = self.get_form(address, postcode, town, phone, fax,
                                          address_country, address_region,
                                          address_county)

        handler = self.get_handler('/ui/abakuc/companies/address_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        # Add Address
        address = context.get_form_value('abakuc:address')
        if not address:
            message = u'Please give an Address'
            return context.come_back(message)

        if not context.get_form_value('abakuc:county'):
            message = u'Please choose a county'
            return context.come_back(message)

        # Link the User to the Address
        keys = ['address', 'postcode', 'town', 'phone', 'fax', 'county']

        for key in keys:
            key = 'abakuc:%s' % key
            value = context.get_form_value(key)
            self.set_property(key, value)

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


    #######################################################################
    # User Interface / Submit Enquiry
    #######################################################################
    enquiry_fields = [
        ('abakuc:enquiry_subject', True),
        ('abakuc:enquiry', True),
        ('abakuc:enquiry_type', True),
        ('ikaaro:firstname', True),
        ('ikaaro:lastname', True),
        ('ikaaro:email', True),
        ('abakuc:phone', False)]


    enquiry_fields_auth = [
        ('abakuc:enquiry_subject', True),
        ('abakuc:enquiry', True),
        ('abakuc:enquiry_type', True),
        ('abakuc:phone', False)]


    enquiry_form__access__ = True
    def enquiry_form(self, context):
        if context.user is None:
            namespace = context.build_form_namespace(self.enquiry_fields)
            namespace['is_authenticated'] = False
        else:
            namespace = context.build_form_namespace(self.enquiry_fields_auth)
            namespace['is_authenticated'] = True
        enquiry_type = context.get_form_value('abakuc:enquiry_type')
        namespace['enquiry_type'] = EnquiryType.get_namespace(enquiry_type)
        namespace['company'] = self.parent.get_property('dc:title')

        handler = self.get_handler('/ui/abakuc/enquiries/enquiry_edit_metadata.xml')
        return stl(handler, namespace)


    enquiry__access__ = True
    def enquiry(self, context):
        root = context.root
        user = context.user

        # Check input data
        if user is None:
            enquiry_fields = self.enquiry_fields
        else:
            enquiry_fields = self.enquiry_fields_auth
        keep = [ x for x, y in enquiry_fields ]
        error = context.check_form_input(enquiry_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Create the user
        confirm = None
        if user is None:
            users = root.get_handler('users')
            email = context.get_form_value('ikaaro:email')
            # Check the user is not already there
            catalog = context.server.catalog
            results = catalog.search(username=email)
            print email, results.get_n_documents()
            if results.get_n_documents() == 0:
                firstname = context.get_form_value('ikaaro:firstname')
                lastname = context.get_form_value('ikaaro:lastname')
                user = users.set_user(email)
                user.set_property('ikaaro:firstname', firstname)
                user.set_property('ikaaro:lastname', lastname)
                confirm = generate_password(30)
                user.set_property('ikaaro:user_must_confirm', confirm)
            else:
                user_id = results.get_documents()[0].name
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm'):
                    confirm = user.get_property('ikaaro:user_must_confirm')
        user_id = str(user.name)

        # Save the enquiry
        if context.user is None:
            phone = context.get_form_value('abakuc:phone') 
        else:
            phone = context.user.get_property('abakuc:phone') or ''
        enquiry_type = context.get_form_value('abakuc:enquiry_type')
        enquiry_subject = context.get_form_value('abakuc:enquiry_subject')
        enquiry = context.get_form_value('abakuc:enquiry')
        row = [datetime.now(), user_id, phone, enquiry_type, enquiry_subject,
               enquiry, False]
        handler = self.get_handler('log_enquiry.csv')
        handler.add_row(row)

        # Authenticated user, we are done
        if confirm is None:
            self.enquiry_send_email(user, rows=[row])
            message = u'Enquiry sent'
            return message.encode('utf-8')

        # Send confirmation email
        hostname = context.uri.authority.host
        from_addr = 'enquiries@uktravellist.info'
        subject = u"[%s] Register confirmation required" % hostname
        subject = self.gettext(subject)
        body = self.gettext(
            u"This email has been generated in response to your"
            u" enquiry on the UK Travel List.\n"
            u"To submit your enquiry, click the link:\n"
            u"\n"
            u"  $confirm_url"
            u"\n"
            u"If the text is on two lines, please copy and "
            u"paste the full line into your browser URL bar."
            u"\n"
            u"Thank you for visiting the UK Travel List website."
            u"\n"
            u"UK Travel List Team")
        url = ';enquiry_confirm_form?user=%s&key=%s' % (user_id, confirm)
        url = context.uri.resolve(url)
        body = Template(body).substitute({'confirm_url': str(url)})
        root.send_email(from_addr, email, subject, body)

        # Back
        company = self.parent.get_property('dc:title')
        message = (
            u"Your enquiry to <strong>%s</strong> needs to be validated."
            u"<p>An email has been sent to <strong><em>%s</em></strong>,"
            u" to finish the enquiry process, please follow the instructions"
            u" detailed within it.</p>"
            u"<p>If you don not receive the email, please check your SPAM"
            u' folder settings or <a href="/;contact_form">contact us.</a></p>'
            % (company, email))
        return message.encode('utf-8')


    enquiry_confirm_form__access__ = True
    def enquiry_confirm_form(self, context):
        root = context.root

        user_id = context.get_form_value('user')
        users = root.get_handler('users')
        user = users.get_handler(user_id)

        # Check register key
        must_confirm = user.get_property('ikaaro:user_must_confirm')
        if (must_confirm is None
            or context.get_form_value('key') != must_confirm):
            return self.gettext(u"Bad key.").encode('utf-8')

        namespace = {}
        namespace['user_id'] = user_id
        namespace['key'] = must_confirm

        handler = self.get_handler('/ui/abakuc/companies/address_enquiry_confirm.xml')
        return stl(handler, namespace)


    enquiry_confirm__access__ = True
    def enquiry_confirm(self, context):
        keep = ['key']
        register_fields = [('newpass', True),
                           ('newpass2', True)]

        # Check register key
        user_id = context.get_form_value('user')
        root = context.root
        users = root.get_handler('users')
        user = users.get_handler(user_id)
        must_confirm = user.get_property('ikaaro:user_must_confirm')
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
            message = u'The passwords do not match.'
            return context.come_back(message, keep=keep)

        # Set user
        user.set_password(password)
        user.del_property('ikaaro:user_must_confirm')

        # Set cookie
        user.set_auth_cookie(context, password)

        # Send email
        self.enquiry_send_email(user)

        # Back
        #goto = "./;%s" % self.get_firstview()
        #return context.come_back(message, goto=goto)
        message = (u"Thank you, your enquiry to has been submitted.<br/>" 
                   u"If you like to login, please choose your password")
        return message.encode('utf-8')

    
    def enquiry_send_email(self, user, rows=None):
        # TODO, The actual system allow to send enquiries
        # to other companies before confirm registration
        # This enquiries are not send
        root = self.get_root()
        users = root.get_handler('users')

        firstname = user.get_property('ikaaro:firstname')
        lastname = user.get_property('ikaaro:lastname')
        email = user.get_property('ikaaro:email')
        to_addrs = [ users.get_handler(x).get_property('ikaaro:email')
                     for x in self.get_members() ]
        # FIXME UK Travel is hardcoded
        subject_template = u'[UK Travel] New Enquiry (%s)'
        body_template = ('Subject : %s\n'
                         'From : %s %s\n'
                         'Phone: %s\n'
                         '\n'
                         '%s')
        if not to_addrs:
            # No members, send to the administrator
            to_addrs.append(root.contact_email)
            company = self.parent.name
            subject_template = '%s - %s (%s)' % (subject_template,
                                                 company, self.name)

        if rows is None:
            csv = self.get_handler('log_enquiry.csv')
            results = csv.search(user_id=user.name)
            rows = []
            for line in results:
                print line
                rows.append(csv.get_row(line))

        for row in rows:
            kk, kk, phone, enquiry_type, enquiry_subject, enquiry, kk = row
            subject = subject_template % enquiry_type
            body = body_template % (enquiry_subject ,firstname, lastname,
                                    phone, enquiry)
            for to_addr in to_addrs:
                root.send_email(email, to_addr, subject, body)

    #######################################################################
    # User Interface / View Enquiries
    #######################################################################
    view_enquiries__access__ = 'is_reviewer_or_member'
    def view_enquiries(self, context):
        root = context.root
        users = root.get_handler('users')

        namespace = {}
        csv = self.get_handler('log_enquiry.csv')
        enquiries = []
        for row in csv.get_rows():
            date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
            if resolved:
                continue
            user = users.get_handler(user_id)
            if user.get_property('ikaaro:user_must_confirm') is None:
                enquiries.append({
                    'index': row.number,
                    'date': format_datetime(date),
                    'firstname': user.get_property('ikaaro:firstname'),
                    'lastname': user.get_property('ikaaro:lastname'),
                    'email': user.get_property('ikaaro:email'),
                    'enquiry_subject': enquiry_subject,
                    'phone': phone,
                    'type': EnquiryType.get_value(type)})
            enquiries.reverse()
        namespace['enquiries'] = enquiries

        handler = self.get_handler('/ui/abakuc/companies/address_view_enquiries.xml')
        return stl(handler, namespace)

    
    view_enquiry__access__ = 'is_reviewer_or_member'
    def view_enquiry(self, context):
        index = context.get_form_value('index', type=Integer)

        row = self.get_handler('log_enquiry.csv').get_row(index)
        date, user_id, phone, type, enquiry_subject, enquiry, resolved = row

        root = context.root
        user = root.get_handler('users/%s' % user_id)

        namespace = {}
        namespace['date'] = format_datetime(date)
        namespace['enquiry_subject'] = enquiry_subject 
        namespace['enquiry'] = enquiry 
        namespace['type'] = type
        namespace['firstname'] = user.get_property('ikaaro:firstname')
        namespace['lastname'] = user.get_property('ikaaro:lastname')
        namespace['email'] = user.get_property('ikaaro:email')
        namespace['phone'] = phone

        handler = root.get_handler('ui/abakuc/companies/address_view_enquiry.xml')
        return stl(handler, namespace)

    
    
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_reviewer_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'ikaaro:reviewers') or
                self.has_user_role(user.name, 'ikaaro:members'))
    

    def is_admin(self, user, object):
        return self.is_reviewer(user, object)


    def is_reviewer(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'ikaaro:reviewers') 


register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
