# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Email, String, Unicode, DateTime
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class


class EnquiriesLog(CSV):

    class_id = 'EnquiriesLog'
  
    columns = ['dateTime', 'typeEnquiry', 'fullname', 'email', 'phone',
        'enquiry']
    schema = {'dateTime': DateTime,
              'typeEnquiry': String,
              'fullname': Unicode,
              'email': Email,
              'phone': String,
              'enquiry': Unicode}



class ApplicationsLog(CSV):

    class_id = 'ApplicationsLog'
  
    columns = ['dateTime', 'fullname', 'email', 'phone']
    schema = {'dateTime': DateTime,
              'fullname': Unicode,
              'email': Email,
              'phone': String}



register_object_class(EnquiriesLog)
register_object_class(ApplicationsLog)
