# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Integer, Unicode
from itools.cms.registry import register_object_class
from itools.stl import stl
from itools.cms import widgets

# Import from abakuc
from website import WebSite


class Destinations(WebSite):
 
    class_id = 'destinations'
    class_title = u'Destinations Guide'
    class_icon16 = 'abakuc/images/Resources16.png'
    class_icon48 = 'abakuc/images/Resources48.png'

    def _get_virtual_handler(self, segment):
        name = segment.name
        if name == 'countries':
            return self.get_handler('/countries')
        return WebSite._get_virtual_handler(self, segment)


    #######################################################################
    # User Interface / Navigation
    #######################################################################
    site_format = 'country'

    def get_level1_title(self, level1):
        return level1

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
        query = {'format': self.site_format}

        if level1 is not None:
            query['level1'] = level1
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
        # Country
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
        countries = root.get_handler('countries')
        country_list = []
        documents = results.get_documents(sort_by='title')
        for country in documents[start:start+size]:
            country = root.get_handler(country.abspath)
            get_property = country.metadata.get_property
            country_list.append(
                {'href': '%s/;view' % self.get_pathto(country),
                 'title': country.title,
                 })
        namespace['countries'] = country_list

        handler = self.get_handler('ui/abakuc/destinations/search.xml')
        return stl(handler, namespace)

register_object_class(Destinations)
