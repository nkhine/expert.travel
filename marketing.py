# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from the Standard Library
from datetime import datetime
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

      {'Claire_Taylor': [<abakuc/exam.Exam.Attempt object at 0x44fd450c>],
       'Emma_Bicknell2': [<abakuc/exam.Exam.Attempt object at 0x4445760c>,
                          <abakuc/exam.Exam.Attempt object at 0x444c580c>],
       'LINDA_MYERS': [<abakuc/exam.Exam.Attempt object at 0x4503be2c>]}
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
        score = 0.0
        last_attempt = self.results.get_last_attempt(username)
        if last_attempt:
            score = last_attempt.get_score()

        return score


    def get_points(self, username):
        score = self.get_score(username)
        if score < 70.0:
            return 0
        n_attempts = self.results.get_n_attempts(username)
        points = score/n_attempts
        last_attempt = self.results.get_last_attempt(username)
        exam_time = self.get_property('abakuc:exam_time')
        if score > 90.0:
            if last_attempt.time_taken < exam_time:
                points += 20
        if last_attempt.time_taken > exam_time:
            delay = last_attempt.time_taken - exam_time
            points = points - delay
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
    edit__access__ = 'is_allowed_to_edit'
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
        actions = [('remove', u'Remove', 'button_delete',
                 'return confirmation("%s");' % message.encode('utf_8'))]

        # Build the namespace
        namespace = {}
        namespace['table'] = widgets.table(columns, rows, [sortby], sortorder,
                                           actions, self.gettext)
        namespace['batch'] = widgets.batch(context.uri, start, 20, total)

        handler = self.get_handler('/ui/abakuc/marketing/edit.xml')
        return stl(handler, namespace)


    remove__access__ = 'is_allowed_to_edit'
    def remove(self, context):
        ids = context.get_form_values('ids')
        if not ids:
            return context.come_back(u'No question(s) selected.')
        for code in ids:
            del self.definition.questions[code]

        self.definition.set_changed()
        return context.come_back(u'Question(s) removed.')


    edit_question_form__access__ = 'is_allowed_to_edit'
    edit_question_form__label__ = u'View'
    def edit_question_form(self, context):
        namespace = {}
        code = context.get_form_value('code')
        namespace['question'] = self.definition.questions[code]

        handler = self.get_handler('/ui/abakuc/marketing/edit_question.xml')
        return stl(handler, namespace)

    edit_question__access__ = 'is_allowed_to_edit'
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
    edit_metadata_form__access__ = 'is_allowed_to_edit'
    edit_metadata_form__label__ = u'Metadata'
    def edit_metadata_form(self, context):
        # Build the namespace
        namespace = {}
        namespace['dc:title'] = self.get_property('dc:title', language='en')
        for pname in ['abakuc:exam_time', 'abakuc:questions_nums',
                      'abakuc:pass_marks_percentage']:
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


    edit_metadata__access__ = 'is_allowed_to_edit'
    def edit_metadata(self, context):
        # The title
        self.set_property('dc:title', context.get_form_value('dc:title'),
                          language='en')
        # The other metadata
        for key in ['abakuc:exam_time', 'abakuc:questions_nums',
                    'abakuc:pass_marks_percentage']:
             self.set_property(key, context.get_form_value(key))
        # Business functions
        #business_functions = context.get_form_values('topic')
        #self.set_property('abakuc:topic', tuple(business_functions))
        #self.definition.business_functions = business_functions

        self.definition.set_changed()
        return context.come_back(u'Metadata changed.')


    #########################################################################
    # Add
    add_question_form__access__ = 'is_allowed_to_edit'
    add_question_form__label__ = u'Add question'
    def add_question_form(self, context):
        handler = self.get_handler('/ui/abakuc/marketing/add_question.xml')
        return stl(handler)

    add_question__access__ = 'is_allowed_to_edit'
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
        namespace['title'] = self.get_property('dc:title')
        namespace['user_attempts'] = self.results.get_n_attempts(user.name) + 1
        handler = self.get_handler('/ui/abakuc/marketing/fill_form.xml')
        data = stl(handler, namespace)
        # Send data
        return data

    fill__access__ = 'is_allowed_to_fill_marketing'
    def fill(self, context):
        username = context.user.name
        filled = self.results.get_n_attempts(username)
        if filled == 0:
            questions = context.get_form_values('questions')
            attempt = Attempt(username, datetime.now())
            exam_questions = self.definition.questions
            for key in questions:
                if key in exam_questions:
                    value = context.get_form_values(key)
                    value = [ int(x) + 1 for x in value ]
                    attempt.questions[key] = value

            self.results.set_changed()
            attempts = self.results.attempts.setdefault(username, [])
            attempt.set_score(self)
            attempts.append(attempt)
            # Redirect the user to the end of Module
            message = 'Thank you'
            return context.come_back(message, '../;end')
        else:
            message = 'Form already submited, please proceed!'
            return context.come_back(message, '../;end')


register_object_class(Marketing)
