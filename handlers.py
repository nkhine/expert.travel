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
  
    columns = ['datetime', 'user_id', 'phone', 'enquiry_type', 
               'enquiry_subject', 'enquiry', 'resolved']
    schema = {'datetime': DateTime,
              'user_id': String(index='keyword'),
              'phone': String,
              'enquiry_type': EnquiryType,
              'enquiry_subject': Unicode,
              'enquiry': Unicode,
              'resolved': Boolean}


    GET__access__ = 'is_reviewer_or_member'
    __view__access__ = 'is_reviewer_or_member'



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
