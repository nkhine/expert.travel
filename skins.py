# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.cms.skins import Skin



class FrontOffice(Skin):

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
        # Topics
        topics = []
        topics_csv = root.get_handler('topics.csv')
        for topic_id, topic_title in topics_csv.get_rows():
            results = root.search(format='company', topic=topic_id)
            topics.append({'href': '/;search?topic=%s' % topic_id,
                           'title': topic_title,
                           'adverts': results.get_n_documents()})
        topics.sort(key=lambda x: x['title'])
        namespace['topics'] = topics

        return namespace
