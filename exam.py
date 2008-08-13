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
from itools.cms.catalog import schedule_to_reindex

# Import from Abakuc
from namespaces import BusinessFunction
from utils import get_sort_name


#############################################################################
# Exam definition
#############################################################################
class Question(object):

    def __init__(self, code='0', type='MCQ', title=u'', correct_options=[],
                 answer=u'', options=[]):
        if isinstance(correct_options, str):
            correct_options = correct_options.split()

        self.code = code
        self.type = type
        self.title = title
        self.correct_options = correct_options
        self.answer = answer
        self.options = options


    def to_str(self, encoding='UTF-8'):
        correct_options = ' '.join(self.correct_options)
        s = '<question code="%s" type="%s" correct_options="%s">\n' \
            % (self.code, self.type, correct_options.replace('&', '&amp;'))
        title = self.title.replace('&', '&amp;')
        s += '  <title>%s</title>\n' % title.encode(encoding)
        answer = self.answer.replace('&', '&amp;')
        s += '  <answer>%s</answer>\n' % answer.encode(encoding)
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


    def correct_options_as_text(self):
        return ' '.join(self.correct_options)


    def input_type(self):
        if self.type == 'MCQ':
            return 'radio'
        return 'checkbox'


    def is_mcq(self):
        return self.type == 'MCQ'



class Definition(Text):

    __slots__ = ['uri', 'timestamp', 'parent', 'name', 'real_handler',
                 'business_functions', 'questions']


    def new(self):
        self.business_functions = []
        self.questions = {}


    def _load_state_from_file(self, file):
        # TEST 015
        business_functions = []
        questions = {}
        for event, value, line_number in Parser(file.read()):
            if event == START_ELEMENT:
                namespace_uri, local_name, attributes = value
                if local_name == 'question':
                    options = []
                    code = attributes[(None, 'code')]
                    type = attributes[(None, 'type')]
                    correct_options = attributes[(None, 'correct_options')].split()
                    question = Question(code=code, type=type,
                                        correct_options=correct_options)
            elif event == END_ELEMENT:
                namespace, local_name = value
                if local_name == 'business_function':
                    business_functions.append(text)
                elif local_name == 'question':
                    question.title = title
                    question.answer = answer
                    question.options = options
                    questions[code] = question
                elif local_name == 'title':
                    title = unicode(text.strip(), 'utf-8')
                elif local_name == 'answer':
                    answer = unicode(text.strip(), 'utf-8')
                elif local_name == 'option':
                    options.append(unicode(text.strip(), 'utf-8'))
            elif event == TEXT:
                text = value

        self.business_functions = business_functions
        self.questions = questions


    def to_str(self, encoding='UTF-8'):
        lines = ['<?xml version="1.0" encoding="%s"?>\n' % encoding,
                 '<exam>\n']
        # Business functions
        for business_function in self.business_functions:
            lines.append('  <business_function>%s</business_function>\n'
                         % business_function)
        # Questions
        questions = self.questions
        codes = questions.keys()
        codes.sort()
        for code in codes:
            lines.append(questions[code].to_str(encoding))
        lines.append('</exam>')
        return ''.join(lines)



#############################################################################
# Exam results
#############################################################################
class Attempt(object):

    def __init__(self, username=None, date=None, time_taken=None, mark=0.0):
        self.username = username
        self.date = date
        self.time_taken = time_taken
        self.questions = {}
        self.mark = mark


    def set_score(self, exam):
        """ compute the score for an exam"""
        mark = 0.0
        if self.questions:
            n_right_answers = n_questions = 0
            questions = exam.definition.questions
            for question_code, answers in self.questions.items():
                if question_code in questions:
                    n_questions += 1
                    question = questions[question_code]
                    if answers:
                        for answer in answers:
                            if str(answer) not in question.correct_options:
                                break
                        else:
                            n_right_answers += 1

            mark = n_right_answers * (100.0/n_questions)

        self.mark = mark


    def get_score(self):
        return self.mark

    def get_time_taken(self):
        return self.time_taken



