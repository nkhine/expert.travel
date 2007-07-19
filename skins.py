# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.skins import Skin

# Import from abakuc
from companies import Company

class FrontOffice(Skin):

    def get_template(self):
        # All front-offices share the same template
        return self.get_handler('/ui/uktravel/template.xhtml')


    def get_left_menus(self, context):
        return []


    def get_styles(self, context):
        styles = Skin.get_styles(self, context)
        styles.append('/ui/uktravel/style.css')
        return styles


    def get_breadcrumb(self, context):
        """Return a list of dicts [{name, url}...] """
        here = context.handler
        root = self._get_site_root(context)

        # Build the list of handlers that make up the breadcrumb
        handlers = [root]
        for segment in context.uri.path:
            name = segment.name
            if name:
                handler = handlers[-1].get_handler(name)
                handlers.append(handler)

        #  Build the namespace
        breadcrumb = []
        for handler in handlers:
            url = '%s/;view' % here.get_pathto(handler)
            # The title
            title = handler.get_title_or_name()
            # Name
            breadcrumb.append({'name': title, 'short_name': title, 'url': url})

        return breadcrumb


    def build_namespace(self, context):
        namespace = Skin.build_namespace(self, context)

        # Navigation (level 1)
        site_root = context.handler.get_site_root()
        results = context.root.search(format=site_root.site_format)
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



class FOCompanies(FrontOffice):

    def get_left_menus(self, context):
        handler = context.handler
        # Main Menu
        menus = []
        if isinstance(handler, Company):
            menu = self.get_main_menu(context)
            if menu is not None:
                menus.append(menu)

        # Content Menu XXX (Futur)
        #menu = self.get_content_menu(context)
        #menus.append(menu)
        return menus


    def get_main_menu_options(self, context):
        handler = context.handler
        options = []
        append = options.append
        path = handler.abspath
        append({'path': path, 'method': 'view',
                'title': u'Company details',
                'icon': '/ui/abakuc/images/AddressBook16.png'})
        append({'path': path, 'method': 'view_jobs',
                'title': u'Jobs',
                'icon': '/ui/abakuc/images/JobBoard16.png'})
        append({'path': path, 'method': 'view_branches',
                'title': u'Branches',
                'icon': '/ui/images/UserFolder16.png'})

        return options

