# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import os
import re
import datetime

# Import from itools
from itools import get_abspath
from itools.datatypes import Unicode
from itools import vfs
from itools.stl import stl
from itools.xhtml.XHTML import Document as itoolsDocument
from itools.web import get_context
from itools.cms.registry import register_object_class

# Import from ikaaro
from itools.cms.Folder import Folder as ikaaroFolder
from itools.cms.workflow import WorkflowAware as ikaaroWorkflowAware
from itools.cms.Handler import Handler
from itools.cms.File import File as ikaaroImage

# Import from abakuc
from base import Handler

#w|!clear; /Users/khinester/Sites/itools/0.13/Python-2.4.3/bin/icms-stop /Users/khinester/Sites/itools/0.13/abakuc.com ; /Users/khinester/Sites/itools/0.13/Python-2.4.3/bin/python setup.py clean build install ; /Users/khinester/Sites/itools/0.13/Python-2.4.3/bin/icms-start /Users/khinester/Sites/itools/0.13/abakuc.com


############################################################################
# Adverts 
############################################################################

class Adverts(Handler, ikaaroFolder):

    class_id = 'adverts'
    class_title = u'Adverts'
    class_description = u'Folder containing all the Adverts'
    class_icon48 = 'abakuc/images/Advert48.png'
    class_icon16 = 'abakuc/images/Advert16.png'

    def get_document_types(self):
        return [Advert]

register_object_class(Adverts)

class Advert(Handler, ikaaroFolder):

    class_id = 'advert'
    class_title = u'Advert'
    class_description = u'Add a new Advert'
    class_icon48 = 'abakuc/images/Advert48.png'
    class_icon16 = 'abakuc/images/Advert16.png'



    ########################################################################
    # Skeleton
    def get_skeleton(self):
        path = get_abspath(globals(), 'abakuc/images/px.png')
        pix = get_resource(path)

        return {'.body': itoolsDocument(), '.logo': ikaaroImage(pix),
                '.picture1': ikaaroImage(pix), '.picture2': ikaaroImage(pix),
                '.picture3': ikaaroImage(pix), '.picture4': ikaaroImage(pix)}


    def _get_handler(self, segment, resource):
        name = segment.name
        if name == '.body':
            return itoolsDocument(resource)
        elif name == '.logo':
            return ikaaroImage(resource)
        elif name == '.picture1':
            return ikaaroImage(resource)
        elif name == '.picture2':
            return ikaaroImage(resource)
        elif name == '.picture3':
            return ikaaroImage(resource)
        elif name == '.picture4':
            return ikaaroImage(resource)
        return ikaaroFolder._get_handler(self, segment, resource)

    # security access
    def is_owner_or_admin(self):
        user = get_context().user
        owner = self.metadata.get_property('owner')
        if user is not None:
            if user.name == owner or self.is_admin():
                return True
        
        return False

    def is_allowed_to_view(self):
        if not self.is_owner_or_admin():
            if self.workflow_state != 'public':
                return False

        return True 

    #def is_allowed_to_trans(self, name):
    #    context = get_context()
    #    root, user = context.root, context.user

    #    if user is None:
    #        return False

    #    if user.name in root.get_handler('admins').get_usernames():
    #        return True
    #    if user.name in root.get_handler('reviewers').get_usernames():
    #        return True

    #    if name == 'request':
    #        return True
    #    elif name == 'unrequest':
    #        return True
    #    elif name == 'retire':
    #        return True

    #    return False

    def is_allowed_to_edit(self):
        if self.metadata.get_property('state') == 'private':
            return self.is_owner_or_admin()
        return self.is_admin()


    state_form__access__ = is_owner_or_admin
    edit_state__access__ = True 

    # define tabs
    view__access__ = is_allowed_to_view
    view__label__ = 'Preview'
    def view(self):
        context = get_context()
        root = context.root

        # body
        body = self.get_handler('.body').to_str()

        # logo
        logo = self.get_handler('.logo')
        p_logo = self.get_pathto(logo)

        # namespace
        namespace = {}
        namespace['name'] = self.title_or_name
        namespace['body'] = body
        namespace['logo'] = p_logo

        # Add the link if the advertisement is at least normal
       # status = self.get_property('abakuc:index_state')
       # if status in ['normal', 'advanced']:
       #     namespace['is_normal_or_advanced'] = True
       #     namespace['link'] = self.get_property('abakuc:link')

       #     owner = self.get_property('owner')
       #     user = root.get_handler('users/%s' % owner)
       #     namespace['street'] = user.get_property('branch:street')
       #     namespace['postal_code'] = user.get_property('branch:postal_code')
       #     namespace['city'] = user.get_property('branch:city')
       #     namespace['state'] = user.get_property('branch:state')
       #     #namespace['country'] = user.get_property('branch:country')
       #     namespace['phone'] = user.get_property('branch:phone')
       #     namespace['fax'] = user.get_property('branch:fax')
       # else:
       #     namespace['is_normal_or_advanced'] = False

        # picture
        picture1 = self.get_handler('.picture1')
        p_picture1 = self.get_pathto(picture1)
        namespace['picture1'] = p_picture1
        namespace['style'] = 'style1'

        style = self.metadata.get_property('abakuc:template_style')
        if style == 'style2':
            picture2 = self.get_handler('.picture2')
            p_picture2 = self.get_pathto(picture2)
            namespace['picture2'] = p_picture2
            
            picture3 = self.get_handler('.picture3')
            p_picture3 = self.get_pathto(picture3)
            namespace['picture3'] = p_picture3

            picture4 = self.get_handler('.picture4')
            p_picture4 = self.get_pathto(picture4)
            namespace['picture4'] = p_picture4
            namespace['style'] = None

        handler = self.get_handler('/ui/abakuc/advert_view.xml')
        return stl(handler, namespace)


    #enquiry_form__access__ = is_allowed_to_view
    enquiry_form__label__ = u'Enquiry'
    #def enquiry_form(self):
    #    context = get_context()
    #    root = context.root
    #    catalog = root.get_handler('.catalog')

    #    owner = self.metadata.get_property('owner')
    #    owner = catalog.search(format='user', name=owner).next()
    #    owner = root.get_handler(owner.abspath)
    #    email = owner.metadata.get_property('abakuc:email' or '')

    #    namespace = {}
    #    namespace['adv_email'] = email
    #    form = context.request.form
    #    for name in ['email', 'name', 'dtel', 'etel', 'address', 'enquiry']:
    #        namespace[name] = form.get(name) or ''

    #    handler = self.get_handler('/ui/abakuc/Advert_enquiry_form.xml')
    #    return stl(handler, namespace)


    #send_enquiry__access__ = is_allowed_to_view
    #def send_enquiry(self, adv_email, **kw):
    #    context = get_context()
    #    request, response = context.request, context.response

    #    # Load form values
    #    enquiry = Unicode.decode(kw['enquiry'].strip())
    #    name = Unicode.decode(kw['name'].strip())
    #    email = kw['email'].strip()
    #    dtel = Unicode.decode(kw['dtel'].strip())
    #    etel = Unicode.decode(kw['etel'].strip())
    #    address = Unicode.decode(kw['address'].strip())

    #    # Check input
    #    if not email or not enquiry:
    #        message = self.gettext(
    #            u'You have not filled the required fields, please try again')
    #        # XXX Fix this, pass the parameters back to the form
    #        comeback(message)
