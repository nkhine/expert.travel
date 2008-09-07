# -*- coding: UTF-8 -*-
# Copyright (C) 2008 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import cStringIO
import datetime
import string

# Import from itools
from itools.handlers import Image, Text
from itools.stl import stl
from itools.web import get_context
from itools.cms.registry import register_object_class
from itools.cms.folder import Folder

# Import from reportlab
from reportlab.pdfgen.canvas import Canvas
from reportlab import platypus
from reportlab.platypus import Frame
from reportlab.lib import pagesizes
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

pattern = ('This is to Certify\n'
           '$user_title <b>$fullname</b>\n'
           'Qualified\n'
           'Successfully Completed "$TM"\n'
           '$date\n')

class Certificate(Folder):

    class_id = 'certificate'
    class_layout = {
        '.image.jpg': Image,
        '.text': Text}
    class_title = u'Certificate'
    class_description = u'...'
    class_icon16 = 'abakuc/images/Certificate16.png'
    class_icon48 = 'abakuc/images/Certificate48.png'
    class_views = [['preview'],
                   ['upload_form'],
                   ['edit_metadata']]


    def new(self, **kw):
        Folder.new(self)
        # .image.jpg
        root = get_context().root
        source = root.get_handler('ui/abakuc/certificate/landscape.jpg')
        image = Image()
        image.load_state_from(source.uri)
        self.cache['.image.jpg'] = image
        # .text
        text = Text()
        text.load_state_from_string(pattern)
        self.cache['.text'] = text


    ########################################################################
    # User Interface
    ########################################################################
    def get_document_types(self):
        return []


    ########################################################################
    # Preview / View
    preview__access__ = 'is_training_manager'
    preview__label__ = u'Preview'
    def preview(self, context):
        handler = self.get_handler('/ui/abakuc/certificate/preview.xml')
        return stl(handler)


    view__access__ = 'is_training_manager'
    def view(self, context):
        response = context.response
        response.set_header('Content-Type', 'image/jpeg')
        return self.get_handler('.image.jpg').to_str()


    topdf__access__ = 'is_training_manager_or_member'
    def topdf(self, context):
        response, user = context.response, context.user

        #skin_name = context.root.get_skin_name()

        mod = self.parent
        date = datetime.date.today()
        exam = mod.get_exam(user.name)
        if exam is not None:
            last_attempt = exam.results.get_last_attempt(user.name)
            if last_attempt is not None:
                date = last_attempt.date
        date = str(date.strftime('%e %B %Y')).strip()
        
        info = {}
        info['fullname'] = user.get_title().encode('UTF-8')

        info['date'] = date
        info['TP'] = 'Training Programme 1'
        info['TM'] = mod.get_property('dc:title').encode('UTF-8')
        info['user_title'] = user.get_property('user:user_title')

        certificate = self.get_handler('.image.jpg')
        certificate = cStringIO.StringIO(certificate.to_str())

        # found img factor
        tmp = platypus.Image(certificate)
        w, h = tmp.imageWidth, tmp.imageHeight

        # define the style 
        style = ParagraphStyle('h1')
        style.fontSize = 22
        style.leading = 32 #style.rightIndent = 5
        style.leftIndent = 0

        text = self.get_handler('.text').to_str()
        text = string.Template(text).safe_substitute(info)
        texts = text.splitlines()

        # write the main text 
        story = []
        for text in texts[:-1]:
            # Reportlab expects proper HTML (no '&')
            text = text.replace('&', '&amp;')
            story.append(platypus.Paragraph(text, style))

        # write the date
        style2 = ParagraphStyle('h1')
        style2.fontSize, style2.alignment = 16, 2 
        story.append(platypus.Paragraph(texts[-1], style2))

        pdf_doc = cStringIO.StringIO()
        if w > h:
            a4 = pagesizes.landscape(pagesizes.A4[:])
            pw, ph = a4
            f = Frame(2*pw/8, 1.16*2*ph/8, 3.5*pw/8., 1.3*2*ph/8, 
                      showBoundary=0)
        else:
            a4 = pagesizes.A4[:]
            pw, ph = a4
            f = Frame(1.2*2*pw/8., 3*ph/8, 4*pw/8, 2*ph/8., showBoundary=0)

        c = Canvas(pdf_doc, pagesize=a4)
        #canvas.saveState()
        factor = max(float(w)/pw, float(h)/ph) * 1.0
        certificate.seek(0)
        image = ImageReader(certificate)
        c.drawImage(image, 0, 0, width=w/factor, height=h/factor)
        #canvas.restoreState()

        f.addFromList(story,c)
        c.save() 
        pdf_doc.seek(0); data = pdf_doc.read(); pdf_doc.close()
        response.set_header('Content-Type', 'application/pdf')
        response.set_header('Content-Disposition',
                            'attachment; filename="certificate.pdf"')
        return data


    ########################################################################
    # Image
    upload_form__access__  = 'is_training_manager'
    upload_form__label__ = u'Upload Image'
    def upload_form(self, context):
        handler = self.get_handler('/ui/file/upload.xml')
        return stl(handler)


    upload__access__  = 'is_training_manager'
    def upload(self, context):
        file = context.get_form_value('file')
        if file is None:
            return context.come_back(u'No file has been entered.')

        filename, mimetype, body = file
        if mimetype != 'image/jpeg':
            return context.come_back(u'Image format must be JPEG.')

        # Check wether the handler is able to deal with the uploaded file
        image = self.get_handler('.image.jpg')
        try:
            image.load_state_from_string(body)
        except:
            image.load_state()
            return context.come_back(u'The file is corrupt, cannot upload.')

        return context.come_back(u'Version uploaded.')


    ########################################################################
    # Text
    edit_metadata__access__ = 'is_training_manager'
    edit_metadata__label__ = u'Edit'
    def edit_metadata(self, context):
        root = get_context().root
        namespace = {}
        # Pattern
        namespace['data'] = self.get_handler('.text').to_str()
        # Business functions
        topics = self.get_property('abakuc:topic')
        namespace['topics'] = root.get_topics_namespace(topics)
        namespace['topics'].insert(0, {'is_selected': 'False', 'id': 'all',
                                                   'title': 'All'})
        if not topics: 
            topics = ['all']
        for x in namespace['topics']:
            x['is_selected'] = x['id'] in topics 

        handler = self.get_handler('/ui/abakuc/certificate/edit_metadata.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_training_manager'
    def edit(self, context):
        data = context.get_form_value('data')
        topics = context.get_form_values('topics')
        # The pattern
        data = unicode(data, 'UTF-8')
        self.get_handler('.text').set_data(data)
        # Business functions
        self.set_property('abakuc:topic', tuple(topics))

        return context.come_back(u'Changes saved.')


register_object_class(Certificate)
