
# Import from the Standard Library
from datetime import datetime, date
from operator import itemgetter
from urllib import urlencode

# itools
from itools.datatypes import Boolean, DataType, Integer, String, Unicode
from itools.catalog import EqQuery, OrQuery, AndQuery
from itools.handlers import Text
from itools.csv import CSV
from itools.stl import stl
from itools.web import get_context
from itools.cms.access import AccessControl
from itools.cms import widgets
from itools.cms.registry import register_object_class
from itools.cms.folder import Folder

class Date(DataType):

    @staticmethod
    def decode(value):
        if not value:
            return None
        day, month, year = value.split('/')
        if len(year) == 2:
            year = '20%s' % year
        year, month, day = int(year), int(month), int(day)
        return date(year, month, day)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return value.strftime('%d/%m/%Y')



############################################################################
# Tour Operators, Destinations and Hotels
############################################################################
class SimpleTable(CSV):

    columns = ['title', 'state']
    schema = {'title': Unicode,
              'state': Boolean}


    def edit(self, context):
        index = context.get_form_value('id', type=Integer)
        title = context.get_form_value('title', type=Unicode)
        state = context.get_form_value('state', type=Boolean)

        self.set_changed()
        self.lines[index] = [title, state]


    def get_row_title(self, index):
        return self.lines[index][0]


    def get_active_rows(self, index=None):
        return [ {'name': i, 'value': x[0], 'selected': index == i}
                 for i, x in enumerate(self.lines) if x[1] is True ]


    def get_active_destinations(self, indexes=None):
        return [ {'name': i, 'value': x[0], 'selected': str(i) in indexes}
                 for i, x in enumerate(self.lines) if x[1] is True ]


    ########################################################################
    # User interface
    ########################################################################
    def manage_table(self, context, action):
        selected_value = context.get_form_value('selected_value', type=Integer)

        # Build the namespace
        namespace = {}
        namespace['action_add'] = ';create_%s' % action
        namespace['action_edit'] = ';edit_%s' % action

        if self.name == '.destinations':
            href = ';manage_destinations?%s'
        elif self.name == '.hotels':
            href = ';manage_hotels?%s'
        else:
            href = ';manage_tour_operators?%s'

        rows = []
        for row_id, row in enumerate(self.lines):
            title, state = row

            info = {}
            info['id'] = row_id
            info['title'] = title
            info['state'] = state and 'enabled' or 'disabled'
            info['href'] = href % urlencode({'selected_value': row_id})

            if row_id == selected_value:
                info['selected'] = True
                info['enable'] = state
                info['disable'] = not state
            else:
                info['selected'] = False

            rows.append(info)

        rows.sort(key=lambda x: x['title'])
        namespace['rows'] = rows

        root = context.root
        handler = root.get_handler('ui/abakuc/bookings/manage_table.xml')
        return stl(handler, namespace)


############################################################################
# Types of holidays
############################################################################
class HolidayTypes(Text):

    __slots__ = ['uri', 'timestamp', 'parent', 'name', 'real_handler',
                 'items']


    def new(self):
        self.items = {}


    def _load_state_from_file(self, file):
        items = {}

        data = file.read()
        for line in data.split('\n'):
            types = line.split(':')
            main_type = types[0]
            if len(types) > 1:
                subtypes = types[1].split(',')
                if subtypes and subtypes[0]:
                    if main_type in items:
                        items[main_type].extend(subtypes)
                    else:
                        items[main_type] = subtypes
                else:
                    items[main_type] = []

        self.items = items


    def to_str(self):
        items = self.items
        lines = []
        for main_type in items:
            subtypes = items[main_type]
            lines.append('%s:%s' % (main_type, ','.join(subtypes)))

        return '\n'.join(lines)


    ########################################################################
    # API
    def get_lines(self):
        items = self.items

        lines = []
        keys = items.keys()
        for key in keys:
            subtypes = items[key]
            if subtypes:
                for subtype in subtypes:
                    lines.append(key + '/' + subtype)
            else:
                lines.append(key)
        lines.sort()
        return lines


    def set(self, key, value):
        self.set_changed()
        self.items[key] = value


############################################################################
# Bookings
############################################################################
duration_values = {0: 'Less than 7', 1: 'From 7 to 14', 2: 'More than 14'}

state_values = {0: 'approved', 1: 'cancelled', 2: 'rejected', 3: 'pending'}


class BookingData(CSV):

    columns = ['id', 'date_booking', 'reference_number', 'from_date',
               'to_date', 'party_name',
               'user', 'tour_operator', 'holiday_type', 'holiday_subtype',
               'number', 'duration', 'destination1', 'destination2',
               'destination3', 'destination4', 'destination5', 'comments',
               'state', 'hotel']

    schema = {'id': Integer(index='keyword'),
              'date_booking': Date,
              'reference_number': String,
              'from_date': Date,
              'to_date': Date,
              'party_name': Unicode,
              'user': String(index='keyword'),
              'tour_operator': String(index='keyword'),
              'holiday_type': String(index='keyword'),
              'holiday_subtype': String(index='keyword'),
              'number': Integer,
              'duration': String(index='keyword'),
              'destination1': String(index='keyword'),
              'destination2': String(index='keyword'),
              'destination3': String(index='keyword'),
              'destination4': String(index='keyword'),
              'destination5': String(index='keyword'),
              'comments': Unicode,
              'state': Integer,
              'hotel': String(index='keyword')}


    def append(self, line):
        line.setdefault('state', '3')
        if 'id' not in line:
            line['id'] = len(self.lines) + 1

        line = [ line[name] for name in self.columns ]
        self.add_row(line)


    def get_booking_by_id(self, booking_id):
        booking_id = int(booking_id)
        for index in self.search(id=booking_id):
            return self.get_row(index)
        return None



