# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from string import Template

# Import from itools
from itools.cms.skins import Skin
from itools.stl import stl
from itools.web import get_context
from itools.cms.widgets import tree, build_menu
from itools.cms.utils import reduce_string
from itools.uri.generic import decode_query
from itools.handlers import Folder
from itools.cms.base import Node
# Import from abakuc
from expert_travel import ExpertTravel
from companies import Company, Address
from training import Training, Module, Topic
from document import Document
from countries import Country
from utils import get_sort_name

class Node(object):

    def __init__(self, handler):
        self.children = []
        self.handler = handler

    def click(self, path):
        handler =  self.handler
        # fill children
        if isinstance(handler, Folder):
            #allowed_instances = Module, Topic, Document
            #
            #XXX For some reason, I get to dictionary items
            #one with .en extentsion and the other without:
            #...
            #'short_name': u'topic1',
            # 'submenus': [   {   'active': False,
            #                     'class': '',
            #                     'class2': '',
            #                     'name': u'First page',
            #                     'open': False,
            #                     'short_name': u'First page',
            #                     'submenus': [   ],
            #                     'url': 'page1.xhtml/;view'},
            #                 {   'active': False,
            #                     'class': '',
            #                     'class2': '',
            #                     'name': u'First page',
            #                     'open': False,
            #                     'short_name': u'First page',
            #                     'submenus': [   ],
            #                     'url': 'page1.xhtml.en/;view'},
            allowed_instances = Module, Topic 
            handlers = [
                handler.get_handler(x) for x in handler.get_handler_names()
                ]
            handlers = [
                h for h in handlers if isinstance(h, allowed_instances) ]
            handlers.sort(lambda x, y: cmp(get_sort_name(x.name),
                                           get_sort_name(y.name)))
            self.children = [ Node(h) for h in handlers ]
        # parse the path
        if path:
            child_name, path = path[0], path[1:]
            child_name = str(child_name)
            for child in self.children:
                if child.handler.name == child_name:
                    child.click(path)
                    break

    def get_tree(self, here):
        ns = {}
        handler = self.handler
        name = handler.title or handler.name
        ns['name'] = name
        ns['short_name'] = name # XXX
        submenus = [ child.get_tree(here) for child in self.children ]
        ns['submenus'] = submenus
        ns['open'] = bool(len(submenus))
        ns['class'] = ''
        ns['class2'] = ''
        ns['active'] = handler.name in str(get_context().uri.path)
        if isinstance(handler, Document):
            ns['url'] = '%s/;view' % here.get_pathto(handler)
        else:
            ns['url'] = '%s/;view' % here.get_pathto(handler)

        return ns

