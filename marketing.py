# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime
from collections import defaultdict
import random
from time import time

# Import from itools
from itools.datatypes import DateTime, Date, Integer, ISOCalendarDate, ISOTime
from itools.handlers import Text
from itools.xml import Parser, START_ELEMENT, END_ELEMENT, TEXT
from itools.stl import stl
from itools.web import get_context
from itools.cms.folder import Folder
from itools.cms import widgets
from itools.cms.messages import *
from itools.cms.registry import register_object_class

# Import from Abakuc
from utils import get_sort_name

#############################################################################
# Marketing form definition
#############################################################################
class Question(object):

    def __init__(self, code='0', type='MCQ', title=u'', options=[]):
        self.code = code
        self.type = type
        self.title = title
        self.options = options

    def to_str(self, encoding='UTF-8'):
        s = '<question code="%s" type="%s">\n' \
            % (self.code, self.type)
        title = self.title.replace('&', '&amp;')
        s += '  <title>%s</title>\n' % title.encode(encoding)
        for option in self.options:
            option = option.replace('&', '&amp;')
            s += '  <option>%s</option>\n' % option.encode(encoding)
        s += '</question>\n'
        return s

    #########################################################################
    # API
    def get_main_code(self):
        code = self.code.strip()
        if code.isdigit():
            return int(code)
        for i, c in enumerate(code):
            if not c.isdigit():
                break
        return int(code[:i])

    def get_sub_code(self):
        code = self.code.strip()
        if code.isdigit():
            return None
        for i, c in enumerate(code):
            if not c.isdigit():
                break
        return code[i:]


    def get_responses(self):
        return self.responses

    #########################################################################
    # The methods below are used for the user interface
    def options_as_text(self):
        """Used in the edit template."""
        return '\n'.join(self.options)


    #def correct_options_as_text(self):
    #    return ' '.join(self.correct_options)

    def input_type(self):
        if self.type == 'MCQ':
            return 'radio'
        elif self.type == 'MAQ':
            return 'checkbox'
        return 'textbox'

    def is_mcq(self):
        return self.type == 'MCQ'

    def is_maq(self):
        return self.type == 'MAQ'

    def is_textbox(self):
        return self.type == 'TEXTBOX'


class Survey(Text):

    __slots__ = ['uri', 'timestamp', 'parent', 'name', 'real_handler',
                  'questions']


    def new(self):
        self.questions = {}


    def _load_state_from_file(self, file):
        # TEST 015
        questions = {}
        for event, value, line_number in Parser(file.read()):
            if event == START_ELEMENT:
                namespace_uri, local_name, attributes = value
                if local_name == 'question':
                    options = []
                    code = attributes[(None, 'code')]
                    type = attributes[(None, 'type')]
                    #correct_options = attributes[(None, 'correct_options')].split()
                    question = Question(code=code, type=type)
            elif event == END_ELEMENT:
                namespace, local_name = value
                if local_name == 'question':
                    question.title = title
                    #question.answer = answer
                    question.options = options
                    questions[code] = question
                elif local_name == 'title':
                    title = unicode(text.strip(), 'utf-8')
                #elif local_name == 'answer':
                #    answer = unicode(text.strip(), 'utf-8')
                elif local_name == 'option':
                    options.append(unicode(text.strip(), 'utf-8'))
            elif event == TEXT:
                text = value

        self.questions = questions


    def to_str(self, encoding='UTF-8'):
        lines = ['<?xml version="1.0" encoding="%s"?>\n' % encoding,
                 '<survey>\n']
        # Business functions
        # Questions
        questions = self.questions
        codes = questions.keys()
        codes.sort()
        for code in codes:
            lines.append(questions[code].to_str(encoding))
        lines.append('</survey>')
        return ''.join(lines)

    def get_responses(self):
        return 0 

