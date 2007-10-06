# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime, date
from string import Template
import mimetypes

# Import from itools
from itools.datatypes import Email, Integer, String, Unicode
from itools.i18n.locale_ import format_datetime
from itools.catalog import EqQuery, AndQuery, RangeQuery
from itools.stl import stl
from itools.web import get_context
from itools.xml import get_element
from itools.xhtml import Document as XHTMLDocument
from itools.cms.website import WebSite
from itools.cms.access import AccessControl, RoleAware
from itools.cms.binary import Image
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.utils import generate_password
from itools.cms.tracker import Tracker
from itools.cms.widgets import table, batch
from itools.cms.catalog import schedule_to_reindex
from itools.cms.utils import reduce_string
from itools.cms.workflow import WorkflowAware

# Import from abakuc
from base import Handler, Folder
from handlers import EnquiriesLog, EnquiryType

class Training(RoleAware, WorkflowAware, WebSite):

    class_id = 'training'
    class_title = u'Training programme'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    class_views = [['view'], 
                   ['browse_content?mode=list',
                    'browse_content?mode=thumbnails'],
                   ['new_resource_form'],
                   ['state_form'],
                   ['permissions_form', 'new_user_form'],
                   ['edit_metadata_form']]

    site_format = 'module'

    def get_level1_title(self, level1):
        return None

    def get_document_types(self):
        return [Module]

    #######################################################################
    # ACL
    #######################################################################

    #######################################################################
    # Security / Access Control
    #######################################################################
    #def is_allowed_to_edit(self, user, object):
    #    for address in self.search_handlers(handler_class=Address):
    #        if address.is_allowed_to_edit(user, address):
    #            return True
    #    return False

    #def is_reviewer(self, user, object):
    #    for address in self.search_handlers(handler_class=Address):
    #        if address.is_reviewer(user, address):
    #            return True
    #    return False


    ####################################################################
    # Users - list all participant of the training programme
    get_members_namespace__access__ = 'is_allowed_to_edit'
    get_members_namespace__label__ = u'Users'
    def get_members_namespace(self, context):
        """
        Returns a namespace (list of dictionaries) to be used 
        in the branch view list.
        """
        # This works, but returns only the user's id
        # and also don't know how to break it down
        # into individual branches.
        addresses = self.search_handlers(handler_class=Address)
        members = []
        for address in addresses:
            branch_members = address.get_members()
            for username in branch_members:
                url = '/users/%s/;profile' % username 
                members.append({'id': username,
                                'url': url})
        # List users 

        return members

    #######################################################################
    # User Interface
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return 'bobo'

#######################################################################
# Training module 
#######################################################################

