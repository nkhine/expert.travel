
# Import from the Standard Library
import os
import re
from datetime import datetime

# Import from itools
from itools.uri import get_reference, Path
from itools import get_abspath
from itools import i18n
from itools.web import get_context
from itools.xml import xml
from itools.stl import stl
from itools.cms.widgets import Breadcrumb
from itools.cms.html import XHTMLFile
from itools.handlers.file import File as itoolsFile
from itools.cms.registry import register_object_class, get_object_class
from itools.i18n import get_language_name
from itools.cms.messages import *
from itools.rest import checkid
from itools.datatypes import FileName
from itools.datatypes import DateTime
from itools.html import Parser as HTMLParser
# Import from abakuc
#from workflow import iHTML, TraveluniWorkflowAware
#from namespaces import BusinessFunction
from utils import get_new_id, get_sort_name

class Document(XHTMLFile):

    class_id = 'document'
    class_aliases = []
    class_title = u'Training Document'
    class_views = [['view'],
                   ['edit_form'],
                   ['edit_metadata_form'],
                   ['state_form']]

    @classmethod
    def new_instance_form(cls, context, name=''):
        root = context.root
        here = context.handler
        site_root = here.get_site_root()
        namespace = {}
        # The class id
        namespace['class_id'] = cls.class_id
        website_languages = site_root.get_property('ikaaro:website_languages')
        default_language = website_languages[0]
        languages = []
        for code in website_languages:
            language_name = get_language_name(code)
            languages.append({'code': code,
                              'name': cls.gettext(language_name),
                              'isdefault': code == default_language})
        namespace['languages'] = languages

        handler = root.get_handler('/ui/abakuc/training/document/new_instance.xml')
        return stl(handler, namespace)


    @classmethod
    def new_instance(cls, container, context):
        title = context.get_form_value('dc:title')
        language = context.get_form_value('dc:language')

        # Generate the new_instance name
        # based on the class_id
        document_names = [ x for x in container.get_handler_names()
                           if x.startswith(cls.class_id) ]
        if document_names:
            i = get_sort_name(max(document_names))[1]+ 1
            name = '%s%d.%s' % (cls.class_id, i, cls.class_extension)
        else:
            name = '%s1.%s' % (cls.class_id, cls.class_extension)

        # Check the name
        name = name.strip()
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
        metadata.set_property('dc:language', language)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)

        goto = './%s/;%s' % (name, handler.get_firstview())
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)
    #######################################################################
    # ACL
    def is_allowed_to_view(self, user, object):
        # Protect the document
        return self.is_branch_manager_or_member(user, object)

    #######################################################################
    # View
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    view__title__ = u'View'
    def view(self, context):
        here = context.handler
        # Module and Topic
        topic = here.parent
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
        next_doc_img = self.get_handler('/ui/abakuc/images/next_doc.gif')
        namespace['next_doc_img'] = self.get_pathto(next_doc_img)
        prev_doc_img = self.get_handler('/ui/abakuc/images/prev_doc.gif')
        namespace['prev_doc_img'] = self.get_pathto(prev_doc_img)
        if document_names:
            # Next document
            if is_last_document:
                if is_last_topic:
                    namespace['next_doc'] = '../../;end'
                else:
                    next_topic = topics[topic_index + 1]
                    next_topic_documents = next_topic.get_document_names()
                    if next_topic_documents:
                        namespace['next_doc'] = (
                            '../../%s/%s/;view'
                            % (next_topic.name, next_topic_documents[0]))
                    else:
                        namespace['next_doc'] = '../../;end'
            else:
                namespace['next_doc'] = (
                    '../%s/;view' % document_names[doc_index + 1])
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
                            '../../%s/%s/;view'
                            % (prev_topic.name, prev_topic_documents[-1]))
                    else:
                        namespace['prev_doc'] = None
            else:
                namespace['prev_doc'] = (
                    '../%s/;view' % document_names[doc_index - 1])

        namespace['documents'] = []
        i = 1
        for document_name in document_names:
            namespace['documents'].append(
                {'url': '../%s/;view' % document_name,
                 'index': i, 'is_current': document_name == self.name})
            i += 1

        namespace['topic'] = {'title': topic.title_or_name}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        namespace['image1'] = image1 = self.get_property('abakuc:image1')
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
        # Image 2
        namespace['image2'] = image2 = self.get_property('abakuc:image2')
        namespace['image2_title'] = ''
        namespace['image2_credit'] = ''
        namespace['image2_keywords'] = ''
        if image1:
            try:
                image2 = self.parent.get_handler(image2[3:])
            except:
                pass
            else:
                namespace['image2_title'] = image2.get_property('dc:title')
                namespace['image2_credit'] = image2.get_property('dc:description')
                namespace['image2_keywords'] = image2.get_property('dc:subject')
        # Body text
        body = self.get_body()
        if body is None:
            namespace['text'] = None
        else:
            namespace['text'] = body.get_content_elements()

        handler = self.get_handler('/ui/abakuc/training/document/view.xml')
        return stl(handler, namespace)

    #######################################################################
    # Edit / Inline / edit form
    edit_form__access__ = 'is_allowed_to_edit'
    edit_form__label__ = u'Edit'
    edit_form__sublabel__ = u'Inline'
    def edit_form(self, context):
        """WYSIWYG editor for HTML documents."""
        data = self.get_epoz_data()
        # If the document has not a body (e.g. a frameset), edit as plain text
        if data is None:
            return Text.edit_form(self, context)

        # Edit with a rich text editor
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        namespace['timestamp'] = DateTime.encode(datetime.now())
        namespace['rte'] = self.get_rte(context, 'data', data)
        # Images
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

        # Image 2
        namespace['image2'] = image2 = self.get_property('abakuc:image2')
        namespace['image2_title'] = ''
        namespace['image2_credit'] = ''
        namespace['image2_keywords'] = ''
        if image1:
            try:
                image2 = self.parent.get_handler(image2[3:])
            except:
                pass
            else:
                namespace['image2_title'] = image2.get_property('dc:title')
                namespace['image2_credit'] = image2.get_property('dc:description')
                namespace['image2_keywords'] = image2.get_property('dc:subject')
        handler = self.get_handler('/ui/abakuc/training/document/edit.xml')
        return stl(handler, namespace)


    edit_image__access__ = 'is_admin'
    def edit_image(self, context):
        media_folder = '/media'
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=itoolsFile, start=media_folder)
        # Avoid general template
        response = context.response
        response.set_header('Content-Type', 'text/html; charset=UTF-8')

        handler = self.get_handler('/ui/abakuc/training/document/edit_image.xml')
        return stl(handler, namespace)


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
        Allow to upload and add an image to epoz
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


    addimage_form__access__ = 'is_allowed_to_edit'
    def addimage_form(self, context):
        from file import File
        from binary import Image
        from widgets import Breadcrumb
        # Build the bc
        if isinstance(self, File):
            start = self.parent
        else:
            start = self
        # Construct namespace
        namespace = {}
        namespace['bc'] = Breadcrumb(filter_type=Image, start=start)
        namespace['message'] = context.get_form_value('message')

        prefix = Path(self.abspath).get_pathto('/ui/html/addimage.xml')
        handler = self.get_handler('/ui/html/addimage.xml')
        return stl(handler, namespace, prefix=prefix)

    #addimage_form__access__ = 'is_allowed_to_edit'
    #def addimage_form(self, context):
    #    from itools.cms.file import File
    #    from itools.cms.binary import Image
    #    from itools.cms.widgets import Breadcrumb
    #    here = context.handler
    #    site_root = here.get_site_root()
    #    start = site_root.get_handler('media')
    #    # Construct namespace
    #    namespace = {}
    #    namespace['bc'] = Breadcrumb(filter_type=Image, start=start)
    #    namespace['message'] = context.get_form_value('message')

    #    prefix = Path(self.abspath).get_pathto('/ui/abakuc/training/document/addimage.xml')
    #    handler = self.get_handler('/ui/abakuc/training/document/addimage.xml')
    #    return stl(handler, namespace, prefix=prefix)




    #######################################################################
    # Edit / Inline / edit
    edit__access__ = 'is_allowed_to_edit'
    def edit(self, context, sanitize=False):
        timestamp = context.get_form_value('timestamp', type=DateTime)
        if timestamp is None or timestamp < self.timestamp:
            return context.come_back(MSG_EDIT_CONFLICT)

        new_body = context.get_form_value('data')
        new_body = HTMLParser(new_body)
        if sanitize:
            new_body = sanitize_stream(new_body)
        # Save the changes
        # "get_epoz_document" is to set in your editable handler
        document = self.get_epoz_document()
        old_body = document.get_body()
        document.set_changed()
        document.events = (document.events[:old_body.start+1]
                           + new_body
                           + document.events[old_body.end:])

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
        # Image 2
        image2_title = context.get_form_value('image2_title')
        image2_credit = context.get_form_value('image2_credit')
        image2_keywords = context.get_form_value('image2_keywords')
        image2 = context.get_form_value('abakuc:image2')
        self.set_property('abakuc:image2', image2)
        if image2:
            image2 = self.parent.get_handler(image2[3:])
            image2_title = unicode(image2_title, 'utf8')
            image2.set_property('dc:title', image2_title, language='en')
            image2_keywords = unicode(image2_keywords, 'utf8')
            image2.set_property('dc:subject', image2_keywords)
            image2_credit = unicode(image2_credit, 'utf8')
            image2.set_property('dc:description', image2_credit,
                                language='en')
        return context.come_back(MSG_CHANGES_SAVED)

register_object_class(Document)
