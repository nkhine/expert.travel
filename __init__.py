# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath, get_version
from itools.cms.skins import register_skin

# Import from abakuc
import metadata
from skins import FrontOffice
from root import Root


__version__ = get_version(globals())


# Register the skins
path = get_abspath(globals(), 'ui/abakuc')
register_skin('abakuc', path)

for name in ['uktravel']:
    path = get_abspath(globals(), 'ui/%s' % name)
    register_skin(name, FrontOffice(path))
