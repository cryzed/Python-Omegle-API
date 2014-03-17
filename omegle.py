import re
import json
import math
import time
import random
import urllib
import threading
import mechanize
from httplib import BadStatusLine


RANDID_SELECTION = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
SERVER_LIST = ['front1.omegle.com', 'front2.omegle.com', 'front3.omegle.com',
               'front4.omegle.com', 'front5.omegle.com', 'front6.omegle.com',
               'front7.omegle.com', 'front8.omegle.com', 'front9.omegle.com']
RECAPTCHA_CHALLENGE_URL = 'http://www.google.com/recaptcha/api/challenge?k=%s'
RECAPTCHA_IMAGE_URL = 'http://www.google.com/recaptcha/api/image?c=%s'
recaptcha_challenge_regex = re.compile(r"challenge\s*:\s*'(.+)'")


def nocache():
    return '%r' % random.random()


def randid():
    randid = ''
    for _ in range(0, 8):
        c = int(math.floor(32 * random.random()))
        randid += RANDID_SELECTION[c]
    return randid


# This EventThread allows us to actively stop the thread from running, by
# setting the self._stop event-flag.
class EventThread(threading.Thread):

    def __init__(self, instance, start_url):
        threading.Thread.__init__(self)
        self.instance = instance
        self.start_url = start_url
        self._stop = threading.Event()

    def run(self):
        response = self.instance.browser.open(self.start_url)
        data = json.load(response)
        self.instance.client_id = data['clientID']
        self.instance._handle_events(data['events'])

        while not self.instance.connected:
            self.instance.event()
            if self._stop.isSet():
                self.instance.disconnect()
                return
            time.sleep(self.instance.event_delay)

        while self.instance.connected:
            self.instance.event()
            if self._stop.isSet():
                self.instance.disconnect()
                return
            time.sleep(self.instance.event_delay)

    def stop(self):
        self._stop.set()


class Client(object):
    STATUS_URL = 'http://%s/status?nocache=%s&randid=%s'
    START_URL = 'http://%s/start?rcs=%s&firstevents=%s&spid=%s&randid=%s&lang=%s'
    RECAPTCHA_URL = 'http://%s/recaptcha'
    EVENTS_URL = 'http://%s/events'
    TYPING_URL = 'http://%s/typing'
    STOPPED_TYPING_URL = 'http://%s/stoppedtyping'
    DISCONNECT_URL = 'http://%s/disconnect'
    SEND_URL = 'http://%s/send'

    def __init__(self, rcs=1, firstevents=1, spid='', random_id=None, topics=[], lang='en', event_delay=3):
        self.rcs = rcs
        self.firstevents = firstevents
        self.spid = spid
        self.random_id = random_id or randid()
        self.topics = topics
        self.lang = lang
        self.event_delay = event_delay

        self.server = random.choice(SERVER_LIST)
        self.client_id = None
        self.connected = False
        self.browser = mechanize.Browser()
        self.browser.addheaders = []
        self.event_handlers = {
            'waiting': self.handle_waiting,
            'connected': self.handle_connected,
            'recaptchaRequired': self.handle_recaptcha_required,
            'recaptchaRejected': self.handle_recaptcha_required,
            'commonLikes': self.handle_common_likes,
            'typing': self.handle_typing,
            'stoppedTyping': self.handle_stopped_typing,
            'gotMessage': self.handle_got_message,
            'strangerDisconnected': self.handle_stranger_disconnected,
            'statusInfo': self.handle_dummy,
            'identDigests': self.handle_dummy
        }

    def register_handler(self, name, handler):
        if name == 'connected':
            self.event_handlers[name] = self._connected_decorator(handler)
        elif name == 'strangerDisconnected':
            self.event_handlers[name] = self._stranger_disconnect_decorator(handler)
        else:
            self.event_handlers[name] = handler

    def _handle_events(self, events):
        for event in events:
            name = event[0]
            if name in self.event_handlers:
                if len(event) > 1:
                    try:
                        self.event_handlers[name](self, *event[1:])
                    except TypeError:
                        print 'DEBUG', name, event, self.event_handlers
                    continue
                self.event_handlers[name](self)
            else:
                print 'Unhandled event: %s' % event

    @staticmethod
    def _connected_decorator(function):
        def decorator(instance):
            instance.connected = True
            function(instance)
        return decorator

    @staticmethod
    def handle_dummy(self, *args):
        pass

    @staticmethod
    def handle_waiting(self):
        print 'Looking for someone you can chat with...'

    @staticmethod
    def _stranger_disconnect_decorator(function):
        def decorator(instance):
            instance.connected = False
            return function(instance)
        return decorator

    @staticmethod
    def handle_connected(self):
        print "You're now chatting with a random stranger. Say hi!"

    @staticmethod
    def handle_recaptcha_required(self, challenge):
        url = RECAPTCHA_CHALLENGE_URL % challenge
        source = self.browser.open(url).read()
        challenge = recaptcha_challenge_regex.search(source).groups()[0]
        url = RECAPTCHA_IMAGE_URL % challenge
        print 'Recaptcha required: %s' % url
        response = raw_input('Response: ')
        self.recaptcha(challenge, response)

    @staticmethod
    def handle_common_likes(self, likes):
        print 'You both like %s.' % ', '.join(likes)

    @staticmethod
    def handle_typing(self):
        print 'Stranger is typing...'

    @staticmethod
    def handle_stopped_typing(self):
        print 'Stranger has stopped typing.'

    @staticmethod
    def handle_got_message(self, message):
        print 'Stranger: %s' % message

    @staticmethod
    def handle_stranger_disconnected(self):
        print 'Stranger has disconnected.'

    def status(self):
        server = random.choice(SERVER_LIST)
        url = self.STATUS_URL % (server, nocache(), self.random_id)
        response = self.browser.open(url)
        data = json.load(response)
        return data

    def start(self):
        url = self.START_URL % (self.server, self.rcs, self.firstevents,
                                self.spid, self.random_id, self.lang)
        if self.topics:
            parameter = urllib.urlencode({'topics': json.dumps(self.topics)})
            url += '&' + parameter

        thread = EventThread(self, url)
        thread.start()
        return thread

    def recaptcha(self, challenge, response):
        url = self.RECAPTCHA_URL % self.server
        data = {'id': self.client_id, 'challenge':
                challenge, 'response': response}
        try:
            self.browser.open(url, urllib.urlencode(data))
        except BadStatusLine:
            return

    def event(self):
        url = self.EVENTS_URL % self.server
        data = {'id': self.client_id}
        try:
            response = self.browser.open(url, urllib.urlencode(data))
            data = json.load(response)
        except Exception:
            return
        if data:
            self._handle_events(data)

    def typing(self):
        url = self.TYPING_URL % self.server
        data = {'id': self.client_id}
        try:
            self.browser.open(url, urllib.urlencode(data))
        except BadStatusLine:
            return

    def stopped_typing(self):
        url = self.STOPPED_TYPING_URL % self.server
        data = {'id': self.client_id}
        try:
            self.browser.open(url, urllib.urlencode(data))
        except BadStatusLine:
            return

    def send(self, message):
        url = self.SEND_URL % self.server
        data = {'msg': message, 'id': self.client_id}
        try:
            self.browser.open(url, urllib.urlencode(data))
        except BadStatusLine:
            return

    def disconnect(self):
        self.connected = False
        url = self.DISCONNECT_URL % self.server
        data = {'id': self.client_id}
        try:
            self.browser.open(url, urllib.urlencode(data))
        except BadStatusLine:
            return

