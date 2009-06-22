# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>
# Import from the Standard Library
import locale
import datetime
from urllib import urlencode

# Import from itools
from itools.cms.access import RoleAware
from itools.cms.file import File
from itools.cms.folder import Folder
from itools.cms.messages import *
from itools.cms.registry import register_object_class, get_object_class
from itools.cms.workflow import WorkflowAware
from itools.datatypes import Decimal
from itools.stl import stl
from itools.uri import Path, get_reference
from itools.web import get_context
from itools.cms.utils import reduce_string

# Import from abakuc
from utils import title_to_name
from utils import abspath_to_relpath, get_sort_name
from handlers import PriceMatrix


class Room(Folder, WorkflowAware):
    """
    Address objects, which are part of a hotel can add room objects.
    These are folderish objects with images and price.csv file.
    Each room object will have a price.csv which is in the form of:
    from-date, to-date, price,
    The room object will have a abakuc:type metadata:
    standard, executive, deluxe, familiy, presidential

    """
    class_id = 'room'
    class_title = u'Room'
    class_description = u'Hotel room'
    class_icon16 = 'abakuc/images/Briefcase16.png'
    class_icon48 = 'abakuc/images/Briefcase48.png'
    class_views = [
        ['view'],
        ['manage'],
        ['browse_content?mode=list'],
        ['new_resource_form'],
        ['state_form'],
        ['bookings_form']]

    edit_fields = [('dc:title' ,True),
                   ('dc:description', False),
                   ('abakuc:news_text', False)]

    def new(self, **kw):
        Folder.new(self, **kw)
        # Room price matrix 
        handler = PriceMatrix()
        cache = self.cache
        cache['price.csv'] = handler
        cache['price.csv.metadata'] = handler.build_metadata()

    def get_document_types(self):
        return [File]


    @classmethod
    def new_instance_form(cls, context):
        namespace = context.build_form_namespace(cls.edit_fields)
        namespace['class_id'] = Room.class_id
        path = '/ui/abakuc/room/new_instance_form.xml'
        handler = context.root.get_handler(path)
        return stl(handler, namespace)

    @classmethod
    def new_instance(cls, container, context):
        from datetime import datetime
        username = ''
        if context is not None:
            user = context.user
            if user is not None:
                username = user.name

        # Check data
        keep = [ x for x, y in cls.edit_fields ]
        error = context.check_form_input(cls.edit_fields)
        if error is not None:
            return context.come_back(error, keep=keep)
        # Generate the name(id)
        x = container.search_handlers(handler_class=cls)
        y =  str(len(list(x))+1)
        name = 'room%s' % y
        while container.has_handler(name):
              try:
                  names = name.split('-')
                  if len(names) > 1:
                      name = '-'.join(names[:-1])
                      number = str(int(names[-1]) + 1)
                      name = [name, number]
                      name = '-'.join(name)
                  else:
                      name = '-'.join(names) + '-1'
              except:
                  name = '-'.join(names) + '-1'

        # Job title
        title = context.get_form_value('dc:title')
        # Set properties
        handler = cls()
        metadata = handler.build_metadata()
        for key in ['dc:title' ,]:
            try:
                value = context.get_form_value(key)
                if not value:
                    message = (u"You have to fill all fields. You can edit"
                               u" these afterwords")
                    return context.come_back(message)
                metadata.set_property(key, context.get_form_value(key))
            except:
                message = u'Error of DataTypes.'
                return context.come_back(message)

        # Set the date the news was posted
        date = datetime.now()
        metadata.set_property('dc:date', date)
        # Add the object
        handler, metadata = container.set_object(name, handler, metadata)

        # Room price matrix 
        #handler = PriceMatrix()
        #cache = container.cache
        #cache['price.csv'] = handler
        #cache['price.csv.metadata'] = handler.build_metadata()

        #goto = './%s/;%s' % (name, handler.get_firstview())
        message = u'Room has been added. Please add some images or media files.'
        return context.come_back(message)


register_object_class(Room)
