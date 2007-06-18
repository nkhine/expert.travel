# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.stl import stl
from itools.cms.registry import register_object_class
from itools.cms.html import XHTMLFile
from itools.catalog import EqQuery
from itools.cms.widgets import table, batch

# Import from abakuc
from website import WebSite
from metadata import JobTitle, SalaryRange


class UKTravel(WebSite):
 
    class_id = 'uktravel'
    class_title = u'UK Travel List'
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
    # View Jobs 
    #######################################################################
    view_jobs__access__ = True
    view_jobs__label__ = u'Our jobs'
    def view_jobs(self, context):
        namespace = {}
        namespace['batch'] = ''
        sortby = context.get_form_value('sortby', 'closing_date')
        sortorder = context.get_form_value('sortorder', 'up')
        reverse = (sortorder == 'down')
        columns = [('name', u'Id'),
                   ('closing_date', u'Closing Date'),
                   ('title', u'Title'),
                   ('company', u'Company'),
                   ('function', u'Function'),
                   ('description', u'Short description')]

        # Get all Jobs
        root = context.root
        catalog = context.server.catalog
        results = catalog.search(EqQuery('format', 'Job'))
        documents = results.get_documents(sort_by=sortby, reverse=reverse)
        # Construct the lines of the table
        jobs = []
        for job in documents:
            job = root.get_handler(job.abspath)
            get = job.get_property
            # Informations about The company
            address = job.parent
            company = address.parent
            # Information about the job
            url = '/companies/%s/%s/%s/;view' % (company.name,
                                                      address.name, job.name)
            job_to_add ={'img': '/ui/abakuc/images/JobBoard16.png',
                         'name': (job.name,url),
                         'closing_date': get('abakuc:closing_date'),
                         'title': get('dc:title'),
                         'company': company.get_property('dc:title'),
                         'function': JobTitle.get_value(
                                        get('abakuc:function')),
                         'description': get('dc:description')}
            jobs.append(job_to_add)
        
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 20
        batch_total = len(jobs)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        jobs = jobs[batch_start:batch_fin]
        # Namespace 
        if jobs:
            job_table = table(columns, jobs, [sortby], sortorder,[])
            job_batch = batch(context.uri, batch_start, batch_size, batch_total)
            msg = None
        else:
            job_table = None
            job_batch = None
            msg = u'Sorry but there are no jobs'
        
        namespace['table'] = job_table
        namespace['batch'] = job_batch
        namespace['msg'] = msg 
        # Return the page
        handler = self.get_handler('/ui/%s/view_jobs.xhtml' % self.name)
        return stl(handler, namespace)




register_object_class(UKTravel)
