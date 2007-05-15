# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>



def title_to_name(title):
    title = title.encode('ascii', 'replace')
    name = title.lower().replace('/', '_').replace('?', '_')
    return '_'.join(name.split())