class FrontOffice(Skin):
    '''
    As a front office we require 3 types of navigation:
    1) On the main directories sites such as
        a) Expert.Travel - we want to list all business functions
        b) Destinations Guide - we want to list all continents
    2) We also have Company views, where each Company object has
    its own navigation:
        a) News
        b) Jobs
        c) Branches
    3) Lastly we also have Training programme view, here we list
    all the Modules for each training programme.

    We also need to consider the fact that expert.travel has
    i18n versions so that http://uk.expert.travel will list
    only companies that have UK addresses.
    '''

    def build_namespace(self, context):
        root = context.root
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        namespace = Skin.build_namespace(self, context)

        # Level0 correspond to the country (uk, fr) ...
        level0 = [ x[1] for x in root.get_authorized_country(context) ]
        # Navigation (level 1)
        site_root = context.handler.get_site_root()
        results = root.search(level0=level0, format=site_root.site_format)
        # Flat
        level1 = []
        # XXX Here is a bug #133 if you re-start
        # the server you no longer have a list
        # you need to re-index
        # Why is it when you index all topics
        # are a list, but when you restart they are not?
        for x in results.get_documents():
            x = x.level1
            if isinstance(x, list):
                level1.extend(x)
            else:
                y = x.split(' ')
                level1.extend(y)
        # Unique
        # Only works on Expert.Travel and Company objects
        level1 = set(level1)
        pp.pprint(level1)
        level1 = [ {'name': x, 'title': site_root.get_level1_title(x)}
                   for x in level1 ]
        level1.sort(key=lambda x: x['title'])
        namespace['level1'] = level1
        # Returns the Module, for Training object
        context_menu_html = self.get_context_menu_html(context)
        if context_menu_html is None:
            namespace['context_menu_html'] = 'None' 
        else:    
            namespace['context_menu_html'] = context_menu_html

        return namespace

    def get_main_menu(self, context):
        user = context.user
        root = context.site_root
        here = context.handler or root

        menu = []
        for option in self.get_main_menu_options(context):
            path = option['path']
            method = option['method']
            title = option['title']
            src = option['icon']

            handler = root.get_handler(path)
            ac = handler.get_access_control()
            if ac.is_access_allowed(user, handler, method):
                href = '%s/;%s' % (here.get_pathto(handler), method)
                menu.append({'href': href, 'title': self.gettext(title),
                             'class': '', 'src': src, 'items': []})
    
        if not menu:
            return None

        return {'title': self.gettext(u'Main Menu'),
                'content': build_menu(menu)}

    def get_main_menu_options(self, context):
        #handler = context.handler
        root = context.handler.get_site_root()
        path = root.abspath

        options = []
        append = options.append
        append({'path': path, 'method': 'news',
                'title': u'News',
                'icon': '/ui/abakuc/images/News16.png'})
        append({'path': path, 'method': 'jobs',
                'title': u'Jobs',
                'icon': '/ui/abakuc/images/JobBoard16.png'})
        append({'path': path, 'method': 'addresses',
                'title': u'Contact us',
                'icon': '/ui/images/UserFolder16.png'})
        append({'path': path, 'method': 'modules',
                'title': u'Training Modules',
                'icon': '/ui/abakuc/images/Resources16.png'})
        return options

    def get_context_menu(self, context):
        """
        Lists contents of objects menu.
        """
        # FIXME Hard-Coded
        from jobs import Job
        from news import News
        here = context.handler
        while here is not None:
            if isinstance(here, (Job, News)):
                break
            here = here.parent
        else:
            return None

        base = context.handler.get_pathto(here)

        menu = []
        for view in here.get_views():
            # Find out the title
            if '?' in view:
                name, args = view.split('?')
                args = decode_query(args)
            else:
                name, args = view, {}
            title = getattr(here, '%s__label__' % name)
            if callable(title):
                title = title(**args)
            # Append to the menu
            menu.append({'href': '%s/;%s' % (base, view),
                         'title': self.gettext(title),
                         'class': '', 'src': None, 'items': []})

        return {'title': self.gettext(here.class_title),
                'content': build_menu(menu)}


    #def get_content_menu(self, context):
    #    here = context.handler
    #    user = context.user

    #    options = []
    #    # Parent
    #    parent = here.parent
    #    if parent is not None:
    #        firstview = parent.get_firstview()
    #        options.append({'href': '../;%s' % (firstview),
    #                        'src': None,
    #                        'title': '<<',
    #                        'class': '',
    #                        'items': []})

    #    # Content
    #    size = 0
    #    allowed_instances = Folder
    #    if isinstance(here, allowed_instances):
    #        for handler in here.search_handlers():
    #            ac = handler.get_access_control()
    #            if not ac.is_allowed_to_view(user, handler):
    #                continue
    #            firstview = handler.get_firstview()
    #            src = handler.get_path_to_icon(size=16, from_handler=here)
    #            options.append({'href': '%s/;%s' % (handler.name, firstview),
    #                            'src': src,
    #                            'title': handler.get_title(),
    #                            'class': '',
    #                            'items': []})
    #            size += 1

    #    menu = build_menu(options)
    #    title = Template(u'Content ($size)').substitute(size=size)

    #    return {'title': title, 'content': menu}

    def get_navigation_menu(self, context):
        """Build the namespace for the navigation menu."""
        handler = context.handler
        root = handler.get_site_root()
        menu = tree(root, active_node=context.handler,
                    allow=Company, user=context.user)
        return {'title': self.gettext(u'Navigation'), 'content': menu}

    ########################################################################
    # Training Programme left menu
    def get_context_menu_html(self, context):
        root = context.root
        # Not Found
        here = context.handler
        if here is None:
            here = root
        # Namespace
        site_root = here.get_site_root()
        tree = Node(site_root)
        tree.click(context.path[2:])
        menus = tree.get_tree(here)
        template_path = \
          'ui/abakuc/training/context_menu_html.xml'

        namespace = {}
        namespace['menus'] = menus
        #namespace['horiz_nav'] = self.get_global_menu_ns(context)
        template = root.get_handler(template_path)
        return stl(template, namespace)


    def get_modules_menu(self, context):
        """Build the namespace for the navigation menu."""
        root = context.handler.get_site_root()
        menu = tree(root, active_node=context.handler,
                    allow=Training, user=context.user)
        return {'title': self.gettext(u'Modules'), 'content': menu}

    def is_training(self, context):
        '''Return a bool'''
        training = self.get_site_root()
        if isinstance(training, Training):
            training = True
        return training

    def get_left_menus(self, context):
        root =  context.handler.get_site_root()
 
        menus = []
        if isinstance(root, Company):
            # Navigation
            menu = self.get_navigation_menu(context)
            menus.append(menu)
            # Main Menu
            menu = self.get_main_menu(context)
            if menu is not None:
                menus.append(menu)
            # Parent's Menu
            menu = self.get_context_menu(context)
            if menu is not None:
                menus.append(menu)
        elif isinstance(root, Training):
            # Navigation
            menu = self.get_navigation_menu(context)
            menus.append(menu)
            # Main Menu
            menu = self.get_main_menu(context)
            if menu is not None:
                menus.append(menu)
        elif isinstance(root, ExpertTravel):
            # Navigation
            menu = self.get_navigation_menu(context)
            menus.append(menu)

        return menus


