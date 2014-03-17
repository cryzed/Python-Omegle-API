import time
import textwrap

import irc.client

import omegle


class OmegleBot(irc.client.IRC):

    def __init__(self, message_part_delay=1, max_message_length=361, max_retries=3, reconnect_delay=30, reacquire_nickname_delay=30, omegle_topic_delay=30):
        irc.client.IRC.__init__(self)
        self.message_part_delay = message_part_delay
        self.max_message_length = max_message_length
        self.max_retries = max_retries
        self.reconnect_delay = reconnect_delay
        self.reacquire_nickname_delay = reacquire_nickname_delay
        self.omegle_topic_delay = omegle_topic_delay

        self.original_nickname = None
        self.channels = []
        self.connection = self.server()
        self.connection.buffer_class.errors = 'replace'

        self.omegle_client = omegle.Client(event_delay=2)
        self.omegle_target = None
        self.omegle_is_typing = False
        self.omegle_client_active = False

        self.omegle_client.register_handler('waiting', self.handle_omegle_waiting)
        self.omegle_client.register_handler('connected', self.handle_omegle_connected)
        self.omegle_client.register_handler('commonLikes', self.handle_omegle_common_likes)
        self.omegle_client.register_handler('typing', self.handle_omegle_typing)
        self.omegle_client.register_handler('stoppedTyping', self.handle_omegle_stopped_typing)
        self.omegle_client.register_handler('gotMessage', self.handle_omegle_got_message)
        self.omegle_client.register_handler('strangerDisconnected', self.handle_omegle_stranger_disconnected)

        self.add_global_handler('welcome', self.handle_welcome)
        self.add_global_handler('nicknameinuse', self.handle_nicknameinuse)
        self.add_global_handler('pubmsg', self.handle_pubmsg)
        self.add_global_handler('disconnect', self.handle_disconnect)

    def connect(self, address, port, nickname, channels=[]):
        self.original_nickname = nickname
        self.channels = channels
        self.connection.connect(address, port, nickname)
        self.process_forever()

    def handle_welcome(self, connection, event):
        for channel in self.channels:
            connection.join(channel)

    def handle_pubmsg(self, connection, event):
        message = event.arguments[0]
        nickname = connection.get_nickname()

        command = None
        tokens = message.split()
        if tokens:
            command = tokens[0]

        if command == '!omegle':
            if self.omegle_client_active:
                return
            topics = [topic.strip() for topic in message.encode('utf-8', 'ignore')[7:].split(',') if topic.strip()]
            self.omegle_client.topics = topics
            self.omegle_client.start()
            self.omegle_client_active = True
            self.omegle_target = event.target

        elif command in ('!d', '!disconnect') and self.omegle_client_active:
            try:
                self.omegle_client.disconnect()
            except:
                pass
            self.omegle_client_active = False
            connection.privmsg(self.omegle_target, 'You have disconnected.')

        elif message.lower().startswith(nickname.lower()):
            message = message[len(nickname) + 1:].strip()
            for _ in range(self.max_retries):
                try:
                    self.omegle_client.send(message.encode('utf-8', 'ignore'))
                    break
                except:
                    time.sleep(self.message_part_delay)

    def handle_disconnect(self, connection, event):
        self.reconnect()

    def reconnect(self):
        if not self.connection.is_connected():
            try:
                self.connection.execute_delayed(self.reconnect_delay, self.reconnect)
                self.connection.reconnect()
            except irc.client.ServerConnectionError:
                pass

    def handle_nicknameinuse(self, connection, event):
        nickname_in_use = event.arguments[0]
        alternative_nickname = nickname_in_use + '_'
        if connection.get_nickname() != alternative_nickname:
            connection.nick(alternative_nickname)
        connection.execute_delayed(self.reacquire_nickname_delay, self.reacquire_nickname)

    def reacquire_nickname(self):
        self.connection.nick(self.original_nickname)

    def handle_omegle_waiting(self, instance):
        self.connection.privmsg(self.omegle_target, 'Looking for someone you can chat with...')

    def handle_omegle_connected(self, instance):
        self.connection.privmsg(self.omegle_target, "You're now chatting with a random stranger. Say hi!")

    def handle_omegle_common_likes(self, instance, likes):
        self.connection.privmsg(self.omegle_target, 'You both like %s.' % ', '.join(likes))

    def handle_omegle_typing(self, instance):
        if not self.omegle_is_typing:
            self.connection.privmsg(self.omegle_target, 'Stranger is typing...')
            self.omegle_is_typing = True

    def handle_omegle_stopped_typing(self, instance):
        self.connection.privmsg(self.omegle_target, 'Stranger has stopped typing.')
        self.omegle_is_typing = False

    def handle_omegle_got_message(self, instance, message):
        message = 'Stranger: ' + message.replace('\n', ' ')
        parts = textwrap.wrap(message, self.max_message_length)

        if len(parts) == 1:
            self.connection.privmsg(self.omegle_target, message)
        else:
            for part in parts:
                self.connection.privmsg(self.omegle_target, part)
                time.sleep(self.message_part_delay)
        self.omegle_is_typing = False

    def handle_omegle_stranger_disconnected(self, instance):
        self.connection.privmsg(self.omegle_target, 'Stranger has disconnected.')
        self.omegle_is_typing = False
        self.omegle_client_active = False


def main():
    bot = OmegleBot()
    try:
        bot.connect('irc.server.net', 6667, 'Omegle IRC Bot', ['#channel'])
    except KeyboardInterrupt:
        bot.omegle_client.disconnect()


if __name__ == '__main__':
    main()
