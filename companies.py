# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime
from string import Template

# Import from itools
from itools.datatypes import Email, Integer, String, Unicode
from itools.i18n.locale_ import format_datetime
from itools.stl import stl
from itools.web import get_context
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class
from itools.cms.utils import generate_password
from itools.cms.tracker import Tracker

# Import from abakuc
from base import Handler, Folder
from handlers import EnquiriesLog, EnquiryType
from website import WebSite


class Companies(Folder):

    class_id = 'companies'
    class_title = u'Companies Directory'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    def get_document_types(self):
        return [Company]

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return 'bobo'



class Company(AccessControl, Folder):

    class_id = 'company'
    class_title = u'Company'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'


    def get_document_types(self):
        return [Address]


    #######################################################################
    # API
    #######################################################################
    def get_website(self):
        website = self.get_property('abakuc:website')
        if website.startswith('http://'):
            return website
        return 'http://' + website

    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_allowed_to_edit(self, user, object):
        for address in self.search_handlers(handler_class=Address):
            if address.is_allowed_to_edit(user, address):
                return True
        return False


    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['website'] = self.get_website()
        namespace['logo'] = self.has_handler('logo')

        addresses = []
        for address in self.search_handlers():
            addresses.append({
                'name': address.name,
                'address': address.get_property('abakuc:address')})
        namespace['addresses'] = addresses
 
        handler = self.get_handler('/ui/abakuc/company_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(name=None, website=None, topics=None, types=None, logo=None):
        root = get_context().root

        namespace = {}
        namespace['title'] = name
        namespace['website'] = website
        namespace['topics'] = root.get_topics_namespace(topics)
        namespace['types'] = root.get_types_namespace(types)
        namespace['logo'] = logo

        handler = root.get_handler('ui/abakuc/company_form.xml')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        title = self.get_property('dc:title')
        website = self.get_property('abakuc:website')
        topics = self.get_property('abakuc:topic')
        types = self.get_property('abakuc:type')
        logo = self.has_handler('logo')
        namespace['form'] = self.get_form(title, website, topics, types, logo)

        handler = self.get_handler('/ui/abakuc/company_edit_metadata.xml')
        return stl(handler, namespace)


    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        website = context.get_form_value('abakuc:website')
        topics = context.get_form_values('topic')
        types = context.get_form_values('type')
        logo = context.get_form_value('logo')

        self.set_property('dc:title', title, language='en')
        self.set_property('abakuc:website', website)
        self.set_property('abakuc:topic', tuple(topics))
        self.set_property('abakuc:type', types)

        # The logo
        if context.has_form_value('remove_logo'):
            if self.has_handler('logo'):
                self.del_handler('logo')
        elif logo is not None:
            filename, mimetype, data = logo
            if self.has_handler('logo'):
                logo = self.get_handler('logo')
                try:
                    logo.load_state_from_string(data)
                except:
                    self.load_state()
            else:
                logo = Image()
                try:
                    logo.load_state_from_string(data)
                except:
                    pass
                else:
                    logo = self.set_handler('logo', logo)
                    logo.set_property('state', 'public')

        # Reindex
        root = context.root
        for address in self.search_handlers(format='address'):
            root.reindex_handler(address)

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)



