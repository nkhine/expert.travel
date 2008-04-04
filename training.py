# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime, date

# Import from itools
from itools.stl import stl
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.registry import register_object_class
from itools.cms.widgets import batch
from itools.cms.skins import Skin 
from itools.cms.file import File
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware
from itools.datatypes import FileName
from itools.web import get_context
from itools.cms.catalog import schedule_to_reindex
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.uri import Path, get_reference

# Import from abakuc
from companies import Company
from base import Handler, Folder
from website import SiteRoot 
from document import Document
from utils import get_sort_name
from exam import Exam
from news import News
from jobs import Job
from metadata import JobTitle, SalaryRange
from namespaces import Region, BusinessFunction, JobFunction, BusinessProfile
from marketing import Marketing

month_names = [
    u'January', u'February', u'March', u'April', u'May', u'June',
    u'July', u'August', u'September', u'October', u'November', u'December']

class Trainings(SiteRoot):

    class_id = 'trainings'
    class_title = u'Training programmes'
    class_icon16 = 'abakuc/images/Trainings16.png'
    class_icon48 = 'abakuc/images/Trainings48.png'
    class_views = [
                ['view'],
                ['browse_content?mode=list'],
                ['new_resource_form'],
                ['edit_metadata_form']]

    
    site_format = 'training'

    def get_document_types(self):
        return [Training]

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = True 
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Training)
        items = []
        for item in items:
            state = item.get_property('state')
            if state == 'public':
                get = item.get_property
                url = '%s/;view' %  item.name
                description = reduce_string(get('dc:description'),
                                            word_treshold=90,
                                            phrase_treshold=240)
                items_to_add = {'url': url,
                          'description': description,
                          'title': item.title_or_name}
                items.append(items_to_add)


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
            msgs = (u'There is one training programme.',
                    u'There are ${n} training programmes.')
            batch = batch(context.uri, batch_start, batch_size, 
                          batch_total, msgs=msgs)
            msg = None
        else:
            batch = None
            msg = u'Currently there no published training programmes.'
        
        namespace['batch'] = batch
        namespace['msg'] = msg 
        namespace['items'] = items
        namespace['title'] = title 
        handler = self.get_handler('/ui/abakuc/training/list.xml')
        return stl(handler, namespace)

