# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Email, String, Unicode, DateTime
from itools.cms.csv import CSV
from itools.cms.registry import register_object_class


class EnquiriesLog(CSV):

    class_id = 'EnquiriesLog'
  
    schema = {'dateTime':DateTime,
              'typeEnquiry':String,
              'fullname':Unicode,
              'email':Email,
              'phone':String,
              'enquiry':Unicode}


    columns = ['dateTime','typeEnquiry','fullname','email','phone','enquiry']

class ApplicationsLog(CSV):

    class_id = 'EnquiriesLog'
  
    schema = {'dateTime':DateTime,
              'fullname':Unicode,
              'email':Email,
              'phone':String}


    columns = ['dateTime','fullname','email','phone']


register_object_class(EnquiriesLog)
register_object_class(ApplicationsLog)
