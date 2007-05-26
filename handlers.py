# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import (Boolean, DateTime, Email, Enumerate, String,
    Unicode)
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class


class EnquiryType(Enumerate):

    options = [
        {'name': 'information', 'value': u'Information Request'},
        {'name': 'complaint', 'value': u'Complaint'}
        ]



class EnquiriesLog(CSV):

    class_id = 'EnquiriesLog'
  
    columns = ['datetime', 'enquiry_type', 'user_id', 'phone', 'enquiry',
        'resolved']
    schema = {'datetime': DateTime,
              'enquiry_type': EnquiryType,
              'user_id': String(index='keyword'),
              'phone': String,
              'enquiry': Unicode,
              'resolved': Boolean}



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
