# -*- coding: ISO-8859-1 -*-

# Import from Python
import datetime

# Import from itools
import itools
from itools.workflow.workflow import Workflow
from itools.web import get_context
from itools.cms.workflow import WorkflowAware as ikaaroWorkflowAware
from itools.cms.html import XHTMLFile as ikaaroHTML
from itools.cms.registry import register_object_class

# Import from here
from Handler import Handler



# Workflow definition
workflow = Workflow()

# Specify the workflow states
workflow.add_state(u'private', title=u'Private',
                   description=(u'A private document only can be reached by'
                                u' authorized users.'))
workflow.add_state(u'pending', title=u'Pending',
                   description=(u'A pending document awaits review from'
                                ' authorized users to be keep for waiting.'))
workflow.add_state(u'public', title=u'Public',
                   description=(u'A public document can be reached by even'
                                u' anonymous users.'))
workflow.add_state(u'waiting', title=u'Waiting',
                   description=(u'A waiting document awaits validation from '
                                'authtorized users to be published.'))

# Specify the workflow transitions
workflow.add_trans('request', 'private', 'pending',
                   description=u'Request the document publication.')
workflow.add_trans('reject', 'pending', 'private',
                   description=u'Reject the document.')
workflow.add_trans('accept', 'pending', 'waiting',
                   description=u'Accept the document.')
workflow.add_trans('publish', 'waiting', 'public',
                   description=u'Make the document public.')
workflow.add_trans('retire', 'public', 'private',
                   description=u'Retire the document.')
# Specify the initial state (try outcommenting this)
workflow.set_initstate('private')



class TraveluniWorkflowAware(ikaaroWorkflowAware):
    """Workflow definition for the traveluni documents"""

    workflow = workflow

    

class iHTML(Handler, TraveluniWorkflowAware, ikaaroHTML):
    pass

register_object_class(iHTML)


workflow = Workflow()
workflow.add_state(u'public', title=u'Public',
                   description=(u'A public document can be reached by even'
                                u' anonymous users.'))
workflow.set_initstate('public')


class PublicWorkflowAware(ikaaroWorkflowAware):
    """Substitute basic workflow definition by a default public state"""

    workflow = workflow