#   #                  name=name, enquiry=enquiry, dtel=dtel, etel=etel,
#   #                  address=address, email=email)
    #        return

    #    # Build the email message
    #    # The subject
    #    subject = self.gettext(u'[abakuc cities] New enquiry')
    #    # The body
    #    sender_info = [self.gettext(u'This enquiry comes from:\n\n')]
    #    for input in [('name', name), ('email', email), ('dtel', dtel),
    #                  ('etel', etel), ('address', address)]:
    #        sender_info.append(u'  %s: %s\n' % input)
    #    sender_info.append(u'\n')

    #    body = ''.join(sender_info)
    #    body += self.gettext(u'Enquiry:\n\n  %s') % enquiry
    #    body += '\n\n\n\n--\nabakuc cities: %s' % self.name

    #    # Send the email message
    #    root = context.root
    #    try:
    #        root.send_email("%s <%s>" % (kw['name'], kw['email']), adv_email,
    #                        subject, body)
    #    except:
    #        message = u'We failed to send your enquiry, please try again'
    #        message = self.gettext(message)
    #        comeback(message)
#   #                  name=kw['name'], enquiry=enquiry,
#   #                  dtel=kw['dtel'], etel=kw['etel'], address=kw['address'],
#   #                  email=kw['email'])
    #        return

    #    # Log the enquiry that has just been send
    #    enquiry_log = root.get_handler('.enquiry_log')
    #    enquiry_log.state.lines.append([unicode(datetime.datetime.now()),
    #                                   adv_email, body.replace('\n', ' ')])
    #    enquiry_log.set_changed()

    #    # Come back
    #    message = self.gettext(
    #        u'THANK YOU FOR YOUR ENQUIRY. This is now with the advertiser'
    #        u' concerned. They will be in touch with you.')
    #    if 'Adverts' in str(request.uri):
    #        comeback(message)
    #        return

    #    response.redirect(';view?message=%s' % message)


    def get_epoz_data(self):
        return self.get_handler('.body').get_body().get_content_as_html()


    edit_form__access__ = True 
    edit_form__label__ = u'Edit'
    def edit_form(self):
        """WYSIWYG editor for HTML documents."""
        # If the document has not a body (e.g. a frameset), edit as plain text
        handler = self.get_handler('.body')
        body = handler.get_body()

        if body is None:
            return Text.edit_form(handler)

        namespace = {}

        # Title and link
        namespace['title'] = self.metadata.get_property('dc:title')
        namespace['link'] = self.metadata.get_property('abakuc:link') or 'http://'
        
        # Edit with a rich text editor
        html = body.get_content_as_html()
        namespace['rte'] = self.get_rte('data', html)
        
        # logo
        logo = self.get_handler('.logo')
        p_logo = self.get_pathto(logo)
        namespace['logo'] = p_logo

        # template_style
        style = self.metadata.get_property('abakuc:template_style')
        namespace['template_style'] = [
            {'name': 'style1', 'exemple':'/ui/abakuc/images/style1.png',
             'checked': style=='style1'},
            {'name':' style2', 'exemple':'/ui/abakuc/images/style2.png',
             'checked': style=='style2'}]
        
        # picture*
        # blah
        picture1 = self.get_handler('.picture1')
        p_picture1 = self.get_pathto(picture1)
        namespace['picture1'] = p_picture1
        namespace['style'] = 'style1'
        namespace['p_title'] = 'Picture'
        
        if style == 'style2':
            picture2 = self.get_handler('.picture2')
            p_picture2 = self.get_pathto(picture2)
            namespace['picture2'] = p_picture2
            picture3 = self.get_handler('.picture3')
            p_picture3 = self.get_pathto(picture3)
            namespace['picture3'] = p_picture3
            picture4 = self.get_handler('.picture4')
            p_picture4 = self.get_pathto(picture4)
            namespace['picture4'] = p_picture4
            namespace['style'] = None
            namespace['p_title'] = 'Pictures'

        handler = self.get_handler('/ui/abakuc/advert_edit.xml')
        return stl(handler, namespace)



    edit__access__ = True 
    def edit(self, logo=None, picture1=None, **kw):
        # XXX This code is ugly. We must: (1) write our own XML parser, with
        # support for fragments, and (2) use the commented code.
        root = get_context().root
        
        body_handler = self.get_handler('.body')

        body_handler.set_changed()

        new_body = kw['data']
        # Epoz returns HTML, coerce to XHTML (by tidy)
        stdin, stdout, stderr = os.popen3('tidy -i -utf8 -asxhtml')
        stdin.write(new_body)
        stdin.close()
        new_body = stdout.read()
        # To unicode
        new_body = unicode(new_body, 'utf-8')
        # Get only the body
        expr = re.compile(u'<body>(.*)</body>', re.I + re.S)
        match = expr.search(new_body)
        new_body = match.group()
        # Replace by the new body
        data = body_handler.to_str()
        data = expr.sub(new_body, data).encode('utf8')

        resource = memory.File(data)
        handler = body_handler.__class__(resource)

        body_handler.state.root_element = handler.get_root_element()

        # set title and link
        language = 'en'
        self.set_property('dc:title', kw['dc:title'])
        if kw['abakuc:link'] != 'http://':
            self.set_property('abakuc:link', kw['abakuc:link'])

        # check choosen template_style and reindex the handler
        style = kw.get('style', '')
        if style:
            self.set_property('abakuc:template_style', style)

        root.reindex_handler(self)

        # Upload LOGO
        path = get_abspath(globals(), 'ui/abakuc/images/px.png')
        pix = get_resource(path)

        if kw.get('remove_logo'):
            self.upload_image('logo', pix)
        elif logo:
            self.upload_image('logo', logo)

        if kw.get('remove_p1'):
            self.upload_image('picture1', pix)
        elif picture1:
            self.upload_image('picture1', picture1)

        if kw.get('remove_p2'):
            self.upload_image('picture2', pix)
        elif kw.get('picture2'):
            self.upload_image('picture2', kw['picture2'])

        if kw.get('remove_p3'):
            self.upload_image('picture3', pix)
        elif kw.get('picture3'):
            self.upload_image('picture3', kw['picture3'])

        if kw.get('remove_p4'):
            self.upload_image('picture4', pix)
        elif kw.get('picture4'):
            self.upload_image('picture4', kw['picture4'])

        return context.come_back(u'Your advert has been edited.')


    # Upload for logo and pictures
    def upload_image(self, type, resource):
        handler_names = self.get_handler_names()

        # Check wether the handler is able to deal with the uploaded file
        input = self.get_handler('.%s' % type)
        try:
            input.load_state(resource)
            input.save_state()
        except:
            raise UserError, \
              ('Upload failed: either the file does not match this '  
              'document type (%s) or it contains errors.') \
              % self.get_mimetype() 



    ########################################################################
    # Metadata
    #edit_metadata_form__access__ = is_allowed_to_edit
    edit_metadata_form__label__ = u'Properties'
    def edit_metadata_form(self):
        context = get_context()
        root = context.root
        catalog = root.get_handler('.catalog')
        
        # Build the namespace
        namespace = {}

        get_property = self.metadata.get_property
        namespace['title'] = get_property('dc:title')
        namespace['description'] = get_property('dc:description')

        # users
        namespace['admin'] = context.user.is_admin()
        if namespace['admin']:
            users = []
            users_list = catalog.search(format='user')
            for user in users_list:
                users.append({'name': user.name, 
                          'is_selected': user.name==self.get_property('owner')})
            namespace['users'] = users 
            
            # index state
            index_state = self.get_property('abakuc:index_state')
            index = [{'name':'basic', 'is_selected':index_state=='basic'}, 
                     {'name':'normal', 'is_selected':index_state=='normal'}, 
                     {'name':'advanced', 'is_selected':index_state=='advanced'}]
            namespace['index_state'] = index 

        # Topics
        #topics = self.get_property('abakuc:topics') or ()

        #ns = []
        #for h in catalog.search(format='topics', workflow_state='public'):
        #    title = h.title_or_name
        #    ns.append((title, {'name':h.name, 'title':title,
        #                       'checked':h.name in topics}))
        #ns.sort()
        #ns = [t[-1] for t in ns]

        #namespace['topics'] = ns
          
        # cities
        all_cities = [h for h in catalog.search(format='City')]
        cities = self.get_property('city') or ()

        ns = []
        for dest in all_cities:
            title = dest.title_or_name
            ns.append((title, {'name':dest.name, 'title':title,
                               'checked':dest.name in city}))
        ns.sort()
        ns = [t[-1] for t in ns]

        namespace['city'] = ns
          
        handler = self.get_handler('/ui/abakuc/advert_metadata.xml')
        return stl(handler, namespace)


    #edit_metadata__access__ = is_allowed_to_edit
    def edit_metadata(self, **kw):
        context = get_context()
        root = context.root
        catalog = root.get_handler('.catalog')

        self.set_property('dc:title', kw['dc:title'])
        self.set_property('dc:description', kw['dc:description'])

        if context.user.is_admin():
            self.set_property('owner', kw['owner'])
            self.set_property('abakuc:index_state', kw['index_state'])

        # Update topics
        #topics, selected_topics = [], []

        #if 'topics' in kw.keys():
        #    topics = kw['topics']

        #    for h in catalog.search(format='topics'):
        #        if h.name in topics:
        #            selected_topics.append(h.name)
        #            
        #self.set_property('abakuc:topics', tuple(selected_topics))

        # Update cities
        city, selected_city = [], []

        if 'dest' in kw.keys():
            city = kw['city']
            all_cities = [h for h in catalog.search(format='City')]
            for dest in all_cities:
                if dest.name in city:
                    selected_city.append(dest.name)
        self.set_property('abakuc:City', tuple(selected_city))

        # Reindex
        root.reindex_handler(self)

        return context.come_back('Properties changed.')


    def get_views(self):
        return ['edit_metadata_form', 'edit_form', 'view']


    ########################################################################
    # Indexing
    ########################################################################
    def get_catalog_indexes(self):
        indexes = ikaaroFolder.get_catalog_indexes(self)

        get_property = self.metadata.get_property
        #indexes['city'] = list(get_property('city'))
        #indexes['topics'] = list(get_property('abakuc:topics'))
        #indexes['index_state'] = get_property('abakuc:index_state')
        #indexes['template_style'] = get_property('abakuc:template_style')

        return indexes


    # XXX Maybe removed
    def get_cities(self):
        return list(self.metadata.get_property('abakuc:city'))

    city = property(get_cities, None, None, '')


    # XXX Maybe removed
    #def get_topics(self):
    #    return list(self.metadata.get_property('abakuc:topics'))

    #topics = property(get_topics, None, None, '')

register_object_class(Advert)

