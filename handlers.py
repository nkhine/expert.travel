# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import (Boolean, DateTime, Email, Enumerate, String,
    Unicode)
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class
from itools.cms.base import Handler as iHandler
#from itools.cms.Handler import Handler as iHandler

class Handler(iHandler):

    #def get_site_root(self):
    #    from App import SiteRoot
    #    handler = self
    #    while not isinstance(handler, SiteRoot):
    #        handler = handler.parent
    #    return handler


    def get_publication_date(self):
        state = self.get_property('state')
        if state != 'public':
            return None
        transitions = self.get_property('ikaaro:wf_transition')

        # XXX Broken resource (See #779)
        if transitions == [{}]:
            return None

        dates = [ x[('dc', 'date')] for x in transitions ]

        # XXX Some old news are published, but don't have any transition.
        if not dates:
            return None

        dates.sort()
        return dates[-1]

class EnquiryType(Enumerate):

    options = [
        {'name': 'information', 'value': u'Information Request'},
        {'name': 'complaint', 'value': u'Complaint'}
        ]



class EnquiriesLog(CSV):

    class_id = 'EnquiriesLog'

    columns = ['datetime', 'user_id', 'phone', 'enquiry_type',
               'enquiry_subject', 'enquiry', 'resolved']
    schema = {'datetime': DateTime,
              'user_id': String(index='keyword'),
              'phone': String,
              'enquiry_type': EnquiryType,
              'enquiry_subject': Unicode,
              'enquiry': Unicode,
              'resolved': Boolean}


    GET__access__ = 'is_branch_manager_or_member'
    __view__access__ = 'is_branch_manager_or_member'



class ApplicationsLog(CSV):

    class_id = 'ApplicationsLog'

    columns = ['datetime', 'firstname', 'lastname', 'email', 'phone']
    schema = {'datetime': DateTime,
              'firstname': Unicode,
              'lastname': Unicode,
              'email': Email,
              'phone': String}



register_object_class(EnquiriesLog)
register_object_class(ApplicationsLog)
