# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the standard library
from datetime import date

# Import from itools
from itools.catalog import EqQuery, AndQuery, PhraseQuery, RangeQuery
from itools import get_abspath
from itools.cms.csv import CSV
from itools.cms.html import XHTMLFile
from itools.cms.registry import register_object_class
from itools.cms.widgets import table, batch
from itools.cms.utils import reduce_string
from itools.stl import stl

# Import from abakuc
from metadata import JobTitle, SalaryRange
from website import WebSite


class ExpertTravel(WebSite):
 
    class_id = 'expert_travel'
    class_title = u'Expert Travel Website'
    class_icon48 = 'abakuc/images/Import48.png'
    class_icon16 = 'abakuc/images/Import16.png'

    def new(self, **kw):
        WebSite.new(self, **kw)
        cache = self.cache
        # Add extra handlers here
        news = XHTMLFile()
        cache['news.xhtml'] = news
        cache['news.xhtml.metadata'] = news.build_metadata(
            **{'dc:title': {'en': u'News Folder List'}})
        events = XHTMLFile()
        cache['events.xhtml'] = events
        cache['events.xhtml.metadata'] = events.build_metadata(
            **{'dc:title': {'en': u'Events'}})
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
        return WebSite._get_virtual_handler(self, segment)

      
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

    #######################################################################
    # List last 5 jobs and 5 news items for Home page
    #######################################################################
    def view(self, context):
        root = context.root
        namespace = {}
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
        documents = documents[0:4]
        news_items = []
        for news in documents:
            news = root.get_handler(news.abspath)
            address = news.parent
            company = address.parent
            url = '/companies/%s/%s/%s' % (company.name, address.name, news.name)
            news_items.append({'url': url,
                         'title': news.title})
        namespace['news'] = news_items
        # Return the page
        handler = root.get_skin().get_handler('home.xhtml')
        return stl(handler, namespace)


    #######################################################################
    # View Jobs 
    #######################################################################
    view_jobs__access__ = True
    view_jobs__label__ = u'Our jobs'
    def view_jobs(self, context):
        from root import world

        root = context.root

        namespace = {}
        # Total number of jobs
        today = date.today().strftime('%Y-%m-%d')
        query = [EqQuery('format', 'Job'),
                 RangeQuery('closing_date', today, None)]
        results = root.search(AndQuery(*query))
        namespace['number_of_jobs'] = results.get_n_documents()

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
        namespace['nb_jobs'] = results.get_n_documents()

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
        handler = self.get_handler('/ui/uk.expert.travel/view_jobs.xhtml')
        return stl(handler, namespace)


register_object_class(ExpertTravel)