def check_dates(from_date, to_date):
    date_error = []

    try:
        begin = Date.decode(from_date)
    except:
        date_error.append(u"'From date' is malformed")

    try:
        end = Date.decode(to_date)
    except:
        date_error.append(u"'End date' is malformed")

    if date_error:
        return date_error

    if begin >= end:
        return [u"'To date' must be before 'From date'"]

    return []



class Bookings(AccessControl, Folder):

    class_layout = {
        '.holiday_types': HolidayTypes,
        '.bookings': BookingData,
        '.destinations': SimpleTable,
        '.hotels': SimpleTable,
        '.tour_operators': SimpleTable}
    class_icon16 = 'abakuc/images/Booking16.png'
    class_icon48 = 'abakuc/images/Booking48.png'
    class_id = 'bookings'
    class_title = u'Bookings module'
    class_description = u"Manage Tourist Agent's bookings"
    class_views = [['manage_bookings', 'booking_create_form'],
                   ['statistics'],
                   ['manage_tour_operators'],
                   ['manage_destinations'],
                   ['manage_hotels'],
                   ['manage_holiday_types']]


    def new(self):
        Folder.new(self)
        cache = self.cache
        cache['.tour_operators'] = SimpleTable()
        cache['.hotels'] = SimpleTable()
        cache['.destinations'] = SimpleTable()
        cache['.holiday_types'] = HolidayTypes()
        cache['.bookings'] = BookingData()


    #######################################################################
    # API
    #######################################################################
    def get_destination(self, index):
        return self.get_handler('.destinations').get_row_title(index)


    def get_hotel(self, index):
        return self.get_handler('.hotels').get_row_title(index)


    def get_tour_operator(self, index):
        return self.get_handler('.tour_operators').get_row_title(index)


    #######################################################################
    # ACL
    #######################################################################
    def is_training_manager(self, user, object):
        return self.parent.is_training_manager(user, object)

    def is_allowed_to_manage(self, user, object):
        if user is None:
            return False
        if self.is_training_manager(user, object):
            return True

        return user is not None and user.is_branch_member(user, self)


    def is_allowed_to_edit(self, user, object):
        if self.is_training_manager(user, object):
            return True

        if user is None:
            return False

        context = get_context()
        if not context.has_form_value('booking_id'):
            return False

        bookings = self.get_handler('.bookings')
        booking_id = context.get_form_value('booking_id')
        booking_id = int(booking_id)
        search = bookings.search(id=booking_id, user=user.name)

        return len(search) > 0


    def is_allowed_to_create(self, user, object):
        if self.is_allowed_to_manage(user, object):
            return True

        office = self.parent
        if office.is_training_manager(user, self):
            return True

        return get_context().get_form_value('user') == user.name


    def is_allowed_to_delete(self, user, object):
        if self.is_allowed_to_edit(user, object):
            return True

        booking_ids = get_context().get_form_value('booking_id')
        if booking_ids:
            bookings = self.get_handler('.bookings')
            user_bookings_index = bookings.columns['user'].get(user.name)

            items = bookings.items
            my_bookings = set([ item['id'] for item in items
                                if items.index(item) in user_bookings_index ])

            booking_ids = set(booking_ids)
            return booking_ids.issubset(my_bookings)

        return True


    #######################################################################
    # Manage bookings
    #######################################################################
    def search_bookings(self, query=None, **kw):
        bookings = self.get_handler('.bookings')
        if query or kw:
            ids = bookings.search(query, **kw)
            return bookings.get_rows(ids)
        return bookings.get_rows()


    manage_bookings__access__ = 'is_allowed_to_manage'
    manage_bookings__label__ = u'Manage bookings'
    manage_bookings__sublabel__ = u'Manage bookings'
    def manage_bookings(self, context):
        filter_criteria = context.get_form_value('filter_criteria')
        filter_value = context.get_form_value('filter_value')
        filter_duration = context.get_form_value('filter_duration')

        root = context.root
        booking_name = self.name
        bookings = self.get_handler('.bookings')
        holiday_types = self.get_handler('.holiday_types')
        #skin_name = context.root.get_skin_name()

        user = context.user
        namespace = {}
        namespace['booking_name'] = booking_name 
        edit_url = '/%s/;booking_edit_form?' % booking_name
        namespace['user'] = None

        filters = filter_criteria or filter_duration
        namespace['filters'] = filters
        namespace['filter_criteria'] = filter_criteria
        namespace['filter_value'] = filter_value
        namespace['filter_duration'] = filter_duration

        #to = self.parent
        office_name = self.get_site_root() 
        if office_name.is_training_manager(user, self):
            manager = True
            is_travel_agent = False
            csv_url = '/%s/;csv?' % booking_name
            states = ['Reject', 'Approve']
            # Search
            if not filters:
                objects = bookings.get_rows()
            else:
                # Search
                query = self.build_query(filter_duration, filter_criteria,
                                         filter_value)
                objects = self.search_bookings(query)

                # Update namespace
                if filter_duration is not None:
                    # Duration
                    label = duration_values[int(filter_duration)]
                    namespace['filter_duration_label'] = label
                    # Update CSV URL
                    csv_url += 'filter_duration=%s' % filter_duration

                if filter_criteria is not None:
                    # file_criteria_label
                    label = {'tour_operator': 'Tour Operator',
                             'destination': 'Destination',
                             'hotel': 'Hotel',
                             'holiday_type': 'Holiday Type',
                             'holiday_subtype': 'Holiday Sub-Type',
                             'user': 'User'}[filter_criteria]
                    namespace['filter_criteria_label'] = label
                    # file_value_label
                    if filter_criteria == 'tour_operator':
                        index = int(filter_value)
                        label = self.get_tour_operator(index)
                    elif filter_criteria == 'destination':
                        index = int(filter_value)
                        label = self.get_destination(index)
                    else:
                        label = filter_value
                    namespace['filter_value_label'] = label
                    # Update CSV URL
                    csv_url += '&filter_criteria=%s' % filter_criteria
                    csv_url += '&filter_value=%s' % filter_value
            # CSV URL
            namespace['csv_url'] = csv_url
        else:
            manager = False
            is_travel_agent = True 
            states = ['Cancel','Request']
            namespace['user'] = user.name
            namespace['manage_action'] = u"Cancel selected bookings"
            objects = self.search_bookings(**{'user': user.name})

        #else:
        namespace['is_travel_agent'] = is_travel_agent

        # FIXME 015
        columns = [('reference_number', u'Reference'),
                   ('user', u'User'),
                   ('email', u'E-Mail'),
                   ('tour_operator', u'Tour Operator'),
                   ('holiday_type', u'Holiday Type'),
                   ('holiday_subtype', u'Sub Type'),
                   ('duration', u'Duration'),
                   ('state', u'State')]
        if is_travel_agent:
            del columns[1:3] 

        rows = []
        for booking in objects:
            get_value = booking.get_value
            duration = get_value('duration')
            holiday_type = get_value('holiday_type')
            holiday_subtype = get_value('holiday_subtype')
            tour_operator = get_value('tour_operator')

            id = get_value('id')
            href = edit_url + urlencode({'booking_id' : id})
            info = {
                'checkbox': not bool(filters),
                'id': id,
                'reference_number': (get_value('reference_number'), href),
                'holiday_type': get_value('holiday_type'),
                'holiday_subtype': holiday_subtype}
            # Tour operator
            index = tour_operator
            try:
                index = int(index)
            except:
                # This happens when there are no tour operators defined
                info['tour_operator'] = ''
            else:
                info['tour_operator'] = self.get_tour_operator(index)
            # Duration
            info['duration'] = duration_values.get(duration, u'Unknown')
            # State
            state = get_value('state')
            info['state'] = state_values.get(state, u'Unknown').capitalize()
            # Username / Email
            if is_travel_agent is False:
                userid = get_value('user')
                user = root.get_user(userid)
                if user is None:
                    info['user'] = "Unknown"
                    info['email'] = "Unknown"
                else:
                    info['user'] = (user.get_property('ikaaro:username'), href)
                    email = user.get_property('ikaaro:email')
                    info['email'] = (email, "mailto:%s" % email)

            rows.append(info)

        # Sort
        sortby = context.get_form_value('sortby', 'reference_number')
        sortorder = context.get_form_value('sortorder', 'down')
        start = context.get_form_value('batchstart', type=Integer, default=0)
        if sortby in [x[0] for x in columns]:
            rows.sort(key=itemgetter(sortby), reverse=(sortorder=='down'))

        if is_travel_agent is True:
            actions = [('booking_state_form', u'Request', 'button_ok', None),
                       ('booking_state_form', u'Cancel', 'button_delete', None)]
        else:
            actions = [('booking_state_form', u'Reject', 'button_delete', None),
                       ('booking_state_form', u'Approve', 'button_ok', None)]

        total = len(rows)
        size = 5
        rows = rows[start:start+size]
        namespace['table'] = widgets.table(columns, rows, [sortby],
                                           sortorder, actions, self.gettext)
        namespace['states'] = states
        namespace['total'] = total
        namespace['batch'] = widgets.batch(context.uri, start, size, total)

        handler = root.get_handler('ui/abakuc/bookings/manage.xml')
        return stl(handler, namespace)


    csv__access__ = 'is_allowed_to_manage'
    def csv(self, context):
        root = context.root
        filter_criteria = context.get_form_value('filter_criteria')
        filter_value = context.get_form_value('filter_value')
        filter_duration = context.get_form_value('filter_duration')

        bookings = self.get_handler('.bookings')
        tour_operators = self.get_handler('.tour_operators')
        destinations = self.get_handler('.destinations')
        hotels = self.get_handler('.hotels')

        data = []
        keys = ["date_booking", "reference_number", "from_date", "to_date",
                "party_name",
                "user", "tour_operator", "holiday_type", "holiday_subtype",
                "number", "duration", "destination1", "destination2",
                "destination3", "destination4", "destination5", "comments",
                "hotel"]
        # The header
        header = ','.join([ '"%s"' % x for x in keys ])
        data.append(header)
        # The body
        query = self.build_query(filter_duration, filter_criteria,
                                 filter_value)
        for item in self.search_bookings(query):
            line = []
            for key in keys:
                value = item.get_value(key)
                if key == 'tour_operator':
                    try:
                        value = tour_operators.get_row_title(int(value))
                    except:
                        value = ''
                elif key.startswith('destination'):
                    try:
                        value = destinations.get_row_title(int(value))
                    except:
                        value = ''
                elif key == 'hotel':
                    if value is not None and value is not '':
                        value = hotels.get_row_title(int(value))
                elif key == 'duration':
                    value = duration_values[int(value)]
                elif key == 'user':
                    user = root.search(name=value).get_documents()
                    if user:
                        value = Unicode.encode(user[0].username)
                line.append('"%s"' % value)
            data.append(','.join(line))

        response = context.response
        response.set_header('Content-Type', 'text/comma-separated-values')
        response.set_header('Content-Disposition',
                            'attachment; filename="bookings.csv"')
        return u'\n'.join(data).encode('utf-8')


    edit_booking__access__ = 'is_allowed_to_edit'
    def edit_booking(self, context):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        destinations = context.get_form_values('destination')
        if not destinations or len(destinations) > 5:
            message = (u'Please select a destination.')
            return context.come_back(message)

        from_date = context.get_form_value('from_date')
        to_date = context.get_form_value('to_date')
        date_error = check_dates(from_date, to_date)

        if date_error:
            message = ', '.join(date_error) \
                      + (u": Data was not stored in database, please change "
                         u"the values below")

            params = {}
            for key in context.get_form_keys():
                params[key] = context.get_form_value(key)
            goto = './;booking_edit_form?%s' % urlencode(params)
            return context.come_back(message, goto=goto)

        booking_id = context.get_form_value('booking_id')
        bookings = self.get_handler('.bookings')
        booking = bookings.get_booking_by_id(booking_id)
        if not booking:
            message = u"Booking not found"
            return context.come_back(message)

        bookings.set_changed()
        catalog = bookings.catalog
        catalog.unindex_document(booking, booking.number)
        for name in ['reference_number', 'party_name', 'user',
                     'tour_operator', 'number', 'duration',
                     'hotel', 'from_date', 'to_date']:
            datatype = bookings.schema[name]
            value = context.get_form_value(name)
            value = datatype.decode(value)
            booking.set_value(name, value)

        # Manage up to 5 destinations
        datatype = bookings.schema['destination1']
        for i in range(1, 6):
            if destinations:
                booking.set_value('destination%i' % i,
                                  datatype.decode(destinations[0]))
                del destinations[0]
            else:
                booking.set_value('destination%i' % i, datatype.decode(''))


        holiday_type = context.get_form_value('holiday_types')
        if '/' in holiday_type:
            holiday_type, holiday_subtype = holiday_type.split('/')
        else:
            holiday_subtype = ''
        booking.set_value('holiday_type', holiday_type)
        booking.set_value('holiday_subtype', holiday_subtype)
        # Reindex row
        catalog.index_document(booking, booking.number)

        message = u"Booking Modified"
        return context.come_back(message)


    booking_create_form__access__ = 'is_allowed_to_manage'
    booking_create_form__sublabel__ = u'Add booking'
    def booking_create_form(self, context):
        user = context.user
        namespace = {'is_create_form': True}
        namespace['title'] = u"Register a new Booking"
        namespace['button_label'] = u"Add the booking"
        namespace['button_name'] = ";create_booking"
        for key in 'filter_criteria', 'filter_duration', 'filter_value':
            namespace[key] = context.get_form_value(key)

        office = self.parent
        namespace['is_admin'] = office.is_training_manager(user, self)

        bookings = self.get_handler('.bookings')

        for header in bookings.columns:
            namespace[header] = ''

        for key in context.get_form_keys():
            namespace[key] = context.get_form_value(key)
        namespace['username'] = user.get_property('ikaaro:username')
        namespace['user'] = user.name

        # Tour operators
        tour_operators = self.get_handler('.tour_operators')
        namespace['tour_operators'] = tour_operators.get_active_rows()
        namespace['tour_operator'] = ''

        # Destinations
        destinations = self.get_handler('.destinations')
        namespace['destinations'] = destinations.get_active_rows()
        for i in range(1, 6):
            namespace['destination%i' % i] = ''

        # Hotels
        hotels = self.get_handler('.hotels')
        namespace['hotels'] = hotels.get_active_rows()
        namespace['hotel'] = ''

        # Holiday types
        holiday_types = self.get_handler('.holiday_types')
        namespace['duration_values'] = [
            {'key': key, 'value': value, 'selected': False}
            for key, value in duration_values.items()]

        namespace['holiday_types'] = holiday_types.get_lines()[:]
        if namespace['holiday_type'] in namespace['holiday_types']:
            namespace['holiday_types'].remove(namespace['holiday_type'])

        # Show information to selecte up to 5 destinations only to canada
        #namespace['info_dest'] = (context.root.get_skin_name() == 'canada')
        namespace['info_dest'] = 'canada'

        handler = self.get_handler('/ui/abakuc/bookings/form.xml')
        return stl(handler, namespace)


    booking_edit_form__access__ = 'is_allowed_to_edit'
    def booking_edit_form(self, context):
        booking_id = context.get_form_value('booking_id')
        user = context.user

        namespace = {'is_create_form': False}
        namespace['title'] = self.gettext(u"Edit a booking")
        namespace['button_label'] = self.gettext(u"Modify the booking")
        namespace['button_name'] = ";edit_booking"
        for key in 'filter_criteria', 'filter_duration', 'filter_value':
            namespace[key] = context.get_form_value(key)

        office = self.parent
        namespace['is_admin'] = office.is_training_manager(user, self)

        bookings = self.get_handler('.bookings')
        booking_id = int(booking_id)
        booking_index = bookings.search(id=booking_id)[0]
        booking = bookings.get_row(booking_index)
        for header in bookings.columns:
            value = booking.get_value(header)
            if header == 'user':
                username = user.get_property('ikaaro:username')
                #if namespace['is_admin'] is False:
                #    username = user.get_property('ikaaro:username')
                #else:
                #    root = context.root
                #    username = root.search(name=value, format=User.class_id)
                #    username = username.get_documents()
                #    if username:
                #        username = username[0].username
                #namespace['username'] = username or value
                namespace['username'] = username
            datatype = bookings.schema[header]
            namespace[header] = datatype.encode(value)

        for key in context.get_form_keys():
            namespace[key] = context.get_form_value(key)

        # Tour operators
        try:
            index = int(namespace['tour_operator'])
        except:
            index = 0
        tour_operators = self.get_handler('.tour_operators')
        namespace['tour_operators'] = tour_operators.get_active_rows(index)

        # Destinations
        index = []
        for i in range(1, 6):
            index.append(namespace['destination%i'%i])
        destinations = self.get_handler('.destinations')
        namespace['destinations'] = destinations.get_active_destinations(index)

        # Hotels
        hotels = self.get_handler('.hotels')
        index = namespace['hotel']
        if index:
            index = int(index)
        namespace['hotels'] = hotels.get_active_rows(index)

        # Holidays
        holiday_types = self.get_handler('.holiday_types')
        namespace['holiday_type'] = namespace['holiday_type'] + \
                                    '/' + namespace['holiday_subtype']
        if namespace['holiday_type'][-1] == '/':
            namespace['holiday_type'] = namespace['holiday_type'][:-1]
        namespace['holiday_types'] = holiday_types.get_lines()[:]
        if namespace['holiday_type'] in namespace['holiday_types']:
            namespace['holiday_types'].remove(namespace['holiday_type'])

        # Durations
        namespace['duration_values'] = [
            {'key': key, 'value': value,
             'selected': (namespace['duration'] == str(key))}
            for key, value in duration_values.items()]

        # Show information to selecte up to 5 destinations only to canada
        namespace['info_dest'] = 'canada'

        handler = self.get_handler('/ui/abakuc/bookings/form.xml')
        return stl(handler, namespace)


    create_booking__access__ = 'is_allowed_to_create'
    def create_booking(self, context):
        destinations = context.get_form_values('destination')
        if not destinations or len(destinations) > 5:
            message = (u'Please select a destination.')
            return context.come_back(message)

        filter_criteria = context.get_form_value('filter_criteria')
        filter_value = context.get_form_value('filter_value')
        filter_duration = context.get_form_value('filter_duration')

        params = {}
        from_date = context.get_form_value('from_date')
        to_date = context.get_form_value('to_date')
        date_error = check_dates(from_date, to_date)
        if date_error:
            message = ', '.join(date_error) \
                      + (u" : Data was not stored in database, please change "
                         u"the values below")
            method = './;booking_create_form'
            for key in context.get_form_keys():
                params[key] = context.get_form_value(key)
        else:
            bookings = self.get_handler('.bookings')
            booking = {}

            # Add date the booking is added
            booking['date_booking']  = date.today()

            for name in ['reference_number', 'from_date', 'to_date',
                         'party_name', 'tour_operator', 'number', 'duration',
                         'hotel', 'comments']:
                datatype = bookings.schema[name]
                value = context.get_form_value(name, '')
                booking[name] = datatype.decode(value)

            # Manage up to 5 destinations
            datatype = bookings.schema['destination1']
            for i in range(1, 6):
                if destinations:
                    booking['destination%i' % i] = datatype.decode(\
                                                              destinations[0])
                    del destinations[0]
                else:
                    booking['destination%i' % i] = datatype.decode('')

            # Holiday type and sub type
            holiday_type = context.get_form_value('holiday_types')
            if '/' in holiday_type:
                holiday_type, holiday_subtype = holiday_type.split('/')
                #holiday_types = holiday_types[0]
                #holiday_subtype = holiday_types[:1]
            else:
                holiday_subtype = ''
            booking['holiday_type'] = holiday_type
            booking['holiday_subtype'] = holiday_subtype
            booking['user'] = context.get_form_value('user', context.user)
            bookings.set_changed()
            bookings.append(booking)

            message = u"Booking added"
            method = "./;manage_bookings"

        if filter_duration and filter_criteria:
            params.update({'filter_criteria': filter_criteria,
                           'filter_duration': filter_duration,
                           'filter_value': filter_value})

        goto = '%s?%s' % (method, urlencode(params))
        return context.come_back(message, goto=goto)


    booking_state_form__access__ = 'is_allowed_to_delete'
    def booking_state_form(self, context):
        states = {'Approve': 0, 'Reject': 2, 'Cancel': 1, 'Request': 3}
        state_label = context.get_form_value(';booking_state_form')
        state = states[state_label]

        booking_ids = context.get_form_values('ids')
        filter_duration = context.get_form_value('filter_duration')
        filter_criteria = context.get_form_value('filter_criteria')
        filter_value = context.get_form_value('filter_value')

        namespace = {}
        bookings = self.get_handler('.bookings')
        namespace['state'] = state
        namespace['state_label'] = state_label
        namespace['booking_ids'] = booking_ids
        namespace['booking_ids_label'] = ', '.join(booking_ids)
        namespace['filter_duration'] = filter_duration
        namespace['filter_value'] = filter_value
        namespace['filter_criteria'] = filter_criteria

        handler = self.get_handler('/ui/abakuc/bookings/state_form.xml')
        return stl(handler, namespace)


    booking_change_state__access__ = 'is_allowed_to_delete'
    def booking_change_state(self, context):
        states = {0: 'Approve', 2: 'Reject', 1: 'Cancel', 3: 'Request'}
        booking_ids = context.get_form_values('booking_ids')
        bookings = self.get_handler('.bookings')
        duration = context.get_form_value('filter_duration')
        criteria = context.get_form_value('filter_criteria')
        state = Integer.decode(context.get_form_value('state'))
        comments = Unicode.decode(context.get_form_value('comments'))
        value = context.get_form_value('filter_value')
        if booking_ids:
            timestamp = datetime.now().strftime('%m/%d/%Y(%H:%M)')
            state_label = states[state]
            for booking_id in booking_ids:
                booking = bookings.get_booking_by_id(booking_id)
                bookings.set_changed()
                booking.set_value('state', state)
                old_comments = booking.get_value('comments')
                comments = u"%s:%s\n%s\n\n%s" % (timestamp, state_label,
                                                 comments, old_comments)
                booking.set_value('comments', comments)
            message = u"Booking %s" % state_values[state]
        else:
            message = u"Booking not found"

        params = {}
        if duration and criteria:
            params.update({'criteria': criteria, 'duration': duration,
                           'value': value})

        goto = './;manage_bookings?%s' % urlencode(params)
        return context.come_back(message, goto=goto)


    #########################################################################
    # Tour Operators
    manage_tour_operators__label__ = u'Tour Operators'
    manage_tour_operators__access__ = 'is_training_manager'
    def manage_tour_operators(self, context):
        handler = self.get_handler('.tour_operators')
        return handler.manage_table(context, 'tour_operator')


    create_tour_operator__access__ = 'is_training_manager'
    def create_tour_operator(self, context):
        title = context.get_form_value('title', type=Unicode)

        self.get_handler('.tour_operators').add_row([title, True])
        return context.come_back(u'Tour Operator added')


    edit_tour_operator__access__ = 'is_training_manager'
    def edit_tour_operator(self, context):
        self.get_handler('.tour_operators').edit(context)
        return context.come_back(u"Value changed")


    #########################################################################
    # Destinations
    manage_destinations__label__ = u'Destinations'
    manage_destinations__access__ = 'is_training_manager'
    def manage_destinations(self, context):
        handler = self.get_handler('.destinations')
        return handler.manage_table(context, 'destination')


    create_destination__access__ = 'is_training_manager'
    def create_destination(self, context):
        title = context.get_form_value('title', type=Unicode)
        title.encode('utf-8')
        #title = unicode(title, 'UTF-8')

        self.get_handler('.destinations').add_row([title, True])
        return context.come_back(u'Destination added')


    edit_destination__access__ = 'is_training_manager'
    def edit_destination(self, context):
        self.get_handler('.destinations').edit(context)
        return context.come_back(u"Value changed")


    #########################################################################
    # Hotels
    manage_hotels__label__ = u'Hotels'
    manage_hotels__access__ = 'is_training_manager'
    def manage_hotels(self, context):
        handler = self.get_handler('.hotels')
        return handler.manage_table(context, 'hotel')


    create_hotel__access__ = 'is_training_manager'
    def create_hotel(self, context):
        title = context.get_form_value('title', type=Unicode)

        self.get_handler('.hotels').add_row([title, True])
        return context.come_back(u'Hotel added')


    edit_hotel__access__ = 'is_training_manager'
    def edit_hotel(self, context):
        self.get_handler('.hotels').edit(context)
        return context.come_back(u"Value changed")


    #########################################################################
    # Holiday types
    manage_holiday_types__label__ = u'Holiday types'
    manage_holiday_types__access__ = 'is_training_manager'
    def manage_holiday_types(self, context):
        root = context.root
        holiday_types = self.get_handler('.holiday_types')
        edit_url = "./;manage_holiday_types?"

        selected_holiday_type = context.get_form_values('selected_holiday_type')
        selected_holiday_subtype = context.get_form_values('selected_holiday_subtype')

        objects = []
        types = []
        items = holiday_types.items
        for holiday_type in items:
            type_info = {}
            type_info['value'] = holiday_type
            type_info['title'] = holiday_type
            type_info['subtypes'] = []
            if selected_holiday_type and selected_holiday_type == holiday_type:
                type_info['selected'] = True
            else:
                type_info['selected'] = False

            params = {}
            for key in context.get_form_keys():
                if key != 'message':
                    params[key] = context.get_form_value(key)

            params['selected_holiday_type'] = holiday_type
            type_info['href'] = edit_url + urlencode(params)
            subtypes = items[holiday_type]
            subtypes.sort()
            for subtype in subtypes:
                subparams = params.copy()
                subtype_info = {}
                subtype_info['value'] = subtype
                subtype_info['title'] = holiday_type + '/' + subtype
                subparams['selected_holiday_subtype'] = subtype
                subtype_info['href'] = edit_url + urlencode(subparams)
                if selected_holiday_subtype and \
                       selected_holiday_subtype == subtype:
                    subtype_info['selected'] = True
                    type_info['selected'] = False
                    subtype_info['types'] = items.keys()
                    subtype_info['types'].remove(holiday_type)
                else:
                    subtype_info['selected'] = False

                type_info['subtypes'].append(subtype_info)
            objects.append(type_info)

        objects.sort(key=lambda x: x['title'])

        namespace = {}
        namespace['types'] = items.keys()
        namespace['objects'] = objects
        namespace['total'] = len(objects)

        handler = root.get_handler('ui/abakuc/bookings/holiday_types.xml')
        return stl(handler, namespace)


    create_holiday_type__access__ = 'is_training_manager'
    def create_holiday_type(self, context):
        new_holiday_type_value = context.get_form_value('new_holiday_type_value')
        new_holiday_type_value = new_holiday_type_value.strip()
        holiday_types = self.get_handler('.holiday_types')
        if new_holiday_type_value:
            if new_holiday_type_value not in holiday_types.items:
                if '/' in new_holiday_type_value:
                    message = u"Holiday type must not contain '/'."
                else:
                    message = u"Holiday Type added"
                    holiday_types.set(new_holiday_type_value, [])
            else:
                message = u'This Holiday Type exists'
        else:
            message = u'Holiday type is missing'

        return context.come_back(message)


    create_holiday_subtype__access__ = 'is_training_manager'
    def create_holiday_subtype(self, context):
        new_subtype_holiday_type = context.get_form_value('new_subtype_holiday_type')
        new_holiday_subtype_value = context.get_form_value('new_holiday_subtype_value')
        holiday_types = self.get_handler('.holiday_types')
        if new_subtype_holiday_type and new_holiday_subtype_value:
            new_subtype_holiday_type = new_subtype_holiday_type.strip()
            new_holiday_subtype_value = new_holiday_subtype_value.strip()

            items = holiday_types.items
            if new_subtype_holiday_type in items:
                holiday_subtype = items[new_subtype_holiday_type]
                if new_holiday_subtype_value not in holiday_subtype:
                    if '/' in new_holiday_subtype_value:
                        message = u"Holiday subtype must not contain '/'."
                    else:
                        message = u"Holiday Type added"
                        holiday_subtype.append(new_holiday_subtype_value)
                        holiday_types.set(new_subtype_holiday_type,
                                          holiday_subtype)
                else:
                    message = u'This Holiday SubType exists'
            else:
                message = u'This Holiday Type does not exists'
        else:
            message = u'Holiday type is missing'

        return context.come_back(message)


    edit_holiday_type__access__ = 'is_training_manager'
    def edit_holiday_type(self, context):
        holiday_type_new_value = context.get_form_value('holiday_type_new_value')
        holiday_type_old_value = context.get_form_value('holiday_type_old_value')

        holiday_types = self.get_handler('.holiday_types')
        items = holiday_types.items
        if holiday_type_old_value in items:
            if holiday_type_new_value not in items:
                holiday_subtypes = items[holiday_type_old_value]
                del items[holiday_type_old_value]
                holiday_types.set(holiday_type_new_value, holiday_subtypes)
                message = u"Value changed"
            elif holiday_type_new_value == holiday_type_old_value:
                message = u'Same value: no change'
            else:
                message = u'New value exists'
        else:
            message = u'The initial value does not exists'

        return context.come_back(message)


    edit_holiday_subtype__access__ = 'is_training_manager'
    def edit_holiday_subtype(self, context):
        type_new_value = context.get_form_value('holiday_type_new_value').strip()
        type_old_value = context.get_form_value('holiday_type_old_value')
        subtype_new_value = context.get_form_value('holiday_subtype_new_value').strip()
        subtype_old_value = context.get_form_value('holiday_subtype_old_value')

        if not type_new_value or not subtype_new_value:
            return context.come_back(u'New Holiday SubType missing')

        holiday_types = self.get_handler('.holiday_types')
        items = holiday_types.items
        if type_old_value not in items:
            message = u"Initial Type does not exists: ('$type')"
            return context.come_back(message, type=type_old_value)

        if type_new_value not in items:
            message = u"Destination Type does not exists: ('$type')"
            return context.come_back(message, type=type_new_value)

        holiday_types.set_changed()
        items[type_old_value].remove(subtype_old_value)
        items[type_new_value].append(subtype_new_value)

        return context.come_back(u'Holiday SubType changed')


    delete_holiday_types__access__ = 'is_training_manager'
    def delete_holiday_types(self, context):
        selected_holiday_types = context.get_form_values('selected_holiday_types')
        selected_holiday_subtypes = context.get_form_values('selected_holiday_subtypes')

        holiday_types = self.get_handler('.holiday_types')
        items = holiday_types.items
        holiday_types.set_changed()
        if selected_holiday_subtypes:
            for subtype in selected_holiday_subtypes:
                types = subtype.split('/')
                holiday_type = types[0]
                if len(types) > 1:
                    holiday_subtype = types[1]
                else:
                    holiday_subtype = None
                if holiday_subtype:
                    if (selected_holiday_types
                        and holiday_type in selected_holiday_types):
                        continue

                    if holiday_type in items:
                        if holiday_subtype in items[holiday_type]:
                            items[holiday_type].remove(holiday_subtype)

        if selected_holiday_types:
            for holiday_type in selected_holiday_types:
                if holiday_type in items:
                    del items[holiday_type]

        return context.come_back(u'Holiday (Sub)Type(s) deleted')


    #########################################################################
    # Statistics
    statistics__access__ = 'is_training_manager'
    statistics__label__ = u'Statistics'
    def statistics(self, context):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        root = context.root
        booking_name = self.name
        column = context.get_form_value('column', 'holiday_type')
        holiday_type = context.get_form_value('holiday_type')
        namespace = {}
        namespace['booking_name'] = booking_name
        bookings = self.get_handler('.bookings')
        tour_operators = self.get_handler('.tour_operators')
        destinations = self.get_handler('.destinations')
        hotels = self.get_handler('.hotels')
        holiday_types = self.get_handler('.holiday_types')

        # Search criteria
        namespace['criterias'] = [
            {'value': 'holiday_type', 'title': 'Holiday Type'},
            {'value': 'tour_operator', 'title': 'Tour operator'},
            {'value': 'destination', 'title': 'Destination'},
            {'value': 'hotel', 'title': 'Hotels'},
            {'value': 'user', 'title': 'Users'} ]
        for criteria in namespace['criterias']:
            value = criteria['value']
            criteria['selected'] = (value == column)
            if column == 'holiday_subtype' and value == 'holiday_type':
                criteria['selected'] = True

        # The Y axis
        base_query = None
        y_axis_key = column
        if column is None:
            y_axis = []
        elif column == 'holiday_type':
            y_axis = [ (x, x) for x in holiday_types.items ]
        elif column == 'tour_operator':
            y_axis = [ (i, line[0])
                       for i, line in enumerate(tour_operators.lines) ]
        elif column == 'destination':
            y_axis = [ (i, line[0])
                       for i, line in enumerate(destinations.lines) ]
        elif column == 'hotel':
            y_axis = [ (i, line[0])
                       for i, line in enumerate(hotels.lines) ]
        elif column == 'user':
            y_axis = [ (x, x) for x in bookings.get_index('user') ]
        elif column == 'holiday_subtype':
            base_query = EqQuery('holiday_type', holiday_type)
            y_axis = [ (x,x) for x in holiday_types.items[holiday_type] ]

        # Build the grid
        namespace['holiday_type'] = (column == 'holiday_type')
        namespace['holiday_subtype'] = (column == 'holiday_subtype')
        durations = ['0', '1', '2']
        total = {'0': 0, '1': 0, '2': 0}

