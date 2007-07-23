# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.skins import Skin
from itools.web import get_context

# Import from abakuc
from expert_travel import ExpertTravel

class FrontOffice(Skin):

    def get_template(self):
        context = get_context()
        root = context.root
        # Set a default template
        template = '/ui/uk/template.xhtml'

        # Select the template (considering counties)
        country = root.get_website_country(context)
        if country:
            template = '/ui/%s/template.xhtml' % self.name
            # If template not exist, raise
            if not self.has_handler(template):
                raise LookupError, "The Template %s don't exist" % template

        return self.get_handler(template)


    def get_left_menus(self, context):
        return []


    def get_styles(self, context):
        styles = Skin.get_styles(self, context)
        styles.append('/ui/%s/style.css' % self.name)
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
        root = context.root
        namespace = Skin.build_namespace(self, context)

        # Level0 correspond to the country (uk, fr) ...
        level0 = None
        authorized_countries = root.get_authorized_countries(context)
        if len(authorized_countries)==1:
            country_name, country_code = authorized_countries[0]
            level0 = country_code
        # Navigation (level 1)
        site_root = context.handler.get_site_root()
        results = context.root.search(level0=level0,format=site_root.site_format)
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

    """
      Skin for companies
    """

    def get_template_prefix(self):
        """
        Return the prefix of the template to use
        """
        context = get_context()
        root = context.root
        website_type = root.get_website_type(context)
        if website_type==1:
            # We are on a country website as
            # uk.expert.travel/companies/itaapy
            return root.get_host_prefix(context)
        elif website_type==2:
            # We are on a company website as
            # itaapy.expert.travel
            company = root.get_host_prefix(context)
            company_skin = '/ui/companies/%s/template.xhtml' % company
            if self.has_handler(company_skin):
                # The company has a personalized skin
                template_prefix = 'companies/%s' % company
            else:
                # Set the default company skin
                template_prefix = 'companies/'
        else:
            raise ValueError, 'Invalid value'

        return template_prefix


    def get_template(self):
        template_prefix = self.get_template_prefix()
        return self.get_handler('/ui/%s/template.xhtml' % template_prefix)


    def get_styles(self, context):
        styles = Skin.get_styles(self, context)
        template_prefix = self.get_template_prefix()
        styles.append('/ui/%s/style.css' % template_prefix)
        return styles


    def get_left_menus(self, context):
        # Main Menu
        menus = []
        menu = self.get_main_menu(context)
        if menu is not None:
            menus.append(menu)

        # Content Menu XXX (Futur)
        #menu = self.get_content_menu(context)
        #menus.append(menu)
        return menus


    def get_main_menu_options(self, context):
        options = []
        append = options.append
        handler = context.handler
        root = handler.get_site_root()
        path = root.abspath

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