class DestinationsSkin(FrontOffice):

    def build_namespace(self, context):
        root = context.root
        namespace = Skin.build_namespace(self, context)

        # Navigation (level 1)
        site_root = context.handler.get_site_root()
        results = root.search(format=site_root.site_format)
        # Flat
        level1 = []
        for x in results.get_documents():
            x = x.level1
            if isinstance(x, list):
                level1.extend(x)
            else:
                level1.append(x)
        # Unique
        level1 = set(level1)
        level1 = [ {'name': x, 'title': site_root.get_level1_title(x)}
                   for x in level1 ]
        level1.sort(key=lambda x: x['title'])
        namespace['level1'] = level1

        return namespace

    def get_left_menus(self, context):
        menus = []

        root =  context.handler.get_site_root()
        if isinstance(root, Country):
            # Main Menu
            menu = self.get_main_menu(context)
            if menu is not None:
                menus.append(menu)

        return menus

    def get_main_menu_options(self, context):
        options = []
        append = options.append
        handler = context.handler
        root = handler.get_site_root()
        path = root.abspath

        append({'path': path, 'method': 'view',
                'title': u'Country details',
                'icon': '/ui/abakuc/images/AddressBook16.png'})
        append({'path': path, 'method': 'jobs',
                'title': u'Jobs',
                'icon': '/ui/abakuc/images/JobBoard16.png'})
        append({'path': path, 'method': 'view_addresses',
                'title': u'Branches',
                'icon': '/ui/images/UserFolder16.png'})
        return options


class CompanySkin(FrontOffice):
    """Skin for companies"""

    def get_template(self):
        try:
            return self.get_handler('template.xhtml')
        except LookupError:
            # Default
            return self.get_handler('../.expert.travel/template.xhtml')


class CountrySkin(FrontOffice):
    """Skin for countries"""

    def get_template(self):
        try:
            return self.get_handler('template.xhtml')
        except LookupError:
            # Default
            return self.get_handler('../.destinationsguide.info/template.xhtml')


websites = {
    # Main Sites
    'fr.expert.travel': FrontOffice,
    'uk.expert.travel': FrontOffice,
    'destinationsguide.info': DestinationsSkin,
    # Companies
    'abakuc.expert.travel': CompanySkin,
    '.expert.travel': CompanySkin,
}

countries = {
    '.destinationsguide.info': CountrySkin,
    'angola.destinationsguide.info': CountrySkin,
}

trainings = {
    #'training.expert.travel': TrainingSkin,
    'tp1.training.expert.travel': FrontOffice,
    'uk.tp1.expert.travel': FrontOffice,
}