class Module(Folder):

    class_id = 'module'
    class_title = u'Trainig module'
    class_icon16 = 'abakuc/images/AddressBook16.png'
    class_icon48 = 'abakuc/images/AddressBook48.png'

    new_resource_form__access__ = 'is_allowed_to_edit'
    new_resource__access__ = 'is_allowed_to_edit'

    def get_document_types(self):
        return [Topic, Folder]

    #######################################################################
    # User Interface / View
    #######################################################################
    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['description'] = self.get_property('dc:description')
        namespace['modules'] = self.view_modules(context)

        handler = self.get_handler('/ui/abakuc/training_view.xml')
        return stl(handler, namespace)


    ####################################################################
    # View training modules 
    view_modules__label__ = u'Training modules'
    view_modules__access__ = True
    def view_modules(self, context):
        namespace = {}
        modules = self.search_handlers(handler_class=Module)
        namespace['modules'] = []
        for module in modules:
            url = '%s/;view' %  module.name
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            namespace['modules'].append({'url': url,
                      'description': description,
                      'title': module.title_or_name})

        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 5
        batch_total = len(items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        items = items[batch_start:batch_fin]
        # Namespace 
        if items:
            msgs = (u'There is one module.',
                    u'There are ${n} modules.')
            batch = batch(context.uri, batch_start, batch_size, 
                          batch_total, msgs=msgs)
            msg = None
        else:
            batch = None
            msg = u'Currently there no published training modules.'
        
        namespace['batch'] = news_batch
        namespace['msg'] = msg 
        namespace['items'] = items

        handler = self.get_handler('/ui/abakuc/training_modules_view.xml')
        return stl(handler, namespace)

    #######################################################################
    # User Interface / Edit
    #######################################################################
    edit_metadata_form__access__ = 'is_reviewer'
    def edit_metadata_form(self, context):
        namespace = {}
        namespace['referrer'] = None
        if context.get_form_value('referrer'):
            namespace['referrer'] = str(context.request.referrer)
        # Form
        title = self.get_property('dc:title')
        # Description
        description = self.get_property('dc:description')

        handler = self.get_handler('/ui/abakuc/training_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        title = context.get_form_value('dc:title')
        description = context.get_form_value('dc:description')

        self.set_property('dc:title', title, language='en')
        self.set_property('dc:description', description, language='en')

        message = u'Changes Saved.'
        goto = context.get_form_value('referrer') or None
        return context.come_back(message, goto=goto)


#######################################################################
# Training topic 
#######################################################################
class Topic(Folder):

    class_id = 'topic'
    class_title = u'Module topic'
    class_icon16 = 'abakuc/images/Employees16.png'
    class_icon48 = 'abakuc/images/Employees48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['permissions_form', 'new_user_form']]

    def get_document_types(self):
        return [News, Job]

    #######################################################################
    # User Interface / View
    #######################################################################
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
        for address in self.parent.search_handlers(handler_class=Address):
            company = address.parent
            current_address = self.get_property('abakuc:address')
            url = '/companies/%s/%s/;view' % (company.name, address.name)
            addresses.append({
                'name': address.name,
                'is_current': address.name == current_address,
                'url': url,
                'address': address.get_property('abakuc:address'),
                'phone': address.get_property('abakuc:phone'),
                'fax': address.get_property('abakuc:fax')})
        namespace['addresses'] = addresses

        ################ 
        # Branch Members
        namespace['users'] = self.get_members_namespace(address)

        ######## 
        # Jobs
        namespace['batch'] = ''
        # Construct the lines of the table
        root = context.root
        catalog = context.server.catalog
        query = []
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(EqQuery('format', 'Job'))
        query.append(EqQuery('company', self.parent.name))
        query.append(EqQuery('address', self.name))
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        jobs = []
        for job in list(documents):
            job = root.get_handler(job.abspath)
            get = job.get_property
            # Information about the job
            company = address.parent
            address = job.parent
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 job.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=90,
                                        phrase_treshold=240)
            jobs.append({'url': url,
                         'title': job.title,
                         'function': JobTitle.get_value(get('abakuc:function')),
                         'salary': SalaryRange.get_value(get('abakuc:salary')),
                         'county': county,
                         'region': region,
                         'closing_date': get('abakuc:closing_date'),
                         'description': description})
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 2 
        batch_total = len(jobs)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        jobs = jobs[batch_start:batch_fin]
        # Namespace 
        if jobs:
            job_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, 
                              msgs=(u"There is 1 job announcement.",
                                    u"There are ${n} job announcements."))
            msg = None
        else:
            job_batch = None
            msg = u"Appologies, currently we don't have any job announcements"
        # Namespace 
        namespace['job_batch'] = job_batch 
        namespace['msg'] = msg 
        namespace['jobs'] = jobs
        ######## 
        # News 
        namespace['batch'] = ''
        # Construct the lines of the table
        root = context.root
        catalog = context.server.catalog
        query = []
        today = (date.today()).strftime('%Y-%m-%d')
        query.append(EqQuery('format', 'news'))
        query.append(EqQuery('company', self.parent.name))
        query.append(EqQuery('address', self.name))
        query.append(RangeQuery('closing_date', today, None))
        query = AndQuery(*query)
        results = catalog.search(query)
        documents = results.get_documents()
        news_items = []
        for news in list(documents):
            news = root.get_handler(news.abspath)
            get = news.get_property
            # Information about the news
            address = news.parent
            company = address.parent
            url = '/companies/%s/%s/%s/;view' % (company.name, address.name,
                                                 news.name)
            description = reduce_string(get('dc:description'),
                                        word_treshold=10,
                                        phrase_treshold=60)
            news_items.append({'url': url,
                               'title': news.title,
                               'closing_date': get('abakuc:closing_date'),
                               'description': description})
        # Set batch informations
        batch_start = int(context.get_form_value('batchstart', default=0))
        batch_size = 2 
        batch_total = len(news_items)
        batch_fin = batch_start + batch_size
        if batch_fin > batch_total:
            batch_fin = batch_total
        news_items = news_items[batch_start:batch_fin]
        # Namespace 
        if news_items:
            news_batch = batch(context.uri, batch_start, batch_size,
                              batch_total, 
                              msgs=(u"There is 1 news item.",
                                    u"There are ${n} news items."))
            msg = None
        else:
            news_batch = None
            msg = u"Currently there is no news."
        # Namespace 
        namespace['news_batch'] = news_batch
        namespace['news_msg'] = msg 
        namespace['news_items'] = news_items
        handler = self.get_handler('/ui/abakuc/address_view.xml')
        return stl(handler, namespace)


    #######################################################################
    # User Interface / Edit
    #######################################################################
    @staticmethod
    def get_form(address=None, postcode=None, town=None, phone=None, fax=None,
                 address_country=None, address_region=None,
                 address_county=None):
        context = get_context()
        root = context.root
        # List authorized countries
        countries = [
            {'name': x, 'title': x, 'selected': x == address_country}
            for x, y in root.get_authorized_countries(context) ]
        nb_countries = len(countries)
        if nb_countries < 1:
            raise ValueError, 'Number of countries is invalid'

        # Show a list with all authorized countries
        countries.sort(key=lambda x: x['title'])
        regions = root.get_regions_stl(country=address_country,
                                       selected_region=address_region)
        county = root.get_counties_stl(region=address_region,
                                       selected_county=address_county)
        namespace = {}
        namespace['address'] = address
        namespace['postcode'] = postcode
        namespace['town'] = town 
        namespace['phone'] = phone
        namespace['fax'] = fax
        namespace['countries'] = countries
        namespace['regions'] = regions
        namespace['counties'] = county
        handler = root.get_handler('ui/abakuc/address_form.xml')
        return stl(handler, namespace)


    edit_metadata_form__access__ = 'is_reviewer'
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
        # Get the country,  the region and  the county
        from root import world
        address_county = self.get_property('abakuc:county')
        if address_county is None:
            address_country = None
            address_region = None
        else:
            rows = world.get_row(address_county)
            address_country = rows.get_value('country')
            address_region = rows.get_value('region')
        namespace['form'] = self.get_form(address, postcode, town, phone, fax,
                                          address_country, address_region,
                                          address_county)

        handler = self.get_handler('/ui/abakuc/address_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_reviewer'
    def edit_metadata(self, context):
        # Add Address
        address = context.get_form_value('abakuc:address')
        if not address:
            message = u'Please give an Address'
            return context.come_back(message)

        if not context.get_form_value('abakuc:county'):
            message = u'Please choose a county'
            return context.come_back(message)

        # Link the User to the Address
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
            catalog = context.server.catalog
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
            else:
                user_id = results.get_documents()[0].name
                user = users.get_handler(user_id)
                if user.has_property('ikaaro:user_must_confirm'):
                    confirm = user.get_property('ikaaro:user_must_confirm')
        user_id = str(user.name)

        # Save the enquiry
        if context.user is None:
            phone = context.get_form_value('abakuc:phone') 
        else:
            phone = context.user.get_property('abakuc:phone') or ''
        enquiry_type = context.get_form_value('abakuc:enquiry_type')
        enquiry_subject = context.get_form_value('abakuc:enquiry_subject')
        enquiry = context.get_form_value('abakuc:enquiry')
        row = [datetime.now(), user_id, phone, enquiry_type, enquiry_subject,
               enquiry, False]
        handler = self.get_handler('log_enquiry.csv')
        handler.add_row(row)

        # Authenticated user, we are done
        if confirm is None:
            self.enquiry_send_email(user, rows=[row])
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

    
    def enquiry_send_email(self, user, rows=None):
        # TODO, The actual system allow to send enquiries
        # to other companies before confirm registration
        # This enquiries are not send
        root = self.get_root()
        users = root.get_handler('users')

        firstname = user.get_property('ikaaro:firstname')
        lastname = user.get_property('ikaaro:lastname')
        email = user.get_property('ikaaro:email')
        to_addrs = [ users.get_handler(x).get_property('ikaaro:email')
                     for x in self.get_members() ]
        # FIXME UK Travel is hardcoded
        subject_template = u'[UK Travel] New Enquiry (%s)'
        body_template = ('Subject : %s\n'
                         'From : %s %s\n'
                         'Phone: %s\n'
                         '\n'
                         '%s')
        if not to_addrs:
            # No members, send to the administrator
            to_addrs.append(root.contact_email)
            company = self.parent.name
            subject_template = '%s - %s (%s)' % (subject_template,
                                                 company, self.name)

        if rows is None:
            csv = self.get_handler('log_enquiry.csv')
            results = csv.search(user_id=user.name)
            rows = []
            for line in results:
                print line
                rows.append(csv.get_row(line))

        for row in rows:
            kk, kk, phone, enquiry_type, enquiry_subject, enquiry, kk = row
            subject = subject_template % enquiry_type
            body = body_template % (enquiry_subject ,firstname, lastname,
                                    phone, enquiry)
            for to_addr in to_addrs:
                root.send_email(email, to_addr, subject, body)

    #######################################################################
    # User Interface / View Enquiries
    #######################################################################
    view_enquiries__access__ = 'is_reviewer_or_member'
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
            if user.get_property('ikaaro:user_must_confirm') is None:
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

    
    view_enquiry__access__ = 'is_reviewer_or_member'
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

    
    
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_reviewer_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return (self.has_user_role(user.name, 'ikaaro:reviewers') or
                self.has_user_role(user.name, 'ikaaro:members'))
    

    def is_admin(self, user, object):
        return self.is_reviewer(user, object)


    def is_reviewer(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        return self.has_user_role(user.name, 'ikaaro:reviewers') 


register_object_class(Companies)
register_object_class(Company)
register_object_class(Address)
