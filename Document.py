
# Import from the Standard Library
import os
import re
from time import time

# Import from itools
from itools.uri import get_reference
from itools import i18n
from itools.web import get_context
from itools.xml import xml 
from itools.cms.html import XHTMLFile
from itools.stl import stl
from itools.cms.widgets import Breadcrumb
from itools.handlers.file import File as itoolsFile

# Import from TravelUni
from WorkflowAware import iHTML, TraveluniWorkflowAware
from namespaces import BusinessFunction
from utils import get_sort_name



class Document(XHTMLFile):

    class_id = 'Document'
    class_aliases = []
    class_title = u'Document'
    class_views = [['preview'],
                   ['edit_form'],
                   ['state_form']]


    GET__mtime__ = None
    def GET(self, context):
        return get_reference('%s/;preview' % self.name)


    @classmethod
    def new_instance_form(cls):
        here = get_context().handler
        document_names = [ x for x in here.get_document_names()
                           if x.startswith('page') ]
        if document_names:
            i = get_sort_name(document_names[-1])[1] + 1
            name = 'page%d' % i
        else:
            name = 'page1'
        return iHTML.new_instance_form.im_func(cls, name)


    #######################################################################
    # Indexing
    def get_catalog_indexes(self):
        indexes = iHTML.get_catalog_indexes(self)
        indexes['tourist_office_name'] = self.parent.parent.parent.name
        return indexes


    #########################################################################
    # User Interface
    #########################################################################
    preview__access__ = 'is_allowed_to_view'
    preview__label__ = u'Preview'
    def preview(self, context):
        # Module and Topic
        topic = self.parent
        module = topic.parent
        # List of topics
        topics = module.get_topics()
        topic_index = topics.index(topic)
        is_first_topic = topic_index == 0
        is_last_topic = topic_index == len(topics) - 1
        # List of documents
        namespace = {}

        # Navigation in documents
        document_names = topic.get_document_names()
        doc_index = document_names.index(self.name)
        is_first_document = doc_index == 0
        is_last_document = doc_index == len(document_names) - 1
        namespace['next_doc'] = None
        namespace['prev_doc'] = None
        next_doc_img = self.get_handler('/ui/traveluni/images/next_doc.gif')
        namespace['next_doc_img'] = self.get_pathto(next_doc_img)
        prev_doc_img = self.get_handler('/ui/traveluni/images/prev_doc.gif')
        namespace['prev_doc_img'] = self.get_pathto(prev_doc_img)
        if document_names:
            # Next document
            if is_last_document:
                if is_last_topic:
                    namespace['next_doc'] = '../../;end_training'
                else:
                    next_topic = topics[topic_index + 1]
                    next_topic_documents = next_topic.get_document_names()
                    if next_topic_documents:
                        namespace['next_doc'] = (
                            '../../%s/%s/;preview'
                            % (next_topic.name, next_topic_documents[0]))
                    else:
                        namespace['next_doc'] = '../../;end_training'
            else:
                namespace['next_doc'] = (
                    '../%s/;preview' % document_names[doc_index + 1])
            # Previous document
            prev_doc = None
            if is_first_document:
                if is_first_topic:
                    namespace['prev_doc'] = None
                else:
                    prev_topic = topics[topic_index - 1]
                    prev_topic_documents = prev_topic.get_document_names()
                    if prev_topic_documents:
                        namespace['prev_doc'] = (
                            '../../%s/%s/;preview'
                            % (prev_topic.name, prev_topic_documents[-1]))
                    else:
                        namespace['prev_doc'] = None
            else:
                namespace['prev_doc'] = (
                    '../%s/;preview' % document_names[doc_index - 1])

        namespace['documents'] = []
        i = 1
        for document_name in document_names:
            namespace['documents'].append(
                {'url': '../%s/;preview' % document_name,
                 'index': i, 'is_current': document_name == self.name})
            i += 1

        # The document
        get_property = self.get_metadata().get_property
        namespace['topic'] = {'title': topic.title_or_name}
        namespace['title'] = self.title
        namespace['description'] = get_property('dc:description')
        namespace['body'] = self.get_body().get_content()
        namespace['dyk_title'] = get_property('document:dyk_title')
        namespace['dyk_description'] = get_property('document:dyk_description')
        namespace['map_image'] = get_property('document:map_image')
        top1 = get_property('document:top1')
##        top1 = top1.replace('&lt;', '<').replace('&amp;', '&')
        top2 = get_property('document:top2')
##        top2 = top2.replace('&lt;', '<').replace('&amp;', '&')
        top3 = get_property('document:top3')
##        top3 = top3.replace('&lt;', '<').replace('&amp;', '&')
        top4 = get_property('document:top4')
