# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2007 Luis Arturo Belmar-Letelier <luis@itaapy.com>
# Copyright (C) 2007 Nicolas Deram <nicolas@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from datetime import datetime
import mimetypes
from operator import itemgetter
from string import Template
from re import sub

# Import from itools
from itools.datatypes import Boolean, DateTime, Integer, String, Unicode, XML
from itools.cms.versioning import VersioningAware
from itools.i18n import format_datetime
from itools.rest import checkid
from itools.handlers import Config
from itools.csv import IntegerKey, CSV as BaseCSV
from itools.xml import Parser
from itools.stl import stl
from itools.uri import encode_query, Reference
from itools.cms.csv import CSV
from itools.cms.file import File
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.text import Text
from itools.cms.utils import generate_name
from itools.cms.registry import register_object_class, get_object_class
from itools.cms import widgets

# Definition of the fields of the forms to add and edit an issue
issue_fields = [('title', True), ('assigned_to', False),
                ('comment', False), ('file', False)]


class Products(Folder):

    class_id = 'products'
    class_title = u'Member products'
    class_description = u'Manage products'
    class_icon16 = 'images/tracker16.png'
    class_icon48 = 'images/tracker48.png'
    class_views = [
        ['add_form'],
        ['browse_content?mode=list'],
        ['edit_metadata_form']]

    def new(self, **kw):
        Folder.new(self, **kw)
        cache = self.cache

    def get_document_types(self):
        return []


    #######################################################################
    # API
    #######################################################################
    def get_new_id(self, prefix=''):
        ids = []
        for name in self.get_handler_names():
            if name.endswith('.metadata'):
                continue
            if prefix:
                if not name.startswith(prefix):
                    continue
                name = name[len(prefix):]
            try:
                id = int(name)
            except ValueError:
                continue
            ids.append(id)

        if ids:
            ids.sort()
            return prefix + str(ids[-1] + 1)
        
        return prefix + '0'


    def get_members_namespace(self, value, not_assigned=False):
        """
        Returns a namespace (list of dictionaries) to be used for the
        selection box of users (the 'assigned to' field).
        """
        users = self.get_handler('/users')
        members = []
        if not_assigned is True:
            members.append({'id': 'nobody', 'title': 'NOT ASSIGNED'})
        for username in self.get_site_root().get_members():
            user = users.get_handler(username)
            members.append({'id': username, 'title': user.get_title()})
        # Select
        if isinstance(value, str):
            value = [value]
        for member in members:
            member['is_selected'] = (member['id'] in value)

        return members

    view__access__ = 'is_allowed_to_view'
    view__label__ = u'View'
    def view(self, context):
        return '0'
    #######################################################################
    # User Interface / Add Issue
    add_form__access__ = 'is_allowed_to_edit'
    add_form__label__ = u'Add'
    def add_form(self, context):
        # Set Style
        css = self.get_handler('/ui/abakuc/product/tracker.css')
        context.styles.append(str(self.get_pathto(css)))

        # Build the namespace
        namespace = {}
        namespace['title'] = context.get_form_value('title', type=Unicode)
        # Others
        users = self.get_handler('/users')
        assigned_to = context.get_form_values('assigned_to', type=String)
        namespace['users'] = self.get_members_namespace(assigned_to)

        handler = self.get_handler('/ui/abakuc/product/add_issue.xml')
        return stl(handler, namespace)


    add_issue__access__ = 'is_allowed_to_edit'
    def add_issue(self, context):
        keep = ['title']
        # Check input data
        error = context.check_form_input(issue_fields)
        if error is not None:
            return context.come_back(error, keep=keep)

        # Add
        id = self.get_new_id()
        issue, metadata = self.set_object(id, Product())
        issue._add_row(context)

        goto = context.uri.resolve2('../%s/;edit_form' % issue.name)
        return context.come_back(u'New issue addded.', goto=goto)


    go_to_issue__access__ = 'is_allowed_to_view'
    def go_to_issue(self, context):
        issue_name = context.get_form_value('issue_name')
        if not issue_name in self.get_handler_names():
            return context.come_back(u'Issue not found.')
        issue = self.get_handler(issue_name)
        if not isinstance(issue, Product):
            return context.come_back(u'Issue not found.')
        return context.uri.resolve2('../%s/;edit_form' % issue_name)



