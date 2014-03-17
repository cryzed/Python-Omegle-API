import omegle
#from omegle import RECAPTCHA_CHALLENGE_URL, RECAPTCHA_IMAGE_URL, recaptcha_challenge_regex

#import deathbycaptcha


#DEATH_BY_CAPTCHA_USERNAME = ''
#DEATH_BY_CAPTCHA_PASSWORD = ''
#death_by_captcha_client = deathbycaptcha.SocketClient(DEATH_BY_CAPTCHA_USERNAME, DEATH_BY_CAPTCHA_PASSWORD)


def get_handle_waiting(name, other_client):
    def handle_waiting(client):
        print '[%s] Looking for someone you can chat with...' % name
    return 'waiting', handle_waiting


def get_handle_connected(name, other_client):
    def handle_connected(client):
        print "[%s] You're now chatting with a random stranger. Say hi!" % name
    return 'connected', handle_connected


def get_handle_common_likes(name, other_client):
    def handle_common_likes(client, likes):
        print '[%s] You both like %s.' % (name, ', '.join(likes))
    return 'commonLikes', handle_common_likes


def get_handle_typing(name, other_client):
    def handle_typing(client):
        # print '[%s] Stranger is typing...' % name
        other_client.typing()
    return 'typing', handle_typing


def get_handle_stopped_typing(name, other_client):
    def handle_stopped_typing(client):
        # print '[%s] Stranger has stopped typing.' % name
        other_client.stopped_typing()
    return 'stoppedTyping', handle_stopped_typing


def get_handle_got_message(name, other_client):
    def handle_got_message(client, message):
        print '[%s] Stranger: %s' % (name, message)
        for _ in range(3):
            try:
                other_client.send(message.encode('utf-8'))
                break
            except Exception:
                pass
    return 'gotMessage', handle_got_message


def get_handle_stranger_disconnected(name, other_client):
    def handle_stranger_disconnected(client):
        print '[%s] Stranger has disconnected.' % name
        client.disconnect()
        other_client.disconnect()
    return 'strangerDisconnected', handle_stranger_disconnected


#def get_handle_recaptcha_required(name, other_client):
#    def handle_recaptcha_required(client, challenge):
#        print 'Decoding Captcha...',
#        url = RECAPTCHA_CHALLENGE_URL % challenge
#        source = client.browser.open(url).read()
#        challenge = recaptcha_challenge_regex.search(source).groups()[0]
#        url = RECAPTCHA_IMAGE_URL % challenge
#        _, path = tempfile.mkstemp()
#        client.browser.retrieve(url, path)
#        captcha = death_by_captcha_client.decode(path)
#        client.recaptcha(challenge, captcha['text'])
#        print ' done.'
#    return 'recaptchaRequired', handle_recaptcha_required


#def get_handle_recaptcha_rejected(name, other_client):
#    def handle_recaptcha_rejected(client, challenge):
#        print '[%s] Decoding Captcha...',
#        url = RECAPTCHA_CHALLENGE_URL % challenge
#        source = client.browser.open(url).read()
#        challenge = recaptcha_challenge_regex.search(source).groups()[0]
#        url = RECAPTCHA_IMAGE_URL % challenge
#        _, path = tempfile.mkstemp()
#        client.browser.retrieve(url, path)
#        captcha = death_by_captcha_client.decode(path)
#        client.recaptcha(challenge, captcha['text'])
#        print ' done.'
#    return 'recaptchaRejected', handle_recaptcha_rejected


def main():
    client1 = omegle.Client(event_delay=1)
    client2 = omegle.Client(event_delay=1)
    handlers = [get_handle_waiting, get_handle_connected, get_handle_common_likes,
                get_handle_typing, get_handle_stopped_typing, get_handle_got_message,
                get_handle_stranger_disconnected]

    for handler in handlers:
        name, function = handler('Stranger 1', client2)
        client1.register_handler(name, function)
        name, function = handler('Stranger 2', client1)
        client2.register_handler(name, function)

    thread1 = client1.start()
    thread2 = client2.start()

    while thread1.isAlive() or thread2.isAlive():
        try:
            thread1.join(0.1)
            thread2.join(0.1)
        except KeyboardInterrupt:
            break

    print 'Disconnecting... ',
    thread1.stop()
    thread2.stop()


if __name__ == '__main__':
    main()