#############################################################################
# Exam results
#############################################################################
class Attempt(object):

    def __init__(self, username=None, date=None,  mark=0.0):
        self.username = username
        self.date = date
        self.questions = {}
        self.mark = mark


    def set_score(self, exam):
        """ compute the score for an exam"""
        mark = 100.0
        self.mark = mark

    def get_score(self):
        return self.mark

    def get_time_taken(self):
        time_taken = 20
        return self.time_taken

class Response(Text):
    """
    The handler's state is stored in the variable 'attempts', whose
    structure is:

      {username: [attempt1, attempt2, ...], }

    For instance:

      {'1': [<abakuc/exam.Exam.Attempt object at 0x44fd450c>],
       '2': [<abakuc/exam.Exam.Attempt object at 0x4445760c>,
                          <abakuc/exam.Exam.Attempt object at 0x444c580c>],
       '3': [<abakuc/exam.Exam.Attempt object at 0x4503be2c>]}
    """

    __slots__ = ['uri', 'timestamp', 'parent', 'name', 'real_handler',
                 'attempts']


    def new(self):
        self.attempts = {}

    def _load_state_from_file(self, file):
        # TEST 015
        attempts = {}
        for event, value, line_number in Parser(file.read()):
            if event == START_ELEMENT:
                namespace_uri, local_name, attributes = value
                if local_name == 'attempt':
                    attempt = Attempt()
                    attempt.username = attributes[(None, 'username')]
                    date = attributes[(None, 'date')]
                    # FIXME 015 Remove the "try/except" block after upgrading
                    try:
                        attempt.date = DateTime.decode(date)
                    except ValueError:
                        date, time = date.split(' ')
                        date = ISOCalendarDate.decode(date)
                        time = ISOTime.decode(time)
                        attempt.date = datetime.combine(date, time)
                    #attempt.time_taken = int(attributes[(None, 'time_taken')])
                    attempt.mark = float(attributes[(None, 'mark')])
                elif local_name == 'question':
                    question_code = attributes[(None, 'code')]
                    question_answers = []
            elif event == END_ELEMENT:
                namespace, local_name = value
                if local_name == 'attempt':
                    user_attempts = attempts.setdefault(attempt.username, [])
                    user_attempts.append(attempt)
                elif local_name == 'question':
                    attempt.questions[question_code] = question_answers
                elif local_name == 'answer':
                    question_answers.append(int(answer_value))
            elif event == TEXT:
                answer_value = value

        self.attempts = attempts


    def to_str(self, encoding='UTF-8'):
        lines = ['<?xml version="1.0" encoding="%s"?>' % encoding,
                 '<response>']
        attempts = self.attempts
        for username in attempts:
            for attempt in attempts[username]:
                lines.append(
                    '<attempt username="%s" date="%s" mark="%2.2f">'
                    % (username, attempt.date.strftime('%Y-%m-%d %H:%M'), attempt.mark))
                questions = attempt.questions
                for question_code in questions:
                    lines.append('  <question code="%s">' % question_code)
                    for answer in questions[question_code]:
                        lines.append('    <answer>%s</answer>' % answer)
                    lines.append('  </question>')
                lines.append('</attempt>')
        lines.append('</response>')
        return '\n'.join(lines)

    def get_analysis(self):
        attempts = self.attempts
        totals = {}
        if len(attempts) < 1:
            return totals
        else:
            for attempt in attempts:
                responses = []
                for username in attempts:
                    for attempt in attempts[username]:
                        response = attempt.questions
                    responses.append(response)
            answered = defaultdict(list)
            for response in responses:
                for q, a in response.items():
                    answered[q].extend(a)
            for q, answers in answered.items():
                counts = totals[q] = defaultdict(int)
                for a in answers:
                    counts[a] += 1
            return totals

    def get_no_responses(self):
        return len(self.attempts)

    def get_first_attempt(self, username):
        attempts = self.attempts
        if username in attempts:
            attempts = attempts[username]
            attempts.sort(lambda x,y: cmp(x.date, y.date))
            return attempts[0]
        return None


    def get_last_attempt(self, username):
        attempts = self.attempts
        if username in attempts:
            attempts = attempts[username]
            attempts.sort(lambda x,y: cmp(x.date, y.date))
            return attempts[-1]
        return None


    def get_n_attempts(self, username):
        return len(self.attempts.get(username, []))

    def get_n_totals(self, option):
        return len(self.attempts.get(option, []))

    def remove_attempt(self, username, date):
        """ date = '2004-06-30T13:20:00' """
        if username in self.attempts:
            attempts = [ x for x in self.attempts[username]
                         if x.date.isoformat() != date ]
            self.set_changed()
            if attempts:
                self.attempts[username] = attempts
            else:
                del self.attempts[username]

    def get_respondants(self):
        attempts = self.attempts
        respondants = []
        for username in attempts:
            respondants.append(username)
        return respondants

    def get_response(self, username):
        attempts = self.attempts
        responses = []
        for attempt in attempts[username]:
            response = attempt.questions
            return response
        #responses.append(response)
        #return responses