###########################################################################
# Tables
###########################################################################
class SelectTable(CSV):

    class_id = 'tracker_select_table'

    columns = ['id', 'title']
    schema = {'id': IntegerKey, 'title': Unicode}


    def get_options(self, value=None, sort=True):
        options = [ {'id': x[0], 'title': x[1]} for x in self.get_rows() ]
        if sort is True:
            options.sort(key=lambda x: x['title'])
        # Set 'is_selected'
        if value is None:
            for option in options:
                option['is_selected'] = False
        elif isinstance(value, list):
            for option in options:
                option['is_selected'] = (option['id'] in value)
        else:
            for option in options:
                option['is_selected'] = (option['id'] == value)

        return options


    def get_row_by_id(self, id):
        for x in self.search(id=id):
            return self.get_row(x)
        return None


    def view(self, context):
        namespace = {}

        # The input parameters
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 30

        # The batch
        total = len(self.lines)
        namespace['batch'] = widgets.batch(context.uri, start, size, total,
                                           self.gettext)

        # The table
        actions = []
        if total:
            ac = self.get_access_control()
            if ac.is_allowed_to_edit(context.user, self):
                actions = [('del_row_action', u'Remove', 'button_delete',None)]

        columns = self.get_columns()
        columns.insert(0, ('index', u''))
        columns.append(('issues', u'Issues'))
        rows = []
        index = start
        getter = lambda x, y: x.get_value(y)

        filter = self.name[:-5]
        if self.name.startswith('priorit'):
            filter = 'priority'

        for row in self.lines[start:start+size]:
            rows.append({})
            rows[-1]['id'] = str(index)
            rows[-1]['checkbox'] = True
            # Columns
            rows[-1]['index'] = index, ';edit_row_form?index=%s' % index
            for column, column_title in columns[1:-1]:
                value = getter(row, column)
                datatype = self.get_datatype(column)
                is_enumerate = getattr(datatype, 'is_enumerate', False)
                rows[-1][column] = value
            count = 0
            for handler in self.parent.search_handlers(handler_class=Product):
                if handler.get_value(filter) == index:
                    count += 1
            value = '0'
            if count != 0:
                value = '<a href="../;view?%s=%s">%s issues</a>'
                if count == 1:
                    value = '<a href="../;view?%s=%s">%s issue</a>'
                value = Parser(value % (filter, index, count))
            rows[-1]['issues'] = value
            index += 1

        # Sorting
        sortby = context.get_form_value('sortby')
        sortorder = context.get_form_value('sortorder', 'up')
        if sortby:
            rows.sort(key=itemgetter(sortby), reverse=(sortorder=='down'))

        namespace['table'] = widgets.table(columns, rows, [sortby], sortorder,
                                           actions)

        handler = self.get_handler('/ui/csv/view.xml')
        return stl(handler, namespace)


###########################################################################
# Issues
###########################################################################
class History(BaseCSV):

    columns = ['datetime', 'username', 'title', 'assigned_to',
               'comment', 'file']
    schema = {'datetime': DateTime,
              'username': String,
              'title': Unicode,
              'assigned_to': String,
              'comment': Unicode,
              'file': String}