#        indexes = bookings.indexes
        if column == 'holiday_subtype' and holiday_type:
            namespace['holiday_type_value'] = holiday_type
#            if holiday_type in columns['holiday_type']:
#                values = holiday_types.items.get(holiday_type)
#        else:
#            values = bookings.get_index(column)

        results = []
        total = {'0' : 0, '1' : 0, '2' : 0, 'total' : 0}
        namespace['total'] = 0

        namespace['users'] = None 
        for value, label in y_axis:
            line = {'value': label, 'total': 0}
            if column == 'user':
                from users import User
                namespace['users'] = (column == 'user')
                pp.pprint(namespace['users'])
                username = root.search(name=label, format=User.class_id)
                username = username.get_documents()
                if username:
                    href = "/users/%s/;view" % username[0].name
                    line['value'] = {'href': href,
                                     'title': username[0].title_or_name}
            # Forget changes on query (destination & duration filters)
            c_query = base_query

            if column == 'holiday_type':
                params = {'column': 'holiday_subtype', 'holiday_type': value}
                line['holiday_type_filter_url'] = "/%s/;statistics?" % booking_name + \
                                                  urlencode(params)
            if column == 'destination':
                # Destinations 1 to 5
                query = OrQuery(*[EqQuery('destination%i' % i, str(value))
                                  for i in range(1,6)])
            else:
                query = EqQuery(column, str(value))

            c_query = query if c_query is None else AndQuery(c_query, query)

            # For each of the 3 durations
            for duration in durations:
                query = EqQuery('duration', duration)
                if c_query is not None:
                    query = AndQuery(c_query, query)

                params = {}
                params['filter_duration'] = duration
                params['filter_criteria'] = column
                params['filter_value'] = value
                pp.pprint(params['filter_criteria'])
                href = "/%s/;manage_bookings?" % booking_name + urlencode(params)
                count = len(bookings.search(query))
                line[str(duration)] = {'href': href, 'size': count}

                params_column = params.copy()
                del params_column['filter_criteria']
                del params_column['filter_value']
                total['url_%s' % duration] = "/%s/;manage_bookings?" % booking_name + \
                                             urlencode(params_column)
                total[str(duration)] += count

                params_row = params.copy()
                del params_row['filter_duration']
                line['total'] += count
                line['total_url'] = "/%s/;manage_bookings?" % booking_name + \
                                    urlencode(params_row)

            total['total'] += line['total']
            results.append(line)
        namespace['results'] = results
        namespace['total'] = total

        handler = self.get_handler('/ui/abakuc/bookings/statistics.xml')
        return stl(handler, namespace)


    def build_query(self, duration, criteria, value, base_query=None):
        query, query_duration = None, None
        bookings = self.get_handler('.bookings')
        # Specified criteria
        if criteria is not None:
            if criteria == 'destination':
                query = []
                for i in range(1,6):
                    key = 'destination%i' % i
                    query.append(EqQuery(key, value))
                query = AndQuery(OrQuery(*query))
            else:
                datatype = bookings.schema[criteria]
                query = EqQuery(criteria, datatype.decode(value))
        # Specified duration
        if duration is not None:
            query_duration = EqQuery('duration', duration)
            # Join criteria and duration
            if query:
                query_duration = AndQuery(query, query_duration)
            return query_duration
        return query


register_object_class(Bookings)