class Address(RoleAware, Folder):

    class_id = 'address'
    class_title = u'Address'
    class_icon16 = 'abakuc/images/Employees16.png'
    class_icon48 = 'abakuc/images/Employees48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form', 'new_user_form']]

    __fixed_handlers__ = ['log_enquiry.csv']


    def new(self, **kw):
        Folder.new(self, **kw)
        handler = EnquiriesLog()
        cache = self.cache
        cache['log_enquiry.csv'] = handler
        cache['log_enquiry.csv.metadata'] = self.build_metadata(handler)


    def get_document_types(self):
        return []


    def get_catalog_indexes(self):
        from root import world

        indexes = Folder.get_catalog_indexes(self)
        company = self.parent
        indexes['level1'] = list(company.get_property('abakuc:topic'))
        county_id = self.get_property('abakuc:county')
        if county_id:
            row = world.get_row(county_id)
            indexes['level2'] = row[7]
            indexes['level3'] = str(county_id)
        indexes['level4'] = self.get_property('abakuc:town')
        indexes['title'] = company.get_property('dc:title')
        return indexes


    #######################################################################
    # API
    #######################################################################
    def get_title(self):
        address = self.get_property('abakuc:address')
        return address or self.name


    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'Address'
    view__access__ = True
    def view(self, context):
        from root import world

        county_id = self.get_property('abakuc:county')
        if county_id is None:
            # XXX Every address should have a county
            country = region = county = '-'
        else:
            row = world.get_row(county_id)
            country = row[6]
            region = row[7]
            county = row[8]

        namespace = {}
        namespace['company'] = self.parent.get_property('dc:title')
        namespace['logo'] = self.parent.has_handler('logo')
        namespace['address'] = self.get_property('abakuc:address')
        namespace['town'] = self.get_property('abakuc:town')
        namespace['postcode'] = self.get_property('abakuc:postcode')
        namespace['phone'] = self.get_property('abakuc:phone')
        namespace['fax'] = self.get_property('abakuc:fax')
        namespace['country'] = country
        namespace['region'] = region
        namespace['county'] = county
        
        addresses = []
        for address in self.parent.search_handlers():
            addresses.append({
                'name': address.name,
                'address': address.get_property('abakuc:address')})
        namespace['addresses'] = addresses
 

        handler = self.get_handler('/ui/abakuc/address_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 address_county=None):
        from root import world
        root = get_context().root
        
        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town 
        namespace['phone'] = phone
        namespace['fax'] = fax
        
        rows = world.get_rows()
        
        countries = {}
        regions = {}
        for index, row in enumerate(rows):
            country = row[6]
            region = row[7]
            county = row[8]
            is_selected = (index == address_county)
            id = str(index)

            # Add the country if not yet added
            if country in countries:
                country_ns = countries[country]
            else:
                country_ns = {'id': index, 'title': country,
                              'is_selected': False, 'display': 'none',
                              'regions': []}
                countries[country] = country_ns

            # Add the region if not yet added
            if region in regions:
                region_ns = regions[region]
            else:
                region_ns = {'id': index, 'title': region,
                              'is_selected': False, 'display': 'none',
                              'counties': []}
                regions[region] = region_ns
                # Add to the country
                country_ns['regions'].append(
                    {'id': id, 'title': region, 'is_selected': False})

            region_ns['counties'].append({'id': id, 'title': county,
                                          'is_selected': is_selected})

            # If this county is selected, activate the right blocks
            if is_selected:
                country_ns['is_selected'] = True
                country_ns['display'] = 'inherit'
                region_ns['is_selected'] = True
                region_ns['display'] = 'inherit'
                for x in country_ns['regions']:
                    if x['title'] == region:
                        x['is_selected'] = True
                        break

        countries = countries.values()
        countries.sort(key=lambda x: x['title'])
        namespace['countries'] = countries

        regions = regions.values()
        regions.sort(key=lambda x: x['title'])
        namespace['regions'] = regions

        handler = root.get_handler('ui/abakuc/address_form.xml.en')
        return stl(handler, namespace)


    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        address = self.get_property('abakuc:address')
        postcode = self.get_property('abakuc:postcode')
        town = self.get_property('abakuc:town')
        phone = self.get_property('abakuc:phone')
        fax = self.get_property('abakuc:fax')
        address_county = self.get_property('abakuc:county')
        namespace['form'] = self.get_form(address, postcode, town, phone, fax,
                                          address_county)

        handler = self.get_handler('/ui/abakuc/address_edit_metadata.xml')
        return stl(handler, namespace)


    def edit_metadata(self, context):
        keys = ['address', 'postcode', 'town', 'phone', 'fax', 'county']

        for key in keys:
            key = 'abakuc:%s' % key
            value = context.get_form_value(key)
            self.set_property(key, value)

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


    #######################################################################
    # User Interface / Submit Enquiry
    #######################################################################
    enquiry_fields = [
        ('abakuc:enquiry_subject', True),
        ('abakuc:enquiry', True),
        ('abakuc:enquiry_type', True),
        ('ikaaro:firstname', True),
        ('ikaaro:lastname', True),
        ('ikaaro:email', True),
        ('abakuc:phone', False)]


    enquiry_fields_auth = [
        ('abakuc:enquiry_subject', True),
        ('abakuc:enquiry', True),
        ('abakuc:enquiry_type', True),
        ('abakuc:phone', False)]


    enquiry_form__access__ = True
    def enquiry_form(self, context):
        if context.user is None:
            namespace = context.build_form_namespace(self.enquiry_fields)
            namespace['is_authenticated'] = False
        else:
            namespace = context.build_form_namespace(self.enquiry_fields_auth)
            namespace['is_authenticated'] = True
        enquiry_type = context.get_form_value('abakuc:enquiry_type')
        namespace['enquiry_type'] = EnquiryType.get_namespace(enquiry_type)
        namespace['company'] = self.parent.get_property('dc:title')

        handler = self.get_handler('/ui/abakuc/enquiry_edit_metadata.xml')
        return stl(handler, namespace)


    enquiry__access__ = True
    def enquiry(self, context):
        root = context.root
        user = context.user

        # Check input data
        if user is None:
            enquiry_fields = self.enquiry_fields
        else:
            enquiry_fields = self.enquiry_fields_auth
        keep = [ x for x, y in enquiry_fields ]
        error = context.check_form_input(enquiry_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Create the user
        confirm = None
        if user is None:
            users = root.get_handler('users')
            email = context.get_form_value('ikaaro:email')
            # Check the user is not already there
            catalog = root.get_handler('.catalog')
            results = catalog.search(username=email)
            print email, results.get_n_documents()
            if results.get_n_documents() == 0:
                firstname = context.get_form_value('ikaaro:firstname')
                lastname = context.get_form_value('ikaaro:lastname')
                user = users.set_user(email)
                user.set_property('ikaaro:firstname', firstname)
                user.set_property('ikaaro:lastname', lastname)
                confirm = generate_password(30)
                user.set_property('ikaaro:user_must_confirm', confirm)
                root.reindex_handler(user)
            else:
                user_id = results.get_documents()[0].name
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm'):
                    confirm = user.get_property('ikaaro:user_must_confirm')
        user_id = str(user.name)

        # Save the enquiry
        phone = context.get_form_value('abakuc:phone')
        enquiry_type = context.get_form_value('abakuc:enquiry_type')
        enquiry_subject = context.get_form_value('abakuc:enquiry_subject')
        enquiry = context.get_form_value('abakuc:enquiry')
        row = [datetime.now(), user_id, phone, enquiry_type, enquiry_subject,
               enquiry, False]
        handler = self.get_handler('log_enquiry.csv')
        handler.add_row(row)

        # Authenticated user, we are done
        if confirm is None:
            self.enquiry_send_email(user)
            message = u'Enquiry sent'
            return message.encode('utf-8')

        # Send confirmation email
        hostname = context.uri.authority.host
        from_addr = 'enquiries@uktravellist.info'
        subject = u"[%s] Register confirmation required" % hostname
        subject = self.gettext(subject)
        body = self.gettext(
            u"This email has been generated in response to your"
            u" enquiry on the UK Travel List.\n"
            u"To submit your enquiry, click the link:\n"
            u"\n"
            u"  $confirm_url"
            u"\n"
            u"If the text is on two lines, please copy and "
            u"paste the full line into your browser URL bar."
            u"\n"
            u"Thank you for visiting the UK Travel List website."
            u"\n"
            u"UK Travel List Team")
        url = ';enquiry_confirm_form?user=%s&key=%s' % (user_id, confirm)
        url = context.uri.resolve(url)
        body = Template(body).substitute({'confirm_url': str(url)})
        root.send_email(from_addr, email, subject, body)

        # Back
        company = self.parent.get_property('dc:title')
        message = (
            u"Your enquiry to <strong>%s</strong> needs to be validated."
            u"<p>An email has been sent to <strong><em>%s</em></strong>,"
            u" to finish the enquiry process, please follow the instructions"
            u" detailed within it.</p>"
            u"<p>If you don not receive the email, please check your SPAM"
            u' folder settings or <a href="/;contact_form">contact us.</a></p>'
            % (company, email))
        return message.encode('utf-8')


    enquiry_confirm_form__access__ = True
    def enquiry_confirm_form(self, context):
        root = context.root

        user_id = context.get_form_value('user')
        users = root.get_handler('users')
        user = users.get_handler(user_id)

        # Check register key
        must_confirm = user.get_property('ikaaro:user_must_confirm')
        if (must_confirm is None
            or context.get_form_value('key') != must_confirm):
            return self.gettext(u"Bad key.").encode('utf-8')

        namespace = {}
        namespace['user_id'] = user_id
        namespace['key'] = must_confirm

        handler = self.get_handler('/ui/abakuc/address_enquiry_confirm.xml')
        return stl(handler, namespace)


    enquiry_confirm__access__ = True
    def enquiry_confirm(self, context):
        keep = ['key']
        register_fields = [('newpass', True),
                           ('newpass2', True)]

        # Check register key
        user_id = context.get_form_value('user')
        root = context.root
        users = root.get_handler('users')
        user = users.get_handler(user_id)
        must_confirm = user.get_property('ikaaro:user_must_confirm')
        if context.get_form_value('key') != must_confirm:
            return self.gettext(u"Bad key.").encode('utf-8')

        # Check input data
        error = context.check_form_input(register_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Check passwords
        password = context.get_form_value('newpass')
        password2 = context.get_form_value('newpass2')
        if password != password2:
            message = u'The passwords do not match.'
            return context.come_back(message, keep=keep)

        # Set user
        user.set_password(password)
        user.del_property('ikaaro:user_must_confirm')

        # Set cookie
        user.set_auth_cookie(context, password)

        # Send email
        self.enquiry_send_email(user)

        # Back
        #goto = "./;%s" % self.get_firstview()
        #return context.come_back(message, goto=goto)
        message = (u"Thank you, your enquiry to has been submitted.<br/>" 
                   u"If you like to login, please choose your password")
        return message.encode('utf-8')


    def enquiry_send_email(self, user):
        root = self.get_root()
        users = root.get_handler('users')

        firstname = user.get_property('ikaaro:firstname')
        lastname = user.get_property('ikaaro:lastname')
        email = user.get_property('ikaaro:email')
        to_addrs = [ users.get_handler(x).get_property('ikaaro:email')
                     for x in self.get_members() ]
        # FIXME UK Travel is hardcoded
        subject_template = u'[UK Travel] New Enquiry (%s)'
        body_template = ('From : %s %s\n'
                         'Phone: %s\n'
                         '\n'
                         '%s')
        csv = self.get_handler('log_enquiry.csv')
        for row in csv.search(user_id=user.name):
            kk, kk, phone, enquiry_type, enquiry_subject, enquiry, kk = csv.get_row(row)
            subject = subject_template % enquiry_type
            body = body_template % (firstname, lastname, phone, enquiry)
            for to_addr in to_addrs:
                root.send_email(email, to_addr, subject, body)


    #######################################################################
    # User Interface / View Enquiries
    #######################################################################
    view_enquiries__access__ = 'is_allowed_to_view'
    def view_enquiries(self, context):
        root = context.root
        users = root.get_handler('users')

        namespace = {}
        csv = self.get_handler('log_enquiry.csv')
        enquiries = []
        for row in csv.get_rows():
            date, user_id, phone, type, enquiry_subject, enquiry, resolved = row
            if resolved:
                continue
            user = users.get_handler(user_id)
            enquiries.append({
                'index': row.number,
                'date': format_datetime(date),
                'firstname': user.get_property('ikaaro:firstname'),
                'lastname': user.get_property('ikaaro:lastname'),
                'email': user.get_property('ikaaro:email'),
                'enquiry_subject': enquiry_subject,
                'phone': phone,
                'type': EnquiryType.get_value(type)})
        enquiries.reverse()
        namespace['enquiries'] = enquiries

        handler = self.get_handler('/ui/abakuc/address_view_enquiries.xml')
        return stl(handler, namespace)

    
    view_enquiry__access__ = 'is_allowed_to_view'
    def view_enquiry(self, context):
        index = context.get_form_value('index', type=Integer)

        row = self.get_handler('log_enquiry.csv').get_row(index)
        date, user_id, phone, type, enquiry_subject, enquiry, resolved = row

        root = context.root
        user = root.get_handler('users/%s' % user_id)

        namespace = {}
        namespace['date'] = format_datetime(date)
        namespace['enquiry_subject'] = enquiry_subject 
        namespace['enquiry'] = enquiry 
        namespace['type'] = type
        namespace['firstname'] = user.get_property('ikaaro:firstname')
        namespace['lastname'] = user.get_property('ikaaro:lastname')
        namespace['email'] = user.get_property('ikaaro:email')
        namespace['phone'] = phone

        handler = root.get_handler('ui/abakuc/address_view_enquiry.xml')
        return stl(handler, namespace)



register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
