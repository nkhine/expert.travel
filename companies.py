# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import locale
import sha
import pickle
import subprocess
from datetime import datetime, date, timedelta
from string import Template
import mimetypes

# Import from itools
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.catalog import schedule_to_reindex
from itools.cms.csv import CSV
from itools.cms.html import XHTMLFile
from itools.cms.metadata import Password
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.utils import generate_password
from itools.cms.utils import reduce_string
from itools.cms.versioning import VersioningAware
from itools.cms.widgets import table, batch
from itools.cms.workflow import WorkflowAware
from itools.datatypes import Email, Integer, String, Unicode, FileName
from itools.i18n.locale_ import format_datetime
from itools.stl import stl
from itools.uri import Path, Reference, get_reference, encode_query
from itools.web import get_context
from itools.xhtml import Document as XHTMLDocument
from itools.xml import get_element
from itools import get_abspath
from itools.handlers import get_handler

# Import from abakuc
from base import Handler, Folder
from forum import Forum
from handlers import EnquiriesLog, EnquiryType, AffiliationTable
from jobs import Job
from metadata import JobTitle, SalaryRange
from news import News
from product import Product
from utils import get_sort_name, t1, t2, t3, t4, t5
from website import SiteRoot

def crypt_captcha(captcha):
    return sha.new(captcha).digest()

