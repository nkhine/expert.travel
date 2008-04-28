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
from website import SiteRoot
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

class Company(SiteRoot):

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

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'countries':
            return self.get_handler('/countries')
        if name == 'companies':
            return self.get_handler('/companies')
        return SiteRoot._get_virtual_handler(self, segment)
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

    def is_branch_manager(self, user, object):
        for address in self.search_handlers(handler_class=Address):
            if address.is_branch_manager(user, address):
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
        namespace['website'] = self.get_website()
        namespace['logo'] = self.has_handler('logo')
        namespace['tabs'] = self.get_tabs_stl(context)

        handler = self.get_handler('/ui/abakuc/companies/company/view.xml')
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
    addresses__label__ = u'Branches'
    addresses__access__ = True
    def addresses(self, context):
        namespace = {}
        addresses = self.search_handlers(handler_class=Address)
        items = []
        for address in addresses:
            company = address.parent
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            enquire = '/companies/%s/%s/;enquiry_form' % (company.name, address.name)
            address_to_add = {'url': url,
                               'enquire': enquire,
                               'address': address.get_property('abakuc:address'),
                               'town': address.get_property('abakuc:town'),
                               'postcode': address.get_property('abakuc:postcode'),
                               'phone': address.get_property('abakuc:phone'),
                               'fax': address.get_property('abakuc:fax'),
                               'title': address.title_or_name}

            items.append(address_to_add) 

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

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        addresses = items[batch_start:batch_fin]
        # Namespace 
        if addresses:
            msgs = (u'There is one addresse.',
                    u'There are ${n} addresses.')
            address_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            address_table = None
            address_batch = None
            msg = u'Sorry but there is no address associated with this company.'

        namespace['addresses'] = items 
        namespace['msg'] = msg 
        namespace['batch'] = address_batch
        handler = self.get_handler('/ui/abakuc/companies/company/addresses.xml')

        return stl(handler, namespace)

    ####################################################################
    # List addresses 
    list_addresses__label__ = u'Branches'
    list_addresses__access__ = True
    def list_addresses(self, context):
        namespace = {}
        addresses = self.search_handlers(handler_class=Address)
        items = []
        for address in addresses:
            company = address.parent
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            enquire = '/companies/%s/%s/;enquiry_form' % (company.name, address.name)
            address_to_add = {'url': url,
                               'enquire': enquire,
                               'address': address.get_property('abakuc:address'),
                               'town': address.get_property('abakuc:town'),
                               'postcode': address.get_property('abakuc:postcode'),
                               'phone': address.get_property('abakuc:phone'),
                               'fax': address.get_property('abakuc:fax'),
                               'title': address.title_or_name}

            items.append(address_to_add) 

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

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        addresses = items[batch_start:batch_fin]
        # Namespace 
        if addresses:
            msgs = (u'There is one addresse.',
                    u'There are ${n} addresses.')
            address_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            address_table = None
            address_batch = None
            msg = u'Sorry but there is no address associated with this company.'

        namespace['addresses'] = items 
        namespace['msg'] = msg 
        namespace['batch'] = address_batch
        handler = self.get_handler('/ui/abakuc/companies/company/list_addresses.xml')

        return stl(handler, namespace)


    ####################################################################
    # List jobs 
    list_jobs__label__ = u'List jobs'
    list_jobs__access__ = True
    def list_jobs(self, context):
        from root import world
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
            county_id = get('abakuc:county')
            if county_id is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                row = world.get_row(county_id)
                region = row[7]
                county = row[8]
            url = '/companies/%s/%s/%s/' % (company.name, address.name, job.name)
            apply = '%s/;application_form' % (url)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'apply': apply,
                         'title': get('dc:title'),
                         'county': county,
                         'region': region,
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
        handler = self.get_handler('/ui/abakuc/companies/company/jobs.xml')
        return stl(handler, namespace)

    #######################################################################
    # Jobs - Search Interface
    #######################################################################
    jobs__access__ = True
    jobs_label__ = u'Jobs'
    def jobs(self, context):
        from root import world
        root = context.root
        namespace = {}
        # Total number of jobs
        today = date.today().strftime('%Y-%m-%d')
        query = [EqQuery('format', 'Job'),
                 EqQuery('company', self.name),
                 RangeQuery('closing_date', today, None)]
        # Search fields
        function = context.get_form_value('function') or None
        salary = context.get_form_value('salary') or None
        county = context.get_form_value('county') or None
        job_title = context.get_form_value('job_title') or None
        if job_title:
            job_title = job_title.lower()
        # Get Jobs (construct the query for the search)
        if function:
            query.append(EqQuery('function', function))
        if salary:
            query.append(EqQuery('salary', salary))
        if county:
            query.append(EqQuery('county', county))
        results = root.search(AndQuery(*query))

        # Construct the lines of the table
        add_line = True
        jobs = []
        for job in results.get_documents():
            job = root.get_handler(job.abspath)
            get = job.get_property
            address = job.parent
            company = address.parent
            county_id = get('abakuc:county')
            if county_id is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                row = world.get_row(county_id)
                region = row[7]
                county = row[8]
            url = '/companies/%s/%s/%s' % (company.name, address.name,
                                           job.name)
            apply = '%s/;application_form' % (url)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            if job_title is None or job_title in (job.title).lower():
                jobs.append({
                    'url': url,
                    'title': job.title,
                    'function': JobTitle.get_value(get('abakuc:function')),
                    'salary': SalaryRange.get_value(get('abakuc:salary')),
                    'county': county,
                    'region': region,
                    'apply': apply,
                    'closing_date': get('abakuc:closing_date'),
                    'description': description})
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
            job_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, 
                              msgs=(u"There is 1 job announcement.",
                                    u"There are ${n} job announcements."))
            msg = None
        else:
            job_batch = None
            msg = u"Appologies, currently we don't have any job announcements"
        namespace['batch'] = job_batch
        namespace['msg'] = msg 
        namespace['jobs'] = jobs

        # Search Namespace
        namespace['function'] = JobTitle.get_namespace(function)
        namespace['salary'] = SalaryRange.get_namespace(salary)
        namespace['job_title'] = job_title
        # Return the page
        handler = self.get_handler('/ui/abakuc/jobs/search.xhtml')
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
        handler = self.get_handler('/ui/abakuc/companies/company/news.xml')
        return stl(handler, namespace)

    #######################################################################
    # News - Search Interface 
    #######################################################################
    news__access__ = True
    news__label__ = u'Current news'
    def news(self, context):
        root = context.root
        namespace = {}
        # Total number of news items 
        today = date.today().strftime('%Y-%m-%d')
        query = [EqQuery('format', 'news'),
                 EqQuery('company', self.name),
                 RangeQuery('closing_date', today, None)]

        # Search fields
        #function = context.get_form_value('function') or None
        #salary = context.get_form_value('salary') or None
        #county = context.get_form_value('county') or None
        news_title = context.get_form_value('news_title') or None
        if news_title:
            news_title = news_title.lower()
        # Get Jobs (construct the query for the search)
        #if function:
        #    query.append(EqQuery('function', function))
        #if salary:
        #    query.append(EqQuery('salary', salary))
        #if county:
        #    query.append(EqQuery('county', county))
        results = root.search(AndQuery(*query))
        namespace['nb_news'] = results.get_n_documents()

        # Construct the lines of the table
        add_line = True
        news_items = []
        for news in results.get_documents():
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
            url = '/companies/%s/%s/%s' % (company.name, address.name,
                                           news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            if news_title is None or news_title in (news.title).lower():
                news_items.append({
                    'url': url,
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
        namespace['news_items'] = news_items

        # Search Namespace
        #namespace['function'] = JobTitle.get_namespace(function)
        #namespace['salary'] = SalaryRange.get_namespace(salary)
        namespace['news_title'] = news_title
        # Return the page
        handler = self.get_handler('/ui/abakuc/news/search.xhtml')
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

        handler = root.get_handler('ui/abakuc/companies/company/form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_branch_manager'
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

        handler = self.get_handler('/ui/abakuc/companies/company/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
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

    __roles__ = [
        {'name': 'abakuc:training_manager', 'title': u"Training Manager",
         'unit': u"Training Manager"},
        {'name': 'abakuc:branch_manager', 'title': u"Branch Manager",
         'unit': u"Branch Manager"},
        {'name': 'abakuc:branch_member', 'title': u"Branch Member",
         'unit': u"Branch Member"},
        {'name': 'abakuc:partner', 'title': u"Partner",
         'unit': u"Partner"},
        {'name': 'abakuc:guest', 'title': u"Guest",
         'unit': u"Guest"},
    ]

    __fixed_handlers__ = ['log_enquiry.csv']

    permissions_form__access__ = 'is_branch_manager'
    permissions__access__ = 'is_branch_manager'
    edit_membership_form__access__ = 'is_branch_manager'
    edit_membership__access__ = 'is_branch_manager'
    new_user_form__access__ = 'is_branch_manager'
    new_user__access__ = 'is_branch_manager'
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


    get_epoz_data__access__ = 'is_branch_manager_or_member'
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
        namespace['news'] = self.news(context)
        namespace['jobs'] = self.jobs(context)
        namespace['branches'] = self.addresses(context)
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

        handler = self.get_handler('/ui/abakuc/companies/company/address/view.xml')
        return stl(handler, namespace)

    ####################################################################
    # View news 
    news__label__ = u'News'
    news__access__ = True
    def news(self, context):
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
        handler = self.get_handler('/ui/abakuc/companies/company/news.xml')
        return stl(handler, namespace)

    ####################################################################
    # View jobs 
    jobs__label__ = u'Our jobs'
    jobs__access__ = True
    def jobs(self, context):
        from root import world
        namespace = {}
        namespace['batch'] = ''
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
            company = address.parent
            get = job.get_property
            county_id = get('abakuc:county')
            if county_id is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                row = world.get_row(county_id)
                region = row[7]
                county = row[8]
            # Information about the job
            url = '/companies/%s/%s/%s/' % (company.name, address.name, job.name)
            apply = '%s/;application_form' % (url)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'apply': apply,
                         'title': get('dc:title'),
                         'county': county,
                         'region': region,
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
        handler = self.get_handler('/ui/abakuc/companies/company/jobs.xml')
        return stl(handler, namespace)

    ####################################################################
    # View branches 
    addresses__label__ = u'Our branches'
    addresses__access__ = True
    def addresses(self, context):
        namespace = {}
        addresses = self.parent.search_handlers(handler_class=Address)
        items = []
        for address in addresses:
            company = address.parent
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            enquire = '/companies/%s/%s/;enquiry_form' % (company.name, address.name)
            address_to_add = {'url': url,
                               'enquire': enquire,
                               'address': address.get_property('abakuc:address'),
                               'town': address.get_property('abakuc:town'),
                               'postcode': address.get_property('abakuc:postcode'),
                               'phone': address.get_property('abakuc:phone'),
                               'fax': address.get_property('abakuc:fax'),
                               'title': address.title_or_name}

            items.append(address_to_add) 

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

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        addresses = items[batch_start:batch_fin]
        # Namespace 
        if addresses:
            msgs = (u'There is one addresse.',
                    u'There are ${n} addresses.')
            address_batch = batch(context.uri, batch_start, batch_size, 
                              batch_total, msgs=msgs)
            msg = None
        else:
            address_table = None
            address_batch = None
            msg = u'Sorry but there is no address associated with this company.'

        namespace['addresses'] = items 
        namespace['msg'] = msg 
        namespace['batch'] = address_batch
        handler = self.get_handler('/ui/abakuc/companies/company/addresses.xml')

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
            {'name': y, 'title': x, 'selected': x == address_country}
            #{'name': x, 'title': x, 'selected': x == address_country}
            for x, y in root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'
        # Show a list with all authorized countries
        countries.sort(key=lambda y: y['name'])
        regions = root.get_regions_stl(country_code=address_country,
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
        handler = root.get_handler('ui/abakuc/companies/company/address/form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_branch_manager'
    def edit_metadata_form(self, context):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
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
        # Get the country, the region and the county
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

        pp.pprint(address_country)
        pp.pprint(address_region)
        handler = self.get_handler('/ui/abakuc/companies/company/address/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
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
        from_addr = 'enquiries@expert.travel'
        subject = u"[%s] Confirmation required" % hostname
        subject = self.gettext(subject)
        body = self.gettext(
            u"This email has been generated in response to your"
            u" enquiry on Expert.Travel .\n"
            u"To submit your enquiry, click the link:\n"
            u"\n"
            u"  $confirm_url"
            u"\n"
            u"If the text is on two lines, please copy and "
            u"paste the full line into your browser URL bar."
            u"\n"
            u"Thank you for visiting the Expert.Travel."
            u"\n"
            u"UK.Expert.Travel Team")
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

        handler = self.get_handler('/ui/abakuc/enquiries/address_enquiry_confirm.xml')
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
    view_enquiries__access__ = 'is_branch_manager_or_member'
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

        handler = self.get_handler('/ui/abakuc/enquiries/address_view_enquiries.xml')
        return stl(handler, namespace)

    
    view_enquiry__access__ = 'is_branch_manager_or_member'
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

        handler = root.get_handler('ui/abakuc/enquiries/address_view_enquiry.xml')
        return stl(handler, namespace)

    
    
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'abakuc:branch_manager') or
                self.has_user_role(user.name, 'abakuc:branch_member'))
    

    def is_admin(self, user, object):
        return self.is_branch_manager(user, object)


    def is_branch_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'abakuc:branch_manager') 


register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
