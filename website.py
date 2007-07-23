# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, Unicode
from itools.stl import stl
from itools.cms.website import WebSite as BaseWebSite
from itools.cms import widgets

# Import from abakuc
from base import Handler


class WebSite(Handler, BaseWebSite):

    #######################################################################
    # User Interface
    #######################################################################
    def GET(self, context):
        return context.uri.resolve2(';view')


    view__access__ = True
    def view(self, context):
        handler = self.get_handler('/ui/%s/home.xhtml' % self.name)
        return stl(handler)


    #######################################################################
    # User Interface
    #######################################################################
    search__access__ = True
    def search(self, context):
        from root import world

        root = context.root

        level1 = context.get_form_value('level1')
        level2 = context.get_form_value('level2')
        level3 = context.get_form_value('level3')
        level4 = context.get_form_value('level4')
        text = context.get_form_value('search_text')

        # XXX hack (fix the bug in itools ?)
        if level1:
            level1 = unicode(level1, 'utf-8')
        if level2:
            level2 = unicode(level2, 'utf-8')
        if level3:
            level3 = unicode(level3, 'utf-8')
        if level4:
            level4 = unicode(level4, 'utf-8')

        # Build the query
        query = {'format': 'address'}


        if level1 is not None:
            query['level1'] = level1
            # Select the good country
            authorized_countries = root.get_authorized_countries(context)
            if len(authorized_countries)==1:
                country_name, country_code = authorized_countries[0]
                query['level0'] = country_code
        if level2 is not None:
            query['level2'] = level2
        if level3 is not None:
            query['level3'] = level3
        if level4 is not None:
            query['level4'] = level4
        if text:
            query['title'] = text

        # The namespace
        namespace = {}
        namespace['title'] = None
        namespace['regions'] = []

        # Breadcrumbs path
        namespace['bread_path'] = []
        nb_level = len(context.uri.query)
        keys = ['level2', 'level3', 'level4']
        for i, key in enumerate(keys):
            # If attribute exist in uri
            if eval(key):
                # If current level is the last, there's no URL
                if nb_level > (i+2):
                    # We Remove parameters which concern a sup level
                    kw = {}
                    for j, x in enumerate(context.uri.query):
                        if j > i+1:
                            kw[x] = None
                    url = context.uri.replace(**kw)
                else:
                    url = None
                namespace['bread_path'].append({'value': eval(key),
                                                'url': url,
                                                'last_level': (i+2)==4})

        # Topic
        if level1 is not None:
            base = context.uri
            namespace['title'] = self.get_level1_title(level1)
            regions = []
            # Level 2
            results = root.search(**query)
            documents = results.get_documents()
            if level2 is None:
                level = set([ x.level2 for x in documents ])
                level = [ {'href': base.replace(level2=x), 'title': x}
                          for x in level ]
            else:
                base = base.replace(level2=level2)
                if level3 is None:
                    level = set([ x.level3 for x in documents ])
                    level = [ {'href': base.replace(level3=x), 'title': x}
                              for x in level ]
                else:
                    base = base.replace(level3=level3)
                    if level4 is None:
                        level = set([ x.level4 for x in documents ])
                        level = [ {'href': base.replace(level4=x), 'title': x}
                                  for x in level ]
                    else:
                        level = []
            level.sort(key=lambda x: x['title'])
            namespace['level'] = level
        
        elif text is not None:
            # Search 
            namespace['level'] = None
            results = root.search(**query)
            documents = results.get_documents()
        else:
            return context.come_back(goto='/')

        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 5
        total = results.get_n_documents()
        namespace['batch'] = widgets.batch(context.uri, start, size, total)

        # Search
        companies = root.get_handler('companies')
        addresses = []
        documents = results.get_documents(sort_by='title')
        for address in documents[start:start+size]:
            address = root.get_handler(address.abspath)
            get_property = address.metadata.get_property
            company = address.parent
            county_id = get_property('abakuc:county')
            if county_id is None:
                # XXX Every address should have a county
                region = ''
                county = ''
            else:
                row = world.get_row(county_id)
                region = row[7]
                county = row[8]
            addresses.append(
                {'href': '%s/;view' % self.get_pathto(address),
                 'title': company.title,
                 'town': get_property('abakuc:town'),
                 'address': get_property('abakuc:address'),
                 'postcode': get_property('abakuc:postcode'),
                 'county': county,
                 'region': region,
                 'phone': get_property('abakuc:phone'),
                 'fax': get_property('abakuc:fax'),
                 })
        namespace['companies'] = addresses

        handler = self.get_handler('ui/abakuc/search.xml')
        return stl(handler, namespace)


    ##########################################################################
    ## Javascript
    ##########################################################################
    get_regions_str__access__ = True
    def get_regions_str(self, context):  
        return context.root.get_regions_str(context)

    get_counties_str__access__ = True
    def get_counties_str(self, context): 
        return context.root.get_counties_str(context)

