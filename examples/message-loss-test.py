import random
import string
import omegle
import threading

last_message = None
connecting_mutex = threading.Semaphore()


def generate_random_string(length, alphabet='0123456789' + string.ascii_letters):
    result = ''
    for _ in range(length):
        result += random.choice(alphabet)
    return result


def get_handle_gotMessage(sender):
    def handle_gotMessage(client, message):
        global last_message

        print 'Received:', message
        if message != last_message:
            print 'Expected %s, Received: %s' % (last_message, message)

        message = generate_random_string(random.randint(8, 256))
        last_message = message

        print 'Sending:', message
        sender.send(message)
        sender.typing()
    return handle_gotMessage


def handle_commonLikes(client, likes):
    print 'Successfully connected with UID', likes[0]
    connecting_mutex.release()


def main():
    global last_message

    uid = generate_random_string(8)
    sender = omegle.Client(topics=[uid])
    receiver = omegle.Client(event_delay=1, topics=[uid])
    receiver.register_handler('gotMessage', get_handle_gotMessage(sender))
    receiver.register_handler('commonLikes', handle_commonLikes)

    connecting_mutex.acquire()
    sender.start()
    receiver.start()

    message = generate_random_string(32)
    last_message = message

    # Just wait until the mutex is released in the handle_commonLikes callback
    connecting_mutex.acquire()
    print 'Sending:', message
    sender.send(message)
    sender.typing()


if __name__ == '__main__':
    main()
