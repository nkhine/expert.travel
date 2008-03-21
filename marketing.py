
# Import from the Standard Library
import datetime
import smtplib

# Import from itools
from itools.stl import stl
from itools.cms.folder import Folder

# Import from TravelUni
import exam

class Question(exam.Question):

    def options_plus_dont_know(self):
        return self.options



class Marketing(exam.Exam):

    class_id = 'Marketing Form'
    class_title = u'Marketing Form'
    class_description = u'The marketing from...'
    class_icon48 = 'abakuc/images/Marketing48.png'


    #########################################################################
    # User Interface
    #########################################################################
    edit_metadata_form = Folder.edit_metadata_form
    edit_metadata = Folder.edit_metadata


    def add_question(self, context):
        handler = self.get_handler('/ui/abakuc/marketing/add_question.xml.en')
        return stl(handler)


    def edit_question(self, context):
        namespace = {}
        code = context.get_form_value('code')
        namespace['question'] = self.definition.questions[code]

        handler = self.get_handler('/ui/abakuc/marketing/edit_question.xml')
        return stl(handler, namespace) 


    #########################################################################
    # Fill form
    fill_form__access__ = 'is_allowed_to_view'
    fill_form__label__ = u'Fill marketing form'
    def fill_form(self, context):
        user = context.user
        # Build the namespace
        namespace = {}
        # Questions
        no_questions = self.get_property('abakuc:questions_nums')
        questions = self.definition.questions
        question_keys = questions.keys()
        question_keys.sort()
        namespace['questions'] = [ questions[x] for x in question_keys ]

        handler = self.get_handler('/ui/abakuc/marketing/fill_form.xml')
        return stl(handler, namespace) 


    fill__access__ = 'is_allowed_to_view'
    def fill(self, context):
        user, root = context.user, context.root

        questions = self.definition.questions

        # Store the results
        attempt = exam.Attempt(user.name, datetime.datetime.now(), 0)
        for key in context.get_form_keys():
            if key in questions:
                value = context.get_form_values(key)
                value = [ int(x) for x in value ]
                attempt.questions[key] = value

        # Send an email to all manager in this Tourist Office
        #office = self.get_site_root()
        #manager_names = office.get_managers_names()
        #if manager_names:
        #    # Build the "to" address
        #    user_folder = root.get_handler('users')
        #    manager_emails = [
        #        user_folder.get_handler(x).get_property('ikaaro:email')
        #        for x in manager_names ]
        #    to_addr = ', '.join(manager_emails)

        #    get_property = user.metadata.get_property
        #    branch = user.get_branch()
        #    from_addr = get_property('ikaaro:email')
        #    fullname = u"%s %s" % (get_property('ikaaro:firstname'),
        #                           get_property('ikaaro:lastname'))
        #    subject = u'Marketing Interest Feedback from "%s"' % fullname
        #    body = 'Record of %s' % fullname
        #    body = body + '\n' + len(body)  * '=' + '\n'
        #    user_infos = []
        #    user_infos.append(fullname)
        #    user_infos.append(from_addr)
        #    user_infos.append(get_property('abakuc:business_function'))
        #    user_infos.append(get_property('abakuc:company_name') or '')
        #    if branch is None:
        #        user_infos.append('  address not available')
        #    else:
        #        user_infos.append('  ' + branch.get_property('abakuc:address'))
        #        user_infos.append('  ' + branch.get_property('abakuc:city'))
        #        user_infos.append('  ' + branch.get_property('abakuc:postcode'))
        #    user_infos.append('\n')
        #    body = body + '\n'.join(user_infos)
        #    body = body + '\nAnswer to Questions\n====================\n'
        #    body_main = []
        #    for question_id, answers in attempt.questions.items():
        #        question = questions[question_id]
        #        question_title = question.title
        #        answer_title = ', '.join(
        #            [ question.options[answer] for answer in answers
        #              if answer < len(question.options) ])

        #        item_line = '%s : %s' % (question_title, answer_title)
        #        body_main.append(item_line)

        #    body = '\n' + body + '\n'.join(body_main)
        #    try:
        #        root.send_email(from_addr, to_addr, subject, body)
        #    except smtplib.SMTPRecipientsRefused:
        #        message = (u'Your email is not allowed to be used here '
        #                   u'(take a look at your email format)')
        #    except smtplib.SMTPSenderRefused:
        #        message = u'Mail server error, please retry later'
        #    else:
        #        results = self.results
        #        results.set_changed()
        #        attempts = results.attempts.setdefault(user.name, [])
        #        attempts.append(attempt)
        #        message = u'The marketing form has been filled.'

        message = u'The marketing form has been filled.'
        return context.come_back(message, '../;end')
