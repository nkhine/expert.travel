# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>


def title_to_name(title):
    title = title.encode('ascii', 'replace')
    title = title.lower()
    name = title.replace('/', '-').replace('?', '-')
    for c in '.,&()':
        name = name.replace(c, '')
    return '-'.join(name.split())



def get_host_prefix(context):
    hostname = context.uri.authority.host
    tab = hostname.split('.', 1)
    if len(tab)>1:
        return tab[0]
    return None