class Product(Folder, VersioningAware):

    class_id = 'product'
    class_layout = {
        '.history': History}
    class_title = u'Product'
    class_description = u'Product'
    class_views = [
        ['edit_form'],
        ['browse_content?mode=list'],
        ['history']]


    def new(self, **kw):
        Folder.new(self, **kw)
        cache = self.cache
        cache['.history'] = History()


    def get_document_types(self):
        return [File]


    #######################################################################
    # API
    #######################################################################
    def get_title(self):
        return '#%s %s' % (self.name, self.get_value('title'))


    def get_rows(self):
        return self.get_handler('.history').get_rows()


    def _add_row(self, context):
        user = context.user
        root = context.root
        parent = self.parent
        users = root.get_handler('users')

        # Datetime
        row = [datetime.now()]
        # User
        if user is None:
            row.append('')
        else:
            row.append(user.name)
        # Title
        title = context.get_form_value('title', type=Unicode).strip()
        row.append(title)
        # Version, Priority, etc.
        for name in ['assigned_to', 'comment']:
            type = History.schema[name]
            value = context.get_form_value(name, type=type)
            if type == Unicode:
                value = value.strip()
            row.append(value)
        # Files
        file = context.get_form_value('file')
        if file is None:
            row.append('')
        else:
            filename, mimetype, body = file
            # Upload
            # The mimetype sent by the browser can be minimalistic
            guessed = mimetypes.guess_type(filename)[0]
            if guessed is not None:
                mimetype = guessed
            # Set the handler
            cls = get_object_class(mimetype)
            handler = cls(string=body)

            # Find a non used name
            filename = checkid(filename)
            filename = generate_name(filename, self.get_handler_names())
            row.append(filename)

            handler, metadata = self.set_object(filename, handler)
            metadata.set_property('format', mimetype)
        # Update
        #modifications = self.get_diff_with(row, context)
        history = self.get_handler('.history')
        history.add_row(row)


    def get_reported_by(self):
        history = self.get_handler('.history')
        return history.get_row(0).get_value('username')


    def get_value(self, name):
        rows = self.get_handler('.history').lines
        if rows:
            return rows[-1].get_value(name)
        return None

    #######################################################################
    # User Interface
    #######################################################################
    edit_form__access__ = 'is_allowed_to_edit'
    edit_form__label__ = u'Edit'
    def edit_form(self, context):
        # Set Style
        css = self.get_handler('/ui/abakuc/product/tracker.css')
        context.styles.append(str(self.get_pathto(css)))
        # Set JS
        js = self.get_handler('/ui/abakuc/product/tracker.js')
        context.scripts.append(str(self.get_pathto(js)))

        # Local variables
        users = self.get_handler('/users')
        (kk, kk, title, assigned_to, comment, file) = self.get_handler('.history').lines[-1]

        # Build the namespace
        namespace = {}
        namespace['number'] = self.name
        namespace['title'] = title
        # Reported by
        reported_by = self.get_reported_by()
        reported_by = self.get_handler('/users/%s' % reported_by)
        namespace['reported_by'] = reported_by.get_title()

        # Assign To
        namespace['users'] = self.parent.get_members_namespace(assigned_to)
        # Comments
        #users = self.get_handler('/users')
        #comments = []
        #i = 0
        #for row in self.get_rows():
        #    comment = row.get_value('comment')
        #    file = row.get_value('file')
        #    if not comment and not file:
        #        continue
        #    datetime = row.get_value('datetime')
        #    # solid in case the user has been removed
        #    username = row.get_value('username')
        #    user_title = username
        #    if users.has_handler(username):
        #        user_title = users.get_handler(username).get_title()
        #    i += 1
        #    comments.append({
        #        'number': i,
        #        'user': user_title,
        #        'datetime': format_datetime(datetime),
        #        'comment': self.indent(comment),
        #        'file': file})
        #comments.reverse()

        namespace['comment'] = comment

        handler = self.get_handler('/ui/abakuc/product/edit_issue.xml')
        return stl(handler, namespace)


    edit__access__ = 'is_allowed_to_edit'
    def edit(self, context):
        # Check input data
        error = context.check_form_input(issue_fields)
        if error is not None:
            return context.come_back(error)
        # Edit
        self._add_row(context)

        return context.come_back(MSG_CHANGES_SAVED)


    #######################################################################
    # User Interface / History
    history__access__ = 'is_allowed_to_view'
    history__label__ = u'History'
    def history(self, context):
        # Set Style
        css = self.get_handler('/ui/abakuc/product/tracker.css')
        context.styles.append(str(self.get_pathto(css)))

        # Local variables
        users = self.get_handler('/users')
        # Initial values
        previous_title = None
        previous_version = None
        previous_type = None
        previous_state = None
        previous_module = None
        previous_priority = None
        previous_assigned_to = None

        # Build the namespace
        namespace = {}
        namespace['number'] = self.name
        rows = []
        i = 0
        for row in self.get_rows():
            (datetime, username, title, assigned_to, comment, file) = row
            # solid in case the user has been removed
            user_exist = users.has_handler(username) 
            usertitle = (user_exist and 
                         users.get_handler(username).get_title() or username)
            i += 1
            row_ns = {'number': i,
                      'user': usertitle,
                      'datetime': format_datetime(datetime),
                      'title': None,
                      'assigned_to': None,
                      'comment': None,
                      'file': file}

            if title != previous_title:
                previous_title = title
                row_ns['title'] = title

            rows.append(row_ns)

        rows.reverse()
        namespace['rows'] = rows

        handler = self.get_handler('/ui/abakuc/product/issue_history.xml')
        return stl(handler, namespace)


    def to_str(self):
        # XXX Used by VersioningAware to define the size of the document
        return ''



###########################################################################
# Register
###########################################################################
register_object_class(Products)
register_object_class(Product)
