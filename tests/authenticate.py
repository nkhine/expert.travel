# This is the test script to test the expert.travel application
# 
######################  INSTALL  ################################
# # [1] install python2.4-setuptools
# $ sudo apt-get install python2.4-setuptools
# 
# # [2] install twill 
# $ wget http://darcs.idyll.org/~t/projects/twill-latest.tar.gz
# $ tar -xzvf twill-latest.tar.gz
# $ cd twill-latest/
# $ sudo python setup.py build install
# 
# # [3] run this script with twill 
# $ python twill_test.py --debug 
# 
# # [4] references
# Twill - http://www.idyll.org/~t/www-tools/twill/
###################################################################

# Import from the Standard Library
from StringIO import StringIO
from re import compile
from sys import argv
from datetime import datetime

# Import from twill
import twill
from twill import get_browser
from twill.namespaces import new_local_dict as ldict
from twill.commands import show, showforms, showlinks, showhistory
from twill.commands import go, submit, follow
from twill.commands import find, notfind
from twill.commands import formvalue, formclear, fv, formfile

mute = False
if argv[-1] != '--debug':
    twill.set_output(StringIO())
    if argv[-1] != '--info':
        mute = True

b = twill.get_browser()
agent = b.set_agent_string('Mozilla/4.0 (compatible; MSIE 5.0; Windows NT 5.1)')
ld = twill.namespaces.new_local_dict()

# Input form for test
print '1  :  .expert_travel'
print '2  :  .expert_travel'
print '3  :  .expert.travel'
print 'Enter: localhost:8080'
machine = raw_input('default (localhost) or choose from above list: ') or '1'
if machine == '1':
    machine = '.expert_travel'
elif machine == '2':
    machine = '.expert.travel'
elif machine == '3':
    machine = '.expert.travel'
else:
    machine = 'localhost:8080'

sep2()
print 'Select site you want to test'
sep2()
print '2  :  uk%s' % machine
print '3  :  fr%s' % machine
print '4  :  us%s' % machine
sep2()
root_url = raw_input('default (http://localhost:8080) or choose from above list:') or 'http://%s.expert.travel' % machine
if root_url == '1':
    root_url = 'http://%s' % machine
elif root_url == '2':
    root_url = 'http://uk%s' % machine
elif root_url == '3':
    root_url = 'http://fr%s' % machine
elif root_url == '4':
    root_url = 'http://us%s' % machine
else:
    root_url = 'http://localhost:8080'

#######################################################################
# API
#######################################################################

def qprint(cond, text_failed='FAIL'):
    print (cond) and '.' or '\n[ERROR] %s\n ' % text_failed, 

def com(cond):
    if not mute:
        print '\n%s' % cond

def sep():
    if not mute:
        print '\n', 60*'#'
def sep2():
    if not mute:
        print '\n', 50*'*'


def authentication(name=None, passwd=None):
    b.go('%s' % root_url)

    # Check if another user is logged in on this client
    link = b.find_link(compile(';login_form'))
    if not link:
        logout()

    com('Authentication')
    b.go('%s/;login_form' % root_url)
    username = raw_input('username : ') or name
    password = raw_input('password : ') or passwd
    fv('loginform', 'username', username)
    fv('loginform', 'password', password)
    b.submit('0')
    b.get_url()
    sep()

def logout():
    com('Log out')
    b.go('%s/;logout' % root_url)
    
def follow_to_url(url, libelle=None):
    com('Go to %s' % libelle or url)
    follow(url)

def my_find(regexp):
    find(regexp)
    qprint(True)

def my_notfind(regexp):
    notfind(regexp)
    qprint(True)

def state_publish():
    follow_to_url(';state_form')
    fv('1', 'transition', 'publish')
    fv('1', 'comments', object_comment)
    b.submit('0')
    my_find("Transition done.")
    my_find("Public.")

def no_publish():
    try:
        state_publish()
    except Exception, e:
        if str(e) == 'no field matches "transition"':
            return True
        if str(e) == 'cannot find value/label "publish" in list control':
            return True
        raise

    return True


def state_request():
    follow_to_url(';state_form')
    fv('1', 'transition', 'request')
    fv('1', 'comments', object_comment)
    b.submit('0')
    my_find("Transition done.")
    my_find("Pending")


def state_unrequest():
    follow_to_url(';state_form')
    fv('1', 'transition', 'unrequest')
    fv('1', 'comments', object_comment)
    b.submit('0')
    my_find("Transition done.")
    my_find("Private")


def state_retire():
    follow_to_url(';state_form')
    fv('1', 'transition', 'retire')
    fv('1', 'comments', object_comment)
    b.submit('0')
    my_find("Transition done.")
    my_find("Private")

def remove_element(url, name):
    """
    Remove the element.
    XXX Problem if trying to remove last item of url.
    """
    # Go to url's browse list
    b.go('%s/;browse_list' % url)
    # Remove element
    com('Remove %s object' % name)
    link1 = b.find_link(compile('%s/;browse_list' % name))
    link2 = b.find_link(compile('%s/;view' % name))
    qprint(link1 or link2)
    if link1:
        if link1.url == '%s/;browse_list' % name:
            fv('2', 'ids:list', name)
            b.submit(';remove')
            com('[info] %s object now removed!' % name)
    elif link2:
        if link2.url == '%s/;view' % name:
            fv('2', 'ids:list', name)
            b.submit(';remove')
            com('[info] %s object now removed!' % name)
    sep()


def main(username=None, password=None):
    """
      Tests begin 
    """
    sep()
    print '\n ### [TESTS BEGUN] ###'
    dtstart = datetime.now()

    # Authentification
    authentication(username, password)

    # Test view access to the section
    duration = datetime.now() - dtstart
    print ('\n ### [TESTS FINISHED in %s] ###' % duration)

main('norman@khine.net', 'a')
