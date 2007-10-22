# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.skins import Skin
from itools.web import get_context
from itools.cms.folder import Folder as DBFolder
from itools.cms.widgets import tree, build_menu
from itools.cms.base import Node
from itools.cms.utils import reduce_string
# Import from abakuc
from companies import Company, Address
from countries import Country


class FrontOffice(Skin):

    def build_namespace(self, context):
        root = context.root
        namespace = Skin.build_namespace(self, context)

        # Level0 correspond to the country (uk, fr) ...
        level0 = [ x[1] for x in root.get_authorized_countries(context) ]
        # Navigation (level 1)
        site_root = context.handler.get_site_root()
        results = root.search(level0=level0, format=site_root.site_format)
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


    def get_main_menu_options(self, context):
        handler = context.handler
        root = handler.get_site_root()
        path = root.abspath

        options = []
        append = options.append
        append({'path': path, 'method': 'list_news',
                'title': u'News',
                'icon': '/ui/abakuc/images/News16.png'})
        append({'path': path, 'method': 'list_jobs',
                'title': u'Jobs',
                'icon': '/ui/abakuc/images/JobBoard16.png'})
        append({'path': path, 'method': 'list_addresses',
                'title': u'Contact us',
                'icon': '/ui/images/UserFolder16.png'})
        return options


    def get_context_menu(self, context):
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


    def get_navigation_menu(self, context):
        """Build the namespace for the navigation menu."""
        handler = context.handler
        root = handler.get_site_root()
        menu = tree(root, active_node=context.handler,
                    allow=Company, user=context.user)
        return {'title': self.gettext(u'Navigation'), 'content': menu}


    def get_left_menus(self, context):
        menus = []
        root =  context.handler.get_site_root()
        if isinstance(root, Company):
            # Main Menu
            menu = self.get_main_menu(context)
            if menu is not None:
                menus.append(menu)
            # Parent's Menu
            menu = self.get_context_menu(context)
            if menu is not None:
                menus.append(menu)
            # Navigation
            menu = self.get_navigation_menu(context)
            menus.append(menu)

        return menus


    #######################################################################
    # Breadcrumb
    #######################################################################
    #def get_breadcrumb(self, context):
    #    """Return a list of dicts [{name, url}...] """
    #    here = context.handler
    #    #root = context.site_root
    #    root = self._get_site_root(context)
    #    # Build the list of handlers that make up the breadcrumb
    #    handlers = [root]
    #    for segment in context.uri.path:
    #        name = segment.name
    #        if name:
    #            try:
    #                handler = handlers[-1].get_handler(name)
    #            except LookupError:
    #                continue
    #            handlers.append(handler)

    #    #  Build the namespace
    #    breadcrumb = []
    #    for handler in handlers:
    #        if not isinstance(handler, Node):
    #            break
    #        # The link
    #        view = handler.get_firstview()
    #        if view is None:
    #            url = None
    #        else:
    #            url = '%s/;%s' % (here.get_pathto(handler), view)
    #        # The title
    #        title = handler.get_title()
    #        short_title = reduce_string(title, 15, 30) 
    #        # Name
    #        breadcrumb.append({'name': title, 'short_name': short_title,
    #                           'url': url})

    #    return breadcrumb


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
        append({'path': path, 'method': 'view_jobs',
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
    # Countries
    'angola.destinationsguide.info': CountrySkin,
    '.destinationsguide.info': CountrySkin,
}

