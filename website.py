# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
import datetime

# Import from itools
from itools.datatypes import Integer, Unicode
from itools.stl import stl
from itools.cms import widgets
from itools.cms.access import RoleAware
from itools.cms.utils import generate_password
from itools.cms.website import WebSite as BaseWebSite
from itools.web import get_context
from itools.cms.catalog import schedule_to_reindex
from itools.uri import Path, get_reference

# Import from abakuc
from base import Handler

class SiteRoot(Handler, BaseWebSite):
    __roles__ = RoleAware.__roles__ + [
        {'name': 'abakuc:training_manager', 'title': u"Training Manager",
         'unit': u"Training Manager"},
        {'name': 'abakuc:branch_manager', 'title': u"Branch Manager",
         'unit': u"Branch Manager"},
        {'name': 'abakuc:branch_member', 'title': u"Branch Member",
         'unit': u"Branch Member"},
        {'name': 'abakuc:partner', 'title': u"Partner",
         'unit': u"Partner"},
        {'name': 'abakuc:guest', 'title': u"Guest",
         'unit': u"Guest"},
    ]
    ########################################################################
    # Logout
    logout__access__ = True
    def logout(self, context):
        """Logs out of the application."""
        # Remove the cookie
        context.del_cookie('__ac')
        # XXX review the cookies names
        context.del_cookie('user_profile_cookie')
        context.del_cookie('address_cookie')
        context.del_cookie('profile_cookie')
        context.del_cookie('company_cookie')
        context.del_cookie('media_tabs_cookie')
        context.del_cookie('product_cookie')

        # Remove the user from the context
        context.user = None
        # Say goodbye
        handler = self.get_handler('/ui/abakuc/logout.xml')
        return stl(handler)

    ########################################################################
    # Login
    login_form__access__ = True
    login_form__label__ = u'Login'
    def login_form(self, context):
        namespace = {}
        here = context.handler
        site_root = here.get_site_root()
        namespace['action'] = '%s/;login' % here.get_pathto(site_root)
        namespace['username'] = context.get_form_value('username')

        handler = self.get_handler('/ui/abakuc/login.xml')
        return stl(handler, namespace)


    login__access__ = True
    def login(self, context, goto=None):
        email = context.get_form_value('username', type=Unicode)
        password = context.get_form_value('password')

        # Don't send back the password
        keep = ['username']

        # Check the email field has been filed
        email = email.strip()
        if not email:
            message = u'Type your email please.'
            return context.come_back(message, keep=keep)

        # Check the user exists
        root = context.root

        # Search the user by username (login name)
        results = root.search(username=email)
        if results.get_n_documents() == 0:
            message = u'The user "$username" does not exist.'
            return context.come_back(message, username=email, keep=keep)

        # Get the user
        brain = results.get_documents()[0]
        user = root.get_handler('users/%s' % brain.name)

        # Check the user is active
        if user.get_property('ikaaro:user_must_confirm'):
            message = u'The user "$username" is not active.'
            return context.come_back(message, username=email, keep=keep)

        # Check the user is not disabled 
        if user.get_property('abakuc:user_disabled'):
            message = u'The user "$username" has been disabled.'
            return context.come_back(message, username=email, keep=keep)

        # Check the password is right
        if not user.authenticate(password):
            return context.come_back(u'The password is wrong.', keep=keep)

        # Set cookie
        user.set_auth_cookie(context, password)

        # Update registration date 
        registration_date = user.get_property('abakuc:registration_date')
        if registration_date is None:
            user.set_property('abakuc:registration_date', datetime.date.today())
        # Update last login date
        last_login_date = user.get_property('abakuc:last_login_date')
        if last_login_date:
            user.set_property('abakuc:previous_login_dates', last_login_date)
        # Add login date
        user.set_property('abakuc:last_login_date', datetime.date.today())
        # Set context
        context.user = user

        # Come back
        referrer = context.request.referrer
        if referrer:
            if not referrer.path:
                return referrer
            params = referrer.path[-1].params
            if not params:
                return referrer
            if params[0] != 'login_form':
                return referrer

        if goto is not None:
            return get_reference(goto)

        # Add user to current Training Programme
        # XXX need to fix this as now it adds the user to all
        # folders that have membership.
        #training = root.get_handler('training')
        #if training == training:
        if not self.has_user_role(user.name, 'abakuc:training_manager') and \
           not self.has_user_role(user.name, 'abakuc:branch_manager') and \
           not self.has_user_role(user.name, 'abakuc:branch_member'):
            self.set_user_role(user.name, 'abakuc:branch_member')
            schedule_to_reindex(user)

        return get_reference('users/%s' % user.name)

    ########################################################################
    # Register
    def is_allowed_to_register(self, user, object):
        return self.get_property('ikaaro:website_is_open')


    register_fields = [('ikaaro:firstname', True),
                       ('ikaaro:lastname', True),
                       ('ikaaro:email', True),
                       ('abakuc:terms', True)]


    register_form__access__ = 'is_allowed_to_register'
    register_form__label__ = u'Register'
    def register_form(self, context, functions=None):
        root = get_context().root
        namespace = context.build_form_namespace(self.register_fields)
        namespace['functions'] = root.get_functions_namespace(functions)
        handler = self.get_handler('/ui/abakuc/register.xml')
        return stl(handler, namespace)


    register__access__ = 'is_allowed_to_register'
    def register(self, context):
        keep = ['ikaaro:firstname', 'ikaaro:lastname', \
                'ikaaro:email', 'abakuc:terms']
        # Check input data
        error = context.check_form_input(self.register_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Get input data
        firstname = context.get_form_value('ikaaro:firstname').strip()
        lastname = context.get_form_value('ikaaro:lastname').strip()
        email = context.get_form_value('ikaaro:email').strip()
        terms = context.get_form_value('abakuc:terms')
        functions = context.get_form_value('functions')

        # Check email address has an MX record
        email_uri = 'mailto:'+email
        r1 = get_reference(email_uri)
        host = r1.host
        import dns.resolver
        from dns.exception import DNSException
        # Here we check to see if email host has an MX record
        try:
            # This may take long
            answers = dns.resolver.query(host, 'MX')
        except DNSException, e:
            answers = None
        if not answers:
            message = u'The email supplied is invalid!'
            return context.come_back(message, keep=keep)
        # Do we already have a user with that email?
        root = context.root
        results = root.search(email=email)
        users = self.get_handler('users')
        if results.get_n_documents():
            user = results.get_documents()[0]
            user = users.get_handler(user.name)
            if not user.has_property('ikaaro:user_must_confirm'):
                message = u'There is already an active user with that email.'
                return context.come_back(message, keep=keep)
        else:
            # Add the user
            user = users.set_user(email, None)
            user.set_property('ikaaro:firstname', firstname, language='en')
            user.set_property('ikaaro:lastname', lastname, language='en')
            # Set the role
            from training import Training
            office = self.get_site_root()
            if isinstance(office, Training):
                # Sets the role of the user, from training.py
                default_role = self.__roles__[2]['name']
                self.set_user_role(user.name, default_role)
            else:
                default_role = self.__roles__[0]['name']
                self.set_user_role(user.name, default_role)
            #default_role = self.__roles__[0]['name']
            #self.set_user_role(user.name, default_role)
        # Set product specific data
        user.set_property('abakuc:functions', functions)
        # Set the registration date
        user.set_property('abakuc:registration_date', datetime.date.today())
        # Set the terms & conditions
        user.set_property('abakuc:terms', terms)
        # Send confirmation email
        key = generate_password(30)
        user.set_property('ikaaro:user_must_confirm', key)
        user.send_confirmation(context, email)

        # Bring the user to the login form
        message = self.gettext(
            u"An email has been sent to you, to finish the registration "
            u"process follow the instructions detailed in it.")
        return message.encode('utf-8')

    terms__access__ = True
    def terms(self, context):
        root = context.root
        skin = root.get_skin()
        skin_path = skin.abspath
        namespace = {}
        if skin_path == '/ui/aruni':
            handler = self.get_handler('/ui/abakuc/terms.xml')
        else:
            handler = root.get_skin().get_handler('/ui/abakuc/terms.xml')
        return stl(handler, namespace) 

    about__access__ = True
    def about(self, context):
        root = context.root
        skin = root.get_skin()
        skin_path = skin.abspath
        namespace = {}
        if skin_path == '/ui/aruni':
            handler = self.get_handler('/ui/abakuc/about.xml')
        else:
            handler = root.get_skin().get_handler('/ui/abakuc/about.xml')
        return stl(handler, namespace)

    bookmarks__access__ = True
    def bookmarks(self, context):
        root = context.root
        skin = root.get_skin()
        skin_path = skin.abspath
        namespace = {}
        if skin_path == '/ui/aruni':
            handler = self.get_handler('/ui/abakuc/bookmarks.xml')
        else:
            handler = root.get_skin().get_handler('/ui/abakuc/bookmarks.xml')
        return stl(handler, namespace)
    # http://del.icio.us/post?url=http://uk.expert.travel/
    # http://digg.com/submit?url=http://www.cruise.co.uk/cruise-guides/
    # http://reddit.com/submit?url=http://www.cruise.co.uk/cruise-guides/
    # http://www.facebook.com/sharer.php?u=http://www.cruise.co.uk/cruise-guides/
    # http://www.stumbleupon.com/submit?url=http://www.cruise.co.uk/
    #######################################################################
    # User Interface
    #######################################################################
    def GET(self, context):
        return context.uri.resolve2(';view')


    #view__access__ = True
    #def view(self, context):
    #    root = context.root

    #    handler = root.get_skin().get_handler('home.xhtml')
    #    return stl(handler)


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
        #if level1:
        #    level1 = unicode(level1, 'utf-8')
        #if level2:
        #    level2 = unicode(level2, 'utf-8')
        #if level3:
        #    level3 = unicode(level3, 'utf-8')
        #if level4:
        #    level4 = unicode(level4, 'utf-8')

        # Build the query
        query = {'format': self.site_format}

        if level1 is not None:
            query['level1'] = level1
            # Select the good country
            level0 = [ x[1] for x in root.get_authorized_countries(context) ]
            query['level0'] = level0
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
        #namespace['title'] = 'Hello' 
        namespace['banner'] = None
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
            # get the namespace for the banner based on the search.
            #namespace['banner'] = self.get_level1_title(level1)
            # here we want to search the banners folder and return the
            # banners associated with this 'level1'

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

            county = get_property('abakuc:county')
            if county is None:
                # XXX Every address should have a county
                region = ''
                county = ''
            else:
                for row_number in world.search(county=county):
                    row = world.get_row(row_number)
                    region = row[7]
                    county = get_property('abakuc:county')
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

