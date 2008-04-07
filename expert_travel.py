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
from website import SiteRoot
from utils import t1, t2, t3, t4

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
                   ['edit_metadata_form']]


    def new(self, **kw):
        SiteRoot.new(self, **kw)
        cache = self.cache
        # Add extra handlers here
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
        help = XHTMLFile()
        cache['help.xhtml'] = help
        cache['help.xhtml.metadata'] = help.build_metadata(
            **{'dc:title': {'en': u'Help'}})

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        if name == 'training':
            return self.get_handler('/training')
        return SiteRoot._get_virtual_handler(self, segment)

      
    #######################################################################
    # User Interface / Navigation
    #######################################################################
    site_format = 'address'

    def get_level1_title(self, level1):
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

    #def get_training_uri(self, context):
    #    """Return a dict {training_icon, training}."""
    #    root = context.site_root
    #    home = '/training/%s/;%s' % (training.name, training.get_firstview())
    #    get_training = {'name': training.name, 'title': training.get_title(),
    #            'home': home}
    #    return {'info': get_training}

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
                <li><a href="#fragment-3"><span>Marketplace</span></a></li>
                <li><a href="#fragment-4"><span>Training</span></a></li>
            </ul>
            <div id="fragment-1">
              ${news} 
            </div>
            <div id="fragment-2">
              ${jobs}
            </div>
            <div id="fragment-3">
              {Training Programmes}
              Available training programmes for Travel Agents &amp; Tour
              Operator staff
            </div>
            <div id="fragment-4">
              {marketplace}
            </div>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)


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
        from root import world
        root = context.root
        here = context.handler
        site_root = here.get_site_root()
        namespace = {}
        namespace['user']= self.get_user_menu(context)
        # Get Company and Address
        namespace['address'] = None
        address = self.get_address()
        # Get the 5 last Jobs
        # XXX Fix so that it lists only jobs specific for the Country
        catalog = context.server.catalog
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
        # Construct the lines of the table
        #catalog = context.server.catalog
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
            get = news.get_property
            address = news.parent
            company = address.parent
            url = '/companies/%s/%s/%s' % (company.name, address.name, news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            news_items.append({'url': url,
                               'title': news.title,
                               'closing_date': get('abakuc:closing_date'),
                               'description': description})
        namespace['news'] = news_items
        namespace['news_url'] = ';news'

        # Login Form 
        namespace['action'] = '%s/;login' % here.get_pathto(site_root)
        namespace['username'] = context.get_form_value('username')

        namespace['tabs'] = self.get_tabs_stl(context)
        if address is None:
            handler = root.get_skin().get_handler('home.xhtml')
            return stl(handler, namespace)
        company = address.parent
        
        
        # Company
        namespace['company'] = {'name': company.name,
                                #'website': company.get_website(),
                                'path': self.get_pathto(company)}
        # Add news
        add_news = '/companies/%s/%s/;new_resource_form?type=news' % (company.name,
                                                                address.name)
        add_jobs = '/companies/%s/%s/;new_resource_form?type=Job' % (company.name,
                                                                address.name)
        # Address
        county = address.get_property('abakuc:county')
        addr = {'name': address.name,
                'add_news': add_news,
                'add_jobs': add_jobs,
                'address_path': self.get_pathto(address)}

        namespace['address'] = addr
        #XXX Fix as this does not work when viewing from Back-Office
        #XXX See [#119] http://bugs.abakuc.com/show_bug.cgi?id=119
        # Return the page
        handler = root.get_skin().get_handler('home.xhtml')
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
            county_id = get('abakuc:county')
            if county_id is None:
                # XXX Every job should have a county
                region = ''
                county = ''
            else:
                row = world.get_row(county_id)
                region = row[7]
                county = row[8]
            url = '/companies/%s/%s/%s' % (company.name, address.name, job.name)
            apply = '/companies/%s/%s/%s/;application_form' % (company.name, address.name, job.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'url': url,
                         'apply': apply,
                         'region': region,
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


register_object_class(ExpertTravel)