class Marketing(Folder):

    class_id = 'marketing'
    class_layout = {
        '.survey': Survey,
        '.response': Response}
    class_title = u'Training Marketing Form'
    class_description = u'Marketing forms for training programmes.'
    class_icon16 = 'abakuc/images/Marketing16.png'
    class_icon48 = 'abakuc/images/Marketing48.png'
    class_views = [['edit'],
                   ['edit_metadata_form'],
                   ['add_question_form'],
                   ['analyse', 'csv'],
                   ['clean_attempts_form'],
                   ['fill_form']]


    def new(self):
        Folder.new(self)
        self.cache['.survey'] = Survey()
        self.cache['.response'] = Response()


    def get_definition(self):
        return self.get_handler('.survey')
    definition = property(get_definition, None, None, '')


    def get_results(self):
        return self.get_handler('.response')
    results = property(get_results, None, None, '')


    #########################################################################
    # Index and search
    def text(self):
        # XXX To be fixed
        return u''


    #########################################################################
    # API
    #########################################################################
    def get_score(self, username):
        score = 100.0
        return score


    def get_points(self, username):
        score = self.get_score(username)
        points = self.get_property('abakuc:points')
        #if score < 70.0:
        #    return 0
        #n_attempts = self.results.get_n_attempts(username)
        #points = score/n_attempts
        #last_attempt = self.results.get_last_attempt(username)
        #exam_time = self.get_property('abakuc:exam_time')
        #if score > 90.0:
        #    if last_attempt.time_taken < exam_time:
        #        points += 20
        #if last_attempt.time_taken > exam_time:
        #    delay = last_attempt.time_taken - exam_time
        #    points = points - delay
        return int(points)


    def get_result(self, username=None):
        """
        Return a four-elements tuple:
        - has the user passed the exam (bool)
        - number of attempts (int)
        - time spent (int)
        - mark scored (float)
        - date of last attempt
        """
        if username is None:
            username = get_context().user.name

        n_attempts = self.results.get_n_attempts(username)
        if n_attempts == 0:
            return False, 0, 0, 0.0, ''

        last_attempt = self.results.get_last_attempt(username)
        time_spent = 20

        mark = last_attempt.get_score()
        date = Date.encode(last_attempt.date)

        has_passed = mark >= self.get_property('abakuc:pass_marks_percentage')
        return has_passed, n_attempts, time_spent, mark, date


    def get_first_result(self, username=None):
        """
        Return a four-elements tuple:
        - has the user passed the exam (bool)
        - number of attempts (int)
        - time spent (int)
        - mark scored (float)
        - date of first attempt
        """
        if username is None:
            username = get_context().user.name

        n_attempts = self.results.get_n_attempts(username)
        if n_attempts == 0:
            return False, 0, 0, 0.0, ''

        first_attempt = self.results.get_first_attempt(username)
        time_spent = first_attempt.time_taken

        mark = first_attempt.get_score()
        date = Date.encode(first_attempt.date)

        has_passed = mark >= self.get_property('abakuc:pass_marks_percentage')
        return has_passed, n_attempts, time_spent, mark, date


    def get_module(self):
        return self.parent


    def get_program(self):
        return self.parent.parent

    #########################################################################
    # User Interface
    #########################################################################

    #########################################################################
    # Edit
    edit__access__ = 'is_training_manager'
    edit__label__ = u'Edit'
    def edit(self, context):
        # Columns
        columns = [('code', u'Code'), ('title', u'Title'), ('type', u'Type')]
        # Rows
        rows = []
        for code, question in self.definition.questions.items():
            # Title
            title = question.title
            if len(title) > 65:
                title = title[:60] + '...'
            # Order
            order = get_sort_name(question.code)
            # Append
            url = ';edit_question_form?code=%s' % code
            rows.append({
                'checkbox': True,
                'id': code,
                'code': code,
                'title': (title, url),
                'type': question.type,
                'order': order,
                         })
        total = len(rows)
        # sort by id (order)
        sortby = context.get_form_value('sortby', 'id')
        sortorder = context.get_form_value('sortorder', 'up')
        rows.sort(key=lambda x: x[sortby])
        if sortorder == 'down':
            rows.reverse()
        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        rows = rows[start:start+20]
        # Actions
        message = self.gettext(MSG_DELETE_SELECTION)
        actions = [('add_question_form', u'Add question', 'button_ok', None),
                   ('remove', u'Remove', 'button_delete',
                 'return confirmation("%s");' % message.encode('utf_8')),
                 ('fill_form', u'Preview form', 'button_ok', None)]

        # Build the namespace
        namespace = {}
        namespace['table'] = widgets.table(columns, rows, [sortby], sortorder,
                                           actions, self.gettext)
        namespace['batch'] = widgets.batch(context.uri, start, 20, total)

        handler = self.get_handler('/ui/abakuc/marketing/edit.xml')
        return stl(handler, namespace)


    remove__access__ = 'is_training_manager'
    def remove(self, context):
        ids = context.get_form_values('ids')
        if not ids:
            return context.come_back(u'No question(s) selected.')
        for code in ids:
            del self.definition.questions[code]

        self.definition.set_changed()
        return context.come_back(u'Question(s) removed.')


    edit_question_form__access__ = 'is_training_manager'
    edit_question_form__label__ = u'View'
    def edit_question_form(self, context):
        namespace = {}
        code = context.get_form_value('code')
        namespace['question'] = self.definition.questions[code]

        handler = self.get_handler('/ui/abakuc/marketing/edit_question.xml')
        return stl(handler, namespace)

    edit_question__access__ = 'is_training_manager'
    def edit_question(self, context):
        # Get form values
        old_code = context.get_form_value('old_code')
        new_code = context.get_form_value('new_code').strip()
        title = context.get_form_value('title')
        options = context.get_form_value('options')
        # Decode values
        title = unicode(title, 'utf-8')
        options = [ x.strip() for x in unicode(options, 'utf-8').splitlines() ]
        options = [ x for x in options if x ]
        # Get the definition
        definition = self.definition
        definition.set_changed()
        # Modify the question
        question = definition.questions.pop(old_code)
        question.code = new_code
        question.title = title
        question.options = options
        definition.questions[new_code] = question

        goto = ';edit_question_form?code=%s' % new_code
        return context.come_back(u'Question changed.', goto=goto)


    #########################################################################
    # Metadata
    edit_metadata_form__access__ = 'is_training_manager'
    edit_metadata_form__label__ = u'Metadata'
    def edit_metadata_form(self, context):
        # Build the namespace
        namespace = {}
        namespace['dc:title'] = self.get_property('dc:title', language='en')
        for pname in ['dc:description', 'abakuc:points']:
            namespace[pname] = self.get_property(pname)

        # Business functions
        #namespace['abakuc:topic'] = BusinessFunction.get_options()
        #namespace['abakuc:topic'].insert(0, {'id': 'all',
        #                                           'label': 'All'})
        #business_functions = self.definition.business_functions
        #for x in namespace['abakuc:topic']:
        #    x['selected'] = x['id'] in business_functions

        handler = self.get_handler('/ui/abakuc/marketing/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_training_manager'
    def edit_metadata(self, context):
        # The title
        self.set_property('dc:title', context.get_form_value('dc:title'),
                          language='en')
        # The other metadata
        for key in ['dc:description', 'abakuc:points']:
             self.set_property(key, context.get_form_value(key))
        # Business functions
        #business_functions = context.get_form_values('topic')
        #self.set_property('abakuc:topic', tuple(business_functions))
        #self.definition.business_functions = business_functions

        self.definition.set_changed()
        return context.come_back(u'Metadata changed.')


    #########################################################################
    # Add
    add_question_form__access__ = 'is_training_manager'
    add_question_form__label__ = u'Add question'
    def add_question_form(self, context):
        handler = self.get_handler('/ui/abakuc/marketing/add_question.xml')
        return stl(handler)

    add_question__access__ = 'is_training_manager'
    add_question__label__ = u'view'
    def add_question(self, context):
        code =  context.get_form_value('code')
        type =  context.get_form_value('type')
        title =  context.get_form_value('title')
        options =  context.get_form_value('options')
        # Build the question
        title = unicode(title, 'utf-8')
        options = unicode(options, 'utf-8')
        options = [ x.replace('&', '&amp;') for x in options.splitlines() if x ]
        question = Question(code, type, title, options)
        # Add the question
        definition = self.definition
        definition.set_changed()
        definition.questions[code] = question

        return context.come_back(u'Question added.', goto=';edit')

    #########################################################################
    # Fill marketing form
    fill_form__access__ = 'is_allowed_to_fill_marketing'
    fill_form__label__ = u'Fill form'
    def fill_form(self, context):
        user = context.user
        # Build the namespace
        namespace = {}
        questions = self.definition.questions
        # Metadata
        namespace['user'] = user
        namespace['questions'] = [ questions[x] for x in questions ]
        print namespace['questions']
        namespace['title'] = self.get_property('dc:title')
        namespace['user_attempts'] = self.results.get_n_attempts(user.name) + 1
        handler = self.get_handler('/ui/abakuc/marketing/fill_form.xml')
        data = stl(handler, namespace)
        # Send data
        return data

    fill__access__ = 'is_allowed_to_fill_marketing'
    def fill(self, context):
        user = context.user 
        username = context.user.name
        questions = self.definition.questions
        filled = self.results.get_n_attempts(username)
        if filled == 0:
            attempt = Attempt(username, datetime.now())
            for  key in context.get_form_keys():
                if key in questions:
                    value = context.get_form_values(key)
                    value = [ int(x) for x in value ]
                    response = self.definition.get_responses()
                    attempt.questions[key] = value

            self.results.set_changed()
            attempts = self.results.attempts.setdefault(username, [])
            attempt.set_score(self)
            attempts.append(attempt)
            # Points
            current_points = self.get_points(user.name)
            # Get user's old points
            existing_points = user.get_property('abakuc:points')
            # Set user's points
            points = str(existing_points + current_points)
            user.set_property('abakuc:points', points)
            # Send mail to the manager
            main_body = []
            for question_id, answers in attempt.questions.items():
                question = questions[question_id]
                question_title = question.title 
                answer_title = ', '.join(
                    [ question.options[answer] for answer in answers
                      if answer < len(question.options) ])

                
                # Get the definition
                definition = self.definition
                definition.set_changed()
                # Modify the question
                response += 1
                item_line = '%s : %s' % (question_title, answer_title)
                main_body.append(item_line)
            # Redirect the user to the end of Module
            message = 'Thank you'
            return context.come_back(message, '../;end')
        else:
            message = 'Form already submited, please proceed!'
            return context.come_back(message, '../;end')

    analyse__access__ = 'is_allowed_to_view_statistics' 
    analyse__label__ = u'Analysis overview'
    analyse__sublabel__ = u'Analysis overview'
    def analyse(self, context):
        questions = self.definition.questions
        tot = self.results.get_analysis()
        namespace = {}
        namespace['title'] = self.get_property('dc:title')
        namespace['download'] = ';csv'
        responses = self.results.get_no_responses() 
        namespace['responses'] = responses
        # Analyse
        if responses < 1:
            namespace['totals'] = None
        else:
            results = []
            for question_id, y in questions.items():
                ns = {}
                question = questions[question_id]
                question_title = question.title
                ns['type'] = question.type
                if question.type == 'MCQ':
                    ns['type_full_name'] = 'Multiple Choice Question'
                else:
                    ns['type_full_name'] = 'Multiple Answer Question'
                ns['title'] = question_title
                option = []
                # XXX Perhaps it can be done more cleanly
                options = [{'q_code': question_id, 'option': id, 'title': x,
                            'type': question.type,
                            'total': str([r[1] for r in tot[question_id].items()
                                          if id == r[0]]).strip('[]'), 
                            'percentage': str([ float(r[1])/float(responses)*100.0 for r in tot[question_id].items()
                                          if id == r[0]]).strip('[]')[:5]}
                                            for id, x in enumerate(y.options)]
                ns['options'] = options
                option.append(ns)
                results.append(ns)
            namespace['totals'] = results 

        handler = self.get_handler('/ui/abakuc/marketing/analysis.xml')
        return stl(handler, namespace)

    csv__access__ = 'is_allowed_to_view_statistics' 
    csv__label__ = u'Download'
    csv__sublabel__ = u'Download'
    def csv(self, context):
        root = context.root
        companies = root.get_handler('companies')
        users = root.get_handler('users')

        questions = self.definition.questions
        tot = self.results.get_analysis()
        data = []
        keys = [
            "topic", "type",
            "firstname", "lastname", "function","email", "contact_me",
            "company_name", "website", "address",
            "town", "county", "region", "postcode",
            "country", "phone", "fax"
            ]
        # Questions
        for question_id, y in self.definition.questions.items():
            keys.append(u'%s' % question_id)
            for id, x in enumerate(y.options):
                keys.append(u'%s' % x)
        # The header
        header = ','.join([ '"%s"' % x for x in keys ]) + u'\n'
        data.append(header)

        respondants = self.results.get_respondants()
        for username in respondants:
            line = []
            user = users.get_handler(username)
            # Address
            address_handler = user.get_address()
            if address_handler is None:
                phone = 'not available'
                fax = 'not available'
                address = 'not available'
                town = 'not available'
                post_code = 'not available'
                county = 'not available'
                region = 'not available'
                country = 'not available'
            else:
                get_property = address_handler.metadata.get_property
                phone = get_property('abakuc:phone')
                fax = get_property('abakuc:fax')
                address = get_property('abakuc:address')
                town = get_property('abakuc:town')
                postcode = get_property('abakuc:postcode')
                county = get_property('abakuc:county')
                if county is not None:
                    from root import world
                    for row_number in world.search(county=county):
                        row = world.get_row(row_number)
                        country = row[6]
                        region = row[7]
            # Company
            if address_handler is not None:
                company = address_handler.parent
                if company is None:
                    company_title = 'not available'
                    company_type = 'not available'
                    company_topic = 'not available'
                    company_website = 'not available'
                else:
                    company_title = company.get_property('dc:title')
                    company_type = company.get_property('abakuc:type')
                    topic = company.get_property('abakuc:topic')
                    company_topic = topic[0]
                    company_website =  company.get_property('abakuc:website')
            else:
                company_title = 'not available'
                company_type = 'not available'
                company_topic = 'not available'
                company_website = 'not available'

            # User
            get_property = user.metadata.get_property

            line.append(u'"%s"' % company_topic)
            line.append(u'"%s"' % company_type)
            line.append(u'"%s"' % \
                        (get_property('ikaaro:firstname') or '').title())
            line.append(u'"%s"' % \
                        (get_property('ikaaro:lastname') or '').title())
            line.append(u'"%s"' % (get_property('abakuc:functions')))
            line.append(u'"%s"' % (get_property('ikaaro:email')))
            line.append(u'"%s"' % ('yes'))
            line.append(u'"%s"' % company_title)
            line.append(u'"%s"' % company_website)
            line.append(u'"%s"' % address)
            line.append(u'"%s"' % town)
            line.append(u'"%s"' % county)
            line.append(u'"%s"' % region)
            line.append(u'"%s"' % postcode)
            line.append(u'"%s"' % country)
            line.append(u'"%s"' % phone)
            line.append(u'"%s"' % fax)

            # Questions
            for question_id, y in self.definition.questions.items():
                line.append(u'%s' % question_id)
                options = []
                for id, x in enumerate(y.options):
                    options.append(id)
                response = \
                    self.results.get_response(username)[question_id]
                for x in options:
                    if x in response:
                        line.append(u'"1"')
                    else:
                        line.append(u'"0"')


            # Make the CSV file
            line = u','.join(line) + u'\n'
            data.append(line)
        response = context.response
        response.set_header('Content-Type', 'text/comma-separated-values')
        response.set_header('Content-Disposition',
                            'attachment; filename="expert_travel.csv"')
        return (u''.join(data)).encode('utf-8')


    ########################################################################
    # Exams overview
    ########################################################################
    clean_attempts_form__access__ = 'is_training_manager'
    clean_attempts_form__label__ = u'Maintenance'
    clean_attempts_form__sublabel__ = u'Exams'
    def clean_attempts_form(self, context):
        """ 
        TP1
          ta_34 mod2 exam1 attempt1 : mark 43%
          ta_34 mod2 exam1 attempt2 : mark 56% 
          ta_34 mod2 exam1 attempt3 : mark 0% 
        """ 
        users = context.root.get_handler('users')
        get_user = users.get_handler

        namespace = {}
        # Get the objects ta_attempts
        rows = []
        attempts = self.results.attempts
        for userid in attempts:
            user = get_user(userid)
            for attempt in attempts[userid]:
                points = int(self.get_points(userid))
                date = attempt.date.isoformat()
                url = self.get_pathto(users).resolve2(userid)
                id = ('%s##%s##%s##%s' % (self.abspath, userid,
                       date, points))
                username = user.get_property('ikaaro:username')
                #username = (firstname+lastname or '').title()
                rows.append({
                    'checkbox': True,
                    'id': id,
                    'username': (username, url),
                    'points': points,
                    'module': self.get_property('dc:title'),
                    'date': date,
                    'checked': ''})
        # Sort
        sortby = context.get_form_values('sortby', default=['username'])
        sortorder = context.get_form_value('sortorder', default='up')
        rows.sort(key=lambda x: x[sortby[0]])
        if sortorder == 'down':
            rows.reverse()

        # Batch
        start = context.get_form_value('batchstart', type=Integer, default=0)
        size = 50
        total = len(rows)
        namespace['batch'] = widgets.batch(context.uri, start, size, total)
        rows = rows[start:start+size]

        # Table
        columns = [('username', u'Username'),
                   ('points', u'Points'),
                   ('module', u'Module'),
                   ('date', u'Date')]
        actions = [('remove_attempts', u'Remove', None, None)]
        namespace['table'] = widgets.table(columns, rows, sortby, sortorder,
            actions, self.gettext)

        handler = self.get_handler('/ui/abakuc/training/clean_attempts.xml')
        return stl(handler, namespace)


    remove_attempts__access__ = 'is_training_manager'
    def remove_attempts(self, context):
        root = context.root
        ids = context.get_form_values('ids')
        users = context.root.get_handler('users')
        get_user = users.get_handler

        if not ids:
            return context.come_back(u'No attempts to removed.')

        for id in ids: 
            abspath, name, date, points = id.split('##')
            #exam = root.get_handler(abspath)
            self.results.remove_attempt(name, date)
            points = int(points)
            # Update the users points
            user = get_user(name)
            existing_points = user.get_property('abakuc:points')
            # Get the exam points based on score
            new_points = existing_points - points
            user.set_property('abakuc:points', new_points)

        return context.come_back(u'Attempt/s removed.')

register_object_class(Marketing)