class Training(SiteRoot, WorkflowAware):

    class_id = 'training'
    class_title = u'Training programme'
    class_icon16 = 'abakuc/images/Training16.png'
    class_icon48 = 'abakuc/images/Training48.png'
    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['statistics', 'league'],
                   ['edit_metadata_form',
                    'virtual_hosts_form',
                    'anonymous_form',
                    'languages_form',
                    'state_form',
                    'contact_options_form'],
                   ['permissions_form',
                    'new_user_form'],
                   ['last_changes']]
    __roles__ = [
        {'name': 'abakuc:training_manager', 'title': u"Training Manager",
         'unit': u"Training Manager"},
        {'name': 'abakuc:branch_manager', 'title': u"Branch Manager",
         'unit': u"Branch Manager"},
        {'name': 'abakuc:partner', 'title': u"Partner",
         'unit': u"Partner"},
        {'name': 'abakuc:branch_member', 'title': u"Branch Member",
         'unit': u"Branch Member"},
    ]
  
    new_resource_form__access__ = 'is_branch_manager' 
    new_resource__access__ = 'is_branch_manager'

    site_format = 'module'

    def get_document_types(self):
        return [Module]

    def get_level1_title(self, level1):
        return level1 

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        if name == 'training':
            return self.get_handler('/training')
        return SiteRoot._get_virtual_handler(self, segment)
    #######################################################################
    # API 
    #######################################################################
    def get_vhosts(self):
        vhosts = self.get_property('ikaaro:vhosts')
        return vhosts

    def get_modules(self):
        modules = list(self.search_handlers(format=Module.class_id))
        modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return modules

    def login(self, context):
        response = SiteRoot.login(self, context)
        if str(response.path[-1]) == ';login_form':
            return response
        user = context.user
        if not self.has_user_role(user.name, 'abakuc:branch_manager') and \
           not self.has_user_role(user.name, 'abakuc:partner') and \
           not self.has_user_role(user.name, 'abakuc:branch_member'):
            self.set_user_role(user.name, 'abakuc:branch_member')
            schedule_to_reindex(user)

        return response

    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_training_form(name=None, description=None, vhosts=None, topics=None):
        root = get_context().root
        namespace = {}
        namespace['title'] = name
        namespace['description'] = description 
        namespace['vhosts'] = vhosts
        namespace['topics'] = root.get_topics_namespace(topics)

        handler = root.get_handler('ui/abakuc/training/training_form.xml')
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
   
   
    def is_travel_agent(self, user, object):
        if user is None:
            return False

        # TEST 015
        return self.has_user_role(user.name, 'abakuc:branch_member')

    # Exam Access Control
    def is_allowed_to_take_exam(self, user, object):
        if self.is_admin(user, object):
            return True

        if not self.is_travel_agent(user, object):
            return False

        # Has the user already passed this exam?
        passed = object.get_result()[0]
        if passed:
            return False
        # Is this the first module?
        module = object.parent
        prev_module = module.get_prev_module()
        if prev_module is None:
            return True
        exam = prev_module.get_exam()
        # Previous module has no exam? (BahamaBay has just one exam at end)
        if exam is None:
            return True
        # Has the user passed the previous exam?
        passed = exam.get_result()[0]
        return bool(passed)

    ########################################################################
    # Statistics
    statistics__access__ = True 
    #statistics__access__ = 'is_allowed_to_view_statistics'
    statistics__label__ = u'Statistics'
    statistics__sublabel__ = u'Statistics'
    def statistics(self, context):
        year = context.get_form_value('year')
        month = context.get_form_value('month')
        module = context.get_form_value('module')
        layout = context.get_form_value('layout', 'region/business_profile')
        region = context.get_form_value('region')

        # Build the namespace
        namespace = {}
        layout_options = [
            ('region/business_profile', u'Region x Business profile'),
            ('region/business_function', u'Region x Business function'),
            ('region/job_function', u'Region x Job function'),
            ('job_function/business_profile',
             u'Job function x Business profile'),
            ('job_function/business_function',
             u'Job function x Business function'),
            ('business_function/business_profile',
             u'Business function x Business profile')]

        namespace['layout'] = [
            {'name': name, 'value': value, 'selected': name == layout}
            for name, value in layout_options ]

        namespace['months'] = [ {'name': i+1, 'value': self.gettext(title),
                                 'selected': str(i+1) == month}
                                for i, title in enumerate(month_names) ]
        years = range(2001, datetime.date.today().year + 1)
        namespace['years'] = [
            {'name': x, 'value': x, 'selected': str(x) == year}
            for x in years ]
        namespace['modules'] = [
            {'name': x.name, 'title': '%d - %s' % (i+1, x.title),
             'selected': x.name == module}
            for i, x in enumerate(self.get_modules()) ]

        # Statistics criterias
        vertical, horizontal = layout.split('/')
        regions = Region.get_namespace(None)
        criterias = {'region': regions,
                     'business_function': BusinessFunction.get_options(),
                     'job_function':  JobFunction.get_options(),
                     'business_profile': BusinessProfile.get_options()}
        horizontal_criterias = criterias[horizontal]
        vertical_criterias = criterias[vertical]

        # Filter the users
        root = context.root
        query = {'training_programmes': self.name}
        if month:
            query['registration_month'] = month
        if year:
            query['registration_year'] = year
        if region:
            query['region'] = region
            vertical_criterias = Region.get_counties(region)
            vertical = 'county'
        # TEST 015
        results = root.search(**query)
        brains = results.get_documents()
        if module:
            aux = []
            mod = self.get_handler(module)
            for brain in brains:
                exam = mod.get_exam(brain.name)
                if exam is None:
                    continue
                has_passed = exam.get_result(brain.name)[0]
                if has_passed:
                    aux.append(brain)
            brains = aux

        # Classify the users
        table = {}
        table[('', '')] = 0
        for x in horizontal_criterias:
            table[(x['name'], '')] = 0
        for y in vertical_criterias:
            table[('', y['name'])] = 0
        for x in horizontal_criterias:
            x = x['name']
            for y in vertical_criterias:
                table[(x, y['name'])] = 0

        for brain in brains:
            x = getattr(brain, horizontal)
            y = getattr(brain, vertical)
            if x and y and (x, y) in table:
                table[(x, y)] += 1
                table[(x, '')] += 1
                table[('', y)] += 1
                table[('', '')] += 1

        # Base URLs
        base_stats = context.uri
        base_show = get_reference(';show_users')
        if month:
            base_show = base_show.replace(month=month)
        if year:
            base_show = base_show.replace(year=year)
        if module:
            base_show = base_show.replace(module=module)

        # Column headers
        namespace['columns'] = [ x['value'] for x in horizontal_criterias ]

        # The rows
        rows = []
        total = [{'name': '', 'value': self.gettext(u'Total')}]

        query = {}
        for y in vertical_criterias + total:
            key, value = vertical, y['name']
            if value:
                query[key] = value
            elif key in query:
                del query[key]
            rows.append({'title': y['value'], 'url': None, 'columns': []})
            if vertical == 'region' and region is None:
                rows[-1]['url'] = base_stats.replace(**query)

            for x in horizontal_criterias + [{'name': ''}]:
                if x['name']:
                    query[horizontal] = x['name']
                elif horizontal in query:
                    del query[horizontal]
                rows[-1]['columns'].append({'n': table[(x['name'], y['name'])],
                                            'url': base_show.replace(**query)})

        namespace['rows'] = rows

        handler = self.get_handler('/ui/abakuc/training/statistics.xml')
        return stl(handler, namespace)


    ########################################################################
    # View 
    view__access__ = True 
    #view__access__ = 'is_allowed_to_edit'
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.get_modules()
        namespace['items'] = []
        for item in items:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(items)
        namespace['title'] = title 
        namespace['vhosts'] = []
        vhosts = self.get_vhosts()
        for vhost in vhosts:
            url = '%s' % vhost
            namespace['vhosts'].append({'url': url})

        #namespace['vhosts'] = self.get_vhosts() 
        handler = self.get_handler('/ui/abakuc/training/view.xml')
        return stl(handler, namespace)
        # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(modules)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #modules = modules[batch_start:batch_fin]
        ## Namespace 
        #if modules:
        #    msgs = (u'There is one module.',
        #            u'There are ${n} modules.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'Currently there no published training modules.'
        #
        #namespace['batch'] = batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_branch_manager'
    def edit_metadata_form(self, context):
        root = get_context().root
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description
        topics = self.get_property('abakuc:topic')
        namespace['topics'] = root.get_topics_namespace(topics)
        handler = self.get_handler('/ui/abakuc/training/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')
        topics = context.get_form_values('topic')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')
        self.set_property('abakuc:topic', tuple(topics))
        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)

    ########################################################################
    # List modules 
    modules__access__ = True 
    #view__access__ = 'is_allowed_to_edit'
    modules__label__ = u'Modules'
    def modules(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Module)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})
        namespace['title'] = title 
        namespace['vhosts'] = []
        vhosts = self.get_vhosts()
        for vhost in vhosts:
            url = '%s' % vhost
            namespace['vhosts'].append({'url': url})

        #namespace['vhosts'] = self.get_vhosts() 
        handler = self.get_handler('/ui/abakuc/training/view.xml')
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
# Training module 
#######################################################################
class Module(Folder):

    class_id = 'module'
    class_title = u'Trainig module'
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'
    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['edit_metadata_form']]

    def get_document_types(self):
        return [Topic, Exam, Marketing]

    new_resource_form__access__ = 'is_admin'

    #######################################################################
    # API 
    #######################################################################
    def get_prev_module(self):
        programme = self.parent
        modules = programme.get_modules()
        index = modules.index(self)
        if index == 0:
            return None
        return modules[index - 1]

    def get_topics(self):
        topics = list(self.search_handlers(format=Topic.class_id))
        topics.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return topics

    def get_address(self):
        root = self.get_root()
        results = root.search(format='address', members=self.name)
        for address in results.get_documents():
            return root.get_handler(address.abspath)
        return None

    def get_exam(self, username=None):
        """
        Returns the exam for the given username (it checks the business
        function). Or None if none exam matches.
        """
        business_function = None
        if username is None:
            username = get_context().user.name

        for exam in self.search_handlers(format=Exam.class_id):
            #business_functions = exam.definition.business_functions
            #if 'all' in business_functions:
            #    return exam
            #if business_function is None:
            #    site_root = self.get_site_root()
            #    user = site_root.get_handler('users/%s' % username)
            #    address = user.get_address()
            #    company = address.parent
            #    business_function = company.get_property('abakuc:business_function')

            #if business_function in business_functions:
            #    return exam
            return exam

        return None
    
    def get_marketing_form(self, username=None):
        """
        Returns the marketing form, if the user has not filled it yet.
        I he has, or if there is not any marketing form, then return None.
        """
        if username is None:
            context = get_context()
            username = context.user.name

        for marketing_form in self.search_handlers(format=Marketing.class_id):
            n_attempts = marketing_form.get_result(username)[1]
            if n_attempts == 0:
                return marketing_form
        return None

    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = True 
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        programme = self.parent
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Topic)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['title'] = title 
        namespace['to_name'] = programme.get_vhosts() 
        handler = self.get_handler('/ui/abakuc/training/module/view.xml')
        return stl(handler, namespace)
        # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(items)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #items = items[batch_start:batch_fin]
        ## Namespace 
        #if items:
        #    msgs = (u'There is one topic.',
        #            u'This module has ${n} topics.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'This module has no published topics.'
        #
        #namespace['batch'] = news_batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_branch_manager'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Generate the module name
        #module_names = [ x for x in here.get_handler_names()
        #                   if x.startswith('module') ]
        #if module_names:
        #    i = get_sort_name(module_names[-1])[1] + 1
        #    name = 'module%d' % i
        #else:
        #    name = 'module1'
        #namespace['name'] = name 
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description

        handler = self.get_handler('/ui/abakuc/training/module/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
    def edit_metadata(self, context):
        name = context.get_form_value('name')
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


    #########################################################################
    # End training
    #########################################################################
    end__access__ = 'is_allowed_to_view'
    def end(self, context):
        here = context.handler
        user = context.user
        # Build the namespace
        namespace = {}
        title = here.get_title()
        namespace['title'] = title 
        namespace['marketing'] = None
        namespace['exam'] = None
        #namespace['game'] = None
        namespace['next'] = None
        namespace['finished'] = False
        #game = self.get_game()
        #if game:
        #    popup = ("window.open('%s/;play',null,'scrollbars=no,"
        #            "width=800,height=700'); return false;") % game.name
        #    namespace['game'] = popup
        # The marketing form
        marketing_form = self.get_marketing_form(user.name)
        if marketing_form is None:
            # Take the exam
            exam = self.get_exam(user.name)
            if exam is not None:
                result = exam.get_result(user.name)
                passed, n_attempts, time, mark, kk = result
                if passed:
                    modules = self.parent.get_modules()
                    module_index = modules.index(self)
                    if module_index == len(modules) - 1:
                        namespace['finished'] = True
                        namespace['profile'] = user.get_profile_url(self)
                    else:
                        next = modules[module_index + 1]
                        namespace['next'] = '../%s/;view' % next.name
                else:
                    exam_path = self.get_pathto(exam)
                    namespace['exam'] = '%s/;take_exam_form' % exam_path

            else:
                modules = self.parent.get_modules()
                module_index = modules.index(self)
                if module_index == len(modules) - 1:
                    namespace['finished'] = True
                    namespace['profile'] = user.get_profile_url(self)
                else:
                    next = modules[module_index + 1]
                    namespace['next'] = '../%s/;view' % next.name

        else:
            namespace['marketing'] = '%s/;fill_form' % marketing_form.name

        namespace['previous'] = ';view'


        handler = self.get_handler('/ui/abakuc/training/module/end.xml')
        return stl(handler, namespace)

#######################################################################
# Training topic 
#######################################################################
class Topic(Folder):

    class_id = 'topic'
    class_title = u'Module topic'
    class_icon16 = 'abakuc/images/Topic16.png'
    class_icon48 = 'abakuc/images/Topic48.png'
    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['edit_metadata_form']]

    def get_document_types(self):
        return [Document, File]

    #######################################################################
    # API 
    #######################################################################
    def get_document_names(self):
        ac = self.get_access_control()
        user = get_context().user

        documents = []
        for handler in self.get_handlers():
            if not isinstance(handler, Document):
                continue
            if handler.real_handler is not None:
                continue
            if ac.is_allowed_to_view(user, handler):
                name = handler.name
                sort_name = get_sort_name(FileName.decode(name)[0])
                documents.append((sort_name, handler.name))
        documents.sort()
        return [ x[1] for x in documents ]
    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_branch_manager_or_member'
    view__label__ = u'View'
    def view(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        items = self.search_handlers(handler_class=Document)
        namespace['items'] = []
        for item in items:
            get = item.get_property
            # XXX Had to hard link the .en in the uri
            # item name seems to strip the language
            language = item.get_property('dc:language')
            url = './%s.%s/;view' %  (item.name, language)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['items'].append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['title'] = title 
        handler = self.get_handler('/ui/abakuc/training/topic/view.xml')
        return stl(handler, namespace)
      # Set batch informations
        #batch_start = int(context.get_form_value('batchstart', default=0))
        #batch_size = 5
        #batch_total = len(items)
        #batch_fin = batch_start + batch_size
        #if batch_fin > batch_total:
        #    batch_fin = batch_total
        #items = items[batch_start:batch_fin]
        ## Namespace 
        #if items:
        #    msgs = (u'There is one topic.',
        #            u'This module has ${n} topics.')
        #    batch = batch(context.uri, batch_start, batch_size, 
        #                  batch_total, msgs=msgs)
        #    msg = None
        #else:
        #    batch = None
        #    msg = u'This module has no published topics.'
        #
        #namespace['batch'] = news_batch
        #namespace['msg'] = msg 

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_branch_manager'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title 
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Description
        description = self.get_property('dc:description')
        namespace['description'] = description

        handler = self.get_handler('/ui/abakuc/training/topic/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_branch_manager'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


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


register_object_class(Trainings)
register_object_class(Training)
register_object_class(Module)
register_object_class(Topic)
