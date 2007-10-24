# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>


def title_to_name(title):
    title = title.encode('ascii', 'replace')
    title = title.lower()
    name = title.replace('/', '-').replace('?', '-')
    for c in '.,&()':
        name = name.replace(c, '')
    return '-'.join(name.split())

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

