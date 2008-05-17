# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Norman Khine <norman@abakuc.com>

# Import from itools
from itools.datatypes import Decimal, Integer, String
from itools.web import get_context
from itools.csv import CSV
from itools.stl import stl
from itools.cms.binary import Flash
from itools.cms.html import XHTMLFile
from itools.cms.folder import Folder

# Import from TravelUni
from exam import Attempt


class Results(CSV):

    columns = ['user_id', 'n_attempts', 'time_spent', 'mark']
    schema = {
        'user_id': String(index='keyword'),
        'n_attempts': Integer,
        'time_spent': Integer,
        'mark': Decimal,
    }

    def new(self, **kw):
        CSV.new(self, **kw)
        self.results = {}


    def add_result(self, user_id, n_attempts, time, mark):
        user_id = str(user_id)
        n_attempts = int(n_attempts)
        time = int(time)
        mark = Decimal.decode(mark)

        self.set_changed()
        self.add_row([user_id, n_attempts, time, mark])


    def get_result(self, user_id):
        results = self.search(user_id=user_id)
        if results:
            return self.get_row(results[-1])
        return None


    def get_n_attempts(self, user_id):
        results = self.search(user_id=user_id)
        if results:
            return results[-1].get_value('n_attempts')
        return 0



class Game(Folder):

    class_id = 'Game'
    class_layout = {
        '.results': Results}
    class_title = u'Game'
    class_icon48 = 'traveluni/images/Game48.png'
    class_icon16 = 'traveluni/images/Game16.png'
    class_description = 'a Game with flash'
    class_views = [['preview'],
                   ['browse_content?mode=thumbnails'],
                   ['edit_metadata_form']]


    __fixed_handlers__ = ['flash.swf', 'instructions']


    def get_results(self):
        return self.get_handler('.results')

    results = property(get_results, None, None, '')


    def new(self):
        Folder.new(self)
        self.cache['.results'] = Results()
        flash = Flash()
        self.cache['flash.swf'] = flash
        self.cache['flash.swf.metadata'] = flash.build_metadata()
        instructions = XHTMLFile()
        self.cache['instructions'] = instructions
        self.cache['instructions.metadata'] = instructions.build_metadata()


    def get_result(self, username=None):
        if username is None:
            context = get_context()
            user = context.user
            username = user.name

        game_time = self.get_property('game:game_time') or '1000'
        attempts_allowed = self.get_property('game:attempts_num') or '1000'

        result = self.results.get_result(username)
        if result is None:
            return False, False, True, 0, attempts_allowed, 0, 0

        kk, n_attempts, time_taken, score = result
        lost = attempts_allowed < n_attempts
        passed = (not lost) and game_time >= time_taken
        play_again = (not lost) and (not passed)

        return (passed, lost, play_again, n_attempts, attempts_allowed,
                time_taken, score)


    #########################################################################
    # User Interface
    #########################################################################
    def get_flash_url(self):
        flash = self.search_handlers(format='application/x-shockwave-flash')
        flash = list(flash)
        if flash:
            flash = flash[0]
            return self.get_pathto(flash)
        return None


    preview__access__ = 'is_allowed_to_view'
    preview__label__ = u'Preview'
    def preview(self, context):
        namespace = {}
        # Game properties
        for pname in ['dc:title', 'dc:description', 'game:game_time',
                      'game:attempts_num']:
            namespace[pname] = self.get_property(pname)

        # Get instructions data if filled
        try:
            instructions = self.get_handler('instructions')
        except LookupError:
            namespace['dc:description'] = ''
        else:
            if instructions.to_text() != '':
                namespace['dc:description'] = instructions.to_str()

        # Find the flash resource
        flash = self.search_handlers(format='application/x-shockwave-flash')
        flash = list(flash)
        if flash:
            flash = flash[0]
            namespace['flash_url'] = str(self.get_pathto(flash))
        else:
            namespace['flash_url'] = ''

        handler = self.get_handler('/ui/traveluni/Game_preview.xml')
        return stl(handler, namespace)


    play__access__ = 'is_allowed_to_view'
    play__label__ = u'Play Game'
    def play(self, context):
        context.response.set_header('Content-Type', 'text/html; charset=UTF-8')

        namespace = {}
        namespace['title'] = self.title
        namespace['game_url'] =  self.get_flash_url()
        namespace['action'] = context.uri.resolve(';catch_result')

        handler = self.get_handler('/ui/traveluni/Game_play.xhtml')
        return stl(handler, namespace)


    catch_result__access__ = 'is_allowed_to_view'
    def catch_result(self, context):
        time_taken = context.get_form_value('time_taken')
        if not time_taken:
            time1 = context.get_form_value('temp1') or 100
            time2 = context.get_form_value('temp2') or 100
            time3 = context.get_form_value('temp3') or 100
            # Thaismile game: check 40/10/20
            time_taken = 1000
            if time1 < 40 and time2 < 10 and time3 < 20:
                time_taken = time1 + time2 + time3

        if time_taken is not None:
            username = context.user.name
            n_attempts = self.results.get_n_attempts(username)
            n_attempts += 1
            score = 0
            time_taken = int(time_taken)
            if time_taken <= (self.get_property('game:game_time') or '1000'):
                score = 50
            elif time_taken <= 90:
                score = 10

            self.results.set_changed()
            self.results.add_result(username, n_attempts, time_taken, score)


    def get_subviews(self, name):
        if name == 'upload_file_form':
            return []
        return Folder.get_subviews(self, name)


    #########################################################################
    # Metadata
    edit_metadata_form__access__ = 'is_allowed_to_edit'
    edit_metadata_form__label__ = u'Game metadata'
    def edit_metadata_form(self, context):
        # Build the namespace
        namespace = {}
        # Title
        namespace['dc:title'] = self.get_property('dc:title', language='en')
        # Bangkok airways game has no limits
        if 'thaismile' in str(context.uri) or 'thailand' in str(context.uri):
            namespace['game_time'] = namespace['attempts_nums'] = None
        else:
            namespace['game_time'] = self.get_property('game:game_time')
            attempts_num = self.get_property('game:attempts_num')
            namespace['attempts_num'] = attempts_num
            namespace['attempts_nums'] = [ {'name': str(x), 'value': str(x),
                                            'selected': x == attempts_num}
                                           for x in range(2, 6) ]

        handler = self.get_handler('/ui/traveluni/Game_edit_metadata.xml')
        return stl(handler, namespace)


    edit_metadata__access__ = 'is_allowed_to_edit'
    def edit_metadata(self, context):
        # The title
        self.set_property('dc:title', context.get_form_value('dc:title'),
                          language='en')
        if 'thaismile' in str(context.uri) or 'thailand' in str(context.uri):
            for key in ['game:game_time', 'game:attempts_num']:
                self.set_property(key, None)
            self.get_handler('flash.swf').set_workflow_state('public')
            self.get_handler('instructions').set_workflow_state('public')
        else:
            for key in ['game:game_time', 'game:attempts_num']:
                self.set_property(key, context.get_form_value(key))

        return context.come_back(u'Metadata changed.')

