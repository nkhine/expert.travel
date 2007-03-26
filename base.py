# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools import get_abspath
from itools.gettext.domains import register_domain
from itools.cms.Handler import Handler as BaseHandler
from itools.cms.Folder import Folder as BaseFolder



class Handler(BaseHandler):

    class_domain = 'abakuc'



class Folder(Handler, BaseFolder):
    pass



# Register domain (i18n)
path = get_abspath(globals(), 'locale')
register_domain(Handler.class_domain, path)
