# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import datetime
import string

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
from itools.xhtml import Document as XHTMLDocument

# Import from abakuc
from bookings import Bookings
from companies import Company, Address
from base import Handler, Folder
from website import SiteRoot
from document import Document
from utils import get_sort_name
from exam import Exam
from news import News
from jobs import Job
from metadata import JobTitle, SalaryRange
from namespaces import Regions, BusinessProfile
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
                #['view'],
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
                   ['statistics', 'show_users','league'],
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
        return [Module, Bookings]

    def get_level1_title(self, level1):
        return None

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

    def is_training(self):
        '''Return a bool'''
        training = self.get_site_root()
        if isinstance(training, Training):
            training = True
        else:
            training = False
        return training

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


    def is_training_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        return True
        ## Is reviewer or member
        #return self.has_user_role(user.name, 'abakuc:training_manager')

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

    def get_news(self, address):
        results = address.search(format='news')
        for news in results.get_documents():
            return address.get_handler(news.abspath)
        return None

    def get_modules_dates(self, modules, username):
        last_exam_passed = True
        dates = []
        for m in modules:
            date = ''
            if last_exam_passed:
                exam = m.get_exam(username)
                if exam is not None:
                    last_exam_passed = False
                    result = exam.get_result(username)
                    if result is not None:
                        last_exam_passed = result[0]
                        if last_exam_passed:
                            date = result[-1]
            dates.append(date)
        return dates

    def get_regions(self, context, country=None, selected_region=None):
        """
        Returns the namespace for all the countries, regions and counties,
        ready to use in STL.

        The namespace structure is:

          [{'id': <country id>,
            'region': [{'id': <region id>,
                        'county': [ {'id': <county id>,
                                     'title': <county title>,
                                     'is_selected': <True | False>
                                    }
                                  ...]
                        'title': <region title>,
                        'is_selected': <True | False>
                        }
                     ...]
            'title': <country title>,
            'is_selected': <True | False>,
            }
           ...]

        """
        from root import world
        #root = get_context().root
        #countries = [
        #    {'id': y, 'title': x, 'is_selected': y == country}
        #    for x, y in root.get_active_countries(context) ]
        #nb_countries = len(countries)
        #if nb_countries < 1:
        #    raise ValueError, 'Number of countries is invalid'
        #countries.sort(key=lambda x: x['title'])

        regions = []
        #for country in countries:
        rows = world.get_rows()
        for row in rows:
            region = row[7]
            if region not in regions:
                regions.append(region)
        regions = [{'id': x,
                    'title': x,
                    'is_selected': x==selected_region} for x in regions]
        regions.sort(key=lambda x: x['title'])
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(regions)
        #pp.pprint(countries)
        return regions
        #return countries
    ########################################################################
    # Statistics
    chart__access__ = True
    #statistics__access__ = 'is_allowed_to_view_statistics'
    chart__label__ = u'Statistics'
    chart__sublabel__ = u'Statistics'
    def chart(self, context):
        # Set style
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        # Add the js scripts
        context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.tablesorter.js')
        context.scripts.append('/ui/abakuc/jquery/addons/jquery.tablesorter.pager.js')
        namespace = {}
        #handler = self.get_handler('/ui/abakuc/statistics/chart.xml')
        handler = self.get_handler('/ui/abakuc/training/chart.xml')
        return stl(handler, namespace)


    ########################################################################
    # Statistics
    statistics__access__ = True
    #statistics__access__ = 'is_allowed_to_view_statistics'
    statistics__label__ = u'Statistics'
    statistics__sublabel__ = u'Statistics'
    def statistics(self, context, address_country=None, address_region=None,
                    address_county=None, topic=None, type=None, function=None):
        '''
        This is the statistics module, which gives us an overview of users who
        are registered for each training programme.

        ACL for this method 
        -------------------
        Users are added in the Members list for the Training programme, as
        Training manager, Branch manager, Partner and Branch member.

        Only Admin and Training manager users can view this interface.
        Partner users may also view this, but it will be implemented later.

        We first build the HTTP request forms, which will query the database.
         1) By default, the first table view is Country / Type
         2) We have six (6) reports - see layout_options list and
         namespace['layout'] which returns a dictionary with the values:
            [   {   'name': 'country/types',
                    'selected': True,
                    'value': u'Region x Business profile'},

        '''
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/excanvas-compressed.js')
        context.scripts.append('/ui/abakuc/fgCharting.jQuery.js')
        from root import world
        root = get_context().root
        import pprint
        pp = pprint.PrettyPrinter(indent=4)


        year = context.get_form_value('year')
        month = context.get_form_value('month')
        module = context.get_form_value('module')
        layout = context.get_form_value('layout', 'country/type')
        country = context.get_form_value('country')
        region = context.get_form_value('region')

        # Build the namespace
        namespace = {}
        # Registration dates
        namespace['months'] = [ {'name': i+1, 'value': self.gettext(title),
                                 'selected': str(i+1) == month}
                                for i, title in enumerate(month_names) ]
        years = range(2001, datetime.date.today().year + 1)
        namespace['years'] = [
            {'name': x, 'value': x, 'selected': str(x) == year}
            for x in years ]
        # Get TP Modules
        modules = self.get_modules()
        namespace['modules'] = [
            {'name': x.name, 'title': '%d - %s' % (i+1, x.title_or_name),
             'selected': x.name == module}
            for i, x in enumerate(modules)]

        # Layout options
        layout_options = [
            ('country/type', u'Country x Business profile'),
            ('country/topic', u'Country x Business function'),
            ('country/function', u'Country x Job functions'),
            ('function/type', u'Job functions x Business profile'),
            ('topic/function', u'Business function x Job functions'),
            ('topic/type', u'Business function x Business profile')]

        namespace['layout'] = [
            {'name': name, 'value': value, 'selected': name == layout}
            for name, value in layout_options ]

        # List authorized countries
        countries = [
            {'id': y, 'title': x, 'is_selected': x == address_country}
            for x, y in root.get_active_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'
        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])

        # Statistics criterias
        vertical, horizontal = layout.split('/')
        criterias = {'country': countries,
                     'topic': root.get_topics_namespace(topic),
                     'function':  root.get_functions_namespace(function),
                     'type': root.get_types_namespace(type)
                     }
        horizontal_criterias = criterias[horizontal]
        vertical_criterias = criterias[vertical]

        # Filter the users
        root = context.root
        query = {'training_programmes': self.name}
        catalog = context.server.catalog
        for key in context.get_form_keys():
            value = context.get_form_value(key)
            if value:
                if key in ('year', 'month'):
                    query['registration_%s' % key] = value
                elif key in catalog.field_numbers:
                    query[key] = value
        if month:
            query['registration_month'] = month
        if year:
            query['registration_year'] = year
        # Countries, regions 
        if country:
            query['country'] = country
            vertical_criterias = Regions.get_regions(country) 
            vertical = 'region'
        # Regions, counties 
        if region:
            query['region'] = region
            vertical_criterias = Regions.get_counties(region) 
            vertical = 'abakuc:county'

        results = root.search(**query)
        brains = results.get_documents()
        if module:
            aux = []
            mod = self.get_handler(module)
            for brain in brains:
                exam = mod.get_exam(brain.name)
                #pp.pprint(exam)
                if exam is None:
                    continue
                has_passed = exam.get_result(brain.name)[0]
                if has_passed:
                    aux.append(brain)
            brains = aux

        ## Classify the users
        table = {}
        table[('', '')] = 0
        for x in horizontal_criterias:
            table[(x['id'], '')] = 0
        for y in vertical_criterias:
            table[('', y['id'])] = 0
        for x in horizontal_criterias:
            x = x['id']
            for y in vertical_criterias:
                #table[ x['id'],y['id'] ] = 0
                table[(x, y['id'])] = 0

        for brain in brains:
            x = getattr(brain, horizontal)
            if isinstance(x, list):
                x = x[0]
                pp.pprint(x)
                #for item in x:
                #    x = item
                #    pp.pprint(x)
            #else:
            #    x
            y = getattr(brain, vertical)
            if isinstance(y, list):
                y = y[0]
                pp.pprint(y)
                #for item in y:
                #    y = item
            #else:
            #    y
            if x and y and (x, y) in table:
                table[(x, y)] += 1
                table[(x, '')] += 1
                table[('', y)] += 1
                table[('', '')] += 1
        #pp.pprint(table)
        ## Base URLs
        base_stats = context.uri
        base_show = get_reference(';show_users')
        namespace['x'] =  base_show
        if month:
            base_show = base_show.replace(month=month)
        if year:
            base_show = base_show.replace(year=year)
        if module:
            base_show = base_show.replace(module=module)

        ## Column headers
        namespace['columns'] = [ x['title'] for x in horizontal_criterias ]

        ## The rows
        rows = []
        total = [{'id': '', 'title': self.gettext(u'Total')}]
        query = {}
        for y in vertical_criterias + total:
            key, value = vertical, y['id']
            if value:
                query[key] = value
            elif key in query:
                del query[key]
            rows.append({'title': y['title'], 'url': None, 'columns': []})
            if vertical == 'country' and country is None:
                rows[-1]['url'] = base_stats.replace(**query)
            if vertical == 'region' and region is None:
                rows[-1]['url'] = base_stats.replace(**query)

            for x in horizontal_criterias + [{'id': ''}]:
                if x['id']:
                    query[horizontal] = x['id']
                elif horizontal in query:
                    del query[horizontal]
                rows[-1]['columns'].append({'n': table[(x['id'], y['id'])],
                                            'url': base_show.replace(**query)})

        namespace['rows'] = rows

        handler = self.get_handler('/ui/abakuc/training/statistics.xml')
        return stl(handler, namespace)

    show_users__access__ = True
    show_users__label__ = u'Show users'
    show_users__sublabel__ = u'Show users'
    def show_users(self, context, address_country=None,\
                    address_region=None, address_county=None):
        from root import world
        import pprint
        pp = pprint.PrettyPrinter(indent=4)

        root = get_context().root
        # Extract the parameters from the request form
        year = context.get_form_value('year')
        month = context.get_form_value('month')
        module = context.get_form_value('module')
        country = context.get_form_value('country', '')
        region = context.get_form_value('region', '')
        county = context.get_form_value('abakuc:county', '')
        topic = context.get_form_value('topic', '')
        function = context.get_form_value('function', '')
        type = context.get_form_value('type', '')
        # Build the namespace
        namespace = {}
        # Registration month
        months = []
        i = 1
        for month_name in month_names:
            months.append({'name': i, 'value': self.gettext(month_name),
                           'selected': str(i) == month})
            i += 1
        namespace['months'] = months
        # Registration year
        years = range(2001, datetime.date.today().year + 1)
        namespace['years'] = [
            {'name': x, 'value': x, 'selected': str(x) == year}
            for x in years ]
        # Modules
        modules = self.get_modules()
        namespace['modules'] = [
            {'name': x.name, 'title': '%d - %s' % (i+1, x.title),
             'short_title': '%d-%s' % (i+1, x.title[:8]),
             'selected': x.name == module}
            for i, x in enumerate(modules) ]
        # List authorized countries
        countries = [
            {'name': y, 'title': x, 'selected': x == address_country}
            for x, y in root.get_active_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'
        # Show a list with all authorized countries
        countries.sort(key=lambda y: y['name'])
        region = root.get_regions_stl(country_code=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        # Region, business function, job function and business profile
        namespace['country'] = countries
        namespace['region'] = region
        namespace['county'] = county
        namespace['topic'] = root.get_topics_namespace(topic)
        namespace['function'] = root.get_functions_namespace(function)
        namespace['type'] = root.get_types_namespace(type)
        # Search users
        root = context.root
        catalog = context.server.catalog
        query = {}
        #Returns the name of the training programme
        query['training_programmes'] = self.name
        
        for key in context.get_form_keys():
            value = context.get_form_value(key)
            if value:
                if key in ('year', 'month'):
                    query['registration_%s' % key] = value
                elif key in catalog.field_numbers:
                    query[key] = value
        users = []
        if module:
            module = self.get_handler(module)
            #pp.pprint(module)
        # TEST 015
        results = root.search(**query)
        for brain in results.get_documents():
            # Filter by module
            if module:
                exam = module.get_exam(brain.name)
                if exam is None:
                    continue
                # Not passed
                if not exam.get_result(brain.name)[0]:
                    continue

            if not root.has_handler(brain.abspath):
                context.server.log_error(context)
                continue

            user = root.get_handler(brain.abspath)
            # Address
            address_handler = user.get_address()
            if address_handler is None:
                phone = 'not available'
                fax = 'not available'
                address = 'not available'
                post_code = 'not available'
            else:
                get_property = address_handler.metadata.get_property
                phone = get_property('abakuc:phone')
                fax = get_property('abakuc:fax')
                address = get_property('abakuc:address')
                post_code = get_property('abakuc:postcode')
            # Company
            if address_handler is not None:
                company = address_handler.parent
                if company is None:
                    company_title = 'not available'
                    company_type = 'not available'
                    company_topic = 'not available'
                else:
                    company_title = company.get_property('dc:title')
                    company_type = company.get_property('abakuc:type')
                    company_topic = company.get_property('abakuc:topic')
            else:
                company_title = 'not available'
                company_type = 'not available'
                company_topic = 'not available'
            # All modules dates
            ns_modules = [{'date': date.encode('utf-8')} for date in
                          self.get_modules_dates(modules, user.name)]

            #pp.pprint(ns_modules)
            get_property = user.metadata.get_property
            users.append(
                {#'title': get_property('abakuc:user_title'),
                 'firstname': get_property('ikaaro:firstname'),
                 'lastname': get_property('ikaaro:lastname'),
                 'company': company_title,
                 'email': get_property('ikaaro:email'),
                 'phone': phone,
                 'fax': fax,
                 'address': address,
                 'post_code': post_code,
                 'functions': get_property('abakuc:functions'),
                 'type': company_type,
                 'topic': company_topic,
                 #'last_module': self.get_last_module_title(user.name),
                 'modules': ns_modules,
                 })
        users.sort(lambda x, y: cmp(x['firstname'].lower(),
                                    y['firstname'].lower()))
        namespace['users'] = users
        pp.pprint(namespace['users'])
        # CSV
        query = '&'.join([ '%s=%s' % (x, context.get_form_value(x))
                           for x in context.get_form_keys() ])
        namespace['csv'] = ';statistics_csv?%s' % query

        handler = self.get_handler('/ui/abakuc/training/show_users.xml')
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
    # News - Search Interface
    #######################################################################
    news__access__ = True
    news__label__ = u'Current news'
    def news(self, context):
        '''
        Return all the news of the training manager's company
        including the addresses.
        '''
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
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
        #pp.pprint(namespace['all_news'])
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_ns)
        pp.pprint(len(news_ns))
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
        handler = self.get_handler('/ui/abakuc/training/search.xhtml')
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
