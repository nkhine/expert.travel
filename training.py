# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import datetime
import string
from StringIO import StringIO

# Import from PIL
from PIL import Image as PILImage

# Import from itools
from itools import vfs
from itools.stl import stl
from itools.cms import widgets
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.registry import register_object_class
from itools.rest import checkid
from itools.cms.messages import *
from itools.cms.widgets import batch
from itools.cms.skins import Skin
from itools.cms.file import File
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware
from itools.datatypes import FileName, Integer
from itools.web import get_context
from itools.cms.catalog import schedule_to_reindex
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.uri import Path, get_reference
from itools.xhtml import Document as XHTMLDocument
from itools.cms.html import XHTMLFile
from itools.cms.folder import Folder as iFolder

# Import from abakuc
from bookings import Bookings
from image_map import ImageMap
from companies import Companies, Company, Address
from base import Handler, Folder
from website import SiteRoot
from document import Document
from utils import get_sort_name, t1, t2, t3, t4
from exam import Exam
from news import News
from media import Media
from jobs import Job
from metadata import JobTitle, SalaryRange
from namespaces import Regions, BusinessProfile
from marketing import Marketing
from certificate import Certificate
from forum import Forum

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

    def get_level1_title(self, level1):
        return None

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
                   ['clean_attempts_form'],
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
        {'name': 'abakuc:partner', 'title': u"Partner",
         'unit': u"Partner"},
        {'name': 'abakuc:branch_member', 'title': u"Member",
         'unit': u"Branch Member"},
    ]

    browse_content__access__ = 'is_admin'
    edit_metadata_form__access__ = 'is_training_manager'
    new_resource_form__access__ = 'is_admin'
    new_resource__access__ = 'is_admin'
    permissions_form__access__ = 'is_admin'
    
    site_format = 'module'

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
        map = ImageMap()
        cache['map'] = map
        cache['map.metadata'] = map.build_metadata(
            **{'dc:title': {'en': u'Interactive map'}})
        media = Media()
        cache['media'] = media
        cache['media.metadata'] = media.build_metadata(
            **{'dc:title': {'en': u'Media folder'}})
        forum = Forum()
        cache['forum'] = forum
        cache['forum.metadata'] = forum.build_metadata(
            **{'dc:title': {'en': u'Forum'}})

    def get_document_types(self):
        return [Bookings, ImageMap, Module, Forum]

    def get_level1_title(self, level1):
        return None

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'companies':
            return self.get_handler('/companies')
        elif name == 'training':
            return self.get_handler('/training')
        return SiteRoot._get_virtual_handler(self, segment)
    #######################################################################
    # API
    #######################################################################
    def get_vhosts(self):
        vhosts = self.get_property('ikaaro:vhosts')
        return vhosts

    def get_image_map(self):
        image_map = list(self.search_handlers(format=ImageMap.class_id))
        image_map.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        return image_map

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

    #def login(self, context):
    #    response = SiteRoot.login(self, context)
    #    if str(response.path[-1]) == ';login_form':
    #        return response
    #    user = context.user
    #    if not self.has_user_role(user.name, 'abakuc:training_manager') and \
    #       not self.has_user_role(user.name, 'abakuc:partner') and \
    #       not self.has_user_role(user.name, 'abakuc:branch_member') and \
    #       not self.has_user_role(user.name, 'abakuc:guest'):
    #        self.set_user_role(user.name, 'abakuc:branch_member')
    #        schedule_to_reindex(user)

    #    return response

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

    #def get_regions(self, context, country=None, selected_region=None):
    #    """
    #    Returns the namespace for all the countries, regions and counties,
    #    ready to use in STL.

    #    The namespace structure is:

    #      [{'id': <country id>,
    #        'region': [{'id': <region id>,
    #                    'county': [ {'id': <county id>,
    #                                 'title': <county title>,
    #                                 'is_selected': <True | False>
    #                                }
    #                              ...]
    #                    'title': <region title>,
    #                    'is_selected': <True | False>
    #                    }
    #                 ...]
    #        'title': <country title>,
    #        'is_selected': <True | False>,
    #        }
    #       ...]

    #    """
    #    from root import world
    #    #root = get_context().root
    #    #countries = [
    #    #    {'id': y, 'title': x, 'is_selected': y == country}
    #    #    for x, y in root.get_active_countries(context) ]
    #    #nb_countries = len(countries)
    #    #if nb_countries < 1:
    #    #    raise ValueError, 'Number of countries is invalid'
    #    #countries.sort(key=lambda x: x['title'])

    #    regions = []
    #    #for country in countries:
    #    rows = world.get_rows()
    #    for row in rows:
    #        region = row[7]
    #        if region not in regions:
    #            regions.append(region)
    #    regions = [{'id': x,
    #                'title': x,
    #                'is_selected': x==selected_region} for x in regions]
    #    regions.sort(key=lambda x: x['title'])
    #    return regions
    #    #return countries
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

    # Global ACL for TP
    def is_admin(self, user, object):
        root = object.get_root()
        if root.is_admin(user, self):
            return True

    def is_training_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        ## Is reviewer or member
        return self.has_user_role(user.name, 'abakuc:training_manager')

    def is_training_manager_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'abakuc:training_manager') or
                self.has_user_role(user.name, 'abakuc:branch_member'))

    # We need this when we view the company object and when on TP
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
        '''
        Who is not allowed to take the exam:
        1) If the user has not passed the exam from previous modules.
        2) If there is a mkt form and has not been submitted.
        '''
        if self.is_admin(user, object):
            return True
        if self.has_user_role(user.name, 'abakuc:training_manager'):
            return True
        if not self.is_travel_agent(user, object):
            return False

        # Has the user already passed this exam?
        passed = object.get_result()[0]
        if passed:
            return False
        # Index the modules by name
        modules = self.get_modules()
        module = object.parent
        index = modules.index(module)

        previous_modules = modules[0:index]
        if previous_modules: 
            exams = []
            for previous_module in previous_modules:
                exam = previous_module.get_exam()
                if exam is not None:
                    passed = exam.get_result(user.name)[0]
                    exams.append(passed)
            if False in exams:
                return False
            else:
                return True
        else:
            passed = object.get_result()[0]
            if passed:
                return False
            else:
                return True 

        #module = object.parent
        #prev_module = module.get_prev_module()
        #if prev_module is None:
        #    return True
        ## Previous module has no exam? (BahamaBay has just one exam at end)
        ## XXX What if we had an exam in module 2 and 4?
        #exam = prev_module.get_exam()
        #if exam is None:
        #    return True
        ## Has the user passed the previous exam?
        #passed = exam.get_result()[0]
        #return bool(passed)

    # Marketing Form Access Control
    def is_allowed_to_fill_marketing(self, user, object):
        if self.is_admin(user, object):
            return True
        if self.has_user_role(user.name, 'abakuc:training_manager'):
            return True
        if not self.is_travel_agent(user, object):
            return False

        # Has the user already filled the Marketing Form?
        passed = object.get_result()[0]
        if passed:
            return False
        # Is this the first module?
        module = object.parent
        prev_module = module.get_prev_module()
        if prev_module is None:
            return True
        marketing = prev_module.get_marketing_form()
        # Previous module has no Marketing Form
        if marketing is None:
            return True
        # Has the user filled the previous Marketing Form?
        passed = marketing.get_result()[0]
        return bool(passed)

    # Statistics Access Control
    def is_allowed_to_view_statistics(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is training manager
        return self.has_user_role(user.name, 'abakuc:training_manager')

    # Map access control
    def is_allowed_to_view_map(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'abakuc:training_manager', 'abakuc:branch_member')
    
    def is_allowed_to_edit_map(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is training manager
        return self.has_user_role(user.name, 'abakuc:training_manager')

    def is_allowed_to_trans(self, user, object, name):
        if user is None:
            return False

        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is training manager
        return self.has_user_role(user.name, 'abakuc:training_manager')

    def is_allowed_to_add(self, user, object):
        # Protect the document
        return self.is_training_manager(user, object)

    def is_allowed_to_edit(self, user, object):
        root = object.get_site_root()
        #if root.has_user_role(user.name, 'abakuc:training_manager', 'abakuc:branch_member'):
        #    return True
        #return False
        return root.is_training_manager_or_member(user, object)

    def is_allowed_to_view(self, user, object):
        root = object.get_site_root()
        # Protect the document
        return root.is_training_manager_or_member(user, object)

    ########################################################################
    # Chart
    ########################################################################
    chart__access__ = 'is_allowed_to_view_statistics'
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
    ########################################################################
    statistics__access__ = 'is_allowed_to_view_statistics'
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
        # Set style
        #context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        # Add the js scripts
        #context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        #context.scripts.append('/ui/abakuc/jquery/jquery.tablesorter.js')
        #context.scripts.append('/ui/abakuc/jquery/addons/jquery.tablesorter.pager.js')

        # Add any additional scrips for display
        #context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        #context.scripts.append('/ui/abakuc/excanvas-compressed.js')
        #context.scripts.append('/ui/abakuc/fgCharting.jQuery.js')
        #hostname = get_context().uri.authority.host
        # Get the variables from the form
        root = get_context().root
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
            ('country/type', u'Geographical x Business profile'),
            ('country/topic', u'Geographical x Business function'),
            ('country/function', u'Geographical x Job functions'),
            ('function/type', u'Job functions x Business profile'),
            ('topic/function', u'Business function x Job functions'),
            ('topic/type', u'Business function x Business profile')]

        namespace['layout'] = [
            {'name': name, 'value': value, 'selected': name == layout}
            for name, value in layout_options ]

        # Layout options
        current_layout = []
        for x, y in layout_options:
            if x == layout:
                namespace['current_layout'] = y
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

        # Filter the users based on the search query
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
        # Filter by country which then lists the regions 
        if country:
            query['country'] = country
            vertical_criterias = Regions.get_regions(country) 
            vertical = 'region'
        # Filter by regions which then lists the counties 
        if region:
            query['region'] = region
            vertical_criterias = Regions.get_counties(region) 
            vertical = 'abakuc:county'

        # Get the results
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
                #for item in x:
                #    x = item
            #else:
            #    x
            y = getattr(brain, vertical)
            if isinstance(y, list):
                y = y[0]
                #for item in y:
                #    y = item
            #else:
            #    y
            if x and y and (x, y) in table:
                table[(x, y)] += 1
                table[(x, '')] += 1
                table[('', y)] += 1
                table[('', '')] += 1
        # Base URLs
        base_stats = context.uri
        # Where are we?
        skin = root.get_skin()
        skin_path = skin.abspath
        if skin_path == '/ui/aruni':
            office_path = self.get_abspath()
            base_show = get_reference('%s/;show_users' % office_path)
            namespace['base'] = '%s/;show_users' % office_path
            namespace['action'] = '%s/;statistics' % office_path
            namespace['download'] = '%s/;statistics_csv' % office_path
        else:
            base_show = get_reference('/;show_users')
            namespace['base'] = '/;show_users'
            namespace['action'] = '/;statistics'
            namespace['download'] = '/;statistics_csv'

        namespace['x'] =  base_show
        if month:
            base_show = base_show.replace(month=month)
        if year:
            base_show = base_show.replace(year=year)
        if module:
            base_show = base_show.replace(module=module)

        # Column headers
        namespace['columns'] = [ x['title'] for x in horizontal_criterias ]

        # The rows
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


    ########################################################################
    # Show users  
    ########################################################################
    show_users__access__ = 'is_allowed_to_view_statistics'
    show_users__label__ = u'Show training members'
    show_users__sublabel__ = u'Show members'
    def show_users(self, context, address_country=None,\
                    address_region=None, address_county=None):
        # Set style
        context.styles.append('/ui/abakuc/jquery/css/jquery.tablesorter.css')
        # Add the js scripts
        context.scripts.append('/ui/abakuc/jquery/jquery-nightly.pack.js')
        context.scripts.append('/ui/abakuc/jquery/jquery.tablesorter.js')
        context.scripts.append('/ui/abakuc/jquery/addons/jquery.tablesorter.pager.js')

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
                    topic = company.get_property('abakuc:topic')
                    company_topic = topic[0]
            else:
                company_title = 'not available'
                company_type = 'not available'
                company_topic = 'not available'
            # All modules dates
            ns_modules = [{'date': date.encode('utf-8')} for date in
                          self.get_modules_dates(modules, user.name)]

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
        users.sort(lambda x, y: cmp(x['lastname'].lower(),
                                    y['firstname'].lower()))
        namespace['users'] = users
        # CSV
        query = '&'.join([ '%s=%s' % (x, context.get_form_value(x))
                           for x in context.get_form_keys() ])
        namespace['csv'] = ';statistics_csv?%s' % query
        namespace['overview'] = ';statistics'

        handler = self.get_handler('/ui/abakuc/training/show_users.xml')
        return stl(handler, namespace)

    ########################################################################
    # Statistics CSV 
    ########################################################################
    statistics_csv__access__ = 'is_allowed_to_view_statistics'
    def statistics_csv(self, context):
        # Geographic
        country = context.get_form_value('country')
        region = context.get_form_value('region')
        county = context.get_form_value('abakuc:county')

        # Topic, Function, Type
        topic = context.get_form_value('topic')
        function = context.get_form_value('function')
        type = context.get_form_value('type')

        year = context.get_form_value('year')
        month = context.get_form_value('month')
        module = context.get_form_value('module')

        # The header
        header = [
            "registration_date","topic", "function", "type",
            "firstname", "lastname", "job_title","email", "contact_me",
            "company_name", "website", "address",
            "town", "county", "region", "postcode",
            "country", "phone", "fax"
            ]

        # All modules
        modules = self.get_modules()
        for i, x in enumerate(modules):
            header.append('"M%d - %s"' % (i+1, x.get_property('dc:title')))

        data = [u','.join(header) + u'\n']

        root = context.root
        companies = root.get_handler('companies')

        # Search users
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
        if module:
            module = self.get_handler(module)
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

            line = []
            user = root.get_handler(brain.abspath)
            # Address
            address_handler = user.get_address()
            if address_handler is None:
                phone = 'not available'
                fax = 'not available'
                address = 'not available'
                town = 'not available'
                post_code = 'not available'
                county = 'not available'
                region = 'not available'
                country = 'not available'
            else:
                get_property = address_handler.metadata.get_property
                phone = get_property('abakuc:phone')
                fax = get_property('abakuc:fax')
                address = get_property('abakuc:address')
                town = get_property('abakuc:town')
                postcode = get_property('abakuc:postcode')
                county = get_property('abakuc:county')
                if county is not None:
                    from root import world
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        country = row[6]
                        region = row[7]
            # Company
            if address_handler is not None:
                company = address_handler.parent
                if company is None:
                    company_title = 'not available'
                    company_type = 'not available'
                    company_topic = 'not available'
                    company_website = 'not available'
                else:
                    company_title = company.get_property('dc:title')
                    company_type = company.get_property('abakuc:type')
                    topic = company.get_property('abakuc:topic')
                    company_topic = topic[0]
                    company_website =  company.get_property('abakuc:website')
            else:
                company_title = 'not available'
                company_type = 'not available'
                company_topic = 'not available'
                company_website = 'not available'

            # All modules dates
            ns_modules = [{'date': date.encode('utf-8')} for date in
                          self.get_modules_dates(modules, user.name)]

            get_property = user.metadata.get_property
            registration_date = get_property('abakuc:registration_date')
            
            # Build the data
            if registration_date is None:
                line.append(u'""')
            else:
                line.append(u'"%s"' % registration_date.strftime('%Y-%m-%d'))

            line.append(u'"%s"' % company_topic)
            line.append(u'"%s"' % company_type)
            line.append(u'"%s"' % (get_property('abakuc:functions')))
            
            line.append(u'"%s"' % \
                        (get_property('ikaaro:firstname') or '').title())
            line.append(u'"%s"' % \
                        (get_property('ikaaro:lastname') or '').title())


            line.append(u'"%s"' % (get_property('abakuc:job_title')))
            line.append(u'"%s"' % (get_property('ikaaro:email')))
            line.append(u'"%s"' % ('yes'))
            line.append(u'"%s"' % company_title)
            line.append(u'"%s"' % company_website)
            line.append(u'"%s"' % address)
            line.append(u'"%s"' % town)
            line.append(u'"%s"' % county)
            line.append(u'"%s"' % region)
            line.append(u'"%s"' % postcode)
            line.append(u'"%s"' % country)
            line.append(u'"%s"' % phone)
            line.append(u'"%s"' % fax)

            # Make the CSV file
            line = u','.join(line) + u'\n'
            data.append(line)

        response = context.response
        response.set_header('Content-Type', 'text/comma-separated-values')
        response.set_header('Content-Disposition',
                            'attachment; filename="expert_travel.csv"')
        return (u''.join(data)).encode('utf-8')

    ########################################################################
    # Exams overview
    ########################################################################
    clean_attempts_form__access__ = 'is_training_manager'
    clean_attempts_form__label__ = u'Maintenance'
    clean_attempts_form__sublabel__ = u'Exams'
    def clean_attempts_form(self, context):
        """ 
        TP1
          ta_34 mod2 exam1 attempte1 : mark 43%
          ta_34 mod2 exam1 attempte2 : mark 56% 
          ta_34 mod2 exam1 attempte3 : mark 0% 
        """ 
        users = context.root.get_handler('users')
        get_user = users.get_handler

        namespace = {}
        # Get the objects ta_attempts
        rows = []
        for module in self.get_modules():
            for exam in module.search_handlers(format=Exam.class_id):
                attempts = exam.results.attempts
                for userid in attempts:
                    user = get_user(userid)
                    for attempt in attempts[userid]:
                        score = int(attempt.get_score())
                        n_attempts = int(exam.get_result(userid)[1])
                        points = int(exam.get_points(userid))
                        date = attempt.date.isoformat()
                        url = self.get_pathto(users).resolve2(userid)
                        id = ('%s##%s##%s##%s##%s##%s' % (exam.abspath, userid,
                              score, n_attempts, date, points))
                        #url = '%s/;view' % url
                        username = user.get_property('ikaaro:username')
                        #username = (firstname+lastname or '').title()
                        rows.append({
                            'checkbox': True,
                            'id': id,
                            'username': (username, url),
                            'score': score,
                            'module': exam.get_property('dc:title'),
                            'date': date,
                            'checked': (score == 0 and 'checked' or '')})
        # Sort
        sortby = context.get_form_values('sortby', default=['score'])
        sortorder = context.get_form_value('sortorder', default='up')
        rows.sort(key=lambda x: x[sortby[0]])
        if sortorder == 'down':
            rows.reverse()

        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 50
        total = len(rows)
        namespace['batch'] = widgets.batch(context.uri, start, size, total)
        rows = rows[start:start+size]

        # Table
        columns = [('username', u'Username'),
                   ('score', u'Score'),
                   ('module', u'Module'),
                   ('date', u'Date')]
        actions = [('remove_attempts', u'Remove', None, None)]
        namespace['table'] = widgets.table(columns, rows, sortby, sortorder,
            actions, self.gettext)

        handler = self.get_handler('/ui/abakuc/training/clean_attempts.xml')
        return stl(handler, namespace)


    remove_attempts__access__ = 'is_training_manager'
    def remove_attempts(self, context):
        root = context.root
        ids = context.get_form_values('ids')
        users = context.root.get_handler('users')
        get_user = users.get_handler

        if not ids:
            return context.come_back(u'No attempts to removed.')

        for id in ids: 
            abspath, name, score, n_attempts, date, points = id.split('##')
            exam = root.get_handler(abspath)
            exam.results.remove_attempt(name, date)
            score = int(score)
            n_attempts = int(n_attempts)
            points = int(points)
            # Update the users points
            user = get_user(name)
            existing_points = user.get_property('abakuc:points')
            # Get the exam points based on score
            if score > 90.0:
                if n_attempts == 1:
                    score += 20
                    new_points = existing_points - score
                else:
                    new_points = existing_points - points
            else:
                new_points = existing_points - score
            user.set_property('abakuc:points', new_points)

        return context.come_back(u'Attempts removed.')

    #######################################################################
    # jQuery TABS for home page 
    #######################################################################
    def get_tabs_stl(self, context):
        # Add a script
        context.scripts.append('/ui/abakuc/jquery-1.2.1.pack.js')
        context.scripts.append('/ui/abakuc/jquery.cookie.js')
        context.scripts.append('/ui/abakuc/ui.tabs.js')
        # Build stl
        namespace = {}
        namespace['news'] = self.list_news(context)
        namespace['modules'] = self.list_modules(context)
        namespace['forum'] = self.forum(context)
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
                <li><a href="#fragment-2"><span>Modules</span></a></li>
                <li><a href="#fragment-3"><span>Training</span></a></li>
                <li><a href="#fragment-4"><span>Marketplace</span></a></li>
                <li><a href="#fragment-5"><span>Forum</span></a></li>
            </ul>
            <div id="fragment-1">
              ${news}
            </div>
            <div id="fragment-2">
              ${modules}
            </div>
            <div id="fragment-3">
              {training}
            </div>
            <div id="fragment-4">
              {marketplace}
            </div>
            <div id="fragment-5">
              ${forum}
            </div>
        </div>
        </stl:block>
                  """
        template = XHTMLDocument(string=template)
        return stl(template, namespace)

    ########################################################################
    # View
    ########################################################################
    view__access__ = True
    #view__access__ = 'is_allowed_to_edit'
    view__label__ = u'View'
    def view(self, context):
        root = context.root
        namespace = {}
        title = self.get_title()
        namespace['title'] = title
        description = self.get_property('dc:description')
        namespace['description'] = description

        # Tabs
        namespace['tabs'] = self.get_tabs_stl(context)

        namespace['vhosts'] = []
        vhosts = self.get_vhosts()
        for vhost in vhosts:
            url = '%s' % vhost
            namespace['vhosts'].append({'url': url})

        skin = root.get_skin()
        skin_path = skin.abspath
        if skin_path == '/ui/aruni':
            handler = self.get_handler('/ui/abakuc/home.xhtml')
        else:
            handler = root.get_skin().get_handler('home.xhtml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_training_manager'
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


    edit_metadata__access__ = 'is_training_manager'
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
    ########################################################################
    modules__access__ = True
    #view__access__ = 'is_allowed_to_edit'
    modules__label__ = u'Modules'
    def modules(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        modules = self.get_modules()
        modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                get_sort_name(y.name)))
        items = []
        for item in modules:
            get = item.get_property
            url = '%s/;view' %  item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            items.append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

        namespace['items'] = items
        namespace['title'] = title
        namespace['description'] = self.get_property('dc:description')
        handler = self.get_handler('/ui/abakuc/training/view.xml')
        return stl(handler, namespace)

    list_modules__access__ = True
    #view__access__ = 'is_allowed_to_edit'
    list_modules__label__ = u'Modules List for TABS'
    def list_modules(self, context):
        here = context.handler
        namespace = {}
        title = here.get_title()
        modules = self.get_modules()
        modules.sort(lambda x, y: cmp(get_sort_name(x.name),
                                get_sort_name(y.name)))
        items = []
        for item in modules:
            get = item.get_property
            url = '%s/;view' %  item.name
            page_picture = item.get_icon70_HTMLtag(20, 32)
            picture_url = '%s/;icon70' % item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            items.append({'url': url,
                      'description': description,
                      'picture_url': picture_url,
                      'page_picture': page_picture,
                      'title': item.title_or_name})

        namespace['items'] = items
        namespace['title'] = title
        namespace['description'] = self.get_property('dc:description')
        # Set batch informations
        batch_start = int(context.get_form_value('t2', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace
        if items:
            msgs = (u'There is one training module.',
                    u'There are ${n} training modules.')
            item_batch = t2(context.uri, batch_start, batch_size,
                              batch_total, msgs=msgs)
            msg = None
        else:
            item_table = None
            item_batch = None
            msg = u'Sorry but there are no modules for this training programme.'

        namespace['batch'] = item_batch
        namespace['msg'] = msg

        handler = self.get_handler('/ui/abakuc/training/list_module.xml')
        return stl(handler, namespace)


    def forum(self, context):
        site_root = self.get_site_root()
        namespace = {}
        forums = []
        # Get the expert.travel forum
        forum = list(site_root.search_handlers(format=Forum.class_id))
        for item in forum:
            forums.append(item)
        # Get all Training programmes forums
        root = context.root
        training = root.get_handler('training')
        items = training.search_handlers(handler_class=Training)
        for item in items:
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
                            'url': url,
                            'threads': threads}

            ns['forum'] = forum_to_add
            current_forums.append(ns)
            forum_links.append({'title': title,
                            'url': url,
                            'is_selected': None})

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
       
        namespace['forum_links'] = forum_links
        namespace['forum'] = current_forums
        handler = self.get_handler('/ui/abakuc/forum/list.xml')
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
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_ns)
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

    list_news__access__ = True
    list_news__label__ = u'Current news'
    def list_news(self, context):
        '''
        Return all the news of the training manager's company
        including the addresses.
        '''
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
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(news_ns)
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
        handler = self.get_handler('/ui/abakuc/training/list_news.xml')
        return stl(handler, namespace)


    #######################################################################
    # New instance form 
    #######################################################################
    forum__access__ = True
    def forum(self, context):
        namespace = {}
        forums = []
        # Get the expert.travel forum
        forum = list(self.search_handlers(format=Forum.class_id))
        for item in forum:
        # Get all Training programmes forums
        #root = context.root
        #training = root.get_handler('training')
        #items = training.search_handlers(handler_class=Training)
        #for item in items:
        #    tp_forum = list(item.search_handlers(format=Forum.class_id))
        #    for item in tp_forum:
        #        item != []
        #        forums.append(item)

            # List the last 5 threads for each forum
            response = Forum.view(item, context)
            namespace['response'] = response
            # Return the page
            handler = self.get_handler('/ui/abakuc/response.xml')
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
        return [Topic, Exam, Marketing, Certificate]

    browse_content__access__ = 'is_training_manager'
    edit_metadata_form__access__ = 'is_training_manager'
    new_resource_form__access__ = 'is_training_manager'
    new_resource__access__ = 'is_training_manager'

    #######################################################################
    # New instance form 
    #######################################################################
    @classmethod
    def new_instance_form(cls, context):
        root = context.root
        namespace = {}
        namespace['class_id'] = cls.class_id
        handler = root.get_handler('/ui/abakuc/training/%s/new_instance.xml' \
                                   % cls.class_id)
        return stl(handler, namespace)


    @classmethod
    def new_instance(cls, container, context):
        root = context.root
        here = context.handler
        site_root = here.get_site_root()
        title = context.get_form_value('title')
        description = context.get_form_value('description')
        website_languages = site_root.get_property('ikaaro:website_languages')
        language = website_languages[0]

        # Generate the new instance name
        handlers = [ x for x in container.get_handler_names()
                           if x.startswith(cls.class_id) ]
        if handlers:
            i = get_sort_name(max(handlers))[1]+ 1
            name = '%s%d' % (cls.class_id, i)
        else:
            name = '%s1' % cls.class_id
        # Check the name
        name = name.strip() or title.strip()
        if not name:
            return context.come_back(MSG_NAME_MISSING)

        name = checkid(name)
        if name is None:
            return context.come_back(MSG_BAD_NAME)

        # Check the name is free
        if container.has_handler(name):
            return context.come_back(MSG_NAME_CLASH)

        # Build the object
        handler = cls()
        metadata = handler.build_metadata()
        metadata.set_property('dc:title', title, language=language)
        metadata.set_property('dc:description', description, language=language)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)

        goto = './%s/;%s' % (name, handler.get_firstview())
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)

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
    
    #def get_previous_results(self, username=None):
    #    """
    #    Returns true if the user has passed all the previous exams 
    #    """
    #    programme = self.parent
    #    modules = programme.get_modules()
    #    index = modules.index(self)
    #    if username is None:
    #        username = get_context().user.name
    #    exams = []
    #    for module in modules[:index]:
    #        exam = module.get_exam(username)
    #        exams.append(exam)
    #    for exam in exams:
    #        not_passed = []
    #        if exam is not None:
    #            passed = exam.get_result(username)[0]
    #            if passed:
    #                print passed
    #            else:
    #                not_passed.append(exam.name)

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
            business_functions = exam.definition.business_functions
            if 'all' in business_functions:
                return exam
            if business_function is None:
                site_root = self.get_site_root()
                user = site_root.get_handler('users/%s' % username)
                address = user.get_address()
                if address:
                    company = address.parent
                    business_function = company.get_property('abakuc:topic')
                    for x in business_function:
                        if x in business_functions:
                            return exam
        return None

    def get_marketing_form(self, username=None):
        """
        Returns the marketing form, if the user has not filled it yet.
        If he has, or if there is not any marketing form, then return None.
        We have an issue here, in that if we have two Marketing Forms
        on the profile page these are listed.
        We need to only display the Marketing Form which has not been filled.
        """
        if username is None:
            context = get_context()
            username = context.user.name

        for marketing_form in self.search_handlers(format=Marketing.class_id):
            n_attempts = marketing_form.get_result(username)[1]
            if n_attempts == 0:
                return marketing_form
        return None

    # Icons and images for list views
    icon220__access__ = True
    def icon220(self, context):
        return self.get_icon(id='220x355', width=220, height=355)


    icon70__access__ = True
    def icon70(self, context):
        return self.get_icon(id='70x70', width=70, height=None)


    def get_icon70_HTMLtag(self, width=70, height=70):
        if not self.get_property('abakuc:image1'):
            return None
        path = self.get_property('abakuc:image1')
        picture = self.get_handler(path)
        #Get the actual picture object
        handler = picture.get_content_type()
        if not vfs.get_size(picture.uri):
            return None
        here = get_context().handler
        return "%s/;icon%s" % (here.get_pathto(self), width)


    icon48__access__ = True
    def icon48(self, context):
        return self.get_icon(id='48x48', width=48, height=48)

    # FIXME _icon
    def get_icon(self, id, width, height):
        response = get_context().response
        #if self.has_handler('.picture'):
        if not self.get_property('abakuc:image1'):
            return None
        path = self.get_property('abakuc:image1')
        picture = self.get_handler(path)
        if vfs.get_size(picture.uri):
            width, height = int(width), height and int(height) or None
            if not hasattr(picture, '_icon'):
                picture._icon = {}
            if id not in picture._icon:
                data = picture.to_str()
                im = PILImage.open(StringIO(data))
                picture_width, picture_height = im.size
                if picture_width > width or picture_height > height:
                    if height == None:
                        ratio = max(*im.size)*1./min(*im.size)
                        height = int(ratio*width)

                    im.thumbnail((width, height))
                    s = StringIO()
                    im.save(s, im.format)
                    data = s.getvalue()
                    s.close()

                picture._icon[id] = data, im.format, im.size

            data, format, size = picture._icon[id]
            response.set_header('Content-Type', 'image/%s' % format)
            return data

        picture = self.get_handler('/ui/%s' % self.class_icon48)
        format = self.class_icon48.split('.')[-1]
        response.set_header('Content-Type', 'image/%s' % format)
        return picture.to_str()

    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = True
    view__label__ = u'View'
    def view(self, context):
        #here = context.handler
        programme = self.parent
        namespace = {}
        title = self.get_title()
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
        namespace['description'] = self.get_property('dc:description')
        namespace['picture_url'] = '%s/;icon220' % self.name
        namespace['to_name'] = programme.get_vhosts()
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(namespace['items'])
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        namespace['items'] = namespace['items'][batch_start:batch_fin]
        # Namespace
        if namespace['items']:
            msgs = (u'There is one topic.',
                    u'This module has ${n} topics.')
            items_batch = batch(context.uri, batch_start, batch_size,
                          batch_total, msgs=msgs)
            msg = None
        else:
            items_batch = None
            msg = u'This module has no published topics.'
        
        namespace['batch'] = items_batch
        namespace['msg'] = msg
        handler = self.get_handler('/ui/abakuc/training/module/view.xml')
        return stl(handler, namespace)

    topics__access__ = True
    topics__label__ = u'Topics View'
    def topics(self, context):
        pass
    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_training_manager'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Title
        title = self.get_property('dc:title')
        namespace['title'] = title
        # Image
        get_property = self.get_metadata().get_property
        namespace['image1'] = image1 = get_property('abakuc:image1')
        namespace['image1_title'] = ''
        namespace['image1_credit'] = ''
        namespace['image1_keywords'] = ''
        if image1:
            try:
                image1 = self.parent.get_handler(image1[3:])
            except:
                pass
            else:
                namespace['image1_title'] = image1.get_property('dc:title')
                namespace['image1_credit'] = image1.get_property('dc:description')
                namespace['image1_keywords'] = image1.get_property('dc:subject')

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


    edit_metadata__access__ = 'is_training_manager'
    def edit_metadata(self, context):
        name = context.get_form_value('name')
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')
        #Image 1
        image1_title = context.get_form_value('image1_title')
        image1_credit = context.get_form_value('image1_credit')
        image1_keywords = context.get_form_value('image1_keywords')
        image1 = context.get_form_value('abakuc:image1')
        self.set_property('abakuc:image1', image1)
        if image1:
            image1 = self.parent.get_handler(image1[3:])
            image1_title = unicode(image1_title, 'utf8')
            image1.set_property('dc:title', image1_title, language='en')
            image1_keywords = unicode(image1_keywords, 'utf8')
            image1.set_property('dc:subject', image1_keywords)
            image1_credit = unicode(image1_credit, 'utf8')
            image1.set_property('dc:description', image1_credit,
                                language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)

    #######################################################################
    # use epoz method to upload and link image
    document_image_form__access__ = 'is_allowed_to_edit'
    def document_image_form(self, context):
        from itools.cms.file import File
        from itools.cms.binary import Image
        from itools.cms.widgets import Breadcrumb
        here = context.handler
        site_root = here.get_site_root()
        start = site_root.get_handler('media')
        # Construct namespace
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=Image, start=start)
        namespace['message'] = context.get_form_value('message')

        prefix = Path(self.abspath).get_pathto('/ui/abakuc/training/document/epozimage.xml')
        handler = self.get_handler('/ui/abakuc/training/document/epozimage.xml')
        return stl(handler, namespace, prefix=prefix)

    document_image__access__ = 'is_allowed_to_edit'
    def document_image(self, context):
        """
        Allow to upload and add an image to the
        media folder and link it to the document.
        """
        from itools.cms.binary import Image
        # Get the container
        here = context.handler
        site_root = here.get_site_root()
        container = site_root.get_handler('media')
        #container = root.get_handler(context.get_form_value('target_path'))
        # Add the image to the handler
        uri = Image.new_instance(container, context)
        if ';document_image_form' not in uri.path:
            handler = container.get_handler(uri.path[0])
            return """
            <script type="text/javascript">
                window.opener.CreateImage('%s');
            </script>
                    """ % handler.abspath

        return context.come_back(message=uri.query['message'])


    #########################################################################
    # End training
    #########################################################################
    end__access__ = 'is_allowed_to_view'
    def end(self, context):
        '''
        This is the end of the training and the programme and we have several
        use cases:

        1) If the module has a Marketing Form we first ask the user to submit
        it.

        2) Once this is submitted, if there is an Exam, we ask the user to take
        the Exam.

        3) Or the user is free to go back to review the module contents.

        An issue that we have to resolve is that if for example we have a
        Marketing Form from a previous module that has not been filled, the user
        is not allowed to proceed.

        We have to ensure that this option is provided.
        '''
        root = self.get_site_root()
        here = context.handler
        user = context.user
        modules = root.get_modules()

        # Build the namespace
        namespace = {}
        title = here.get_title()
        namespace['title'] = title
        namespace['marketing'] = None
        namespace['exam'] = None
        namespace['prev_module'] = None
        #namespace['game'] = None
        namespace['next'] = None
        namespace['finished'] = False
       
        #previous_exams = self.get_previous_results(user.name)
        ## Index the modules by name
        #for index, module in enumerate(modules):
        #    module_index = modules.index(module)
        #    is_first_module = module_index == 0
        #    is_last_module = module_index == len(modules) - 1


        #game = self.get_game()
        #if game:
        #    popup = ("window.open('%s/;play',null,'scrollbars=no,"
        #            "width=800,height=700'); return false;") % game.name
        #    namespace['game'] = popup
        exam = self.get_exam(user.name)
        marketing_form = self.get_marketing_form(user.name)
        # Do we have a previous module?
        prev_module = self.get_prev_module()
        if prev_module is not None:
            # Check to see if there is a marketing form.
            prev_marketing = prev_module.get_marketing_form(user.name)
            if prev_marketing is not None:
                result = prev_marketing.get_result(user.name)
                passed, n_attempts, time, mark, kk = result
                if passed is False:
                    namespace['prev_module'] = '/%s/;view' % (prev_module.name) 
                    namespace['marketing'] = '/%s/%s/;fill_form' % (prev_module.name,
                                                            prev_marketing.name)
            else:
                if marketing_form is not None:
                    namespace['marketing'] = '%s/;fill_form' % marketing_form.name
            # Do we have a previous exam? 
            prev_exam = prev_module.get_exam(user.name)
            if prev_exam is not None:
                result = prev_exam.get_result(user.name)
                passed, n_attempts, time, mark, kk = result
                if passed is False:
                    exam_path = self.get_pathto(prev_exam)
                    namespace['prev_module'] = '/%s/;view' % (prev_module.name) 
                    namespace['exam'] = '/%s/%s/;take_exam_form' % (prev_module.name,
                                                            prev_exam.name)
                # Take the exam
                else:
                    modules = self.parent.get_modules()
                    module_index = modules.index(self)
                    if exam is not None:
                        result = exam.get_result(user.name)
                        passed, n_attempts, time, mark, kk = result
                        if passed:
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
                        next = modules[module_index + 1]
                        namespace['next'] = '../%s/;view' % next.name
                        
        # First module in programme
        else:
            #namespace['prev_module'] = None 
            # The marketing form
            if marketing_form is not None:
                result = marketing_form.get_result(user.name)
                passed, n_attempts, time, mark, kk = result
                if passed is False:
                    namespace['marketing'] = '%s/;fill_form' % marketing_form.name
            else:
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

    new_resource_form__access__ = 'is_training_manager'
    new_resource__access__ = 'is_training_manager'
    edit_metadata_form__access__ = 'is_training_manager'

    def get_document_types(self):
        return [Document, File]

    #######################################################################
    # New instance form 
    #######################################################################
    @classmethod
    def new_instance_form(cls, context):
        root = context.root
        namespace = {}
        namespace['class_id'] = cls.class_id
        handler = root.get_handler('/ui/abakuc/training/%s/new_instance.xml' \
                                   % cls.class_id)
        return stl(handler, namespace)


    @classmethod
    def new_instance(cls, container, context):
        root = context.root
        here = context.handler
        site_root = here.get_site_root()
        title = context.get_form_value('title')
        description = context.get_form_value('description')
        website_languages = site_root.get_property('ikaaro:website_languages')
        language = website_languages[0]

        # Generate the new instance name
        handlers = [ x for x in container.get_handler_names()
                           if x.startswith(cls.class_id) ]
        if handlers:
            i = get_sort_name(max(handlers))[1]+ 1
            name = '%s%d' % (cls.class_id, i)
        else:
            name = '%s1' % cls.class_id
        # Check the name
        name = name.strip() or title.strip()
        if not name:
            return context.come_back(MSG_NAME_MISSING)

        name = checkid(name)
        if name is None:
            return context.come_back(MSG_BAD_NAME)

        # Add the language extension to the name
        #name = FileName.encode((name, cls.class_extension, language))

        # Check the name is free
        if container.has_handler(name):
            return context.come_back(MSG_NAME_CLASH)

        # Build the object
        handler = cls()
        metadata = handler.build_metadata()
        metadata.set_property('dc:title', title, language=language)
        metadata.set_property('dc:description', description, language=language)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)

        goto = './%s/;%s' % (name, handler.get_firstview())
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)


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
    view__access__ = 'is_training_manager_or_member'
    view__label__ = u'View'
    def view(self, context):
        #here = context.handler
        #site_root = here.get_site_root()
        #website_languages = site_root.get_property('ikaaro:website_languages')
        title = self.get_title()
        handlers = list(self.search_handlers(handler_class=Document))
        handlers.sort(lambda x, y: cmp(get_sort_name(x.name),
                                     get_sort_name(y.name)))
        namespace = {}
        items = []
        images = []
        for item in handlers:
            get = item.get_property
            # XXX Had to hard link the .en in the uri
            # item name seems to strip the language
            language = item.get_property('dc:language')
            url = './%s' % item.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            image1 = item.get_property('abakuc:image1')
            image2 = item.get_property('abakuc:image2')
            if image1:
                try:
                    image1 = item.parent.get_handler(image1[3:])
                except:
                    pass
                else:
                    image = image1.get_property('dc:title')
                    credit = image1.get_property('dc:description')
                    keywords = image1.get_property('dc:subject')
                    images.append({'url': image1, 
                              'image': image,
                              'credit': credit,
                              'keywords': keywords})
            if image2:
                try:
                    image2 = item.parent.get_handler(image2[3:])
                except:
                    pass
                else:
                    image = image2.get_property('dc:title')
                    credit = image2.get_property('dc:description')
                    keywords = image2.get_property('dc:subject')
                    images.append({'url': image2, 
                              'image': image,
                              'credit': credit,
                              'keywords': keywords})

            items.append({'url': url,
                      'description': description,
                      'title': item.title_or_name})

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
            msgs = (u'There is one published document.',
                    u'This topic has ${n} published documents.')
            items_batch = batch(context.uri, batch_start, batch_size,
                          batch_total, msgs=msgs)
            msg = None
        else:
            items_batch = None
            msg = u'This topic has no published documents.'
        
        namespace['batch'] = items_batch 
        namespace['msg'] = msg

        namespace['title'] = title
        namespace['description'] = self.get_property('dc:description')
        namespace['items'] = items
        handler = self.get_handler('/ui/abakuc/training/topic/view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_training_manager'
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


    edit_metadata__access__ = 'is_training_manager'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)

#######################################################################
# Register the classes 
#######################################################################

register_object_class(Trainings)
register_object_class(Training)
register_object_class(Module)
register_object_class(Topic)