##        top4 = top4.replace('&lt;', '<').replace('&amp;', '&')
        top = "%s<br/><br/>%s<br/><br/>%s<br/><br/>%s" % (top1, top2, top3,
                                                          top4)
        namespace['is_top_events'] = top1 or top2 or top3 or top4
        namespace['top_events'] = top

        # Images
        image1 = get_property('document:image1')
        namespace['image1'] = None
        if image1:
            image1_name = image1[3:]
            try:
                image = self.parent.get_handler(image1_name)
            except LookupError:
                pass
            else:
                namespace['image1'] = image1
                namespace['image1_title'] = image.get_property('dc:title')
                namespace['image1_credits'] = image.get_property('document:credits')

        image2 = get_property('document:image2')
        namespace['image2'] = None
        if image2:
            image2_name = image2[3:]
            try:
                image = self.parent.get_handler(image2_name)
            except LookupError:
                pass
            else:
                namespace['image2'] = image2
                namespace['image2_title'] = image.get_property('dc:title')
                namespace['image2_credits'] = image.get_property('document:credits')

        handler = self.get_handler('/ui/traveluni/Document_preview.xml')
        return stl(handler, namespace)


    edit_form__access__ = 'is_admin'
    def edit_form(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        # Text body
        data = self.get_body().get_content()
        namespace['rte'] = self.get_rte('doc_body', data)
        # Images
        get_property = self.get_metadata().get_property
        namespace['image1'] = image1 = get_property('document:image1')
        namespace['image1_title'] = ''
        namespace['image1_credits'] = ''
        if image1:
            try:
                image1 = self.parent.get_handler(image1[3:])
            except:
                pass
            else:
                namespace['image1_title'] = image1.get_property('dc:title')
                namespace['image1_credits'] = image1.get_property('document:credits')
        namespace['image2'] = image2 = get_property('document:image2')
        namespace['image2_title'] = ''
        namespace['image2_credits'] = ''
        if image2:
            try:
                image2 = self.parent.get_handler(image2[3:])
            except:
                pass
            else:
                namespace['image2_title'] = image2.get_property('dc:title')
                namespace['image2_credits'] = image2.get_property('document:credits')
        namespace['map_image'] = get_property('document:map_image')
        # Did you know?
        namespace['dyk_title'] = get_property('document:dyk_title')
        namespace['dyk_description'] = get_property('document:dyk_description')
        # Top 4 festivals 
        namespace['top1'] = get_property('document:top1')
        namespace['top2'] = get_property('document:top2')
        namespace['top3'] = get_property('document:top3')
        namespace['top4'] = get_property('document:top4')
        # Business functions
        namespace['business_functions'] = BusinessFunction.get_options()
        namespace['business_functions'].insert(0, {'id': 'all',
                                                   'label': 'All'})
        document_business_functions = get_property('document:business_functions')
        for x in namespace['business_functions']:
            x['is_selected'] = x['id'] in document_business_functions

        handler = self.get_handler('/ui/traveluni/Document_edit.xml')
        return stl(handler, namespace)


    edit_image__access__ = 'is_admin'
    def edit_image(self, context):
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=itoolsFile, start=self.parent)
        # Avoid general template
        response = context.response
        response.set_header('Content-Type', 'text/html; charset=UTF-8')

        handler = self.get_handler('/ui/traveluni/Document_edit_image.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_admin'
    def edit(self, context):
        root = context.root
        body = context.get_form_value('doc_body')
        image1_title = context.get_form_value('image1_title')
        image1_credits = context.get_form_value('image1_credits')
        image2_title = context.get_form_value('image2_title')
        image2_credits = context.get_form_value('image2_credits')
        file = context.get_form_value('file')
        if context.has_form_value('business_functions'):
            business_functions = context.get_form_values('business_functions')
        else:
            business_functions = ['all']

        not_reindexed = False
        # The body
        if file is not None:
            # Check wether the handler is able to deal with the uploaded file
            try:
                self.load_state_from_file(file)
            except:
                message = (u'The uploaded file does not match this'
                           u' document type.')
                return context.come_back(message)
        elif body:
            stdin, stdout, stderr = os.popen3('tidy -i -utf8 -asxhtml')
            stdin.write(body)
            stdin.close()
            data = stdout.read()
            if not body:
                message = (u'ERROR: the document could not be changed, the'
                           u' input data was not proper HTML code.')
                return context.come_back(message)
            self.load_state_from_string(data)
        else:
            not_reindexed = True

        # Change all
        set_property = self.get_metadata().set_property
        for name in 'dc:title', 'dc:description':
            set_property(name, context.get_form_value(name), language='en')
        # business functions
        set_property('document:business_functions', business_functions)

        # Images
        image1 = context.get_form_value('document:image1')
        set_property('document:image1', image1)
        if image1:
            image1 = self.parent.get_handler(image1[3:])
            image1_title = unicode(image1_title, 'utf8')
            image1.set_property('dc:title', image1_title, language='en')
            image1_credits = unicode(image1_credits, 'utf8')
            image1.set_property('document:credits', image1_credits,
                                language='en')
            root.reindex_handler(image1)
        image2 = context.get_form_value('document:image2')
        set_property('document:image2', image2)
        if image2:
            image2 = self.parent.get_handler(image2[3:])
            image2_title = unicode(image2_title, 'utf8')
            image2.set_property('dc:title', image2_title, language='en')
            image2_credits = unicode(image2_credits, 'utf8')
            image2.set_property('document:credits', image2_credits,
                                language='en')
            root.reindex_handler(image2)
        # Map image
        set_property('document:map_image', context.get_form_value('document:map_image'))
        # Did you know?, Festivals
        for name in ['document:dyk_title', 'document:dyk_description',
                     'document:top1', 'document:top2', 'document:top3',
                     'document:top4']:
            set_property(name, context.get_form_value(name), language='en')

        if not_reindexed:
            root.reindex_handler(self)

        return context.come_back(u'The document has been edited.')