class Results(Text):
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
                    attempt.time_taken = int(attributes[(None, 'time_taken')])
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
                 '<results>']
        attempts = self.attempts
        for username in attempts:
            for attempt in attempts[username]:
                lines.append(
                    '<attempt username="%s" date="%s" time_taken="%s" mark="%2.2f">'
                    % (username, attempt.date.strftime('%Y-%m-%d %H:%M'),
                       attempt.time_taken, attempt.mark))
                questions = attempt.questions
                for question_code in questions:
                    lines.append('  <question code="%s">' % question_code)
                    for answer in questions[question_code]:
                        lines.append('    <answer>%s</answer>' % answer)
                    lines.append('  </question>')
                lines.append('</attempt>')
        lines.append('</results>')
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



class Exam(Folder):

    class_id = 'Exam'
    class_layout = {
        '.definition': Definition,
        '.results': Results}
    class_title = u'Training Exam'
    class_description = u'Exams evaluate travel agents.'
    class_icon16 = 'abakuc/images/Exam16.png'
    class_icon48 = 'abakuc/images/Exam48.png'
    class_views = [['edit'],
                   ['edit_metadata_form'],
                   ['clean_attempts_form'],
                   ['add_question_form'],
                   ['take_exam_form']]


    def new(self):
        Folder.new(self)
        self.cache['.definition'] = Definition()
        self.cache['.results'] = Results()


    def get_definition(self):
        return self.get_handler('.definition')
    definition = property(get_definition, None, None, '')


    def get_results(self):
        return self.get_handler('.results')
    results = property(get_results, None, None, '')

    #########################################################################
    # Index and search
    def text(self):
        # XXX To be fixed
        return u''

    #######################################################################
    # ACL
    #######################################################################
    def is_training_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        ## Is reviewer or member
        return self.has_user_role(user.name, 'abakuc:training_manager')

    def is_allowed_to_manage(self, user, object):
        if user is None:
            return False
        if self.is_training_manager(user, object):
            return True

        return user is not None and user.is_branch_member(user, self)

    def is_allowed_to_edit(self, user, object):
        if self.is_training_manager(user, object):
            return True

        if user is None:
            return False


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
        '''
        Here we give the uesr points based on their performance.
        The maximum number of points that they can get is 120
        per exam. Based on:
        If user scores above 90% and the last attempt is
        less then the given time we add 20 points.
        '''
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
        time_spent = last_attempt.time_taken

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
        # Add the js scripts
        context.scripts.append('/ui/table/javascript.js')        
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
        # FIXME 015 Correctly sort by code (order)
        sortby = context.get_form_value('sortby', 'code')
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
                    'return confirmation(%s);' % message.encode('utf_8')),
                    ('take_exam_form', u'Preview exam', 'button_ok', None)]

        # Build the namespace
        namespace = {}
        namespace['table'] = widgets.table(columns, rows, [sortby], sortorder,
                                           actions, self.gettext)
        namespace['batch'] = widgets.batch(context.uri, start, 20, total)

        handler = self.get_handler('/ui/abakuc/exam/edit.xml')
        return stl(handler, namespace)


    remove__access__ = 'is_training_manager'
    def remove(self, context):
        ids = context.get_form_values('ids')
        if not ids:
            return context.come_back(u'Please select a question to remove')
        self.definition.set_changed()
        for code in ids:
            del self.definition.questions[code]

        return context.come_back(u'Question(s) removed.')


    edit_question_form__access__ = 'is_training_manager'
    edit_question_form__label__ = u'View'
    def edit_question_form(self, context):
        namespace = {}
        code = context.get_form_value('code')
        namespace['question'] = self.definition.questions[code]

        handler = self.get_handler('/ui/abakuc/exam/edit_question.xml')
        return stl(handler, namespace)


    edit_question__access__ = 'is_training_manager'
    def edit_question(self, context):
        # Get form values
        old_code = context.get_form_value('old_code')
        new_code = context.get_form_value('new_code').strip()
        title = context.get_form_value('title')
        options = context.get_form_value('options')
        correct_options = context.get_form_value('correct_options', '')
        answer = context.get_form_value('answer', '')
        # Decode values
        title = unicode(title, 'utf-8')
        answer = unicode(answer, 'utf-8')
        options = [ x.strip() for x in unicode(options, 'utf-8').splitlines() ]
        options = [ x for x in options if x ]
        correct_options = correct_options.split()

        # Get the definition
        definition = self.definition
        definition.set_changed()
        # Modify the question
        question = definition.questions.pop(old_code)
        question.code = new_code
        question.title = title
        question.options = options
        question.correct_options = correct_options
        question.answer = answer
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
        for pname in ['abakuc:exam_time', 'abakuc:questions_nums',
                      'abakuc:pass_marks_percentage']:
            namespace[pname] = self.get_property(pname)

        # Business functions
        namespace['abakuc:topic'] = BusinessFunction.get_options()
        namespace['abakuc:topic'].insert(0, {'id': 'all',
                                                   'label': 'All'})
        business_functions = self.definition.business_functions
        for x in namespace['abakuc:topic']:
            x['selected'] = x['id'] in business_functions

        handler = self.get_handler('/ui/abakuc/exam/edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_training_manager'
    def edit_metadata(self, context):
        # The title
        self.set_property('dc:title', context.get_form_value('dc:title'),
                          language='en')
        # The other metadata
        for key in ['abakuc:exam_time', 'abakuc:questions_nums',
                    'abakuc:pass_marks_percentage']:
             self.set_property(key, context.get_form_value(key))
        # Business functions
        business_functions = context.get_form_values('topic')
        self.set_property('abakuc:topic', tuple(business_functions))
        self.definition.business_functions = business_functions

        self.definition.set_changed()
        return context.come_back(u'Metadata changed.')


    #########################################################################
    # Add
    add_question_form__access__ = 'is_training_manager'
    add_question_form__label__ = u'Add question'
    def add_question_form(self, context):
        handler = self.get_handler('/ui/abakuc/exam/add_question.xml')
        return stl(handler)


    add_question__access__ = 'is_training_manager'
    add_question__label__ = u'view'
    def add_question(self, context):
        code =  context.get_form_value('code')
        type =  context.get_form_value('type')
        title =  context.get_form_value('title')
        options =  context.get_form_value('options')
        correct_options =  context.get_form_values('correct_options')
        answer =  context.get_form_value('answer', '')

        # Build the question
        title = unicode(title, 'utf-8')
        options = unicode(options, 'utf-8')
        options = [ x.replace('&', '&amp;') for x in options.splitlines() if x ]
        answer = unicode(answer, 'utf-8')
        answer = answer.replace('&', '&amp;')
        question = Question(code, type, title, correct_options, answer, options)

        # Add the question
        definition = self.definition
        definition.set_changed()
        definition.questions[code] = question

        return context.come_back(u'Question added.', goto=';edit')


    #########################################################################
    # Take Exam
    take_exam_form__access__ = 'is_allowed_to_take_exam'
    take_exam_form__label__ = u'Take exam'
    def take_exam_form(self, context):
        user = context.user
        # Build the namespace
        namespace = {}
        namespace['user'] = user
        # Questions
        no_questions = self.get_property('abakuc:questions_nums')
        questions = self.definition.questions
        if len(questions) > no_questions:
            question_keys = random.sample(questions.keys(), no_questions)
        else:
            question_keys = questions.keys()
        question_keys.sort()
        namespace['questions'] = [ questions[x] for x in question_keys ]
        # Metadata
        namespace['title'] = self.get_property('dc:title')
        namespace['pass_mark'] = self.get_property('abakuc:pass_marks_percentage')
        namespace['exam_time'] = self.get_property('abakuc:exam_time')
        namespace['user_attempts'] = self.results.get_n_attempts(user.name) + 1
        namespace['questions_nums'] = no_questions

        handler = self.get_handler('/ui/abakuc/exam/take_exam_form.xml')
        data = stl(handler, namespace)
        # Start timer
        context.set_cookie('exam_time', time())
        # Send data
        return data

    take_exam__access__ = 'is_allowed_to_take_exam'
    def take_exam(self, context):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        user = context.user
        questions = context.get_form_values('questions')
        time_submit = context.get_cookie('exam_time')

        if not time_submit:
            message = u'Cookies are corrupted, time taken not saved.'
            time_taken = 60
        else:
            message = ''
            seconds = time() - float(time_submit)
            time_taken = int(seconds/60)

        # Score
        username = context.user.name
        attempt = Attempt(username, datetime.now(), time_taken)
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
        # Points
        current_points = self.get_points(user.name)
        # Get user's old points
        existing_points = user.get_property('abakuc:points')
        # Set user's points
        points = str(existing_points + current_points)
        user.set_property('abakuc:points', points)
        # Redirect to the results page
        return context.come_back(message, ';result')


    result__access__ = 'is_allowed_to_view'
    def result(self, context):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        user = context.user

        last_attempt = self.results.get_last_attempt(user.name)
        # Build the namespace
        namespace = {}
        namespace['user'] = user
        # Questions
        question_keys = last_attempt.questions.keys()
        question_keys.sort()
        questions = []
        for key in question_keys:
            values = last_attempt.questions[key]
            question = self.definition.questions.get(key)
            if question is not None:
                question_ns = {}
                question_ns['code'] = question.code
                question_ns['title'] = question.title
                question_ns['input_type'] = question.input_type
                correct_options = question.correct_options
                if isinstance(correct_options, str):
                    correct_options = correct_options.split(',')
                correct_options = [ int(x) for x in correct_options ]
                question_ns['is_correct'] = set(values) == set(correct_options)
                question_ns['answer'] = question.answer
                # Options
                options = []
                for i, option in enumerate(question.options):
                    options.append({'value': option,
                                    'is_checked': (i + 1) in values})
                if question.is_mcq():
                    options.append({'value': "Don't know",
                                    'is_checked': 43 in values})
                question_ns['options'] = options
                questions.append(question_ns)
        namespace['questions'] = questions
        # Metadata
        namespace['title'] = self.get_property('dc:title')
        namespace['exam_time'] = self.get_property('abakuc:exam_time')
        namespace['pass_mark'] = self.get_property('abakuc:pass_marks_percentage')
        n_attempts = self.results.get_n_attempts(user.name)
        namespace['user_attempts'] = n_attempts
        namespace['time_taken'] = last_attempt.time_taken
        namespace['score'] = str(self.get_score(user.name))
        namespace['current_points'] = self.get_points(user.name)
        namespace['questions_nums'] = self.get_property('abakuc:questions_nums')
        namespace['profile_url'] = user.get_profile_url(self)
        namespace['user'] = user.get_title()
        pp.pprint(namespace['user'])
        namespace['try_again_url'] = ';take_exam_form'
        passed = self.get_result(user.name)[0]
        # Display points
        namespace['points'] = user.get_property('abakuc:points')
        namespace['next_module_url'] = None
        if passed:
            program = self.get_program()
            modules = program.get_modules()
            my_module = self.get_module()
            my_module_index = modules.index(my_module)
            next_module_index = my_module_index + 1
            if next_module_index < len(modules):
                next_module = modules[next_module_index]
                next_module_url = str(self.get_pathto(next_module))
                next_module_url += '/;view'
                namespace['next_module_url'] = next_module_url
                namespace['finnished'] = None 
            else:
                namespace['next_module_url'] = user.get_profile_url(self)
                namespace['finnished'] = user.get_profile_url(self)

        handler = self.get_handler('/ui/abakuc/exam/take_exam.xml')
        return stl(handler, namespace)


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
                score = int(attempt.get_score())
                n_attempts = int(self.get_result(userid)[1])
                points = int(self.get_points(userid))
                date = attempt.date.isoformat()
                url = self.get_pathto(users).resolve2(userid)
                id = ('%s##%s##%s##%s##%s##%s' % (self.abspath, userid,
                      score, n_attempts, date, points))
                url = '%s/;view' % url
                username = user.get_property('ikaaro:username')
                #username = (firstname+lastname or '').title()
                rows.append({
                    'checkbox': True,
                    'id': id,
                    'username': (username, url),
                    'score': score,
                    'module': self.get_property('dc:title'),
                    'date': date,
                    'checked': (score == 0 and 'checked' or '')})
        # Sort
        sortby = context.get_form_values('sortby', default=['score'])
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
                   ('score', u'Score'),
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
            abspath, name, score, n_attempts, date, points = id.split('##')
            #exam = root.get_handler(abspath)
            self.results.remove_attempt(name, date)
            score = int(score)
            n_attempts = int(n_attempts)
            points = int(points)
            # Update the users points
            user = get_user(name)
            existing_points = user.get_property('abakuc:points')
            # Get the exam points based on score
            if score > 90.0:
                if n_attempts == 1:
                    score += 20
                    new_points = existing_points - score
                else:
                    new_points = existing_points - points
            else:
                new_points = existing_points - score
            user.set_property('abakuc:points', new_points)

        return context.come_back(u'Attempt/s removed.')



register_object_class(Exam)