class Companies(Folder):

    class_id = 'companies'
    class_title = u'Expert Travel Website'
    class_icon16 = 'abakuc/images/Import16.png'
    class_icon48 = 'abakuc/images/Import48.png'

    class_views = [['view'],
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form', 'anonymous_form', 'contact_options_form']]

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
        # XXX this is very slow, as it has to loop for all companies.
        for item in companies:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            affiliation = get('abakuc:licence')
            #affiliations = pickle.loads(affiliation)
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

        handler = self.get_handler('/ui/abakuc/companies/view.xml')
        return stl(handler, namespace)


class Company(SiteRoot, Folder):

    class_id = 'company'
    class_title = u'Company'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    site_format = 'address'

    class_views = [['view'],
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['permissions_form', 'new_user_form'],
                   ['new_resource_form'],
                   #['history_form'],
                   ['edit_metadata_form']]



    permissions_form__access__ = 'is_allowed_to_edit'
    new_user_form__access__ = 'is_allowed_to_edit'
    browse_content__access__ = 'is_admin'

    def get_document_types(self):
        return []

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
    def is_training(self):
        """
        Check to see if the user is on a training site.
        Return a bool
        """
        training = self.get_site_root()
        from training import Training
        if isinstance(training, Training):
            training = True
        else:
            training = False
        return training

    def get_website(self):
        website = self.get_property('abakuc:website')
        if website.startswith('http://'):
            return website
        return 'http://' + website

    def tabs(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        root = context.root
        namespace = {}
        namespace['news'] = self.list_news(context)
        namespace['jobs'] = self.list_jobs(context)
        namespace['products'] = self.products(context)
        namespace['branches'] = self.list_addresses(context)

        template_path = 'ui/abakuc/companies/company/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_allowed_to_edit(self, user, object):
        if user is not None:
            address = user.get_address()
            if address:
                #for address in self.search_handlers(handler_class=Address):
                return address.has_user_role(user.name, 'abakuc:branch_member')
        else:
            return False

    def is_branch_manager(self, user, object):
        if user is not None:
            for address in self.search_handlers(handler_class=Address):
                if address.is_branch_manager(user, address):
                    return True
        return False

    #def is_branch_manager(self, user, object):
    #    address = user.get_address()
    #    return address.has_user_role(user.name, 'abakuc:training_manager', 'abakuc:branch_member')

    #######################################################################
    # User Interface / View
    #######################################################################
    #view__access__ = 'is_allowed_to_view'
    view__access__ = True 
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        description = reduce_string(self.get_property('dc:description'),
                                        word_treshold=180,
                                        phrase_treshold=480)
        namespace['description'] = description
        namespace['website'] = self.get_website()
        namespace['licence'] = self.get_property('abakuc:licence')
        namespace['logo'] = self.has_handler('logo')
        namespace['tabs'] = self.tabs(context)

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
        root = context.site_root
        here = context.handler or root
        title = here.get_title()
        namespace = {}
        addresses = self.search_handlers(handler_class=Address)
        items = []
        for address in addresses:
            handler = root.get_handler(address.abspath)
            url = '%s/' % here.get_pathto(handler)
            address_to_add = {'url': url+';view',
                               'enquire': url+';enquiry_form',
                               'address': address.get_property('abakuc:address'),
                               'town': address.get_property('abakuc:town'),
                               'postcode': address.get_property('abakuc:postcode'),
                               'phone': address.get_property('abakuc:phone'),
                               'fax': address.get_property('abakuc:fax'),
                               'title': address.title_or_name}

            items.append(address_to_add)

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 2
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace
        if items:
            msgs = (u'There is one addresse.',
                    u'There are ${n} addresses.')
            items_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            items_table = None
            items_batch = None
            msg = u'Sorry but there is no address associated with this company.'

        namespace['msg'] = msg
        namespace['batch'] = items_batch
        namespace['title'] = title
        namespace['items'] = items
        handler = self.get_handler('/ui/abakuc/companies/company/addresses.xml')
        return stl(handler, namespace)

    ####################################################################
    # List addresses
    list_addresses__label__ = u'Branches'
    list_addresses__access__ = True
    def list_addresses(self, context):
        root = context.site_root
        here = context.handler or root
        namespace = {}
        #namespace['title'] = company.title_or_name
        addresses = self.search_handlers(handler_class=Address)
        items = []
        for address in addresses:
            handler = root.get_handler(address.abspath)
            url = '%s/' % here.get_pathto(handler)
            address_to_add = {'url': url,
                               'enquire': url+';enquiry_form',
                               'address': address.get_property('abakuc:address'),
                               'town': address.get_property('abakuc:town'),
                               'postcode': address.get_property('abakuc:postcode'),
                               'phone': address.get_property('abakuc:phone'),
                               'fax': address.get_property('abakuc:fax'),
                               'title': address.title_or_name}

            items.append(address_to_add)

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 2
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace
        if items:
            msgs = (u'There is one addresse.',
                    u'There are ${n} addresses.')
            items_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            items_table = None
            items_batch = None
            msg = u'Sorry but there is no address associated with this company.'

        namespace['msg'] = msg
        namespace['batch'] = items_batch
        namespace['items'] = items
        handler = self.get_handler('/ui/abakuc/companies/company/list_addresses.xml')

        return stl(handler, namespace)

    ####################################################################
    # List jobs
    list_jobs__label__ = u'List jobs'
    list_jobs__access__ = True
    def list_jobs(self, context):
        from root import world
        root = context.site_root
        here = context.handler or root
        namespace = {}
        namespace['batch'] = ''
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
            county = get('abakuc:county')
            if county is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                for row_number in world.search(county=county):
                    row = world.get_row(row_number)
                    region = row[7]
                    county = get('abakuc:county')
            url = '%s/' % here.get_pathto(job)
            apply = '%s/;application_form' % (url)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url+';view',
                         'apply': apply,
                         'title': get('dc:title'),
                         'county': county,
                         'region': region,
                         'closing_date': get('abakuc:closing_date'),
                         'address': address.get_title_or_name(),
                         'function': JobTitle.get_value(
                                        get('abakuc:functions')),
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
        here = context.handler or root
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
            county = get('abakuc:county')
            if county is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                for row_number in world.search(county=county):
                    row = world.get_row(row_number)
                    region = row[7]
                    county = row[8]
            url = '%s/' % here.get_pathto(job)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            if job_title is None or job_title in (job.title).lower():
                jobs.append({
                    'url': url+';view',
                    'title': job.title,
                    'function': JobTitle.get_value(get('abakuc:function')),
                    'salary': SalaryRange.get_value(get('abakuc:salary')),
                    'county': county,
                    'region': region,
                    'apply': url+';application_form',
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
        handler = self.get_handler('/ui/abakuc/jobs/search.xml')
        return stl(handler, namespace)


    ####################################################################
    # View news
    list_news__label__ = u'List news'
    list_news__access__ = True
    def list_news(self, context):
        namespace = {}
        namespace['batch'] = ''
        #Search the catalogue, list all news items in company
        root = context.site_root
        here = context.handler or root
        catalog = context.server.catalog
        query = []
        today = (date.today()).strftime('%Y-%m-%d')
        #query.append(EqQuery('format', 'news'))
        #query.append(EqQuery('company', self.name))
        #query.append(RangeQuery('closing_date', today, None))
        query = [EqQuery('format', 'news'),
                 EqQuery('company', self.name),
                 RangeQuery('closing_date', today, None)]
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
            url = '%s/' % here.get_pathto(news)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            news_items.append({'url': url+';view',
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
        here = context.handler or root
        namespace = {}
        # Total number of news items
        today = date.today().strftime('%Y-%m-%d')
        query = [EqQuery('format', 'news'),
                 EqQuery('company', self.name),
                 RangeQuery('closing_date', today, None)]

        news_title = context.get_form_value('news_title') or None
        if news_title:
            news_title = news_title.lower()
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
            url = '%s/' % here.get_pathto(news)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            if news_title is None or news_title in (news.title).lower():
                news_items.append({
                    'url': url+';view',
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
        handler = self.get_handler('/ui/abakuc/news/search.xml')
        return stl(handler, namespace)

    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(name=None, description=None, website=None, topics=None,\
                types=None, logo=None, rating=None, subject=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['description'] = description
        namespace['website'] = website
        #XXX Make this list only types specific for the sub-site
        #site_specific_types = root.get_site_types(types)
        #if site is localhost list all
        #if site is expert.travel select types with id = 1
        #if site is destinations guide select types with id = 2
        # etc....
        namespace['types'] = root.get_types_namespace(types)
        namespace['logo'] = logo
        namespace['subject'] = subject

        namespace['topics'] = root.get_topics_namespace(topics)

        namespace['rating'] = rating
        #if 'hotel' in topics:
        #    rating = root.get_rating_types(rating)
        #    namespace['rating'] = rating

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
        rating = self.get_property('abakuc:rating')
        logo = self.has_handler('logo')
        subject = self.get_property('dc:subject')
        namespace['form'] = self.get_form(title, description, website,\
                                        topics, types, logo, rating, subject)

        handler = self.get_handler('/ui/abakuc/companies/company/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
    def edit_metadata(self, context):
        username = get_context().user.name
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')
        website = context.get_form_value('abakuc:website')
        rating = context.get_form_value('abakuc:rating')
        logo = context.get_form_value('logo')
        subject = context.get_form_value('dc:subject')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')

        # If hotel we need to set the topic and type
        hotel = self.get_property('abakuc:rating')
        if hotel:
            self.set_property('abakuc:rating', rating)
            topics = ['hotel']
            types = 'other'

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description)
        self.set_property('abakuc:website', website)
        self.set_property('abakuc:topic', tuple(topics))
        self.set_property('abakuc:type', types)
        self.set_property('dc:subject', subject)

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


        property = {
            (None, 'user'): username,
            ('dc', 'date'): datetime.now(),
        }
        self.set_property('ikaaro:history', property)

        # Re-index addresses
        for address in self.search_handlers(handler_class=Address):
            schedule_to_reindex(address)

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)

    ####################################################################
    # List all products 
    products__label__ = u'List products'
    products__access__ = True
    def products(self, context):
        root = context.root
        here = context.handler or root
        from root import world
        namespace = {}
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'product'))
        # We only need this objects items
        query.append(EqQuery('company', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        products = []
        for item in list(documents):
            product = root.get_handler(item.abspath)
            get = product.get_property
            # Information about the item
            address = product.parent
            company = address.parent
            url = '%s/' % self.get_pathto(product)
            description = reduce_string(product.get_property('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            # Price and currency
            price = product.get_property('abakuc:price')
            currency = product.get_property('abakuc:currency')
            currencies = root.get_currency(currency)
            if currency:
                currency = (d for d in currencies if d['is_selected']).next()
                if currency['id'] == 'EUR':
                    locale.setlocale(locale.LC_ALL,('fr', 'ascii'))
                    price = locale.format('%.2f', price, True)
                    format = '%s %s' % (price, currency['sign'])
                else:
                    locale.setlocale(locale.LC_ALL,('en', 'ascii'))
                    price = locale.format('%.2f', price, True)
                    format = '%s %s' % (currency['sign'], price)
            
            else:
                format = None
            #namespace['price'] = format

            # Hotel information
            hotel_location = product.get_property('abakuc:hotel')
            # Every product must have a location
            # XXX what if it is a cruise?

            if hotel_location:
                hotel_address = product.get_address(hotel_location)
                county = hotel_address.get_property('abakuc:county')
                hotel = hotel_address.parent
                #county = get('abakuc:county')
                if county is not None:
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        country = row[6]
                        region = row[7]
                        county = row[8]
                else:
                    country = ''
                    region = ''
                    county = ''

                item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'title': product.get_property('dc:title'),
                             'hotel': hotel.get_property('dc:title'),
                             'region': region,
                             'country': country,
                             'closing_date': get('abakuc:closing_date'),
                             'price': format,
                             'description': description}
            else:
                item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'title': product.get_property('dc:title'),
                             'hotel': None,
                             'region': None,
                             'country': None,
                             'closing_date': get('abakuc:closing_date'),
                             'price': format,
                             'description': description}
            products.append(item_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('t4', default=0))
        batch_size = 5
        batch_total = len(products)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        products = products[batch_start:batch_fin]
        # Namespace
        if products:
            msgs = (u'There is one product.',
                    u'There are ${n} products.')
            products_batch = t4(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            products_table = None
            products_batch = None
            msg = u'Sorry but there are no products'

        namespace['products'] = products
        namespace['batch'] = products_batch
        namespace['msg'] = msg
        handler = self.get_handler('/ui/abakuc/companies/company/products.xml')
        return stl(handler, namespace)

    ####################################################################
    # List company products 
    list_products__label__ = u'List products'
    list_products__access__ = True
    def list_products(self, context):
        from root import world
        namespace = {}
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'product'))
        query.append(EqQuery('company', self.name))
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        products = []
        for item in list(documents):
            product = root.get_handler(item.abspath)
            get = product.get_property
            # Information about the item
            address = product.parent
            company = address.parent
            url = '%s/' % self.get_pathto(product)
            description = reduce_string(product.get_property('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            # Price and currency
            price = product.get_property('abakuc:price')
            currency = product.get_property('abakuc:currency')
            currencies = root.get_currency(currency)
            if currency:
                currency = (d for d in currencies if d['is_selected']).next()
                if currency['id'] == 'EUR':
                    locale.setlocale(locale.LC_ALL,('fr', 'ascii'))
                    price = locale.format('%.2f', price, True)
                    format = '%s %s' % (price, currency['sign'])
                else:
                    locale.setlocale(locale.LC_ALL,('en', 'ascii'))
                    price = locale.format('%.2f', price, True)
                    format = '%s %s' % (currency['sign'], price)
            
            else:
                format = None
            #namespace['price'] = format

            # Hotel information
            hotel_location = product.get_property('abakuc:hotel')
            # Every product must have a location
            # XXX what if it is a cruise?

            if hotel_location:
                hotel_address = product.get_address(hotel_location)
                county = hotel_address.get_property('abakuc:county')
                hotel = hotel_address.parent
                #county = get('abakuc:county')
                if county is not None:
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        country = row[6]
                        region = row[7]
                        county = row[8]
                else:
                    country = ''
                    region = ''
                    county = ''

                item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'title': product.get_property('dc:title'),
                             'hotel': hotel.get_property('dc:title'),
                             'region': region,
                             'country': country,
                             'closing_date': get('abakuc:closing_date'),
                             'price': format,
                             'description': description}
            else:
                item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'title': product.get_property('dc:title'),
                             'hotel': None,
                             'region': None,
                             'country': None,
                             'closing_date': get('abakuc:closing_date'),
                             'price': format,
                             'description': description}
            products.append(item_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('t4', default=0))
        batch_size = 5
        batch_total = len(products)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        products = products[batch_start:batch_fin]
        # Namespace
        if products:
            msgs = (u'There is one product.',
                    u'There are ${n} products.')
            products_batch = t4(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            products_table = None
            products_batch = None
            msg = u'Sorry but there are no products'

        namespace['products'] = products
        namespace['batch'] = products_batch
        namespace['msg'] = msg
        handler = self.get_handler('/ui/abakuc/companies/company/products.xml')
        return stl(handler, namespace)


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
        {'name': 'abakuc:branch_manager', 'title': u"Branch Manager",
         'unit': u"Branch Manager"},
        {'name': 'abakuc:branch_member', 'title': u"Branch Member",
         'unit': u"Branch Member"},
        {'name': 'abakuc:partner', 'title': u"Partner",
         'unit': u"Partner"},
        {'name': 'abakuc:guest', 'title': u"Guest",
         'unit': u"Guest"},
    ]

    __fixed_handlers__ = ['log_enquiry.csv', 'affiliation.csv']

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

        affiliation = AffiliationTable()
        cache['affiliation.csv'] = affiliation
        cache['affiliation.csv.metadata'] = affiliation.build_metadata()

        # Jobs folder
        #title = u'Products folder'
        #kw = {'dc:title': {'en': title}}
        #products = Products()
        #cache['products'] = products
        #cache['products.metadata'] = products.build_metadata(**kw)

    def get_document_types(self):
        return [News, Job, Product]


    get_epoz_data__access__ = 'is_branch_manager_or_member'
    def get_epoz_data(self):
        # XXX don't works
        context = get_context()
        job_text = context.get_form_value('abakuc:job_text')
        return job_text

    def get_products(self):
        root = self.get_root()
        handlers = self.search_handlers(handler_class=Product)
        for product in handlers:
            return root.get_handler(product.abspath)
        return None

    def get_catalog_indexes(self):
        from root import world

        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        topics = company.get_property('abakuc:topic')
        if topics is not None:
            indexes['level1'] = list(topics)
        county = self.get_property('abakuc:county')
        if county:
            for row_number in world.search(county=county):
                row = world.get_row(row_number)
                indexes['level0'] = row.get_value('iana_root_zone')
                indexes['level2'] = row[7]
                indexes['level3'] = self.get_property('abakuc:county')
        indexes['level4'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        # We need to index the news, jobs and products
        indexes['products'] = self.get_products()
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
           functions = user.get_property('abakuc:functions')
           state = user.get_property('state')
           if state == 'public':
                 members.append({'id': user.get_title,
                                 'url': url,
                                 'functions': functions,
                                 'phone': user.get_property('abakuc:phone'),
                                 'title': user.get_title()})
        # List users

        return members


    def tabs(self, context):
        # Set Style
        context.styles.append('/ui/abakuc/images/ui.tabs.css')
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        root = context.root
        namespace = {}
        namespace['news'] = self.news(context)
        namespace['jobs'] = self.jobs(context)
        namespace['products'] = self.products(context)
        namespace['branches'] = self.addresses(context)

        template_path = 'ui/abakuc/companies/company/tabs.xml'
        template = root.get_handler(template_path)
        return stl(template, namespace)

    #########################################################################
    # Affiliations 
    affiliations__label__ = u'Affiliations'
    affiliations__access__ = 'is_branch_manager'
    def affiliations(self, context):
        root = context.root
        root_csv = root.get_handler('affiliations.csv')
        csv = self.get_handler('affiliation.csv')
        rows = root_csv.get_rows()

        namespace = {}
        affiliations = []
        for row in csv.get_rows():
            ids, affiliation_no = row
            #for row_number in root_csv.search(
            #print ids
            #affiliations_list = root.get_affiliations_namespace(ids)
            for count, row in enumerate(rows):
                id = row[0]
                if ids == id:
                    title = row[1]
            affiliations.append({
                'index': row.number,
                #'affiliation': affiliations_list.title,
                'title': title,
                'affiliation': ids,
                'affiliation_no': affiliation_no})
        namespace['affiliations'] = affiliations

    #######################################################################
    # User Interface / View
    #######################################################################
    view__label__ = u'Address'
    view__access__ = True
    def view(self, context):
        from root import world
        county = self.get_property('abakuc:county')
        if county:
            for row_number in world.search(county=county):
                row = world.get_row(row_number)
                country = row[6]
                region = row[7]
        else:
            # XXX Every address should have a county
            country = region = county = '-'

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
        namespace['county'] = self.get_property('abakuc:county')


        ################
        # Tabs 
        namespace['tabs'] = self.tabs(context)

        handler = self.get_handler('/ui/abakuc/companies/company/address/view.xml')
        return stl(handler, namespace)

    ####################################################################
    # list news items in tabs 
    news__label__ = u'News'
    news__access__ = True
    def news(self, context):
        namespace = {}
        namespace['batch'] = ''
        #Search the catalogue, list all news items in address
        root = context.root
        here = context.handler or root
        company = self.parent
        handlers = self.search_handlers(handler_class=News)
        today = (date.today()).strftime('%Y-%m-%d')
        news_items = []
        for item in handlers:
            users = self.get_handler('/users')
            item = root.get_handler(item.abspath)
            get = item.get_property
            closing_date = get('abakuc:closing_date')
            # Information about the news item
            username = item.get_property('owner')
            user_exist = users.has_handler(username)
            usertitle = (user_exist and
                         users.get_handler(username).get_title() or username)
            url = '%s' % here.get_pathto(item)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            news_items.append({'url': url,
                               'title': item.title,
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
    # list jobs for tabs on address view 
    jobs__label__ = u'Our jobs'
    jobs__access__ = True
    def jobs(self, context):
        from root import world
        namespace = {}
        namespace['batch'] = ''
        # Construct the lines of the table
        root = context.root
        here = context.handler or root
        company = self.parent
        today = (date.today()).strftime('%Y-%m-%d')
        handlers = self.search_handlers(handler_class=Job)
        jobs = []
        for job in handlers:
            job = root.get_handler(job.abspath)
            get = job.get_property
            closing_date = get('abakuc:closing_date').strftime('%Y-%m-%d')
            if closing_date > today:
                address = job.parent
                company = address.parent
                county = get('abakuc:county')
                if county is None:
                    # XXX Every job should have a county
                    region = ''
                    county = ''
                else:
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        region = row[7]
                # Information about the job
                url = '%s' % here.get_pathto(job)
                apply = '%s/;application_form' % (url)
                description = reduce_string(get('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'apply': apply,
                             'title': get('dc:title'),
                             'county': get('abakuc:county'),
                             'region': region,
                             'closing_date': get('abakuc:closing_date'),
                             'address': address.get_title_or_name(),
                             'function': JobTitle.get_value(
                                            get('abakuc:functions')),
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
    # List all products for the tabs method on the home page
    products__label__ = u'Products'
    products__access__ = True
    def products(self, context):
        from root import world
        namespace = {}
        root = context.root
        here = context.handler or root
        today = date.today()
        handlers = self.search_handlers(handler_class=Product)
        products = []
        for item in handlers:
            product = root.get_handler(item.abspath)
            get = product.get_property
            closing_date = get('abakuc:closing_date')
            if closing_date is None:
                yesterday = today - timedelta(1)
                closing_date = yesterday
            if closing_date > today:
                # Information about the item
                address = product.parent
                company = address.parent
                url = '%s' % here.get_pathto(item)
                description = reduce_string(product.get_property('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                # Price and currency
                price = product.get_property('abakuc:price')
                currency = product.get_property('abakuc:currency')
                currencies = root.get_currency(currency)
                if currency:
                    currency = (d for d in currencies if d['is_selected']).next()
                    if currency['id'] == 'EUR':
                        locale.setlocale(locale.LC_ALL,('fr', 'ascii'))
                        price = locale.format('%.2f', price, True)
                        format = '%s %s' % (price, currency['sign'])
                    else:
                        locale.setlocale(locale.LC_ALL,('en', 'ascii'))
                        price = locale.format('%.2f', price, True)
                        format = '%s %s' % (currency['sign'], price)
                
                else:
                    format = None                
                # Hotel information
                hotel_location = product.get_property('abakuc:hotel')
                # Every product must have a location
                if hotel_location:
                    hotel_address = product.get_address(hotel_location)
                    county = hotel_address.get_property('abakuc:county')
                    hotel = hotel_address.parent
                    if county is not None:
                        for row_number in world.search(county=county):
                            row = world.get_row(row_number)
                            country = row[6]
                            region = row[7]
                            county = row[8]
                    else:
                        country = ''
                        region = ''
                        county = ''
                    item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                                 'url': url,
                                 'title': product.get_property('dc:title'),
                                 'hotel': hotel.get_property('dc:title'),
                                 'region': region,
                                 'country': country,
                                 'price': format,
                                 'closing_date': get('abakuc:closing_date'),
                                 'description': description}
                else:
                    item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                                 'url': url,
                                 'title': product.get_property('dc:title'),
                                 'hotel': None,
                                 'region': None,
                                 'country': None,
                                 'price': format,
                                 'closing_date': get('abakuc:closing_date'),
                                 'description': description}
                    
                products.append(item_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('t4', default=0))
        batch_size = 5
        batch_total = len(products)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        products = products[batch_start:batch_fin]
        # Namespace
        if products:
            msgs = (u'There is one product.',
                    u'There are ${n} products.')
            products_batch = t4(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            products_table = None
            products_batch = None
            msg = u'Sorry but there are no products'

        namespace['products'] = products
        namespace['batch'] = products_batch
        namespace['msg'] = msg
        handler = self.get_handler('/ui/abakuc/companies/company/products.xml')
        return stl(handler, namespace)

    ####################################################################
    # View branches
    addresses__access__ = 'is_self_or_admin'
    def addresses(self, context):
        namespace = {}
        company = self.parent
        response = Company.list_addresses(company, context)
        namespace['response'] = response
        # Return the page
        handler = self.get_handler('/ui/abakuc/response.xml')
        return stl(handler, namespace)

    #######################################################################
    # User Interface / Edit
    # /usr/sbin/python-updateruu
    #######################################################################
    @staticmethod
    def get_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 freephone=None, address_country=None, address_region=None,
                 address_county=None, hotel=None):
        context = get_context()
        root = context.root
        # List authorized countries
        countries = [
            {'name': y, 'title': x, 'selected': y == address_country}
            for x, y in root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'
        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])
        regions = root.get_regions_stl(country_code=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town
        namespace['phone'] = phone
        namespace['freephone'] = freephone
        namespace['fax'] = fax
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county
        namespace['hotel'] = hotel
        handler = root.get_handler('ui/abakuc/companies/company/address/form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_branch_manager'
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
        freephone = self.get_property('abakuc:freephone')
        fax = self.get_property('abakuc:fax')
        # Get the country, the region and the county
        from root import world
        address_county = self.get_property('abakuc:county')
        if address_county is None:
            address_country = None
            address_region = None
        else:
            for row_number in world.search(county=address_county):
                row = world.get_row(row_number)
                address_country = row[5]
                address_region = row[7]
        namespace['form'] = self.get_form(address, postcode, town, phone, fax,
                                          freephone, address_country, address_region,
                                          address_county)

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
        keys = ['address', 'postcode', 'town', 'phone', 'freephone', 'fax', 'county']

        for key in keys:
            key = 'abakuc:%s' % key
            value = context.get_form_value(key)
            self.set_property(key, value)

        # Set the address meta tags, generated from company and topic
        #company = self.parent
        #description = company.get_property('dc:description')
        #subject = company.get_property('dc:subject')
        #self.set_property('dc:description', description)
        #self.set_propery('dc:subject', subject)
        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        #goto = context.uri.resolve(';edit_account_form')
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
            # Captcha
            import Image as PILImage, ImageDraw, ImageFont
            # create a 5 char random strin
            imgtext = generate_password(5)
            crypt_imgtext = crypt_captcha(imgtext)
            encoded_imgtext = Password.encode('%s' % crypt_imgtext)
            # PIL "code" - open image, add text using font, save as new
            path = get_abspath(globals(), 'ui/images/captcha/bg.jpg')
            sound_path = get_abspath(globals(), 'data/sound')
            sound_output_path = get_abspath(globals(), 'ui/sound')
            im=PILImage.open(path)
            draw=ImageDraw.Draw(im)
            font_path = get_abspath(globals(), 'ui/fonts/SHERWOOD.TTF')
            font=ImageFont.truetype(font_path, 18)
            draw.text((10,10),imgtext, font=font, fill=(100,100,50))
            # save as a temporary image
            # XXX on page refresh the first file is not removed.
            im_name = generate_password(5)
            SITE_IMAGES_DIR_PATH = get_abspath(globals(), 'ui/images/captcha')
            tempname = '%s/%s' % (SITE_IMAGES_DIR_PATH, (im_name + '.jpg'))
            im.save(tempname, "JPEG")
            path = get_abspath(globals(), tempname)
            img = get_handler(path)
            namespace['img'] = img
            namespace['captcha'] = '/ui/abakuc/images/captcha/%s' % (im_name + '.jpg')
            # we need to pass this path as we can then delete the captcha file
            namespace['captcha_path'] = 'ui/images/captcha/%s' % (im_name + '.jpg')
            namespace['crypt_imgtext'] = encoded_imgtext
            # Generate a sound file of the captcha
            sox_filenames = []
            for x in imgtext:
                if x.isupper():
                    sox_filenames.append('%s/upper_%s.wav' % (sound_path, \
                                        x.lower()))
                else:
                    sox_filenames.append('%s/%s.wav' % (sound_path, x))
            subprocess.call(['sox'] + sox_filenames + \
                            ['%s/%s' % (sound_output_path, (im_name + '.wav'))])
            namespace['sound_captcha'] = '/ui/abakuc/sound/%s' % (im_name + '.wav')
            # we need to pass this path as we can then delete the file
            namespace['sound_path'] = 'ui/sound/%s' % (im_name + '.wav')
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
            # We remove the captcha
            captcha_path = context.get_form_value('captcha_path').strip()
            if captcha_path:
                im_handler = get_abspath(globals(), captcha_path)
                from itools import vfs
                vfs.remove(im_handler)
            enquiry_fields = self.enquiry_fields
            keep = [ x for x, y in enquiry_fields ]
            # We check captcha now 
            captcha = context.get_form_value('captcha').strip()
            crypted = crypt_captcha(captcha)
            crypt_imgtext = context.get_form_value('crypt_imgtext')
            decrypt =  Password.decode('%s' % crypt_imgtext)
            if crypted != decrypt:
                message = u'You typed an incorrect captcha string.'
                return context.come_back(message, keep=keep)
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
        subject_template = u'[UK.Expert.Travel] New Enquiry (%s)'
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
        root = context.root
        index = context.get_form_value('index', type=Integer)
        namespace = {}
        if index is not None:
            row = self.get_handler('log_enquiry.csv').get_row(index)
            date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
            user = root.get_handler('users/%s' % user_id)

            namespace['date'] = format_datetime(date)
            namespace['enquiry_subject'] = enquiry_subject
            namespace['enquiry'] = enquiry
            namespace['type'] = type
            namespace['firstname'] = user.get_property('ikaaro:firstname')
            namespace['lastname'] = user.get_property('ikaaro:lastname')
            namespace['email'] = user.get_property('ikaaro:email')
            namespace['phone'] = phone
        else:
            namespace['date'] = None 
            namespace['enquiry_subject'] = None
            namespace['enquiry'] = None
            namespace['type'] = None
            namespace['firstname'] = None
            namespace['lastname'] = None
            namespace['email'] = None
            namespace['phone'] = None

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
