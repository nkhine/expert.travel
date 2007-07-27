# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath, get_version
from itools.cms.skins import register_skin

# Import from abakuc
import metadata
from skins import FrontOffice, FOCompanies, DestinationsSkin
from root import Root


__version__ = get_version(globals())


# Register the skins
path = get_abspath(globals(), 'ui/abakuc')
register_skin('abakuc', path)

path = get_abspath(globals(), 'ui/countries')
register_skin('countries', FrontOffice(path))

path = get_abspath(globals(), 'ui/destinations')
register_skin('destinations', DestinationsSkin(path))

for name in ['companies']:
    path = get_abspath(globals(), 'ui/%s' % name)
    register_skin(name, FOCompanies(path))

for name in ['uk', 'fr']:
    path = get_abspath(globals(), 'ui/%s' % name)
    register_skin(name, FrontOffice(path))
