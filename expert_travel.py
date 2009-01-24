# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
from datetime import date
from string import Template

# Import from itools
from itools.datatypes import XMLAttribute
from itools.catalog import EqQuery, AndQuery, PhraseQuery, RangeQuery
from itools import get_abspath
from itools.cms.csv import CSV
from itools.cms.html import XHTMLFile
from itools.cms.registry import register_object_class
from itools.cms.widgets import table, batch
from itools.cms.utils import reduce_string
from itools.stl import stl
from itools.utils import get_version

from itools.xhtml import Document as XHTMLDocument
# Import from abakuc
from metadata import JobTitle, SalaryRange
from training import Training
from website import SiteRoot
from users import User
from news import News
from utils import t1, t2, t3, t4, t5
from forum import Forum

class ExpertTravel(SiteRoot):

    class_id = 'expert_travel'
    class_title = u'Expert Travel Website'
    class_icon48 = 'abakuc/images/Import48.png'
    class_icon16 = 'abakuc/images/Import16.png'
    class_views = [['view'],
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form', 'contact_options_form']]

    def get_document_types(self):
        return [Forum]

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        if name == 'training':
            return self.get_handler('/training')
        return SiteRoot._get_virtual_handler(self, segment)

    def new(self, **kw):
        SiteRoot.new(self, **kw)
        cache = self.cache
        # Add extra handlers here
        forum = Forum()
        cache['forum'] = forum
        cache['forum.metadata'] = forum.build_metadata(
            **{'dc:title': {'en': u'Forum'}})
        terms = XHTMLFile()
        cache['terms.xhtml'] = terms
        cache['terms.xhtml.metadata'] = terms.build_metadata(
            **{'dc:title': {'en': u'Terms & Conditions'}})
        privacy = XHTMLFile()
        cache['privacy.xhtml'] = privacy
        cache['privacy.xhtml.metadata'] = privacy.build_metadata(
            **{'dc:title': {'en': u'Privacy'}})
        faq = XHTMLFile()
        cache['faq.xhtml'] = faq
        cache['faq.xhtml.metadata'] = faq.build_metadata(
            **{'dc:title': {'en': u'FAQs'}})
        #help = XHTMLFile()
        #cache['help.xhtml'] = help
        #cache['help.xhtml.metadata'] = help.build_metadata(
        #    **{'dc:title': {'en': u'Help'}})

    #######################################################################
    # User Interface
    #######################################################################
    site_format = 'address'

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_allowed_to_edit(self, user, object):
        if not user:
            return False
        address = user.get_address()
        #for address in self.search_handlers(handler_class=Address):
        if address:
            return address.has_user_role(user.name, 'abakuc:branch_member', 'abakuc:branch_manager')

    def is_branch_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        address = user.get_address()
        if address:
            return address.has_user_role(user.name, 'abakuc:branch_manager',
            'abakuc:branch_member')

    def is_training_manager(self, user, object):
        return True

    def get_level1_title(self, level1):
       #return level1
        topics = self.get_handler('../topics.csv')
        for row in topics.get_rows():
            if level1 == row[0]:
                return row[1]
        raise KeyError

    def get_user_menu(self, context):
        """Return a dict {user_icon, user, joinisopen}."""
        user = context.user

        if user is None:
            root = context.site_root
            joinisopen = root.get_property('ikaaro:website_is_open')
            return {'info': None, 'joinisopen': joinisopen}

        home = '/users/%s/;%s' % (user.name, user.get_firstview())
        info = {'name': user.name, 'title': user.get_title(),
                'home': home}
        return {'info': info, 'joinisopen': False}

    def get_tabs_stl(self, context):
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        namespace = {}
        namespace['news'] = self.list_news(context)
        namespace['jobs'] = self.list_jobs(context)
        namespace['products'] = self.list_products(context)
        namespace['training'] = self.training_table(context)
        namespace['forum'] = self.forum(context)
        template = """
        <stl:block xmlns="http://www.w3.org/1999/xhtml"
          xmlns:stl="http://xml.itools.org/namespaces/stl">
            <script type="text/javascript">
                var TABS_COOKIE = 'company_cookie';
                $(function() {
                    $('#container-1 > ul').tabs((parseInt($.cookie(TABS_COOKIE))) || 1,{click: function(clicked) {
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
                <li><a href="#fragment-3"><span>Training</span></a></li>
                <li><a href="#fragment-4"><span>Marketplace</span></a></li>
                <li><a href="#fragment-5"><span>Forum</span></a></li>
            </ul>
            <div id="fragment-1">
              ${news}
            </div>
            <div id="fragment-2">
              ${jobs}
            </div>
            <div id="fragment-3">
              ${training}
            </div>
            <div id="fragment-4">
              ${products}
            </div>
            <div id="fragment-5">
              ${forum}
            </div>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)

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

    def get_address(self):
        root = self.get_root()
        results = root.search(format='address', members=self.name)
        for address in results.get_documents():
            return root.get_handler(address.abspath)
        return None

    #######################################################################
    # List last 5 jobs and 5 news items for Home page
    #######################################################################
    view__access__ = True
    view__label__ = u'View'
    def view(self, context):
        from users import User
        from training import Training
        root = context.root
        user = context.user
        namespace = {}
        namespace['user']= self.get_user_menu(context)
        namespace['tabs'] = self.get_tabs_stl(context)
        namespace['login'] = self.login_form(context)
        namespace['register'] = self.register_form(context)
        if user is not None:
            namespace['profile'] = User.user(user, context)
            namespace['company'] = User.company(user, context)
        skin = root.get_skin()
        skin_path = skin.abspath
        if skin.abspath == '/ui/aruni':
            handler = self.get_handler('/ui/abakuc/home.xhtml')
        else:
            if isinstance(context.site_root, Training):
                handler = context.site_root.get_handler('faq.xhtml')
            else:
                handler = skin.get_handler('home.xhtml')
        return stl(handler, namespace)

    forum__access__ = True
    def forum(self, context):
        user = context.user
        namespace = {}
        forums = []
        # Get the expert.travel forum
        forum = list(self.search_handlers(format=Forum.class_id))
        for item in forum:
            forums.append(item)
        # Get all Training programmes forums
        root = context.root
        training = root.get_handler('training')
        from training import Training
        items = training.search_handlers(handler_class=Training)
        for item in items:
            # We only want to list the published TP forums
            is_open = item.get_property('ikaaro:website_is_open')
            if is_open is True:
                tp_forum = list(item.search_handlers(format=Forum.class_id))
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

            to_url = str(self.get_pathto(root))

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
        if user is not None:
            namespace['my_threads'] = 'users/%s/;my_threads' % user.name
        else:
            namespace['my_threads'] = None 
            
       
        namespace['office'] = None
        namespace['forum_links'] = forum_links
        namespace['forum'] = current_forums
        handler = self.get_handler('/ui/abakuc/forum/list.xml')
        return stl(handler, namespace)        


    terms__access__ = True
    def terms(self, context):
        namespace = {}
        handler = self.get_handler('/ui/abakuc/terms.xml')
        return stl(handler, namespace) 

    about__access__ = True
    def about(self, context):
        root = context.root
        namespace = {}
        handler = self.get_handler('/ui/abakuc/about.xml')
        return stl(handler, namespace) 


    help__access__ = True
    def help(self, context):
        namespace = {}
        handler = self.get_handler('/ui/abakuc/help.xml')
        return stl(handler, namespace) 

    more__access__ = True
    def more(self, context):
        namespace = {}
        handler = self.get_handler('/ui/abakuc/more.xml')
        return stl(handler, namespace) 

    points__access__ = True
    def points(self, context):
        namespace = {}
        handler = self.get_handler('/ui/abakuc/points.xml')
        return stl(handler, namespace) 

    ####################################################################
    # List
    ####################################################################
    list__label__ = u'List news'
    list__access__ = True
    def list(self, context):
        namespace = {}
        namespace['batch'] = ''
        #Search the catalogue, list all news items in company
        root = context.root
        catalog = context.server.catalog
        print catalog
        query = []
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        items = []
        news = []
        jobs = []
        products = []
        from training import Training
        training = self.get_site_root()
        for item in list(documents):
            users = self.get_handler('/users')
            item = root.get_handler(item.abspath)
            get = item.get_property
            # Information about the news item
            username = item.get_property('owner')
            user_exist = users.has_handler(username)
            usertitle = (user_exist and
                         users.get_handler(username).get_title() or username)
            if isinstance(training, Training):
                url = item.abspath
            else:
                url = Path(item.abspath)[1:]
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            items.append({'url': url,
                               'title': item.title,
                               'closing_date': get('abakuc:closing_date'),
                               'date_posted': get('dc:date'),
                               'owner': usertitle,
                               'description': description})
        # Set batch informations
        batch_start = int(context.get_form_value('t1', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace
        if items:
            msgs = (u'There is one news item.',
                    u'There are ${n} news items.')
            batch = t1(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            batch = None
            msg = u'Currently there is no news.'

        namespace['news_batch'] = batch
        namespace['msg'] = msg
        namespace['news_items'] = items
        handler = self.get_handler('/ui/abakuc/companies/company/news.xml')
        return stl(handler, namespace)
    ####################################################################
    # News - List
    ####################################################################
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
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        news_items = []
        from training import Training
        training = self.get_site_root()
        for news in list(documents):
            users = self.get_handler('/users')
            news = root.get_handler(news.abspath)
            get = news.get_property
            # Information about the news item
            username = news.get_property('owner')
            user_exist = users.has_handler(username)
            usertitle = (user_exist and
                         users.get_handler(username).get_title() or username)
            #if isinstance(training, Training):
            #    url = news.abspath
            #else:
            #    url = Path(news.abspath)[1:]
            url = self.get_pathto(news)
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
        batch_start = int(context.get_form_value('t1', default=0))
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
            news_batch = t1(context.uri, batch_start, batch_size,
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
                 RangeQuery('closing_date', today, None)]
        results = root.search(AndQuery(*query))
        namespace['number_of_news'] = results.get_n_documents()

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
        from training import Training
        training = self.get_site_root()
        for news in results.get_documents():
            users = self.get_handler('/users')
            news = root.get_handler(news.abspath)
            get = news.get_property
            # Information about the news item
            username = news.get_property('owner')
            user_exist = users.has_handler(username)
            usertitle = (user_exist and
                         users.get_handler(username).get_title() or username)
            url = self.get_pathto(news)
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
        handler = self.get_handler('/ui/abakuc/news/search.xml')
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
                    country = row[5]
                    region = row[7]
                    county = row[8]
            url = '%s' % self.get_pathto(job)
            #url = '/%s/%s/%s' % (company.name, address.name, job.name)
            apply = '%s/;application_form' % (url)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'apply': apply,
                         'region': region,
                         'county': get('abakuc:county'),
                         'title': get('dc:title'),
                         'closing_date': get('abakuc:closing_date'),
                         'address': address.get_title_or_name(),
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'salary': SalaryRange.get_value(get('abakuc:salary')),
                         'description': description}
            jobs.append(job_to_add)
        # Set batch informations
        batch_start = int(context.get_form_value('t2', default=0))
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
            job_batch = t2(context.uri, batch_start, batch_size,
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
    jobs__label__ = u'Jobs'
    def jobs(self, context):
        from root import world
        root = context.root
        namespace = {}
        # Total number of jobs
        today = date.today().strftime('%Y-%m-%d')
        query = [EqQuery('format', 'Job'),
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
            county = get('abakuc:county')
            if county is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                for row_number in world.search(county=county):
                    row = world.get_row(row_number)
                    country = row[5]
                    region = row[7]
                    county = get('abakuc:county')
            url = '%s/%s' % (self.get_pathto(job), job.name)
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
                    'country': country,
                    'region': region,
                    'county': county,
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
        handler = self.get_handler('/ui/abakuc/jobs/search.xml')
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
        from training import Training
        items = training.search_handlers(handler_class=Training)
        # Construct the lines of the table
        trainings = []
        for item in list(items):
            #job = root.get_handler(job.abspath)
            get = item.get_property
            is_open = item.get_property('ikaaro:website_is_open')
            if is_open is True:
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
        #handler = self.get_handler('/ui/abakuc/training/table.xml')
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)

    ####################################################################
    # List all products for the tabs method on the home page
    list_products__label__ = u'List products'
    list_products__access__ = True
    def list_products(self, context):
        from root import world
        namespace = {}
        root = context.root
        catalog = context.server.catalog
        query = []
        query.append(EqQuery('format', 'product'))
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
            # Hotel information
            hotel_location = product.get_property('abakuc:hotel')
            # Every product must have a location
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

                url = '%s/' % self.get_pathto(product)
                description = reduce_string(product.get_property('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                item_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                             'url': url,
                             'title': product.get_property('dc:title'),
                             'hotel': hotel.get_property('dc:title'),
                             'region': region,
                             'country': country,
                             'closing_date': get('abakuc:closing_date'),
                             'price': get('abakuc:price'),
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

register_object_class(ExpertTravel)
