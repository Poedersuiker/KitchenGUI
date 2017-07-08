from google.cloud import pubsub
from google.cloud.pubsub.subscription import AutoAck
from threading import Thread
import json
import logging


class PubSubConnector(Thread):
    def __init__(self, project, topic_name, subscription_name, action):
        Thread.__init__(self)
        self.running = True
        self.action = action
        self.project = project
        self.topic_name = topic_name

        self.pubsub_client = pubsub.Client(self.project)
        self.topic = self.pubsub_client.topic(self.topic_name)
        self.subscription = self.topic.subscription(subscription_name)

    def run(self):
        while self.running:
            with AutoAck(self.subscription, max_messages=10) as ack:
                for ack_id, message in list(ack.items()):
                    try:
                        data = json.loads(message.data.decode('utf8').replace("'", '"'))
                        self.action(data)
                    except Exception:
                        del ack[ack_id]

    def stop(self):
        self.running = False


class SmartHomeCommands:
    def __init__(self, chatbox):
        logging.info('Started SmartHome pubsub connection')
        self.chatbox = chatbox
        self.pubsub_connection = PubSubConnector('smarthome-ff453', 'commands', 'commands', self.action)

    def action(self, message):
        logging.info('PubSub received: {0}'.format(message['id']))
        self.chatbox.send_msg(message['result']['resolvedQuery'])
        self.chatbox.receive_msg('Operator', message['result']['fulfillment']['speech'])

        if message['result']['action'] == 'web.search':
            for fulfillment_message in message['result']['fulfillment']['messages']:
                if fulfillment_message['type'] == 4 and 'websearch' in fulfillment_message['payload']:
                    print(fulfillment_message['payload']['websearch'])
        else:
            print('New Action')
            print(message['result']['action'])

        return True


def print_action(message):
    if message['result']['action'] == 'web.search':
        for fulfillment_message in message['result']['fulfillment']['messages']:
            if fulfillment_message['type'] == 4 and 'websearch' in fulfillment_message['payload']:
                print(fulfillment_message['payload']['websearch'])
    else:
        print('New Action')
        print(message['result']['action'])

    return True

if __name__ == '__main__':
    ps = PubSubConnector('smarthome-ff453', 'commands', 'commands', print_action)
    ps.start()
